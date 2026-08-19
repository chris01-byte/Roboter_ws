#!/usr/bin/env bash
# Baut den fuer Amadeus benoetigten slam_toolbox-Humble-Backport als separates
# ROS-Overlay. Das Skript veraendert weder /opt/ros/humble noch Shell-Profile.

set -euo pipefail

readonly PINNED_COMMIT="51a99767b3e2ed4076ae5763ff14b69343ffd884"
readonly UPSTREAM_URL="https://github.com/SteveMacenski/slam_toolbox.git"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
MANIFEST="${REPO_ROOT}/vendor_slam_toolbox_humble.repos"
PATCH_FILE="${REPO_ROOT}/patches/slam_toolbox_humble_pure_rotation.patch"
DEFAULT_OVERLAY="${HOME}/amadeus_slam_toolbox_ws"

usage() {
  printf 'Aufruf: %s [OVERLAY_WORKSPACE]\n' "$0"
  printf 'Standard: %s\n' "${DEFAULT_OVERLAY}"
}

die() {
  printf 'FEHLER: %s\n' "$*" >&2
  exit 1
}

verify_patched_tree() {
  local expected_hash path actual_hash
  local expected_paths actual_paths
  expected_paths="$(printf '%s\n' \
    'include/slam_toolbox/slam_toolbox_common.hpp' \
    'lib/karto_sdk/include/karto_sdk/Mapper.h' \
    'lib/karto_sdk/src/Mapper.cpp' \
    'src/slam_toolbox_common.cpp')"
  actual_paths="$(git -C "${SOURCE_DIR}" diff --name-only | LC_ALL=C sort)"
  [[ "${actual_paths}" == "${expected_paths}" ]] ||
    die "Neben dem Amadeus-Backport liegen weitere Aenderungen vor."

  while read -r expected_hash path; do
    actual_hash="$(git -C "${SOURCE_DIR}" hash-object "${path}")"
    [[ "${actual_hash}" == "${expected_hash}" ]] ||
      die "Unerwarteter Inhalt nach Backport: ${path}"
  done <<'PATCHED_BLOB_HASHES'
a416bea22de4ae2d41a159e157673a03c85668a0 include/slam_toolbox/slam_toolbox_common.hpp
9f09d6392acfba5793d2d582c13261e074312e64 lib/karto_sdk/include/karto_sdk/Mapper.h
6ef0688b4f19bcea4b3eaab9fa930e4d9a8fe572 lib/karto_sdk/src/Mapper.cpp
80be7a5ddfd82723cec3ede83553eb35d1ed670d src/slam_toolbox_common.cpp
PATCHED_BLOB_HASHES
}

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi

OVERLAY_WS="${1:-${AMADEUS_SLAM_TOOLBOX_OVERLAY_WS:-${DEFAULT_OVERLAY}}}"
SOURCE_DIR="${OVERLAY_WS}/src/slam_toolbox"

[[ -n "${OVERLAY_WS}" ]] || die "Leerer Overlay-Pfad ist unzulaessig."
case "${OVERLAY_WS}" in
  /|/opt|/opt/ros|/opt/ros/humble|"${REPO_ROOT}")
    die "Unsicherer Overlay-Pfad: ${OVERLAY_WS}"
    ;;
esac

[[ ${EUID} -ne 0 ]] || die "Nicht als root ausfuehren. Das Overlay gehoert in das Benutzerkonto."
[[ -r "${MANIFEST}" ]] || die "Manifest fehlt: ${MANIFEST}"
[[ -r "${PATCH_FILE}" ]] || die "Patch fehlt: ${PATCH_FILE}"
[[ -r /opt/ros/humble/setup.bash ]] || die "ROS 2 Humble wurde unter /opt/ros/humble nicht gefunden."

for command_name in git vcs colcon ros2; do
  command -v "${command_name}" >/dev/null 2>&1 ||
    die "Programm '${command_name}' fehlt. Benoetigt werden git, python3-vcstool und python3-colcon-common-extensions."
done

# ROS-Setup-Skripte koennen Variablen lesen, die vorher noch nicht gesetzt sind.
set +u
# Existierender, oben gepruefter ROS-Systempfad.
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
set -u

mkdir -p "${OVERLAY_WS}/src"

if [[ ! -e "${SOURCE_DIR}" ]]; then
  printf 'Importiere offiziellen slam_toolbox-Stand %s ...\n' "${PINNED_COMMIT}"
  vcs import "${OVERLAY_WS}/src" < "${MANIFEST}"
fi

[[ -d "${SOURCE_DIR}/.git" ]] ||
  die "${SOURCE_DIR} existiert, ist aber kein Git-Checkout. Nichts wurde ueberschrieben."

actual_origin="$(git -C "${SOURCE_DIR}" remote get-url origin)"
[[ "${actual_origin}" == "${UPSTREAM_URL}" ]] ||
  die "Unerwartetes Origin in ${SOURCE_DIR}: ${actual_origin}"

actual_commit="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${actual_commit}" == "${PINNED_COMMIT}" ]] ||
  die "Checkout steht auf ${actual_commit}, erwartet ist ${PINNED_COMMIT}. Nichts wurde zurueckgesetzt."

if git -C "${SOURCE_DIR}" apply --unidiff-zero --reverse --check \
  "${PATCH_FILE}" >/dev/null 2>&1; then
  git -C "${SOURCE_DIR}" diff --cached --quiet ||
    die "Der Checkout enthaelt vorgemerkte Aenderungen."
  [[ -z "$(git -C "${SOURCE_DIR}" ls-files --others --exclude-standard)" ]] ||
    die "Der Checkout enthaelt unbekannte Dateien."
  verify_patched_tree
  printf 'Amadeus-Backport ist bereits angewendet.\n'
elif git -C "${SOURCE_DIR}" diff --quiet &&
     git -C "${SOURCE_DIR}" diff --cached --quiet &&
     [[ -z "$(git -C "${SOURCE_DIR}" ls-files --others --exclude-standard)" ]]; then
  git -C "${SOURCE_DIR}" apply --unidiff-zero --check "${PATCH_FILE}"
  git -C "${SOURCE_DIR}" apply --unidiff-zero "${PATCH_FILE}"
  printf 'Amadeus-Backport wurde angewendet.\n'
else
  die "Checkout enthaelt unbekannte Aenderungen. Diese werden nicht ueberschrieben."
fi

git -C "${SOURCE_DIR}" diff --check

printf 'Baue separates Overlay in %s ...\n' "${OVERLAY_WS}"
(
  cd -- "${OVERLAY_WS}"
  colcon build \
    --symlink-install \
    --packages-select slam_toolbox \
    --cmake-args -DCMAKE_BUILD_TYPE=Release
)

set +u
# Dynamischer, unmittelbar zuvor gebauter Pfad.
# shellcheck disable=SC1091
source "${OVERLAY_WS}/install/setup.bash"
set -u

resolved_prefix="$(ros2 pkg prefix slam_toolbox)"
expected_prefix="${OVERLAY_WS}/install/slam_toolbox"
[[ "${resolved_prefix}" == "${expected_prefix}" ]] ||
  die "Overlay wurde gebaut, aber ROS findet ${resolved_prefix} statt ${expected_prefix}."

printf '\nFERTIG: ROS verwendet in dieser Shell den gepatchten Stand:\n'
printf '  %s\n' "${resolved_prefix}"
printf '\nVor dem Start von Amadeus in jedem neuen Terminal sourcen:\n'
printf '  source %q\n' "${OVERLAY_WS}/install/setup.bash"
printf '\nKontrolle:\n'
printf '  ros2 pkg prefix slam_toolbox\n'
printf '  ros2 param get /slam_toolbox check_min_dist_and_heading_precisely\n'
printf '\nRueckfall ohne Dateiaenderung:\n'
printf '  Ein neues Terminal oeffnen und nur /opt/ros/humble/setup.bash sowie den normalen roboter_ws sourcen.\n'
printf '  Das Overlay nicht sourcen; dann wird wieder das unveraenderte apt-Paket benutzt.\n'
