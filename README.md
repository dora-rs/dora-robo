# Operating-Platform


## Start

get this project

```sh
git cloen https://github.com/DoRobot-Project/Operating-Platform.git
cd Operating-Platform
```

creat conda env

```sh
conda create --name op python==3.11
```

activate conda env

```sh
conda activate op
```

install `poetry`

```sh
# install
curl -sSL https://install.python-poetry.org  | python3 -

# update shell config
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# check
poetry --version
```

install this project

```sh
poetry install
```