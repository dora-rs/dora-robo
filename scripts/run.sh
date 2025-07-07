#!/bin/bash

# 配置参数
CONTAINER_NAME="operating_platform"
PROJECT_DIR="/root/Operating-Platform"
CONDA_ENV1="op-robot-aloha"
CONDA_ENV2="op"
DATAFLOW_PATH="/operating_platform/robot/robots/aloha_v1/robot_aloha_dataflow.yml"

# 启动容器并检查状态
echo "[$(date)] 正在启动容器..."
docker start "$CONTAINER_NAME" || { echo "容器启动失败"; exit 1; }

# 等待容器就绪（可选：根据实际需要调整等待时间）
sleep 5

# 并行执行命令函数
run_command() {
    local cmd="$1"
    local log_file="$2"
    
    echo "[$(date)] 执行命令: $cmd"
    docker exec -t "$CONTAINER_NAME" bash -c "$cmd" > >(tee -a "$log_file") 2>&1 &
    echo $! >> .pids
}

# 准备conda激活命令
CONDA_ACTIVATE="source /opt/conda/etc/profile.d/conda.sh && conda activate"

# 清理旧的PID文件
rm -f .pids

# 并行运行命令
run_command "cd $PROJECT_DIR && $CONDA_ACTIVATE $CONDA_ENV1 && dora run $DATAFLOW_PATH" "dataflow.log"
run_command "cd $PROJECT_DIR && $CONDA_ACTIVATE $CONDA_ENV2 && python operating_platform/core/coordinator.py --robot.type=aloha" "coordinator.log"

echo "[$(date)] 所有进程已启动，PID记录在.pids文件中"
echo "监控日志文件："
echo "- dataflow.log"
echo "- coordinator.log"

# 可选：添加进程监控逻辑