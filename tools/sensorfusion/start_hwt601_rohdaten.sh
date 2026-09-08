#!/usr/bin/env bash
# Only this checkout's passive reader. No base, OAK, EKF or static TF.
set -eo pipefail
HWT_WORKSPACE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -f "$HWT_WORKSPACE/install/local_setup.bash" ]]; then
    echo "HWT-Overlay fehlt: robot_state_estimation in diesem Worktree bauen." >&2
    exit 2
fi
source /opt/ros/humble/setup.bash
source "$HWT_WORKSPACE/install/local_setup.bash"
exec ros2 launch robot_state_estimation hwt601.launch.py
