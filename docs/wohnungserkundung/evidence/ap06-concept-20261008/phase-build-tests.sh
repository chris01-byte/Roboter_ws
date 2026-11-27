#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
source /evidence/ap06-support-install/setup.bash
source /evidence/ap06-missions-20261005/slam-install/setup.bash
export AP06_SIMULATION=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=220 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd /evidence/ap06-repo
colcon --log-base /evidence/ap06-concept-20261008/phase-build-log build --executor sequential --build-base /evidence/ap06-old-product-build --install-base /evidence/ap06-old-product-install --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore src/robot_navigation src/robot_map_manager src/vl53_near_field src/safety_monitor src/amadeus_lidar_bringup --packages-select amadeus_map_identity base_hardware robot_interfaces bt_orchestrator mission_manager robot_state_estimation explore robot_navigation robot_map_manager vl53_near_field safety_monitor amadeus_lidar_bringup > /evidence/ap06-concept-20261008/phase-build.log 2>&1
source /evidence/ap06-old-product-install/setup.bash
source /evidence/ap06-missions-20261005/navfn-install/setup.bash
python3 -m pytest -q src/explore/test tools/simulation/test_ap06_world.py tools/simulation/test_ap06_device_isolation.py tools/simulation/test_ap06_lifecycle.py tools/simulation/test_ap06_trace.py tools/simulation/test_ap06_concept_experiment.py tools/simulation/test_ap06_departure_probe.py > /evidence/ap06-concept-20261008/phase-affected-tests.log 2>&1
colcon --log-base /evidence/ap06-concept-20261008/phase-colcon-log test --executor sequential --build-base /evidence/ap06-old-product-build --install-base /evidence/ap06-old-product-install --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore src/robot_navigation src/robot_map_manager src/vl53_near_field src/safety_monitor src/amadeus_lidar_bringup --packages-select explore --return-code-on-test-failure > /evidence/ap06-concept-20261008/phase-colcon-tests.log 2>&1
colcon test-result --test-result-base /evidence/ap06-old-product-build/explore --all --verbose > /evidence/ap06-concept-20261008/phase-colcon-results.log 2>&1
