import cv2
import time
import torch
import logging
import threading
import traceback

from typing import Any
from functools import cache
from termcolor import colored

from operating_platform.robot.robots.configs import RobotConfig
from operating_platform.robot.robots.utils import make_robot_from_config, Robot, busy_wait, safe_disconnect


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


class Daemon:
    def __init__(self, fps: int | None = None, display = True):
        # self.record = False
        # self.evaluate
        self.fps = fps
        self.display = display

        self.running = False

        # TODO 需要加锁
        self.pre_action: Any | dict[str, torch.Tensor] = None
        self.obs_action: Any | dict[str, torch.Tensor] = None
        self.observation: Any | dict[str, torch.Tensor] = None


    def start(self, config: RobotConfig):
        try:
            self.robot = make_robot_from_config(config)
        except Exception as e:
            KeyboardInterrupt
        self.running = True

        heartbeat_thread = threading.Thread(target=self.process)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
    
    def stop(self):
        self.running = False

    def process(self):
        while self.running:
            start_loop_t = time.perf_counter()


            observation, action = self.robot.teleop_step(record_data=True)

            self.obs_action = action
            self.observation = observation

            if self.action["action"] is not None:
                action = self.robot.send_action(action["action"])
                action = {"action": action}
            

            if self.display and not is_headless():
                image_keys = [key for key in observation if "image" in key]
                for _i, key in enumerate(image_keys, start=1):
                    cv2.imshow(key, observation[key].numpy())
            cv2.waitKey(1)
            
                    #         name = key[len("observation."):]

                    # robot_client.update_stream(name, observation[key].numpy())

            if self.fps is not None:
                busy_wait(1 / self.fps - dt_s)

            dt_s = time.perf_counter() - start_loop_t
            log_control_info(self.robot, dt_s, fps=self.fps)


    @property
    def cameras_info(self):
        cameras = {}
        for name, camera in self.robot.cameras.items():
            cameras[name] = camera.camera_index
        return cameras