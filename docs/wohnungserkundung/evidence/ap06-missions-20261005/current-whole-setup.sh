#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap06-missions-20261005/current-map-support-install/setup.bash
source /evidence/ap03-nav2-install/setup.bash
source /evidence/ap06-support-install/setup.bash
source /evidence/ap06-missions-20261005/slam-install/setup.bash
source /evidence/ap06-product-install/setup.bash
export LD_LIBRARY_PATH=/evidence/ap06-missions-20261005/current-native-runtime-libs:$LD_LIBRARY_PATH
export AP06_SIMULATION=1 ROS_LOCALHOST_ONLY=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
