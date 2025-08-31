# DoRobot-Preview 

> GOSIM 2025 - Dora LeRobot Hackthon - Version

## Start (with Docker) coming soon

<!-- get this project

```sh
git cloen https://github.com/DoRobot-Project/Operating-Platform.git
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

## Start (without Docker)

get this project

```sh
git cloen https://github.com/DoRobot-Project/DoRobot-Preview.git
cd DoRobot-Preview
```

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

# Acknowledgment
 - LeRobot 🤗: [https://github.com/huggingface/lerobot](https://github.com/huggingface/lerobot)
