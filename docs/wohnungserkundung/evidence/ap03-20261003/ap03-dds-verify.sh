#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
source /evidence/ap03-install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=229
export PYTHONPATH=/repo/src/robot_state_estimation/test:/repo/src/robot_navigation/test:$PYTHONPATH
cd /repo
for variant in default-False default-True imu_status-False imu_status-True; do
  python3 -m pytest -q --tb=short "src/robot_navigation/test/test_hwt601_gate_source_callbacks.py::test_passive_wheel_continues_during_busy_callback[$variant]" > "/evidence/ap03-dds-$variant.log" 2>&1
done
