#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
cd /evidence/ap04-repo
colcon --log-base /evidence/ap04-native-product-log build --base-paths \
 src/amadeus_map_identity src/robot_map_manager src/explore src/mission_manager \
 src/robot_state_estimation src/robot_interfaces src/base_hardware src/robot_navigation \
 --build-base /evidence/ap04-native-product-build --install-base /evidence/ap04-native-product-install \
 > /evidence/ap04-native-product-build.log 2>&1
source /evidence/ap04-native-product-install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=228
python3 - <<'PY' > /evidence/ap04-native-bindings.log
import importlib
from ament_index_python.packages import get_package_prefix
for name in ('explore.explore_node','explore.metric_frontier_runtime','explore.metric_frontier_candidates','robot_interfaces.action'):
 m=importlib.import_module(name);print(name,m.__file__)
 assert m.__file__.startswith('/evidence/ap04-native-product-install/'),m.__file__
for name in ('nav2_planner','nav2_navfn_planner','nav2_msgs'):
 print(name,get_package_prefix(name))
 assert get_package_prefix(name).startswith('/evidence/ap03-nav2-install/'),name
PY
python3 tools/analysis/frontier_comparison/nav2_check.py --repo "$PWD" \
 --comparison /evidence/ap04-final-comparison.json --output /evidence/ap04-native-acceptance \
 > /evidence/ap04-native-acceptance.log 2>&1
