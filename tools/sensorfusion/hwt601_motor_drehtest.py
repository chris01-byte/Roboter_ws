#!/usr/bin/env python3
"""Supervised single left turn. Default is passive preflight, never drive.

Requires separately started, isolated base driver. No launch/config writes.
LiDAR raw-scan odometry is independent of IMU and wheels. Local JSONL only.
"""
import argparse
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import select
import sys
import time

from hwt601_bias_stillstand import Integral, profile_config
from robot_state_estimation.quality_core import GyroBiasEstimator

COMMAND = '/hwt_test/cmd_vel'


def angle_delta(a, b):
    return math.atan2(math.sin(a-b), math.cos(a-b))


def base_healthy(state, age):
    return (age <= .3 and state.get('dry_run') is False
            and state.get('allow_rs485') is True
            and state.get('rs485_ready') is True
            and state.get('encoder_feedback_ok') is True
            and state.get('encoder_initialized') is True
            and state.get('encoder_stale') is False
            and state.get('encoder_config_fault_latched') is False)


def stationary(state):
    return all(isinstance(state.get(k), (int, float))
               and math.isfinite(state[k]) and abs(state[k]) <= .01
               for k in ('meas_v_mps', 'meas_w_radps'))


def drive_decision(elapsed, lidar_deg, encoder_deg, displacement, imu_deg):
    values = (elapsed, lidar_deg, encoder_deg, displacement, imu_deg)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Nicht-endlicher Bewegungswert')
    if elapsed > 24 or min(lidar_deg, encoder_deg) < -2:
        raise ValueError('Zeitlimit oder falsche Drehrichtung')
    if encoder_deg > 105 or abs(imu_deg) > 120 or displacement > .12:
        raise ValueError('Winkel-/Translationsgrenze')
    if elapsed > 4 and min(lidar_deg, encoder_deg) < 2:
        raise ValueError('Kein bestaetigter Drehfortschritt')
    if abs(lidar_deg - encoder_deg) > 12:
        raise ValueError('LiDAR und Encoder widersprechen sich')
    return 0.0 if lidar_deg >= 88 else .10


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute and (os.environ.get('AMADEUS_FAHRFREIGABE') != 'JA'
                         or not sys.stdin.isatty()):
        parser.error('Echter Lauf braucht persoenliche Freigabe/TTY und AMADEUS_FAHRFREIGABE=JA')
    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu
    from std_msgs.msg import String
    from rclpy.qos import qos_profile_sensor_data

    rclpy.init()
    node = rclpy.create_node('hwt_motor_drehtest')
    output = Path.home()/'.local/share/amadeus/hwt601'/time.strftime('powered-%Y%m%d-%H%M%S')
    output.mkdir(parents=True, exist_ok=False)
    log = (output/'samples.jsonl').open('x')
    data = {}
    bias = GyroBiasEstimator(replace(profile_config(), stationary_adaptation_time_constant_s=0.0))
    integral = Integral()
    phase = 'preflight'
    fault = None
    fixed = None
    publisher = None
    summary = {'complete': False, 'passed': False, 'execute': args.execute,
               'fusion_ready': False, 'reference': 'lidar_raw_scan_only',
               'collision_monitor': False, 'supervision_required': True}

    def receive(key, value):
        data[key] = (time.monotonic(), value)
        log.write(json.dumps({'received_monotonic_s':data[key][0], 'kind':key,
                              'phase':phase, 'value':value}, allow_nan=False)+'\n')

    def imu(m):
        nonlocal fault
        try:
            stamp = m.header.stamp.sec + m.header.stamp.nanosec*1e-9
            raw = (m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z)
            acc = (m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z)
            if m.header.frame_id != 'hwt601_link' or not all(math.isfinite(v) for v in (*raw,*acc,stamp)):
                raise ValueError('IMU-Frame/Werte ungueltig')
            if abs(time.time()-stamp) > .1 or not 9.0 <= math.sqrt(sum(v*v for v in acc)) <= 11.0:
                raise ValueError('IMU-Zeit/Beschleunigung ungueltig')
            receive('imu', {'stamp':stamp,'gyro':raw,'accel':acc})
            if phase == 'calibrating':
                bias.update(stamp, raw, stationary(data.get('base',(0,{}))[1]))
            if phase in ('turning', 'stopping'):
                integral.add(stamp, tuple(v-b for v,b in zip(raw,fixed)))
                if max(abs(v-b) for v,b in zip(raw,fixed)) > .5 or max(integral.peak[:2]) > 3:
                    raise ValueError('IMU-Drehrate/Kippgrenze')
        except Exception as exc:
            fault = str(exc)

    def odom(m):
        q=m.pose.pose.orientation
        stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        receive('lidar', {'stamp':stamp,'yaw':yaw,'x':m.pose.pose.position.x,'y':m.pose.pose.position.y})

    node.create_subscription(Imu,'/hwt601/imu/data_raw',imu,qos_profile_sensor_data)
    node.create_subscription(Odometry,'/hwt_test/lidar_odom',odom,qos_profile_sensor_data)
    node.create_subscription(String,'/hwt_test/base_state',lambda m:receive('base',json.loads(m.data)),10)
    node.create_subscription(String,'/hwt_test/lidar_status',lambda m:receive('lidar_status',json.loads(m.data)),10)

    def ready(require_still=False):
        now=time.monotonic()
        for key, age in (('imu',.15),('lidar',.6),('lidar_status',1.0),('base',.3)):
            if key not in data or now-data[key][0]>age:
                raise ValueError('Daten fehlen/veraltet: '+key)
        if fault:
            raise ValueError(fault)
        b=data['base'][1]; l=data['lidar_status'][1]
        if not base_healthy(b,now-data['base'][0]):
            raise ValueError('Encoder/Antrieb nicht gesund')
        if not l.get('ready') or l.get('reason') != 'scanmatch_gueltig':
            raise ValueError('LiDAR-Referenz nicht gueltig')
        if abs(time.time()-data['lidar'][1]['stamp']) > .6:
            raise ValueError('LiDAR-Quellzeit veraltet')
        if require_still and not stationary(b):
            raise ValueError('Kein gemessener Stillstand')

    def zero():
        if publisher is not None:
            publisher.publish(Twist())

    try:
        print(f'Lokal: {output}; execute={args.execute}',flush=True)
        until=time.monotonic()+8
        while time.monotonic()<until:
            rclpy.spin_once(node,timeout_sec=.02)
        ready(True)
        if not args.execute:
            summary['complete']=True
            print('PASSIVER PREFLIGHT OK; kein Befehlspublisher erstellt.',flush=True)
        else:
            if node.count_publishers(COMMAND) != 0 or node.count_subscribers(COMMAND) != 1:
                raise ValueError('Isolierter Befehlskanal nicht exklusiv')
            publisher=node.create_publisher(Twist,COMMAND,1)
            phase='calibrating'; until=time.monotonic()+60
            while not bias.result.calibrated:
                zero(); rclpy.spin_once(node,timeout_sec=.01); ready(True)
                if time.monotonic()>until:raise ValueError('Bias-Zeitlimit')
            fixed=tuple(bias.result.bias_radps)
            summary['fixed_bias_radps_xyz']=fixed
            phase='armed'
            print('BEREIT: s + Enter fuer EINE langsame Linksdrehung, q bricht ab. Noch keine Drehung.',flush=True)
            until=time.monotonic()+90
            while True:
                zero(); rclpy.spin_once(node,timeout_sec=.01); ready(True)
                if time.monotonic()>until:raise ValueError('Startfreigabe abgelaufen')
                if select.select([sys.stdin],[],[],0)[0]:
                    line=sys.stdin.readline().strip()
                    if line=='s':break
                    raise ValueError('Bedienerabbruch')
            start_lidar=data['lidar'][1].copy(); start_base=data['base'][1].copy()
            phase='turning'; start=time.monotonic(); next_command=start
            integral.add(data['imu'][1]['stamp'],tuple(v-b for v,b in zip(data['imu'][1]['gyro'],fixed)))
            print('DREHUNG STARTET: links, 0.10 rad/s, maximal 24 s.',flush=True)
            while rclpy.ok():
                rclpy.spin_once(node,timeout_sec=.01); ready()
                l=data['lidar'][1]; b=data['base'][1]
                ld=math.degrees(angle_delta(l['yaw'],start_lidar['yaw']))
                ed=math.degrees(angle_delta(b['yaw'],start_base['yaw']))
                displacement=math.hypot(b['x']-start_base['x'],b['y']-start_base['y'])
                command=drive_decision(time.monotonic()-start,ld,ed,displacement,integral.value[2])
                if command==0:break
                if node.count_publishers(COMMAND)!=1 or node.count_subscribers(COMMAND)!=1:
                    raise ValueError('Befehlskanal nicht mehr exklusiv')
                if select.select([sys.stdin],[],[],0)[0]:
                    sys.stdin.readline(); raise ValueError('Bedienerabbruch')
                if time.monotonic()>=next_command:
                    msg=Twist(); msg.angular.z=command; publisher.publish(msg)
                    next_command=time.monotonic()+.05
            phase='stopping'; until=time.monotonic()+3
            while time.monotonic()<until:
                zero();rclpy.spin_once(node,timeout_sec=.01);ready()
            ready(True)
            lidar=math.degrees(angle_delta(data['lidar'][1]['yaw'],start_lidar['yaw']))
            encoder=math.degrees(angle_delta(data['base'][1]['yaw'],start_base['yaw']))
            summary.update(complete=True, lidar_deg=lidar, encoder_deg=encoder,
                           imu_deg_xyz=integral.value, peak_imu_deg_xyz=integral.peak,
                           imu_minus_lidar_deg=integral.value[2]-lidar,
                           passed=(85<=lidar<=95 and abs(integral.value[2]-lidar)<=5))
    except (Exception,KeyboardInterrupt) as exc:
        summary['error']=f'{type(exc).__name__}: {exc}'
    finally:
        phase='cleanup'
        until=time.monotonic()+2
        while publisher is not None and rclpy.ok() and time.monotonic()<until:
            zero()
            try:rclpy.spin_once(node,timeout_sec=.02)
            except Exception:pass
        summary['stopped_feedback_confirmed']=('base' in data and time.monotonic()-data['base'][0]<.3 and stationary(data['base'][1]))
        summary['passed'] = bool(summary['complete'] and summary['stopped_feedback_confirmed']
                                 and (not args.execute or summary['passed']))
        log.close()
        (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
        print(json.dumps(summary,indent=2),flush=True)
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
    return 0 if summary['complete'] and (not args.execute or summary['passed']) else 2


if __name__=='__main__':
    raise SystemExit(main())
