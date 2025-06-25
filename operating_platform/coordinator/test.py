import draccus
from dataclasses import dataclass, asdict
from pathlib import Path
from pprint import pformat
from deepdiff import DeepDiff
from functools import cache
import traceback
import time
from termcolor import colored
import cv2

from lerobot_lite.robots.configs import RobotConfig
from lerobot_lite.configs import parser
from lerobot_lite.configs.policies import PreTrainedConfig
from lerobot_lite.datasets.lerobot_dataset import *
from lerobot_lite.utils.robot_devices import busy_wait, safe_disconnect
from lerobot_lite.utils.utils import has_method, init_logging, log_say
from lerobot_lite.robots.utils import make_robot_from_config, Robot

from client import RobotClient


robot_client = RobotClient()

@dataclass
class ControlConfig(draccus.ChoiceRegistry):
    pass


@ControlConfig.register_subclass("teleoperate")
@dataclass
class TeleoperateControlConfig(ControlConfig):
    # Limit the maximum frames per second. By default, no limit.
    fps: int | None = None
    teleop_time_s: float | None = None
    # Display all cameras on screen
    display_cameras: bool = True


@ControlConfig.register_subclass("record")
@dataclass
class RecordControlConfig(ControlConfig):
    # Dataset identifier. By convention it should match '{hf_username}/{dataset_name}' (e.g. `lerobot/test`).
    repo_id: str
    # A short but accurate description of the task performed during the recording (e.g. "Pick the Lego block and drop it in the box on the right.")
    single_task: str
    # Root directory where the dataset will be stored (e.g. 'dataset/path').
    root: str | Path | None = None
    policy: PreTrainedConfig | None = None
    # Limit the frames per second. By default, uses the policy fps.
    fps: int = 30
    # Number of seconds before starting data collection. It allows the robot devices to warmup and synchronize.
    warmup_time_s: int | float = 10
    # Number of seconds for data recording for each episode.
    episode_time_s: int | float = 60
    # Number of seconds for resetting the environment after each episode.
    reset_time_s: int | float = 60
    # Number of episodes to record.
    num_episodes: int = 50
    # Encode frames in the dataset into video
    video: bool = True
    # Upload dataset to Hugging Face hub.
    push_to_hub: bool = True
    # Upload on private repository on the Hugging Face hub.
    private: bool = False
    # Add tags to your dataset on the hub.
    tags: list[str] | None = None
    # Number of subprocesses handling the saving of frames as PNG. Set to 0 to use threads only;
    # set to ≥1 to use subprocesses, each using threads to write images. The best number of processes
    # and threads depends on your system. We recommend 4 threads per camera with 0 processes.
    # If fps is unstable, adjust the thread count. If still unstable, try using 1 or more subprocesses.
    num_image_writer_processes: int = 0
    # Number of threads writing the frames as png images on disk, per camera.
    # Too many threads might cause unstable teleoperation fps due to main thread being blocked.
    # Not enough threads might cause low camera fps.
    num_image_writer_threads_per_camera: int = 4
    # Display all cameras on screen
    display_cameras: bool = True
    # Use vocal synthesis to read events.
    play_sounds: bool = True
    # Resume recording on an existing dataset.
    resume: bool = False

    def __post_init__(self):
        # HACK: We parse again the cli args here to get the pretrained path if there was one.
        policy_path = parser.get_path_arg("control.policy")
        if policy_path:
            cli_overrides = parser.get_cli_overrides("control.policy")
            self.policy = PreTrainedConfig.from_pretrained(policy_path, cli_overrides=cli_overrides)
            # self.policy.pretrained_path = policy_path

@dataclass
class ControlPipelineConfig:
    robot: RobotConfig
    control: ControlConfig

    @classmethod
    def __get_path_fields__(cls) -> list[str]:
        """This enables the parser to load config from the policy using `--policy.path=local/dir`"""
        return ["control.policy"]



def sanity_check_dataset_name(repo_id, policy_cfg):
    _, dataset_name = repo_id.split("/")
    # either repo_id doesnt start with "eval_" and there is no policy
    # or repo_id starts with "eval_" and there is a policy

    # Check if dataset_name starts with "eval_" but policy is missing
    if dataset_name.startswith("eval_") and policy_cfg is None:
        raise ValueError(
            f"Your dataset name begins with 'eval_' ({dataset_name}), but no policy is provided ({policy_cfg.type})."
        )

    # Check if dataset_name does not start with "eval_" but policy is provided
    if not dataset_name.startswith("eval_") and policy_cfg is not None:
        raise ValueError(
            f"Your dataset name does not begin with 'eval_' ({dataset_name}), but a policy is provided ({policy_cfg.type})."
        )


def sanity_check_dataset_robot_compatibility(
    dataset: LeRobotDataset, robot: RobotConfig, fps: int, use_videos: bool
) -> None:
    fields = [
        ("robot_type", dataset.meta.robot_type, robot.type),
        ("fps", dataset.fps, fps),
        # ("features", dataset.features, get_features_from_robot(robot, use_videos)),
    ]

    mismatches = []
    for field, dataset_value, present_value in fields:
        diff = DeepDiff(dataset_value, present_value, exclude_regex_paths=[r".*\['info'\]$"])
        if diff:
            mismatches.append(f"{field}: expected {present_value}, got {dataset_value}")

    if mismatches:
        raise ValueError(
            "Dataset metadata compatibility check failed with mismatches:\n" + "\n".join(mismatches)
        )

def log_control_info(robot: Robot, dt_s, episode_index=None, frame_index=None, fps=None):
    log_items = []
    if episode_index is not None:
        log_items.append(f"ep:{episode_index}")
    if frame_index is not None:
        log_items.append(f"frame:{frame_index}")

    def log_dt(shortname, dt_val_s):
        nonlocal log_items, fps
        info_str = f"{shortname}:{dt_val_s * 1000:5.2f} ({1 / dt_val_s:3.1f}hz)"
        if fps is not None:
            actual_fps = 1 / dt_val_s
            if actual_fps < fps - 1:
                info_str = colored(info_str, "yellow")
        log_items.append(info_str)

    # total step time displayed in milliseconds and its frequency
    log_dt("dt", dt_s)

    # TODO(aliberts): move robot-specific logs logic in robot.print_logs()
    if not robot.robot_type.startswith("stretch"):
        for name in robot.leader_arms:
            key = f"read_leader_{name}_pos_dt_s"
            if key in robot.logs:
                log_dt(f"dt_R_leader_{name}", robot.logs[key])

        # for name in robot.follower_arms:
        #     key = f"write_follower_{name}_goal_pos_dt_s"
        #     if key in robot.logs:
        #         log_dt(f"dt_W_foll_{name}", robot.logs[key])

        #     key = f"read_follower_{name}_pos_dt_s"
        #     if key in robot.logs:
        #         log_dt(f"dt_R_foll_{name}", robot.logs[key])

        for name in robot.cameras:
            key = f"read_camera_{name}_dt_s"
            if key in robot.logs:
                log_dt(f"dt_R_camera_{name}", robot.logs[key])

    info_str = " ".join(log_items)
    logging.info(info_str)

@cache
def is_headless():
    """Detects if python is running without a monitor."""
    try:
        import pynput  # noqa

        return False
    except Exception:
        print(
            "Error trying to import pynput. Switching to headless mode. "
            "As a result, the video stream from the cameras won't be shown, "
            "and you won't be able to change the control flow with keyboards. "
            "For more info, see traceback below.\n"
        )
        traceback.print_exc()
        print()
        return True

def init_keyboard_listener():
    # Allow to exit early while recording an episode or resetting the environment,
    # by tapping the right arrow key '->'. This might require a sudo permission
    # to allow your terminal to monitor keyboard events.
    events = {}
    events["exit_early"] = False
    events["rerecord_episode"] = False
    events["stop_recording"] = False

    if is_headless():
        logging.warning(
            "Headless environment detected. On-screen cameras display and keyboard inputs will not be available."
        )
        listener = None
        return listener, events

    # Only import pynput if not in a headless environment
    from pynput import keyboard

    def on_press(key):
        try:
            if key == keyboard.Key.right:
                print("Right arrow key pressed. Exiting loop...")
                events["exit_early"] = True
            elif key == keyboard.Key.left:
                print("Left arrow key pressed. Exiting loop and rerecord the last episode...")
                events["rerecord_episode"] = True
                events["exit_early"] = True
            elif key == keyboard.Key.esc:
                print("Escape key pressed. Stopping data recording...")
                events["stop_recording"] = True
                events["exit_early"] = True
            elif key.char == 'q' or key.char == 'Q':  # 检测q键（不区分大小写）
                print("Q key pressed.")
                events["exit_early"] = True

        except Exception as e:
            print(f"Error handling key press: {e}")

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    return listener, events

def warmup_record(
    robot,
    enable_teleoperation,
    events,
    warmup_time_s,
    display_cameras,
    fps,
):
    control_loop(
        robot=robot,
        events=events,
        control_time_s=warmup_time_s,
        display_cameras=display_cameras,
        fps=fps,
        teleoperate=enable_teleoperation,
    )

def record_episode(
    robot,
    dataset,
    events,
    episode_time_s,
    display_cameras,
    fps,
    single_task,
):
    control_loop(
        robot=robot,
        control_time_s=episode_time_s,
        display_cameras=display_cameras,
        dataset=dataset,
        events=events,
        fps=fps,
        teleoperate=True,
        single_task=single_task,
    )

@safe_disconnect
def teleoperate(robot_cfg: RobotConfig, teleope_cfg: TeleoperateControlConfig):
    # control_loop(
    #     robot,
    #     control_time_s=cfg.teleop_time_s,
    #     fps=cfg.fps,
    #     teleoperate=True,
    #     display_cameras=cfg.display_cameras,
    # )
    pass


@safe_disconnect
def record(
    robot: Robot,
    record_cfg: RecordControlConfig) -> LeRobotDataset:

    print("In Record")
    if record_cfg.resume:
        dataset = LeRobotDataset(
            record_cfg.repo_id,
            root=record_cfg.root,
        )
        if len(robot.cameras) > 0:
            dataset.start_image_writer(
                num_processes=record_cfg.num_image_writer_processes,
                num_threads=record_cfg.num_image_writer_threads_per_camera * len(robot.cameras),
            )
        sanity_check_dataset_robot_compatibility(dataset, robot, record_cfg.fps, record_cfg.video)
    else:
        # Create empty dataset or load existing saved episodes
        sanity_check_dataset_name(record_cfg.repo_id, record_cfg.policy)
        dataset = LeRobotDataset.create(
            record_cfg.repo_id,
            record_cfg.fps,
            root=record_cfg.root,
            robot=robot,
            use_videos=record_cfg.video,
            image_writer_processes=record_cfg.num_image_writer_processes,
            image_writer_threads=record_cfg.num_image_writer_threads_per_camera * len(robot.cameras),
        )

    # Load pretrained policy
    # policy = None if record_cfg.policy is None else make_policy(record_cfg.policy, ds_meta=dataset.meta)

    if not robot.is_connected:
        robot.connect()

    # Execute a few seconds without recording to:
    # 1. teleoperate the robot to move it in starting position if no policy provided,
    # 2. give times to the robot devices to connect and start synchronizing,
    # 3. place the cameras windows on screen
    # enable_teleoperation = policy is None
    # log_say("Warmup record", cfg.play_sounds)
    listener, events = init_keyboard_listener()

    warmup_record(robot, True, events, record_cfg.warmup_time_s, record_cfg.display_cameras, record_cfg.fps)

    if has_method(robot, "teleop_safety_stop"):
        robot.teleop_safety_stop()

    recorded_episodes = 0
    while True:
        if recorded_episodes >= record_cfg.num_episodes:
            break

        log_say(f"Recording episode {dataset.num_episodes}", record_cfg.play_sounds)
        record_episode(
            robot=robot,
            dataset=dataset,
            events=events,
            episode_time_s=record_cfg.episode_time_s,
            display_cameras=record_cfg.display_cameras,
            fps=record_cfg.fps,
            single_task=record_cfg.single_task,
        )

        # Execute a few seconds without recording to give time to manually reset the environment
        # Current code logic doesn't allow to teleoperate during this time.
        # TODO(rcadene): add an option to enable teleoperation during reset
        # Skip reset for the last episode to be recorded
        if not events["stop_recording"] and (
            (recorded_episodes < record_cfg.num_episodes - 1) or events["rerecord_episode"]
        ):
            # log_say("Reset the environment", record_cfg.play_sounds)
            reset_environment(robot, events, record_cfg.reset_time_s, record_cfg.fps)

        if events["rerecord_episode"]:
            # log_say("Re-record episode", record_cfg.play_sounds)
            events["rerecord_episode"] = False
            events["exit_early"] = False
            dataset.clear_episode_buffer()
            continue

        dataset.save_episode()
        recorded_episodes += 1

        if events["stop_recording"]:
            break

    # log_say("Stop recording", record_cfg.play_sounds, blocking=True)
    stop_recording(robot, listener, record_cfg.display_cameras)

    if record_cfg.push_to_hub:
        dataset.push_to_hub(tags=record_cfg.tags, private=record_cfg.private)

    # log_say("Exiting", record_cfg.play_sounds)
    return dataset

# @safe_stop_image_writer
def control_loop(
    robot,
    control_time_s=None,
    teleoperate=False,
    display_cameras=False,
    dataset: LeRobotDataset | None = None,
    events=None,
    # policy: PreTrainedPolicy = None,
    fps: int | None = None,
    single_task: str | None = None,
):


    if events is None:
        events = {"exit_early": False}

    if control_time_s is None:
        control_time_s = float("inf")

    # if teleoperate is not None:
    #     raise ValueError("When `teleoperate` is True, `policy` should be None.")

    if dataset is not None and single_task is None:
        raise ValueError("You need to provide a task as argument in `single_task`.")

    if dataset is not None and fps is not None and dataset.fps != fps:
        raise ValueError(f"The dataset fps should be equal to requested fps ({dataset['fps']} != {fps}).")

    timestamp = 0
    start_episode_t = time.perf_counter()
    # image_show = [ImageShow(30) for _ in range(3)]

    while timestamp < control_time_s:
        start_loop_t = time.perf_counter()

        teleoperate_start_t = time.perf_counter()

        if teleoperate:
            print("In teleoperate")
            observation, action = robot.teleop_step(record_data=True)
            # robot.teleop_step()
        else:
            # observation = robot.capture_observation()
            # # observation["task"] = [single_task[:], single_task[:]]
            # observation.update({"task":[single_task]})

            # if policy is not None:
            #     pred_action = predict_action(
            #         observation, policy, get_safe_torch_device(policy.config.device), policy.config.use_amp
            #     )
            #     # Action can eventually be clipped using `max_relative_target`,
            #     # so action actually sent is saved in the dataset.
            #     action = robot.send_action(pred_action)
            #     action = {"action": action}
            pass
        
        teleoperate_dt_s = time.perf_counter() - teleoperate_start_t
        print(f"teleoperate_dt_s = {teleoperate_dt_s}")

        if dataset is not None:
            frame = {**observation, **action, "task": single_task}
            dataset.add_frame(frame)

        print("after dataset ")
        cv2_display_start_t = time.perf_counter()
        # keboard_key = 0
        if display_cameras and not is_headless():
            image_keys = [key for key in observation if "image" in key]
            for i, key in enumerate(image_keys, start=1):
                # cv2.imshow(key, observation[key].numpy())
                # cv2.waitKey(10)
                name = key[len("observation.images."):]
                robot_client.update_stream(name, observation[key].numpy())
        
        cv_display_dt_s = time.perf_counter() - cv2_display_start_t
        print(f"cv_display_dt_s = {cv_display_dt_s}")

        print("after display_cameras ")
        if fps is not None:
            dt_s = time.perf_counter() - start_loop_t
            busy_wait(1 / fps - dt_s)

        dt_s = time.perf_counter() - start_loop_t
        print(f"dt_s = {dt_s}")
        log_control_info(robot, dt_s, fps=fps)

        timestamp = time.perf_counter() - start_episode_t
        if events["exit_early"]:
        # if events["exit_early"] | keboard_key & 0xFF == ord('q'):
        # if events["exit_early"]:
            events["exit_early"] = False
            break
    
    # for i in range(3):
    #     image_show[i].disconnect()

def reset_environment(robot, events, reset_time_s, fps):
    # TODO(rcadene): refactor warmup_record and reset_environment
    if has_method(robot, "teleop_safety_stop"):
        robot.teleop_safety_stop()

    control_loop(
        robot=robot,
        control_time_s=reset_time_s,
        events=events,
        fps=fps,
        teleoperate=True,
    )


def stop_recording(robot, listener, display_cameras):
    robot.disconnect()

    if not is_headless():
        if listener is not None:
            listener.stop()

        if display_cameras:
            # cv2.destroyAllWindows()
            pass


@parser.wrap()
def main(cfg: ControlPipelineConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))
    
    robot = make_robot_from_config(cfg.robot)
    # robot_client.start()
    cameras = {}
    for name, camera in robot.cameras.items():
        cameras[name] = camera.camera_index
    robot_client.stream_info(cameras)
    robot_client.update_stream_info_to_server()

    if isinstance(cfg.control, TeleoperateControlConfig):
        teleoperate(robot, cfg.control)
    elif isinstance(cfg.control, RecordControlConfig):
        record(robot, cfg.control)

    robot_client.stop()

    


if __name__ == "__main__":
    main() # type: ignore