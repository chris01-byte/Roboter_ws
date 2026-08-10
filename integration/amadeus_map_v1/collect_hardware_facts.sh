#!/usr/bin/env bash
# Read-only inventory for the later Amadeus SLAM/Nav2 integration.
# It never publishes a topic, calls a service, starts a node or moves hardware.
set -u

report_path="${1:-./amadeus-map-hardware-report-$(date -u +%Y%m%dT%H%M%SZ).md}"

if ! command -v ros2 >/dev/null 2>&1; then
  echo "ros2 wurde nicht gefunden. Zuerst ROS 2 Humble sourcen." >&2
  exit 2
fi
if ! command -v timeout >/dev/null 2>&1; then
  echo "timeout wurde nicht gefunden (Paket coreutils)." >&2
  exit 2
fi

run_section() {
  local title="$1"
  shift
  {
    printf '\n## %s\n\n```text\n' "$title"
    "$@" 2>&1
    local command_status=$?
    printf '\n[exit=%s]\n```\n' "$command_status"
  } >> "$report_path"
}

{
  printf '# Amadeus Hardware-/ROS-Inventur\n\n'
  printf -- '- Erzeugt: `%s`\n' "$(date -Iseconds)"
  printf -- '- Host: `%s`\n' "$(hostname)"
  printf -- '- Arbeitsverzeichnis: `%s`\n' "$(pwd)"
  printf '\nDieses Protokoll wurde ausschließlich mit lesenden Befehlen erzeugt.\n'
} > "$report_path"

run_section "Kernel und Architektur" uname -a
run_section "Betriebssystem" cat /etc/os-release
run_section "ROS-Umgebung" \
  bash -c 'printf "ROS_DISTRO=%s\nROS_DOMAIN_ID=%s\nRMW_IMPLEMENTATION=%s\nCYCLONEDDS_URI=%s\n" \
    "${ROS_DISTRO:-}" "${ROS_DOMAIN_ID:-}" "${RMW_IMPLEMENTATION:-}" "${CYCLONEDDS_URI:-}"'
run_section "ROS-Diagnose" timeout 30 ros2 doctor --report
run_section "ROS-Pakete für Mapping und Navigation" \
  bash -c "ros2 pkg list | grep -E '(^|_)(rtabmap|depthai|nav2|navigation2|robot_localization|slam_toolbox)' || true"
run_section "Aktive Nodes" timeout 15 ros2 node list
run_section "Topics mit Typen" timeout 15 ros2 topic list -t
run_section "Actions mit Typen" timeout 15 ros2 action list -t
run_section "Publisher und QoS von /map" timeout 15 ros2 topic info /map --verbose
run_section "Ein OccupancyGrid-Snapshot" \
  timeout 20 ros2 topic echo /map --once \
    --qos-durability transient_local --qos-reliability reliable
run_section "Publisher und QoS von /odom" timeout 15 ros2 topic info /odom --verbose
run_section "Publisher und QoS von /cmd_vel" timeout 15 ros2 topic info /cmd_vel --verbose
run_section "Publisher und QoS von /cmd_vel_nav" timeout 15 ros2 topic info /cmd_vel_nav --verbose
run_section "Publisher und QoS von /cmd_vel_smoothed" \
  timeout 15 ros2 topic info /cmd_vel_smoothed --verbose
run_section "TF map nach base_link" timeout 12 ros2 run tf2_ros tf2_echo map base_link
run_section "TF odom nach base_footprint" \
  timeout 12 ros2 run tf2_ros tf2_echo odom base_footprint
run_section "Sensornahe Topics" \
  bash -c "ros2 topic list -t | grep -Ei 'oak|camera|image|depth|points|cloud|imu|scan|wheel|encoder|odom' || true"

printf 'Bericht geschrieben: %s\n' "$report_path"
