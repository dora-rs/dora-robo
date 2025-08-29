
import numpy as np

from operating_platform.robot.robots.so101_v1.motors.utils import MotorsBus
from operating_platform.robot.robots.so101_v1.motors.feetech import (
    DriveMode,
    FeetechMotorsBus,
    OperatingMode,
    TorqueMode,
)

from functools import cache
import traceback
import logging


TARGET_90_DEGREE_POSITION = np.array([0, 0, 0, 0, 0, 0, 0, 0])


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
    events["complete"] = False

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
            hasattr(key, 'char')
            if key.char.lower() == 'q':
                print("key pressed")
                events["complete"] = True
        except Exception as e:
            print(f"Error handling key press: {e}")

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    return listener, events

def apply_homing_offset(values: np.array, homing_offset: np.array) -> np.array:
    for i in range(len(values)):
        if values[i] is not None:
            values[i] += homing_offset[i]
    return values


def apply_drive_mode(values: np.array, drive_mode: np.array) -> np.array:
    for i in range(len(values)):
        if values[i] is not None and drive_mode[i]:
            values[i] = -values[i]
    return values


def apply_calibration(values: np.array, homing_offset: np.array, drive_mode: np.array) -> np.array:
    values = apply_drive_mode(values, drive_mode)
    values = apply_homing_offset(values, homing_offset)
    return values


def revert_calibration(values: np.array, homing_offset: np.array, drive_mode: np.array) -> np.array:
    """
    Transform working position into real position for the robot.
    """
    values = apply_homing_offset(
        values,
        np.array([-homing_offset if homing_offset is not None else None for homing_offset in homing_offset]),
    )
    values = apply_drive_mode(values, drive_mode)
    return values


def revert_appropriate_positions(positions: np.array, drive_mode: list[bool]) -> np.array:
    for i, revert in enumerate(drive_mode):
        if not revert and positions[i] is not None:
            positions[i] = -positions[i]
    return positions


def compute_corrections(positions: np.array, drive_mode: list[bool], target_position: np.array) -> np.array:
    correction = revert_appropriate_positions(positions, drive_mode)

    for i in range(len(positions)):
        if correction[i] is not None:
            if drive_mode[i]:
                correction[i] -= target_position[i]
            else:
                correction[i] += target_position[i]

    return correction


def compute_nearest_rounded_positions(positions: np.array) -> np.array:
    return np.array(
        [
            round(positions[i] / 1024) * 1024 if positions[i] is not None else None
            for i in range(len(positions))
        ]
    )


#用于计算机械臂的归零偏差
def compute_homing_offset(
    arm: FeetechMotorsBus, drive_mode: list[bool], target_position: np.array
) -> np.array:
    # Get the present positions of the servos
    #从 arm 读取当前伺服电机的位置（“Present_Position”）。apply_calibration 函数使用 drive_mode 
    # 和一个初始零位置数组对这些位置进行校准。
    present_positions = apply_calibration(
        arm.read("Present_Position"), np.array([0, 0, 0, 0, 0, 0, 0]), drive_mode
    )

    nearest_positions = compute_nearest_rounded_positions(present_positions)
    correction = compute_corrections(nearest_positions, drive_mode, target_position)
    return correction


def compute_drive_mode(arm: FeetechMotorsBus, offset: np.array):
    
    # Get current positions
    present_positions = apply_calibration(
        arm.read("Present_Position"), offset, np.array([False, False, False, False, False, False,False,False])
    )

    nearest_positions = compute_nearest_rounded_positions(present_positions)

    # construct 'drive_mode' list comparing nearest_positions and TARGET_90_DEGREE_POSITION
    drive_mode = []
    for i in range(len(nearest_positions)):
        drive_mode.append(nearest_positions[i] != TARGET_90_DEGREE_POSITION[i])
    return drive_mode

# 初始化电机
def init_arm(arm: MotorsBus):
    arm.write("Torque_Enable", TorqueMode.ENABLED.value)
    arm.write("Operating_Mode", OperatingMode.CURRENT_CONTROLLED_POSITION.value)
    arm.write("Goal_Current", 300)

    # Make sure the native calibration (homing offset abd drive mode) is disabled, since we use our own calibration layer to be more generic
    arm.write("Homing_Offset", 0)
    arm.write("Drive_Mode", DriveMode.NON_INVERTED.value)

    print("init_arm: OK!")

# 重置电机的状态，禁用扭矩模式，设置伺服电机的模式
def reset_arm(arm: MotorsBus):
    # To be configured, all servos must be in "torque disable" mode
    arm.write("Torque_Enable", TorqueMode.DISABLED.value)   # 将所有伺服电机的扭矩模式设置为禁用，以确保电机在重置过程中不会施加力量。

    # Use 'extended position mode' for all motors except gripper, because in joint mode the servos can't
    # rotate more than 360 degrees (from 0 to 4095) And some mistake can happen while assembling the arm,
    # you could end up with a servo with a position 0 or 4095 at a crucial point See [
    # https://emanual.robotis.com/docs/en/dxl/x/x_series/#operating-mode11]
    all_motors_except_gripper = [name for name in arm.motor_names if name != "gripper"]
    arm.write("Operating_Mode", OperatingMode.EXTENDED_POSITION.value, all_motors_except_gripper)

    # TODO(rcadene): why?
    # Use 'position control current based' for gripper
    arm.write("Operating_Mode", OperatingMode.CURRENT_CONTROLLED_POSITION.value, "gripper")
    arm.write("Goal_Current", 50, "gripper")

    # Set gripper
    arm.write("Torque_Enable", 1, "gripper")
    arm.write("Goal_Position", GRIPPER_OPEN, "gripper")

    print("reset_arm: OK!")


def run_arm_calibration(arm: MotorsBus, name: str, arm_type: str):
    """Example of usage:
    ```python
    run_arm_calibration(arm, "left", "follower")
    ```
    """
    #先重置机械臂
    init_arm(arm)
    
    listener, events = init_keyboard_listener()

    print(f"Calibrate {name} arm.")

    while True:
        current = arm.read("Present_Current")
        my_pos = arm.read("Present_Position")
        print(f"current = {current}")
        print(f"my_pos = {my_pos}")
        for index, value in enumerate(current, start=0):
            if value >> 15 == 1:
                buma = value  # 补码（这里实际上只是获取 value[0] 的值）
                fanma = buma - 1  # 反码（这里实际上是 value[0] 减 1）
                yuanma = int(format(~fanma & 0xFFFF, '016b'), 2)  # 原码（这里是对 fanma 进行按位取反操作）  
                p_current = yuanma * -1
            else:
                p_current = float(value)
            print(f"index = {index}, value = {value}, p_current = {p_current}")
            print(f"index = {index}, current[{index}] = {current[index]}")
            print(f"index = {index}, my_pos[{index}] = {my_pos[index]}")
            print(f"index = {index}, arm.motor_names[{index}] = {arm.motor_names[index]}")
            if abs(p_current) >= 150:
                arm.write("Goal_Position", my_pos[index], arm.motor_names[index])
        if events["complete"]:
            old_gripper = arm.read("Present_Position", "gripper")
            print(f"Will complete {name} arm calibration")
            while True:
                gripper = arm.read("Present_Position", "gripper")
                print(f"gripper = {gripper}")
                if abs(gripper - old_gripper) >= 150:
                    break
            break

    if not is_headless():
        if listener is not None:
            listener.stop()

    #提示用户放置到水平位置
    # TODO(rcadene): document what position 1 mean
    print(
        f"Please move the '{name} {arm_type}' arm to the horizontal position (gripper fully closed, see {URL_HORIZONTAL_POSITION[arm_type]})"
    )
    # input("Press Enter to continue...")
    #调用 compute_homing_offset 函数来计算在水平位置时的归零偏差，TARGET_HORIZONTAL_POSITION 是预设的水平目标位置。
    #TARGET_HORIZONTAL_POSITION 是预设的水平目标位置。
    horizontal_homing_offset = compute_homing_offset(
        arm, [False, False, False, False, False, False, False, False], TARGET_HORIZONTAL_POSITION
    )

    # TODO(rcadene): document what position 2 mean
    #显示一条消息，提示用户将机械臂移动到90度位置，并要求用户在调整后按回车继续。
    print(
        f"Please move the '{name} {arm_type}' arm to the 90 degree position (gripper fully open, see {URL_90_DEGREE_POSITION[arm_type]})"
    )
    # input("Press Enter to continue...")
    
    #计算驱动模式和归零偏差
    drive_mode = compute_drive_mode(arm, horizontal_homing_offset)
    homing_offset = compute_homing_offset(arm, drive_mode, TARGET_90_DEGREE_POSITION)

    # Invert offset for all drive_mode servos
    for i in range(len(drive_mode)):
        if drive_mode[i]:
            homing_offset[i] = -homing_offset[i]

    print("Calibration is done!")

    print("=====================================")
    print("      HOMING_OFFSET: ", " ".join([str(i) for i in homing_offset]))
    print("      DRIVE_MODE: ", " ".join([str(i) for i in drive_mode]))
    print("=====================================")

    return homing_offset, drive_mode