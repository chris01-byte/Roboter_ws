#!/bin/bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
colcon --log-base /evidence/ap04-upstream-log build --base-paths /evidence/frontier_exploration_ros2-418e9717564a895214275e088ea7075b8ac88f64 --packages-select frontier_exploration_ros2 --build-base /evidence/ap04-upstream-build --install-base /evidence/ap04-upstream-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source /evidence/ap04-upstream-install/setup.bash
colcon --log-base /evidence/ap04-upstream-test-log test --base-paths /evidence/frontier_exploration_ros2-418e9717564a895214275e088ea7075b8ac88f64 --build-base /evidence/ap04-upstream-build --install-base /evidence/ap04-upstream-install
colcon test-result --test-result-base /evidence/ap04-upstream-build --verbose
cmake -S /evidence/ap04-repo/tools/analysis/frontier_comparison -B /evidence/ap04-probe-build
cmake --build /evidence/ap04-probe-build -j2
