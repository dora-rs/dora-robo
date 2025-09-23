conda activate op

python operating_platform/core/inference.py \
    --robot.type=so101 \
    --inference.single_task="start and test so101 arm." \
    --inference.dataset.repo_id="20250906/experimental/test-dataset-1" \
    --policy.path="outputs/train/0906_act_so101_test/checkpoints/010000/pretrained_model"
    