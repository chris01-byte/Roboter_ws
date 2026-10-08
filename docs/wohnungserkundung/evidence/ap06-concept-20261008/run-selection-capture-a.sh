#!/bin/bash
set -eo pipefail
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export ROS_DOMAIN_ID=187
export PYTHONPATH=/evidence/ap06-repo/tools/simulation${PYTHONPATH:+:$PYTHONPATH}
exec taskset -c 0,1,3,4 python3 /evidence/ap06-concept-20261008/capture_selection_product.py \
 --repo /evidence/ap06-repo --output /evidence/ap06-concept-20261008/selection-capture-a \
 --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe \
 --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json \
 --case door68_start_a --ideal-lidar --capture-decisions --save-partial
