
import cv2
import json
import time
import draccus
import socketio
import requests
import traceback
import threading
import queue

from dataclasses import dataclass, asdict
from pathlib import Path
from pprint import pformat
from deepdiff import DeepDiff
from functools import cache
from termcolor import colored
from datetime import datetime


# from operating_platform.policy.config import PreTrainedConfig
from operating_platform.robot.robots.configs import RobotConfig
from operating_platform.robot.robots.utils import make_robot_from_config, Robot, busy_wait, safe_disconnect
from operating_platform.utils import parser
from operating_platform.utils.utils import has_method, init_logging, log_say, get_current_git_branch, git_branch_log, get_container_ip_from_hosts
from operating_platform.utils.data_file import find_epindex_from_dataid_json

from operating_platform.utils.constants import DOROBOT_DATASET
from operating_platform.dataset.dorobot_dataset import *
from operating_platform.dataset.visual.visual_dataset import visualize_dataset

# from operating_platform.core._client import Coordinator
from operating_platform.core.daemon import Daemon
from operating_platform.core.record import Record, RecordConfig
from operating_platform.core.replay import DatasetReplayConfig, ReplayConfig, replay

DEFAULT_FPS = 30

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


@dataclass
class ControlPipelineConfig:
    robot: RobotConfig
    record: RecordConfig
    # control: ControlConfig

    @classmethod
    def __get_path_fields__(cls) -> list[str]:
        """This enables the parser to load config from the policy using `--policy.path=local/dir`"""
        return ["control.policy"]


def record_loop(cfg: ControlPipelineConfig, daemon: Daemon):
    # repo_id = cfg.record.repo_id
    # date_str = datetime.now().strftime("%Y%m%d")

    # # 构建目标目录路径
    # dataset_path = DOROBOT_DATASET

    # git_branch_name = get_current_git_branch()
    # if "release" in git_branch_name:
    #     target_dir = dataset_path / date_str / "user" / repo_id
    # elif "dev"  in git_branch_name:
    #     target_dir = dataset_path / date_str / "dev" / repo_id
    # else:
    #     target_dir = dataset_path / date_str / "dev" / repo_id

    # while True:
    #     keybord = 'a'
    #     # 判断是否存在对应文件夹以决定是否启用恢复模式
    #     resume = False
        

    #     # 检查数据集目录是否存在
    #     if not dataset_path.exists():
    #         logging.info(f"Dataset directory '{dataset_path}' does not exist. Cannot resume.")
    #     else:
    #         # 检查目标文件夹是否存在且为目录
    #         if target_dir.exists() and target_dir.is_dir():
    #             resume = True
    #             logging.info(f"Found existing directory for repo_id '{repo_id}'. Resuming operation.")
    #         else:
    #             logging.info(f"No directory found for repo_id '{repo_id}'. Starting fresh.")

    #     # resume 变量现在可用于后续逻辑
    #     print(f"Resume mode: {'Enabled' if resume else 'Disabled'}")

    #     msg = {
    #         "task_id": "001",
    #         "task_name": cfg.record.repo_id,
    #         "task_data_id": "001",
    #         "collector_id":"001",
    #         "countdown_seconds": 3,
    #         "task_steps": [
    #             {
    #                 "doruation": "10",
    #                 "instruction": "put"
    #             },
    #             {
    #                 "doruation": "2",
    #                 "instruction": "close"
    #             },
    #             {
    #                 "doruation": "5",
    #                 "instruction": "clean"
    #             }
    #         ]
    #     }

    #     record_cfg = RecordConfig(fps=cfg.record.fps, repo_id=repo_id, single_task=cfg.record.single_task, video=daemon.robot.use_videos, resume=resume, root=target_dir)
    #     record = Record(fps=cfg.record.fps, robot=daemon.robot, daemon=daemon, record_cfg = record_cfg, record_cmd=msg)
                
    #     print("="*10, "Start Record", "="*10)
    #     record.start()

    #     print("Press 'n' to next episode or 'e' to end record.")
    #     while True:
    #         daemon.update()
    #         observation = daemon.get_observation()

    #         if observation is not None:
    #             image_keys = [key for key in observation if "image" in key]
    #             for i, key in enumerate(image_keys, start=1):
    #                 img = cv2.cvtColor(observation[key], cv2.COLOR_RGB2BGR) 

    #                 if not is_headless():
    #                     cv2.imshow(key, img)
    #         else:
    #             print("observation is none")

    #         keybord = cv2.waitKey(1)
    #         if keybord in [ord('n'), ord('e'), ord('N'), ord('E')]:
    #             break

    #     record.stop()
    #     record.save()
    #     print(f"total_episodes: {record.dataset.meta.total_episodes}")

    #     if keybord in [ord('e'), ord('E')]:
    #         break

    #     print("*"*10, "Reset Enviroment", "*"*10)
    #     print("Press 'p' to pass reset.")
    #     while True:
    #         keybord = cv2.waitKey(1)
    #         if keybord in [ord('p'), ord('P')]:
    #             break
        
    #     cv2.destroyAllWindows()

    # 确保数据集根目录存在
    dataset_path = DOROBOT_DATASET
    dataset_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Dataset root directory: {dataset_path}")

    while True:
        # 1. 动态获取当前日期（支持跨天运行）
        date_str = datetime.now().strftime("%Y%m%d")
        repo_id = cfg.record.repo_id
        
        # 2. 安全获取Git分支（处理异常情况）
        try:
            git_branch_name = get_current_git_branch()
            logging.debug(f"Current git branch: {git_branch_name}")
        except Exception as e:
            git_branch_name = "unknown"
            logging.warning(f"Failed to get git branch: {str(e)}. Using 'unknown' branch.")
        
        # 3. 构建目标目录路径（更精确的分支判断）
        if git_branch_name.startswith("release/"):
            target_dir = dataset_path / date_str / "user" / repo_id
        elif git_branch_name.startswith("dev/"):
            target_dir = dataset_path / date_str / "dev" / repo_id
        else:
            target_dir = dataset_path / date_str / "experimental" / repo_id
            logging.info(f"Using experimental path for unknown branch: {git_branch_name}")

        # 4. 创建目标目录（确保父目录存在）
        target_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Target directory: {target_dir}")
        
        # 5. 检查恢复模式（更健壮的路径检查）
        resume = False
        if any(target_dir.iterdir()):  # 检查目录是否非空
            resume = True
            logging.info(f"Resuming recording in existing directory: {target_dir}")
        else:
            logging.info(f"Starting new recording session in: {target_dir}")

        # 6. 任务配置（从配置获取而非硬编码）
        try:
            record_cmd = {
                "task_id": cfg.record.task_id or "default_task",
                "task_name": repo_id,
                "task_data_id": cfg.record.data_id or "001",
                "collector_id": cfg.record.collector_id or "default_collector",
                "countdown_seconds": cfg.record.countdown or 3,
                "task_steps": [
                    {
                        "duration": str(step.get("duration", 10)),  # 修复拼写错误
                        "instruction": step.get("instruction", "put")
                    } for step in cfg.record.task_steps
                ]
            }
        except Exception as e:
            logging.error(f"Invalid task configuration: {str(e)}")
            record_cmd = {
                "task_id": "fallback_task",
                "task_name": repo_id,
                "task_data_id": "001",
                "collector_id": "fallback_collector",
                "countdown_seconds": 3,
                "task_steps": [{"duration": "10", "instruction": "put"}]
            }
            logging.warning("Using fallback task configuration")

        # 7. 创建记录器（使用配置参数）
        record_cfg = RecordConfig(
            fps=cfg.record.fps,
            repo_id=repo_id,
            single_task=cfg.record.single_task,
            video=daemon.robot.use_videos,
            resume=resume,
            root=target_dir
        )
        record = Record(
            fps=cfg.record.fps,
            robot=daemon.robot,
            daemon=daemon,
            record_cfg=record_cfg,
            record_cmd=record_cmd
        )
        
        logging.info("="*30)
        logging.info(f"Starting recording session | Resume: {resume} | Episodes: {record.dataset.meta.total_episodes}")
        logging.info("="*30)
        
        # 8. 开始记录（带倒计时）
        if record_cmd.get("countdown_seconds", 3) > 0:
            for i in range(record_cmd["countdown_seconds"], 0, -1):
                logging.info(f"Recording starts in {i}...")
                time.sleep(1)
        
        record.start()
        
        # 9. 用户交互循环（改进的输入处理）
        logging.info("Recording active. Press:")
        logging.info("- 'n' to finish current episode and start new one")
        logging.info("- 'e' to stop recording and exit")
        
        while True:
            daemon.update()
            observation = daemon.get_observation()
            
            # 显示图像（仅在非无头模式）
            if observation and not is_headless():
                for key in observation:
                    if "image" in key:
                        img = cv2.cvtColor(observation[key], cv2.COLOR_RGB2BGR)
                        cv2.imshow(f"Camera: {key}", img)
            
            # 处理用户输入
            key = cv2.waitKey(10)  # 增加延迟减少CPU占用
            if key in [ord('n'), ord('N')]:
                logging.info("Ending current episode...")
                break
            elif key in [ord('e'), ord('E')]:
                logging.info("Stopping recording and exiting...")
                record.stop()
                record.save()
                return  # 直接退出函数
        
        # 10. 保存当前episode
        record.stop()
        record.save()
        logging.info(f"Episode saved. Total episodes: {record.dataset.meta.total_episodes}")
        
        # 11. 环境重置（带超时和可视化）
        logging.info("*"*30)
        logging.info("Resetting environment - Press 'p' to proceed")
        logging.info("Note: Robot will automatically reset in 10 seconds if no input")
        
        reset_start = time.time()
        reset_timeout = 60  # 10秒超时
        
        while time.time() - reset_start < reset_timeout:
            daemon.update()
            if observation := daemon.get_observation():
                for key in observation:
                    if "image" in key:
                        img = cv2.cvtColor(observation[key], cv2.COLOR_RGB2BGR)
                        cv2.imshow(f"Reset View: {key}", img)
            
            key = cv2.waitKey(10)
            if key in [ord('p'), ord('P')]:
                logging.info("Reset confirmed by user")
                break
            elif key in [ord('e'), ord('E')]:
                logging.info("User aborted during reset")
                return
        
        # 12. 清理窗口（仅在无新窗口时）
        if not is_headless():
            cv2.destroyAllWindows()
            logging.debug("Closed all OpenCV windows")


@parser.wrap()
def main(cfg: ControlPipelineConfig):

    init_logging(level=logging.INFO, force=True)
    git_branch_log()
    logging.info(pformat(asdict(cfg)))

    daemon = Daemon(fps=DEFAULT_FPS)
    daemon.start(cfg.robot)
    daemon.update()

    try:
        record_loop(cfg, daemon)
            
    except KeyboardInterrupt:
        print("coordinator and daemon stop")

    finally:
        daemon.stop()
        cv2.destroyAllWindows()
    

if __name__ == "__main__":
    main()
