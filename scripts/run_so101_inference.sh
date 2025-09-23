conda activate op

python operating_platform/core/inference.py \
    --robot.type=so101 \
    --inference.single_task="start and test so101 arm." \
    --inference.dataset.repo_id="/home/HwHiAiUser/DoRobot/dataset/20250914/experimental/so101-test-1/" \
    --policy.path="/home/HwHiAiUser/act1/"
