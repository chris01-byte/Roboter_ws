#!/usr/bin/env bash
# Start only the isolated, no-TF HWT601/encoder shadow EKF.

set -eo pipefail

if [[ "${AMADEUS_HWT_ENCODER_EKF_STILLSTAND:-}" != "JA" ]]; then
  echo "ABBRUCH: AMADEUS_HWT_ENCODER_EKF_STILLSTAND=JA fehlt." >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_dir="$(cd -- "${script_dir}/../.." && pwd)"
source /opt/ros/humble/setup.bash
source "${workspace_dir}/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${AMADEUS_HWT_ENCODER_SHADOW_DOMAIN:-145}"
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS xmlns="https://cdds.io/config"><Domain id="any"><General><Interfaces><NetworkInterface name="lo" multicast="false"/></Interfaces><AllowMulticast>false</AllowMulticast></General><Discovery><Peers><Peer address="localhost"/></Peers><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'

existing_nodes="$(ros2 node list --no-daemon 2>&1)"
expected_nodes=$'/hwt601_encoder_shadow_reader\n/hwt601_encoder_shadow_stillstand_observer\n/hwt601_shadow\n/hwt601_shadow_reader'
if [[ "$(printf '%s\n' "${existing_nodes}" | sort)" != "${expected_nodes}" ]]; then
  echo "ABBRUCH: Vor dem EKF-Start werden exakt Beobachter und drei Quellen erwartet." >&2
  echo "Gefundene Nodes:" >&2
  echo "${existing_nodes}" >&2
  exit 3
fi

echo "Isoliertes HWT601-/Encoder-EKF startet ohne TF und Kontrolleingang."
exec ros2 launch robot_state_estimation hwt601_encoder_shadow_ekf.launch.py
