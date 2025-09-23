# DoRobot-Preview 

> GOSIM 2025 - Dora LeRobot Hackthon - Version

## 0. Start (with Docker) coming soon

<!-- get this project

```sh
git clone https://github.com/jzzzzzzzzzzzzzzzz/dora-dorobot.git
cd Operating-Platform
```

build docker image
```sh
docker build -f docker/Dockerfile.base -t operating-platform:V1.0 .
```

make dir
```sh
mkdir /data/hf
```

run sh
```sh
sh docker/start.sh
```


[tool.uv.sources]
lerobot_lite = { path = "operating_platform/lerobot_lite"} -->

## 1. Start (without Docker)

get this project

```sh
git clone https://github.com/jzzzzzzzzzzzzzzzz/dora-dorobot.git
cd dora-dorobot
```

### 1.1. Initital DoRobot enviroment

creat conda env

```sh
conda create --name op python==3.11
```

activate conda env

```sh
conda activate op
```

install this project

```sh
pip install -e .
```

**install pytorch, according to your platform**

```sh
# ROCM 6.1 (Linux only)
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.1
# ROCM 6.2.4 (Linux only)
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.2.4
# CUDA 11.8
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
# CUDA 12.4
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
# CUDA 12.6
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126
# CPU only
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
```

install libportaudio2

```
sudo apt install libportaudio2
```

### 1.2. Initital SO101 enviroment

Open a new terminal and switch to the DoRobot-Preview project directory.

creat conda env

```sh
conda create --name dr-robot-so101 python==3.10
```

activate conda env

```sh
conda activate dr-robot-so101
```

install robot enviroment

```sh
cd operating_platform/robot/robots/so101_v1
pip install -e .
```

### 1.3. Calibrate SO101 Arm

calibrate leader arm

```
cd operating_platform/robot/components/arm_normal_so101_v1/
dora run dora_calibrate_leader.yml
```

calibrate follower arm

```
cd operating_platform/robot/components/arm_normal_so101_v1/
dora run dora_calibrate_follower.yml
```

## 2. Teleoperate SO101 Arm

```
cd operating_platform/robot/components/arm_normal_so101_v1/
dora run dora_teleoperate_arm.yml
```

## 3. Record Data

You need to unplug all camera and robotic arm data interfaces first, then plug in the head camera.

```
ls /dev/video*
```

you can see:

```
/dev/video0 /dev/video1
```

If you see other indices, please make sure that all other cameras have been disconnected from the computer. If you are unable to remove them, please modify the camera index in the YAML file. 

then plug in the head camera.

```
ls /dev/video*
```

you can see:

```
/dev/video0 /dev/video1 /dev/video2 /dev/video3
```

now, you finish camera connect.

如果确保两个摄像头可以同时工作，可以开两个终端，分别输入

    ffplay /dev/video0
    ffplay /dev/video2

观察是否能够同时开启，如果报错说，设备没有空间，则是usb带宽过小不够相机视频流传输，直接连在主机的高速usb接口上后再测试。

同时注意，如果使用过程中有过断电或录制时视频窗口黑屏显示无法打开某个video，请检查相机端口号是否还是0123，
    
    ls /dev/video*

如果不是，可以选择修改
    
    operating_platform/robot/robots/so101_v1/ora_teleoperate_dataflow.yml

中的相机端口号，对应实际显示的端口号。或者重新插拔相机，使其重新初始化为0123

Next, connect the robotic arm by first plugging in the leader arm's USB interface.

```
ls /dev/ttyACM*
```

you can see:

```
/dev/ttyACM0
```

Then plugging in the follower arm's USB interface.

```
ls /dev/ttyACM*
```

you can see:

```
/dev/ttyACM0 /dev/ttyACM1
```

给予端口权限
    
    sudo chmod 777 /dev/ttyACM*

run dora data flow 

```
cd operating_platform/robot/robots/so101_v1
conda activate dr-robot-so101
dora run dora_teleoperate_dataflow.yml
```

Open a new terminal, then:

```
bash scripts/run_so101_cli.sh
```

You can modify the task name and task description by adjusting the parameters within the run_so101_cli.sh file.

## 4. Train policy

修改scripts/run_so101_train.sh中的参数dataset.repo_id替换1为本地数据集地址

比如：

    --dataset.repo_id=/home/dora/DoRobot/dataset/20250906/experimental/jz-test-dataset

并且保留该地址，后续本地推理时仍需要使用。

选择使用的模型：

    --policy.type=act 

将参数替换为本地保存的地址

    --output_dir=outputs/train/0905_act_so101_test \


启动训练脚本:

```
bash scripts/run_so101_train.sh
```

## 5. Inference

修改scripts/run_so101_inference.sh中的参数

inference.dataset.repo_id修改为本地录制的数据集地址：

    --inference.dataset.repo_id="/home/dora/DoRobot/dataset/20250906/experimental/jz-test-dataset" 

policy.path为保存模型的本地地址：

    --policy.path="outputs/train/0906_act_so101_test/checkpoints/010000/pretrained_model"

运行 dora data flow 

```
cd operating_platform/robot/robots/so101_v1
conda activate dr-robot-so101
dora run dora_teleoperate_dataflow.yml
```

启动训练脚本:

```
bash scripts/run_so101_inference.sh
```

    
# Acknowledgment
 - LeRobot 🤗: [https://github.com/huggingface/lerobot](https://github.com/huggingface/lerobot)
