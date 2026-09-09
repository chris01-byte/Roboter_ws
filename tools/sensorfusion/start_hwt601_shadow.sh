#!/usr/bin/env bash
# Isolated passive HWT601 yaw-rate shadow. Never starts a drive component.

set -eo pipefail

if [[ "${AMADEUS_HWT601_STILLSTAND:-}" != "JA" ]]; then
  echo "ABBRUCH: AMADEUS_HWT601_STILLSTAND=JA fehlt." >&2
  echo "Nur setzen, wenn das Chassis jetzt tatsaechlich stillsteht." >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_dir="$(cd -- "${script_dir}/../.." && pwd)"

if [[ ! -e /dev/ttyUSB_HWT601 ]]; then
  echo "ABBRUCH: /dev/ttyUSB_HWT601 fehlt." >&2
  exit 3
fi
if [[ ! -e /dev/ttyUSB_BASE ]]; then
  echo "ABBRUCH: /dev/ttyUSB_BASE fehlt; Porttrennung nicht pruefbar." >&2
  exit 3
fi
hwt_device="$(readlink -f /dev/ttyUSB_HWT601)"
base_device="$(readlink -f /dev/ttyUSB_BASE)"
if [[ -z "${hwt_device}" || "${hwt_device}" == "${base_device}" ]]; then
  echo "ABBRUCH: HWT- und Motoralias sind nicht sicher getrennt." >&2
  exit 3
fi
if ! command -v fuser >/dev/null 2>&1; then
  echo "ABBRUCH: Portpruefung fuser fehlt." >&2
  exit 4
fi
check_port_free() {
  local port="$1"
  local label="$2"
  local output
  local status
  set +e
  output="$(fuser "${port}" 2>&1)"
  status=$?
  set -e
  if [[ ${status} -eq 0 ]]; then
    echo "ABBRUCH: ${label} wird bereits benutzt: ${output}" >&2
    exit 4
  fi
  if [[ ${status} -ne 1 || -n "${output}" ]]; then
    echo "ABBRUCH: ${label} konnte nicht sicher geprueft werden." >&2
    echo "${output}" >&2
    exit 4
  fi
}
check_port_free /dev/ttyUSB_HWT601 "Der HWT-Port"
check_port_free /dev/ttyUSB_BASE "Der Motorport"

source /opt/ros/humble/setup.bash
if [[ ! -f "${workspace_dir}/install/setup.bash" ]]; then
  echo "ABBRUCH: Workspace ist nicht gebaut (${workspace_dir}/install)." >&2
  exit 5
fi
source "${workspace_dir}/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${AMADEUS_HWT_SHADOW_DOMAIN:-144}"
# The system-wide CycloneDDS profile contains WLAN peers. Replace it for this
# process tree with an explicit loopback-only unicast profile. Do not combine
# this with ROS_LOCALHOST_ONLY=1, which would select loopback twice on Humble.
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS xmlns="https://cdds.io/config"><Domain id="any"><General><Interfaces><NetworkInterface name="lo" multicast="false"/></Interfaces><AllowMulticast>false</AllowMulticast></General><Discovery><Peers><Peer address="localhost"/></Peers><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'

if ! existing_nodes="$(ros2 node list --no-daemon 2>&1)"; then
  echo "ABBRUCH: Die lokale Shadow-Domain konnte nicht geprueft werden:" >&2
  echo "${existing_nodes}" >&2
  exit 6
fi
if [[ -n "${existing_nodes}" ]]; then
  echo "ABBRUCH: Die lokale Shadow-Domain ist nicht leer:" >&2
  echo "${existing_nodes}" >&2
  exit 6
fi

echo "HWT601-Shadow startet in lokaler Domain ${ROS_DOMAIN_ID}."
echo "Nur /shadow/hwt601/*; Bias nach Startkalibrierung fest eingefroren."
exec ros2 launch robot_state_estimation hwt601_shadow.launch.py \
  operator_stationary_confirmed:=true
