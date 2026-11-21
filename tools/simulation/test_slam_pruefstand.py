import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location(
    'slam_pruefstand', Path(__file__).with_name('slam_pruefstand.py'))
pruefstand = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pruefstand)

REPO = Path(__file__).resolve().parents[2]


def test_slam_parameters_are_the_self_healing_product_profile_plus_experiment():
    p = pruefstand.slam_parameter(REPO)['slam_toolbox']['ros__parameters']
    assert p['scan_topic'] == '/scan_normiert'
    assert p['loop_match_minimum_chain_size'] == 20          # Overlay X7 wirkt
    assert p['resolution'] == pytest.approx(0.01)
    versuch = {'slam_toolbox': {'ros__parameters': {'minimum_travel_distance': 0.2}}}
    q = pruefstand.slam_parameter(REPO, versuch)['slam_toolbox']['ros__parameters']
    assert q['minimum_travel_distance'] == pytest.approx(0.2)
    assert q['loop_match_minimum_chain_size'] == 20


def test_stamps_shift_across_second_boundaries():
    stamp = SimpleNamespace(sec=10, nanosec=900_000_000)
    pruefstand.verschiebe(stamp, 250_000_000)
    assert (stamp.sec, stamp.nanosec) == (11, 150_000_000)


def test_recorded_map_to_odom_is_dropped_other_transforms_stay():
    def tf(parent, child):
        return SimpleNamespace(header=SimpleNamespace(frame_id=parent), child_frame_id=child)
    nur_slam = SimpleNamespace(transforms=[tf('map', 'odom')])
    assert pruefstand.ohne_map_odom(nur_slam) is False
    gemischt = SimpleNamespace(transforms=[tf('/map', 'odom'), tf('odom', 'base_link')])
    assert pruefstand.ohne_map_odom(gemischt) is True
    assert [t.child_frame_id for t in gemischt.transforms] == ['base_link']


def test_summaries_report_the_criteria_values():
    reihe = [(10., 10.), (130., 50.), (250., 70.), (370., 90.)]
    cpu = pruefstand.cpu_zusammenfassung(reihe)
    assert cpu['max'] == 90. and cpu['mittel_letzte_2min'] == pytest.approx(80.)
    alter = pruefstand.alter_zusammenfassung([.05]*199 + [.4])
    assert alter['anteil_ueber_grenze'] == pytest.approx(.005)
    assert alter['max_s'] == pytest.approx(.4)
    assert pruefstand.log_zaehlung('x queue is full y preprocessor.cc') == {
        'verworfene_scans': 1, 'ringschluss_ceres': 1}
