#!/usr/bin/env bash
# Start only read-only HWT601 and ESS23 encoder shadow sources.

set -eo pipefail

if [[ "${AMADEUS_HWT601_ENCODER_STILLSTAND:-}" != "JA" ]]; then
  echo "ABBRUCH: AMADEUS_HWT601_ENCODER_STILLSTAND=JA fehlt." >&2
  echo "Nur setzen, wenn das Chassis jetzt tatsaechlich stillsteht." >&2
  exit 2
fi
if [[ "${AMADEUS_BASE_STACK_GESTOPPT:-}" != "JA" ]]; then
  echo "ABBRUCH: AMADEUS_BASE_STACK_GESTOPPT=JA fehlt." >&2
  echo "Der Encoder-Shadow muss alleiniger Master am Motorbus sein." >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_dir="$(cd -- "${script_dir}/../.." && pwd)"

for alias_path in /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE; do
  if [[ ! -e "${alias_path}" ]]; then
    echo "ABBRUCH: ${alias_path} fehlt." >&2
    exit 3
  fi
done
hwt_device="$(readlink -f /dev/ttyUSB_HWT601)"
base_device="$(readlink -f /dev/ttyUSB_BASE)"
if [[ -z "${hwt_device}" || -z "${base_device}" \
      || "${hwt_device}" == "${base_device}" ]]; then
  echo "ABBRUCH: HWT- und Motoralias sind nicht sicher getrennt." >&2
  exit 3
fi

if ! command -v udevadm >/dev/null 2>&1; then
  echo "ABBRUCH: udevadm fuer die Adapteridentitaet fehlt." >&2
  exit 4
fi
if ! base_properties="$(
    udevadm info --query=property --name=/dev/ttyUSB_BASE 2>&1)"; then
  echo "ABBRUCH: Identitaet des Basisadapters nicht lesbar." >&2
  echo "${base_properties}" >&2
  exit 4
fi
if [[ "${base_properties}" != *$'ID_VENDOR_ID=0403'* \
      || "${base_properties}" != *$'ID_MODEL_ID=6001'* \
      || "${base_properties}" != *$'ID_SERIAL_SHORT=BG03R8RZ'* ]]; then
  echo "ABBRUCH: /dev/ttyUSB_BASE ist nicht der abgenommene FTDI-Adapter." >&2
  exit 4
fi
if ! hwt_properties="$(
    udevadm info --query=property --name=/dev/ttyUSB_HWT601 2>&1)"; then
  echo "ABBRUCH: Identitaet des HWT601-Adapters nicht lesbar." >&2
  echo "${hwt_properties}" >&2
  exit 4
fi
if [[ "${hwt_properties}" != *$'ID_VENDOR_ID=1a86'* \
      || "${hwt_properties}" != *$'ID_MODEL_ID=7523'* \
      || "${hwt_properties}" != *'2.4.4.4:1.0'* ]]; then
  echo "ABBRUCH: /dev/ttyUSB_HWT601 ist nicht der abgenommene CH340-Pfad." >&2
  exit 4
fi

if ! command -v fuser >/dev/null 2>&1; then
  echo "ABBRUCH: Portpruefung fuser fehlt." >&2
  exit 5
fi
check_port_free() {
  local port="$1"
  local output
  local status
  set +e
  output="$(fuser "${port}" 2>&1)"
  status=$?
  set -e
  if [[ ${status} -eq 0 ]]; then
    echo "ABBRUCH: Serieller Port wird bereits benutzt: ${port}: ${output}" >&2
    exit 5
  fi
  if [[ ${status} -ne 1 || -n "${output}" ]]; then
    echo "ABBRUCH: Serieller Port nicht sicher pruefbar: ${port}" >&2
    echo "${output}" >&2
    exit 5
  fi
}
check_port_free /dev/ttyUSB_HWT601
check_port_free "${hwt_device}"
check_port_free /dev/ttyUSB_BASE
check_port_free "${base_device}"

source /opt/ros/humble/setup.bash
if [[ ! -f "${workspace_dir}/install/setup.bash" ]]; then
  echo "ABBRUCH: Workspace ist nicht gebaut (${workspace_dir}/install)." >&2
  exit 6
fi
source "${workspace_dir}/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${AMADEUS_HWT_ENCODER_SHADOW_DOMAIN:-145}"
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS xmlns="https://cdds.io/config"><Domain id="any"><General><Interfaces><NetworkInterface name="lo" multicast="false"/></Interfaces><AllowMulticast>false</AllowMulticast></General><Discovery><Peers><Peer address="localhost"/></Peers><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'

if ! existing_nodes="$(ros2 node list --no-daemon 2>&1)"; then
  echo "ABBRUCH: Die lokale Encoder-Shadow-Domain ist nicht pruefbar:" >&2
  echo "${existing_nodes}" >&2
  exit 7
fi
expected_observer="/hwt601_encoder_shadow_stillstand_observer"
if [[ "${existing_nodes}" != "${expected_observer}" ]]; then
  echo "ABBRUCH: Vor dem Quellenstart muss ausschliesslich der passive" >&2
  echo "Observer ${expected_observer} in der lokalen Domain laufen." >&2
  echo "Gefundene Nodes:" >&2
  echo "${existing_nodes}" >&2
  exit 7
fi

echo "HWT601+Encoder-Shadow startet in lokaler Domain ${ROS_DOMAIN_ID}."
echo "Motorbus: ausschliesslich FC03-Leseabfragen; kein cmd_vel, kein TF."
echo "Motorcontroller koennen durch ihre Versorgung weiterhin Haltemoment haben."
exec ros2 launch robot_state_estimation \
  hwt601_encoder_sources_shadow.launch.py \
  operator_stationary_confirmed:=true
