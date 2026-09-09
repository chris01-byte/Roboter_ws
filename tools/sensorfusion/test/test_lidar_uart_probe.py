from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lidar_uart_probe import crc8,parse


def packet(start=8900,end=9100):
    raw=bytearray(b'\x54\x2c'+struct.pack('<HH',3600,start))
    raw.extend(struct.pack('<HB',600,100)*12)
    raw.extend(struct.pack('<HH',end,123))
    raw.append(crc8(raw))
    return bytes(raw)


def test_native_angles_distances_and_noise():
    points,good,bad=parse(b'noise'+packet()+packet()[:20])
    assert (good,bad)==(1,0)
    assert points[0]==(89,600,100)
    assert points[-1]==(91,600,100)


def test_wrap_and_crc_rejection():
    goodframe=packet(35900,100)
    corrupt=bytearray(goodframe);corrupt[7]^=1
    points,good,bad=parse(corrupt+goodframe)
    assert (good,bad)==(1,1)
    assert points[0][0]==359 and points[-1][0]==1


def test_no_transmit_calls():
    source=(Path(__file__).resolve().parents[1]/'lidar_uart_probe.py').read_text()
    assert 'link.write' not in source
    assert 'exclusive=True' in source
