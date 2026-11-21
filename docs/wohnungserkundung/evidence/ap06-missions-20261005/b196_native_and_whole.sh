#!/bin/bash
set -eo pipefail
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export ROS_DOMAIN_ID=222
python3 /evidence/ap06-repo/tools/simulation/ap03_nav2_closed_loop.py --repo /evidence/ap06-repo --output /evidence/ap06-missions-20261005/native-components-v39 > /evidence/ap06-missions-20261005/native-components-v39.log 2>&1
export ROS_DOMAIN_ID=187
python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --output /evidence/ap06-missions-20261005/mission-b-v196 --case door68_start_b --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json --save-partial > /evidence/ap06-missions-20261005/mission-b-v196.log 2>&1
