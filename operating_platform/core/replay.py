import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from pprint import pformat

import draccus

from operating_platform.core.daemon import Daemon

from operating_platform.dataset.dorobot_dataset import DoRobotDataset
from operating_platform.robot.robots.utils import (
    Robot,
    RobotConfig,
    make_robot_from_config,
    busy_wait
)
from operating_platform.utils.utils import (
    init_logging,
    log_say,
)


@dataclass
class DatasetReplayConfig:
    # Dataset identifier. By convention it should match '{hf_username}/{dataset_name}' (e.g. `lerobot/test`).
    repo_id: str
    # Episode to replay.
    episode: int
    # Root directory where the dataset will be stored (e.g. 'dataset/path').
    root: str | Path | None = None
    # Limit the frames per second. By default, uses the policy fps.
    fps: int = 30


@dataclass
class ReplayConfig:
    robot: Robot
    dataset: DatasetReplayConfig
    # Use vocal synthesis to read events.
    play_sounds: bool = False


@draccus.wrap()
def replay(cfg: ReplayConfig):
    init_logging()
    # logging.info(pformat(asdict(cfg)))

    # robot = make_robot_from_config(cfg.robot)
    dataset = DoRobotDataset(cfg.dataset.repo_id, root=cfg.dataset.root, episodes=[cfg.dataset.episode])
    actions = dataset.hf_dataset.select_columns("action")
    # robot.connect()
    robot = cfg.robot

    log_say("Replaying episode", cfg.play_sounds, blocking=True)
    for idx in range(dataset.num_frames):
        start_episode_t = time.perf_counter()

        action_array = actions[idx]["action"]
        action = {}
        for i, name in enumerate(dataset.features["action"]["names"]):
            action[name] = action_array[i]

        # print(f"action: {action}")
        robot.send_action(action)

        dt_s = time.perf_counter() - start_episode_t
        busy_wait(1 / dataset.fps - dt_s)

    # robot.disconnect()


def main():
    replay()


if __name__ == "__main__":
    main()
