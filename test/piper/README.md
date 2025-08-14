# Getting Started with Piper

## Installation (To do once)

```
git clone https://github.com/DoRobot-Project/Operating-Platform.git
cd test/piper
```

create conda env
```
conda create -n dr-piper-rerun python=3.10
```

install dependencies
```
pip install .
pip install piper_sdk
```

```
pip uninsatall rerun-sdk
pip install rerun-sdk==0.23.4
```

```
dora build arms_only.yml
```

## Use

```
dora run arms_only.yml
```