#!/bin/bash
conda activate dorobot

python operating_platform/core/train.py \
  --dataset.repo_id="20250906/experimental/test-dataset-1" \
  --policy.type=act \
  --output_dir=outputs/train/0905_act_so101_test \
  --job_name=act_so101_test \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=False
