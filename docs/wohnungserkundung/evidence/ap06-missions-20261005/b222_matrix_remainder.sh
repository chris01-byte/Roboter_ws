#!/bin/bash
set -o pipefail
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export ROS_DOMAIN_ID=187
for mission_spec in 'door68_start_a mission-a-v222' 'door80_start_c mission-c-v223' 'cancel mission-cancel-v224' 'gyro_hold mission-gyro-v225'; do
  read -r mission_case mission_out <<< "$mission_spec"
  python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --output "/evidence/ap06-missions-20261005/$mission_out" --case "$mission_case" --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json --save-partial > "/evidence/ap06-missions-20261005/$mission_out.log" 2>&1
  mission_code=$?
  printf '%s %d\n' "$mission_case" "$mission_code" >> /evidence/ap06-missions-20261005/b222-matrix-exit-codes.txt
done
