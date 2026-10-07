#!/bin/bash
set -e -o pipefail
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export ROS_DOMAIN_ID=222
python3 /evidence/ap06-repo/tools/simulation/ap03_nav2_closed_loop.py --repo /evidence/ap06-repo --output /evidence/ap06-missions-20261005/native-components-v44 > /evidence/ap06-missions-20261005/native-components-v44.log 2>&1
export ROS_DOMAIN_ID=187
set +e
for mission_spec in 'door68_start_a mission-a-v230' 'door68_start_b mission-b-v231' 'door80_start_c mission-c-v232' 'cancel mission-cancel-v233' 'gyro_hold mission-gyro-v234'; do
  read -r mission_case mission_out <<< "$mission_spec"
  python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --output "/evidence/ap06-missions-20261005/$mission_out" --case "$mission_case" --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json --save-partial > "/evidence/ap06-missions-20261005/$mission_out.log" 2>&1
  mission_code=$?
  printf '%s %d\n' "$mission_case" "$mission_code" >> /evidence/ap06-missions-20261005/b230-matrix-exit-codes.txt
done
