# Modular state estimation

The architecture, transfer contract and staged acceptance plan are documented
in `docs/SENSOR_FUSION_ARCHITEKTUR.md` at the workspace root.

This package separates hardware drivers, trust decisions and state estimation.
It never publishes an actuator command.

```text
wheel driver ---- /wheel/odom_raw -- sensor_adapter -- /fusion/wheel_odom --+
OAK/other IMU --- /oak/imu/data ---- sensor_adapter -- /fusion/imu ---------+--> EKF --> /odom + odom->base_link
HWT601-AGV-485 -- /hwt601/imu/data_raw --/ (alternative IMU source)
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

The planned chassis IMU has its own read-only start. It does not start the
OAK, base driver, TF or filter:

```bash
ros2 launch robot_state_estimation hwt601.launch.py
```

After the confirmed external 180-degree scale check, the first integration
stage is an isolated yaw-rate shadow. It requires a fresh explicit stationary
declaration, calibrates once, freezes the bias and publishes only under
`/shadow/hwt601/*`; it creates no odometry or TF:

From the workspace root, use the checked wrapper rather than invoking the
launch file directly. It verifies both serial ports, an empty graph and a
CycloneDDS loopback-only domain before starting:

```bash
AMADEUS_HWT601_STILLSTAND=JA \
  bash tools/sensorfusion/start_hwt601_shadow.sh
```

Direct launch invocation is only an unqualified developer mechanism and is
not an acceptance procedure.

The derived message is in `base_link` because only the measured, aligned Z
axis is retained. Orientation and acceleration are marked unavailable; no
sensor-origin TF is fabricated. See `docs/HWT601_SHADOW.md` for the measured
covariance, isolated ROS-domain procedure and acceptance limits. The warm
600-second standstill acceptance has passed; cold start, temperature, motor
vibration, encoder fusion and production use remain explicitly open.

The next source stage is prepared separately on
`codex/hwt601-encoder-shadow`. It combines the yaw-only HWT shadow with a
dedicated real FC03 encoder reader, but deliberately starts no EKF. A passive
observer must be running before the sources so encoder evidence covers the
startup-bias phase and the subsequent 600-second direct comparison. It checks
monotonic runtime, translation, twist, angle peaks, source counters and ROS
publisher identity. This stage has not yet opened both real ports together;
see `docs/HWT601_ENCODER_SHADOW.md`.

Only after that direct comparison passes may
`hwt601_encoder_shadow_ekf.launch.py` be used as an isolated observation
filter. It publishes only `/shadow/hwt601/odom` and no TF. Its provisional
covariances strongly favour the HWT yaw rate and neither source supplies an
absolute heading reference, so its output is not yet evidence of a solved map
problem or production readiness.

For staged integration use
`robot_bringup/state_estimation_hwt601_validation.launch.py`. Its base remains
hard-coded motorless, while OAK, adapter and EKF all default to off. Exact
wiring, mounting and acceptance are documented in
`docs/HWT601_INTEGRATION.md`; the static mount TF is intentionally absent
until the delivered sensor is physically measured.
