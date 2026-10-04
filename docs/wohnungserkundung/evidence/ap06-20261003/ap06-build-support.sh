#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
export MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd /evidence/ap06-repo
colcon --log-base /evidence/ap06-support-log build --executor sequential --base-paths \
 /evidence/ap06-dependencies/behaviortree_cpp \
 /evidence/ap06-dependencies/cpp_polyfills/tcb_span /evidence/ap06-dependencies/cpp_polyfills/tl_expected \
 /evidence/ap06-dependencies/rsl \
 /evidence/ap06-dependencies/generate_parameter_library/parameter_traits \
 /evidence/ap06-dependencies/generate_parameter_library/generate_parameter_library_py \
 /evidence/ap06-dependencies/generate_parameter_library/generate_parameter_library \
 /evidence/ap06-dependencies/behaviortree_ros2/btcpp_ros2_interfaces \
 /evidence/ap06-dependencies/behaviortree_ros2/behaviortree_ros2 \
 /evidence/ap06-dependencies/control_msgs/control_msgs \
 /evidence/ap06-dependencies/geographic_info/geographic_msgs \
 /evidence/ap06-dependencies/robot_localization /evidence/ap06-dependencies/slam_toolbox \
 /evidence/ap03-navigation2/nav2_behavior_tree /evidence/ap03-navigation2/nav2_bt_navigator \
 /evidence/ap03-navigation2/nav2_collision_monitor /evidence/ap03-navigation2/nav2_velocity_smoother \
 --build-base /evidence/ap06-support-build --install-base /evidence/ap06-support-install \
 --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DBTCPP_UNIT_TESTS=OFF -DBTCPP_EXAMPLES=OFF -DBTCPP_BUILD_TOOLS=OFF \
 > /evidence/ap06-support-build.log 2>&1
