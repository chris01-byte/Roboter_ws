#!/bin/bash
set -eo pipefail
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=230
source /opt/ros/humble/setup.bash
cd /evidence/ap03-navigation2
colcon --log-base /evidence/ap03-nav2-final-log build --packages-up-to nav2_planner nav2_controller nav2_regulated_pure_pursuit_controller nav2_navfn_planner --build-base /evidence/ap03-nav2-build --install-base /evidence/ap03-nav2-install --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release > /evidence/ap03-nav2-final-build.log 2>&1
source /evidence/ap03-nav2-install/setup.bash
cd /repo
colcon --log-base /evidence/ap03-product-final-log build --base-paths src/amadeus_map_identity src/robot_map_manager src/explore src/mission_manager src/robot_state_estimation src/robot_interfaces src/base_hardware src/robot_navigation --build-base /evidence/ap03-build --install-base /evidence/ap03-install > /evidence/ap03-product-final-build.log 2>&1
source /evidence/ap03-install/setup.bash
python3 - <<'PY' > /evidence/ap03-installed-bindings.log
import importlib,sys,hashlib
from ament_index_python.packages import get_package_prefix
print(sys.version)
for name in ('explore.metric_frontier','explore.metric_frontier_runtime','explore.explore_node','amadeus_map_identity.fingerprint','robot_map_manager.robot_map_manager_node','robot_state_estimation._hwt601_clock','robot_navigation.cmd_vel_mission_gate','base_hardware.encoder_shadow_node','robot_interfaces.action','nav2_msgs.action'):
    m=importlib.import_module(name);print(name,m.__file__)
    prefix='/evidence/ap03-nav2-install/' if name=='nav2_msgs.action' else '/evidence/ap03-install/'
    assert m.__file__.startswith(prefix),m.__file__
for pkg in ('nav2_planner','nav2_controller','nav2_navfn_planner','nav2_regulated_pure_pursuit_controller'):
    prefix=get_package_prefix(pkg);print(pkg,prefix);assert prefix.startswith('/evidence/ap03-nav2-install/')
from pathlib import Path
for file in ('metric_frontier.py','metric_frontier_runtime.py','explore_node.py'):
    original=Path('/repo/src/explore/explore')/file
    installed=Path(importlib.import_module('explore').__file__).parent/file
    assert original.read_bytes()==installed.read_bytes()
    print('identical-installed-source',file,hashlib.sha256(installed.read_bytes()).hexdigest())
PY
python3 -m pytest -q --tb=short src/explore/test/test_metric_motion_geometry.py src/explore/test/test_metric_frontier.py src/explore/test/test_metric_map_lifecycle.py > /evidence/ap03-installed-regressions.log 2>&1
export PYTHONPATH=/repo/src/robot_state_estimation/test:/repo/src/robot_navigation/test:$PYTHONPATH
python3 -m pytest -q --tb=short src/explore/test src/amadeus_map_identity/test src/robot_map_manager/test src/robot_state_estimation/test src/base_hardware/test src/robot_navigation/test/test_hwt601_gate_integration.py src/robot_navigation/test/test_hwt601_gate_pending_wheel.py src/mission_manager/test/test_hwt_recovery_mission.py src/mission_manager/test/test_command_payload.py > /evidence/ap03-final-affected-tests.log 2>&1
colcon --log-base /evidence/ap03-test-log test --base-paths src/amadeus_map_identity src/robot_map_manager src/explore src/mission_manager src/robot_state_estimation src/robot_interfaces src/base_hardware src/robot_navigation --packages-select explore amadeus_map_identity robot_map_manager robot_state_estimation base_hardware --build-base /evidence/ap03-build --install-base /evidence/ap03-install --event-handlers console_direct+ > /evidence/ap03-colcon-tests.log 2>&1
colcon test-result --test-result-base /evidence/ap03-build --verbose > /evidence/ap03-colcon-results.log 2>&1
