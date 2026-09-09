#!/usr/bin/env python3
"""Read STL27L UART without transmitting bytes; preserve native packets locally."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import struct
import subprocess
import time


def crc8(payload):
    value=0
    for byte in payload:
        value ^= byte
        for _ in range(8):
            value=((value<<1)^0x4d if value&0x80 else value<<1)&255
    return value


def parse(raw):
    points=[]; good=bad=0; i=0
    while i+47<=len(raw):
        if raw[i:i+2]!=b'\x54\x2c':
            i+=1;continue
        frame=raw[i:i+47]
        if crc8(frame[:-1])!=frame[-1]:
            bad+=1;i+=1;continue
        start=struct.unpack_from('<H',frame,4)[0]
        end=struct.unpack_from('<H',frame,42)[0]
        if start>=36000 or end>=36000:
            raise ValueError('Native Winkel ausserhalb Protokollbereich')
        span=(end-start)%36000
        for j in range(12):
            distance,intensity=struct.unpack_from('<HB',frame,6+3*j)
            points.append(((start+span*j/11)/100%360,distance,intensity))
        good+=1;i+=47
    return points,good,bad


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',action='store_true',required=True)
    ap.parse_args()
    port='/dev/amadeus_lidar'
    props=subprocess.check_output(['udevadm','info','--query=property','--name='+port],text=True)
    expected='ID_SERIAL=Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5675455eb472ef11ba4e7c4f8fcc3fa0'
    if expected not in props.splitlines():raise ValueError('Falscher USB-Adapter')
    import serial
    started=time.monotonic();raw=bytearray()
    with serial.Serial(port,921600,timeout=.1,exclusive=True) as link:
        while time.monotonic()-started<5:
            raw.extend(link.read(8192))
    points,good,bad=parse(raw)
    out=Path.home()/'.local/share/amadeus/hwt601'/time.strftime('lidar-native-%Y%m%d-%H%M%S')
    out.mkdir(parents=True,exist_ok=False)
    (out/'uart.bin').write_bytes(raw)
    bins=defaultdict(list)
    for angle,distance,intensity in points:
        if distance>0 and intensity>0:bins[int(angle)].append(distance)
    stats=[{'native_clockwise_deg':k,'median_mm':statistics.median(v),'samples':len(v)} for k,v in sorted(bins.items())]
    (out/'angle_bins.json').write_text(json.dumps(stats,indent=2)+'\n')
    result={'output':str(out),'bytes':len(raw),'valid_packets':good,'crc_failures':bad,
            'transmitted_bytes':0,'candidate_bins_500_700mm':[s for s in stats if 500<=s['median_mm']<=700],
            'front_bins_80_100deg':[s for s in stats if 80<=s['native_clockwise_deg']<=100]}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
