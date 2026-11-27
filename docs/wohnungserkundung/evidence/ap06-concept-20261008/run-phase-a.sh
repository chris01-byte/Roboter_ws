#!/bin/bash
set -eo pipefail
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export ROS_DOMAIN_ID=187
exec taskset -c 0,1,3,4 python3 /evidence/ap06-repo/tools/simulation/ap06_concept_experiment.py \
 --repo /evidence/ap06-repo --output /evidence/ap06-concept-20261008/phase-a \
 --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe \
 --profile finite-unmasked --case door68_start_a \
 --source-revision b0fa5eb2b5bef5d1066dcf92892a0830811f575e
