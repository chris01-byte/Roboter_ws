#!/usr/bin/env bash
# Start the passive EKF observer before sources and filter.

set -eo pipefail

if [[ $# -ne 1 || -z "$1" || "$1" != /* ]]; then
  echo "Aufruf: $0 /absoluter/lokaler/Ausgabeordner" >&2
  exit 2
fi

script_path="$(realpath -e -- "${BASH_SOURCE[0]}")"
script_dir="$(dirname -- "${script_path}")"
workspace_dir="$(realpath -e -- "${script_dir}/../..")"
output_dir="$(realpath -m -- "$1")"
if [[ -e "${output_dir}" ]]; then
  echo "ABBRUCH: Der Ausgabeordner existiert bereits: ${output_dir}" >&2
  exit 2
fi
case "${output_dir}/" in
  "${workspace_dir}/"*)
    echo "ABBRUCH: Reale Messdaten duerfen nicht im Repository liegen." >&2
    exit 2
    ;;
esac

source /opt/ros/humble/setup.bash
if [[ ! -f "${workspace_dir}/install/setup.bash" ]]; then
  echo "ABBRUCH: Workspace ist nicht gebaut (${workspace_dir}/install)." >&2
  exit 3
fi
source "${workspace_dir}/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${AMADEUS_HWT_ENCODER_SHADOW_DOMAIN:-145}"
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS xmlns="https://cdds.io/config"><Domain id="any"><General><Interfaces><NetworkInterface name="lo" multicast="false"/></Interfaces><AllowMulticast>false</AllowMulticast></General><Discovery><Peers><Peer address="localhost"/></Peers><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'

existing_nodes="$(ros2 node list --no-daemon 2>&1)"
if [[ -n "${existing_nodes}" ]]; then
  echo "ABBRUCH: Domain ${ROS_DOMAIN_ID} ist nicht leer:" >&2
  echo "${existing_nodes}" >&2
  exit 3
fi

echo "Passiver EKF-Stillstandsbeobachter startet in Domain ${ROS_DOMAIN_ID}."
exec python3 "${script_dir}/hwt601_encoder_shadow_ekf_stillstand.py" \
  --duration 120 --output "${output_dir}"
