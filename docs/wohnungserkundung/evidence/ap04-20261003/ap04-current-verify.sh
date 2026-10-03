#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
cd /evidence/ap04-repo
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=230
colcon --log-base /evidence/ap04-current-final-build-log build --base-paths \
  /evidence/ap03-navigation2/nav2_common /evidence/ap03-navigation2/nav2_msgs \
  src/amadeus_map_identity src/robot_map_manager src/explore src/mission_manager \
  src/robot_state_estimation src/robot_interfaces src/base_hardware src/robot_navigation \
  --build-base /evidence/ap04-current-build --install-base /evidence/ap04-current-install \
  > /evidence/ap04-current-final-build.log 2>&1
source /evidence/ap04-current-install/setup.bash
python3 - <<'PY' > /evidence/ap04-current-installed-bindings.log
import importlib, inspect, sys
from ament_index_python.packages import get_package_prefix
print(sys.version)
for name in ('explore.explore_node','explore.metric_frontier_runtime','explore.metric_frontier','explore.metric_frontier_candidates',
             'amadeus_map_identity.fingerprint','robot_map_manager.robot_map_manager_node',
             'robot_state_estimation.hwt601_imu_node','robot_state_estimation._hwt601_clock',
             'robot_navigation.cmd_vel_mission_gate','base_hardware.encoder_shadow_node',
             'nav2_msgs.action','robot_interfaces.action','nav_msgs.msg','rclpy'):
    m=importlib.import_module(name)
    print(name, m.__file__)
    if not name.startswith(('nav_msgs','rclpy')):
        assert m.__file__.startswith('/evidence/ap04-current-install/'), m.__file__
for name in ('explore','robot_navigation','robot_map_manager','amadeus_map_identity',
             'robot_state_estimation','base_hardware','robot_interfaces','nav2_msgs'):
    prefix=get_package_prefix(name)
    print('prefix',name,prefix)
    assert prefix.startswith('/evidence/ap04-current-install/'), prefix
from robot_interfaces.action import ExploreArea
from nav2_msgs.action import ComputePathToPose
print('actual actions',ExploreArea.__module__,ComputePathToPose.__module__)
PY
python3 -m pytest -q --tb=short src/explore/test/test_metric_motion_geometry.py src/explore/test/test_metric_map_lifecycle.py \
  src/explore/test/test_metric_frontier.py src/explore/test/test_metric_frontier_candidates.py > /evidence/ap04-current-installed-regressions.log 2>&1
export PYTHONPATH=/evidence/ap04-repo/src/robot_state_estimation/test:/evidence/ap04-repo/src/robot_navigation/test:$PYTHONPATH
python3 -m pytest -q --tb=short src/explore/test src/amadeus_map_identity/test \
  src/robot_map_manager/test src/robot_state_estimation/test src/base_hardware/test \
  src/robot_navigation/test/test_hwt601_gate_integration.py \
  src/robot_navigation/test/test_hwt601_gate_pending_wheel.py \
  src/robot_navigation/test/test_hwt601_gate_source_callbacks.py \
  src/mission_manager/test/test_hwt_recovery_mission.py \
  src/mission_manager/test/test_command_payload.py \
  > /evidence/ap04-current-affected-tests.log 2>&1
colcon --log-base /evidence/ap04-current-test-log test --base-paths \
  src/amadeus_map_identity src/robot_map_manager src/explore src/mission_manager \
  src/robot_state_estimation src/robot_interfaces src/base_hardware src/robot_navigation \
  --packages-select explore amadeus_map_identity robot_map_manager robot_state_estimation base_hardware \
  --build-base /evidence/ap04-current-build --install-base /evidence/ap04-current-install \
  --event-handlers console_direct+ > /evidence/ap04-current-colcon-tests.log 2>&1
colcon test-result --test-result-base /evidence/ap04-current-build --verbose \
  > /evidence/ap04-current-colcon-results.log 2>&1
