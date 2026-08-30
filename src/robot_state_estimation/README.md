# Modular state estimation

The architecture, transfer contract and staged acceptance plan are documented
in `docs/SENSOR_FUSION_ARCHITEKTUR.md` at the workspace root.

This package separates hardware drivers, trust decisions and state estimation.
It never publishes an actuator command.

```text
wheel driver ---- /wheel/odom_raw -- sensor_adapter -- /fusion/wheel_odom --+
OAK/other IMU --- /oak/imu/data ---- sensor_adapter -- /fusion/imu ---------+--> EKF --> /odom + odom->base_link
independent LiDAR/visual/floor motion --------------- /fusion/reference_odom -+    (quality monitor only at first)

/scan_normiert + /fusion/imu --> scan_quality_gate --> /scan_qualitaet --> SLAM
SLAM remains the sole publisher of map->odom.
```

The EKF is the maintained ROS `robot_localization` implementation.  Project
code is limited to message validation, covariance handling, diagnostics,
motion disagreement detection and the selective scan gate.

## Sensor contract

- A wheel, visual, LiDAR or floor-motion adapter publishes
  `nav_msgs/Odometry`, uses `child_frame_id=base_link` and supplies measured,
  non-zero covariance.  It never publishes `map->odom`.
- An IMU adapter publishes `sensor_msgs/Imu` in its physical sensor frame.
  The static TF to `base_link` is mandatory; the driver or URDF owns it.
- Global corrections and loop closures stay in SLAM/localization and own
  `map->odom`.  They are not mixed into the continuous local EKF.
- Unknown axes use a large covariance or are disabled in the EKF selection
  vector.  Zero covariance must never mean “perfect” by accident.

Adding a new sensor normally requires one adapter and one YAML profile, not a
change to the quality core.  The first Amadeus profile fuses encoder forward
and yaw velocity with OAK yaw rate.  OAK orientation and acceleration remain
disabled until measured.  An independent odometry source can already be
connected to `/fusion/reference_odom`; it initially changes wheel confidence
only and never replaces motion with a guess.

An optional local LiDAR matcher is included for that reference.  It receives
only scans that passed the IMU gate, does not read wheel odometry, stops on
weak or ambiguous geometry and publishes neither TF nor commands.  It is off
by default (`start_lidar_reference:=false`) until its real-motion covariance
and thresholds have been measured.  Visual odometry or a floor-flow sensor can
replace it on the same topic without changing the adapter or EKF.

After such a source has passed its real acceptance test, select
`config/ekf_encoder_imu_reference.yaml`.  Until then the default
`ekf_encoder_imu.yaml` keeps the source in monitor-only mode.

## Safe start

`fusion.launch.py` starts only passive subscribers, publishers and the EKF. It
does not start `base_hardware`, a camera, a LiDAR or any motor path:

```bash
ros2 launch robot_state_estimation fusion.launch.py
```

For Amadeus, the base driver must eventually publish raw encoder odometry on
`/wheel/odom_raw` with `publish_tf=false`.  The EKF is then the only owner of
`odom->base_link`, and SLAM consumes `/odom` plus `/scan_qualitaet`.  This
production switchover is intentionally separate from the initial parallel,
motorless validation.

Rollback is immediate: stop this launch and use the existing base driver on
`/odom` with `publish_tf=true`.  No motor registers or calibration values are
changed by this package.

Amadeus also provides a deliberately non-overridable motorless validation
launch.  It starts the base with `dry_run=true`, publishes raw wheel odometry,
starts the OAK IMU and then the fusion stack:

```bash
ros2 launch robot_bringup state_estimation_validation.launch.py
```

The STL-27L and the independent reference stay off unless explicitly enabled
with `start_lidar:=true start_lidar_reference:=true`.  Even then, the base
remains hard-coded to dry-run.
