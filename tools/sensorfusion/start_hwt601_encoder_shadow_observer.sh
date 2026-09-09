#!/usr/bin/env bash
# Start the passive observer before the HWT601/encoder shadow sources.

set -eo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo "Aufruf: $0 /absoluter/lokaler/Ausgabeordner" >&2
  exit 2
fi

requested_output_dir="$1"
if [[ "${requested_output_dir}" != /* ]]; then
  echo "ABBRUCH: Der Ausgabeordner muss absolut sein." >&2
  exit 2
fi

if ! script_path="$(realpath -e -- "${BASH_SOURCE[0]}")"; then
  echo "ABBRUCH: Der Observer-Skriptpfad ist nicht kanonisierbar." >&2
  exit 2
fi
script_dir="$(dirname -- "${script_path}")"
if ! workspace_dir="$(realpath -e -- "${script_dir}/../..")"; then
  echo "ABBRUCH: Der Workspace-Pfad ist nicht kanonisierbar." >&2
  exit 2
fi
if ! output_dir="$(realpath -m -- "${requested_output_dir}")"; then
  echo "ABBRUCH: Der Ausgabeordner ist nicht kanonisierbar." >&2
  exit 2
fi
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

if ! existing_nodes="$(ros2 node list --no-daemon 2>&1)"; then
  echo "ABBRUCH: Die lokale Encoder-Shadow-Domain ist nicht pruefbar:" >&2
  echo "${existing_nodes}" >&2
  exit 4
fi
if [[ -n "${existing_nodes}" ]]; then
  echo "ABBRUCH: Die lokale Encoder-Shadow-Domain ist vor dem Observer nicht leer:" >&2
  echo "${existing_nodes}" >&2
  exit 4
fi

echo "Passiver HWT601-/Encoder-Beobachter startet in Domain ${ROS_DOMAIN_ID}."
echo "Danach den geprueften Quellen-Wrapper in einem zweiten Terminal starten."
exec python3 "${script_dir}/hwt601_encoder_shadow_stillstand.py" \
  --duration 600 --output "${output_dir}"
