#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
cd /repo
colcon --log-base /evidence/ap01-verified-build-log build --base-paths /evidence/ap01-navigation2/nav2_common /evidence/ap01-navigation2/nav2_msgs src --packages-select nav2_common nav2_msgs amadeus_map_identity explore mission_manager robot_state_estimation robot_interfaces base_hardware --build-base /evidence/ap01-build --install-base /evidence/ap01-install > /evidence/ap01-verified-build.log 2>&1
source /evidence/ap01-install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=226
export PYTHONPATH=/repo/src/robot_state_estimation/test:$PYTHONPATH
python3 -c 'import robot_state_estimation.hwt601_imu_node as raw, robot_state_estimation._hwt601_clock as clock, robot_interfaces, sensor_msgs, rclpy; print("raw",raw.__file__); print("correlation",clock.__file__); print("interfaces",robot_interfaces.__file__); print("sensor_msgs",sensor_msgs.__file__); print("rclpy",rclpy.__file__)' > /evidence/ap01-imports-installed.log
python3 -m pytest -q /repo/src/robot_state_estimation/test/test_hwt601_time_correlation.py /repo/src/robot_state_estimation/test/test_hwt601_raw_development.py > /evidence/ap01-regressions-installed.log 2>&1
export PYTHONPATH=/repo/src/robot_state_estimation:/repo/src/base_hardware:/repo/src/robot_navigation:/repo/src/explore:/repo/src/mission_manager:$PYTHONPATH
python3 -m pytest -q src/robot_state_estimation/test src/base_hardware/test src/robot_navigation/test/test_hwt601_gate_integration.py src/robot_navigation/test/test_hwt601_gate_pending_wheel.py src/robot_navigation/test/test_hwt601_gate_source_callbacks.py src/explore/test/test_hwt601_recovery_integration.py src/explore/test/test_child_result_policy.py src/explore/test/test_exploration_child_goal.py src/mission_manager/test/test_hwt_recovery_mission.py src/mission_manager/test/test_command_payload.py > /evidence/ap01-regressions-final.log 2>&1
colcon --log-base /evidence/ap01-test-log test --base-paths src --packages-select robot_state_estimation base_hardware --build-base /evidence/ap01-build --install-base /evidence/ap01-install --event-handlers console_direct+ > /evidence/ap01-colcon-test.log 2>&1
colcon test-result --test-result-base /evidence/ap01-build --verbose > /evidence/ap01-colcon-results.log 2>&1
