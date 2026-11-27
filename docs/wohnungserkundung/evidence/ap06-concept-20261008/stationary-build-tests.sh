#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
source /evidence/ap06-support-install/setup.bash
source /evidence/ap06-missions-20261005/slam-install/setup.bash
export AP06_SIMULATION=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=220 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd /evidence/ap06-repo
colcon --log-base /evidence/ap06-concept-20261008/stationary-build-log build --executor sequential --build-base /evidence/ap06-old-product-build --install-base /evidence/ap06-old-product-install --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore src/robot_navigation src/robot_map_manager src/vl53_near_field src/safety_monitor src/amadeus_lidar_bringup src/robot_bringup src/semantic_map_manager --packages-select explore > /evidence/ap06-concept-20261008/stationary-build.log 2>&1
source /evidence/ap06-old-product-install/setup.bash
source /evidence/ap06-missions-20261005/navfn-install/setup.bash
colcon --log-base /evidence/ap06-concept-20261008/stationary-colcon-log test --executor sequential --build-base /evidence/ap06-old-product-build --install-base /evidence/ap06-old-product-install --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore src/robot_navigation src/robot_map_manager src/vl53_near_field src/safety_monitor src/amadeus_lidar_bringup src/robot_bringup src/semantic_map_manager --packages-select explore --return-code-on-test-failure > /evidence/ap06-concept-20261008/stationary-colcon-tests.log 2>&1
colcon test-result --test-result-base /evidence/ap06-old-product-build/explore --all --verbose > /evidence/ap06-concept-20261008/stationary-colcon-results.log 2>&1
