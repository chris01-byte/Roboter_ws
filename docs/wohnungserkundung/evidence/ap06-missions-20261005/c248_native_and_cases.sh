#!/bin/bash
set -e -o pipefail
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export ROS_DOMAIN_ID=222
python3 /evidence/ap06-repo/tools/simulation/ap03_nav2_closed_loop.py --repo /evidence/ap06-repo --output /evidence/ap06-missions-20261005/native-components-v46 > /evidence/ap06-missions-20261005/native-components-v46.log 2>&1
export ROS_DOMAIN_ID=187
set +e
for mission_spec in 'door80_start_c mission-c-v248' 'cancel mission-cancel-v249' 'gyro_hold mission-gyro-v250'; do
  read -r mission_case mission_out <<< "$mission_spec"
  taskset -c 0,1,3,4 python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --output "/evidence/ap06-missions-20261005/$mission_out" --case "$mission_case" --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json --save-partial > "/evidence/ap06-missions-20261005/$mission_out.log" 2>&1
  mission_code=$?
  printf '%s %d\n' "$mission_case" "$mission_code" >> /evidence/ap06-missions-20261005/c248-matrix-exit-codes.txt
done
