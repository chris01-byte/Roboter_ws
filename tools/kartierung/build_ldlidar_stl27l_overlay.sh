#!/usr/bin/env bash
# Baut den gepinnten STL-27L-Treiber mit der engen Shutdown-Race-Korrektur in
# einem separaten ROS-Overlay. /opt, Shell-Profile und bestehende Overlays
# werden nicht veraendert.

set -euo pipefail

readonly PINNED_COMMIT="bf668a89baf722a787dadc442860dcbf33a82f5a"
readonly UPSTREAM_URL="https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2.git"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
MANIFEST="${REPO_ROOT}/vendor_ldlidar_stl_ros2.repos"
PATCH_FILE="${REPO_ROOT}/patches/ldlidar_stl27l_clean_shutdown.patch"
DEFAULT_OVERLAY="${HOME}/amadeus_lidar_shutdown_ws"

die() {
  printf 'FEHLER: %s\n' "$*" >&2
  exit 1
}

if [[ $# -gt 1 ]]; then
  printf 'Aufruf: %s [OVERLAY_WORKSPACE]\n' "$0" >&2
  exit 2
fi

OVERLAY_WS="${1:-${AMADEUS_LIDAR_SHUTDOWN_OVERLAY_WS:-${DEFAULT_OVERLAY}}}"
SOURCE_DIR="${OVERLAY_WS}/src/ldlidar_stl_ros2"

[[ -n "${OVERLAY_WS}" ]] || die "Leerer Overlay-Pfad ist unzulaessig."
case "${OVERLAY_WS}" in
  /|/opt|/opt/ros|/opt/ros/humble|"${REPO_ROOT}")
    die "Unsicherer Overlay-Pfad: ${OVERLAY_WS}"
    ;;
esac
[[ ${EUID} -ne 0 ]] || die "Nicht als root ausfuehren."
[[ -r "${MANIFEST}" ]] || die "Manifest fehlt: ${MANIFEST}"
[[ -r "${PATCH_FILE}" ]] || die "Patch fehlt: ${PATCH_FILE}"
[[ -r /opt/ros/humble/setup.bash ]] || die "ROS 2 Humble fehlt."

for command_name in git vcs colcon; do
  command -v "${command_name}" >/dev/null 2>&1 ||
    die "Programm '${command_name}' fehlt."
done

set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
set -u
command -v ros2 >/dev/null 2>&1 || die "ROS-Programm 'ros2' fehlt."

mkdir -p "${OVERLAY_WS}/src"
if [[ ! -e "${SOURCE_DIR}" ]]; then
  vcs import "${OVERLAY_WS}/src" < "${MANIFEST}"
fi

[[ -d "${SOURCE_DIR}/.git" ]] ||
  die "${SOURCE_DIR} ist kein Git-Checkout. Nichts wurde ueberschrieben."
[[ "$(git -C "${SOURCE_DIR}" remote get-url origin)" == "${UPSTREAM_URL}" ]] ||
  die "Unerwartetes Origin in ${SOURCE_DIR}."
[[ "$(git -C "${SOURCE_DIR}" rev-parse HEAD)" == "${PINNED_COMMIT}" ]] ||
  die "Unerwarteter Treibercommit. Nichts wurde zurueckgesetzt."

if git -C "${SOURCE_DIR}" apply --reverse --check "${PATCH_FILE}" \
    >/dev/null 2>&1; then
  printf 'Shutdown-Korrektur ist bereits angewendet.\n'
elif git -C "${SOURCE_DIR}" diff --quiet &&
     git -C "${SOURCE_DIR}" diff --cached --quiet &&
     [[ -z "$(git -C "${SOURCE_DIR}" ls-files --others --exclude-standard)" ]]; then
  git -C "${SOURCE_DIR}" apply --check "${PATCH_FILE}"
  git -C "${SOURCE_DIR}" apply "${PATCH_FILE}"
  printf 'Shutdown-Korrektur wurde angewendet.\n'
else
  die "Checkout enthaelt unbekannte Aenderungen."
fi

git -C "${SOURCE_DIR}" diff --check
(
  cd -- "${OVERLAY_WS}"
  colcon build --symlink-install --packages-select ldlidar_stl_ros2 \
    --cmake-args -DCMAKE_BUILD_TYPE=Release
)

set +u
# shellcheck disable=SC1091
source "${OVERLAY_WS}/install/setup.bash"
set -u

expected_prefix="${OVERLAY_WS}/install/ldlidar_stl_ros2"
resolved_prefix="$(ros2 pkg prefix ldlidar_stl_ros2)"
[[ "${resolved_prefix}" == "${expected_prefix}" ]] ||
  die "ROS findet ${resolved_prefix} statt ${expected_prefix}."

printf 'FERTIG: source %q\n' "${OVERLAY_WS}/install/setup.bash"
printf 'Rueckfall: frische Shell verwenden und dieses Overlay nicht sourcen.\n'
