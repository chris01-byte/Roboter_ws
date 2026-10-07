"""Actual 2-cm failure / separate controlled 1-cm Native component.
No common full acquisition history, live health, motion grant or whole pass.
"""
import json
from pathlib import Path

import numpy as np
import pytest
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
from explore.explore_node import ExploreNode
from explore.metric_frontier import StartEgressEvidence
from explore.metric_egress_reference import ReferencedStartEgress

DATA = Path(__file__).parent/'data/ap06_b176_start_raster'


def replay(resolution, *, obstacle=False):
    meta = json.loads(DATA.with_suffix('.json').read_text())
    case = meta['cases'][str(resolution)]
    evidence = None
    checks = []
    with np.load(DATA.with_suffix('.npz'), allow_pickle=False) as arrays:
        for index, row in enumerate(case['rows']):
            prefix = case['prefix']
            grid = deserialize_message(arrays[f'{prefix}_raw_{index}'].tobytes(), OccupancyGrid)
            occupancy = np.asarray(grid.data).reshape(grid.info.height, grid.info.width).copy()
            known_key = f'{prefix}_known_{index}'
            inside_key = f'{prefix}_inside_{index}'
            known = arrays[known_key].copy() if known_key in arrays else occupancy == 0
            inside = arrays[inside_key] if inside_key in arrays else np.ones(known.shape, bool)
            if evidence is None:
                fixed = StartEgressEvidence.capture(grid, occupancy, known, inside,
                    tuple(row['pose']), tuple(meta['bounds']), ExploreNode._world_to_grid)
                evidence = ReferencedStartEgress(fixed, row['reference'])
                original = evidence.fixed.unknown.copy()
            if obstacle and index == 1:
                col, r = ExploreNode._world_to_grid(*row['pose'][:2], grid.info)
                occupancy[r, col] = 100
                grid.data = occupancy.ravel().tolist()
                known[r, col] = False
            evidence.refresh(grid, occupancy, inside, row['reference'])
            valid, reason = evidence.check_trajectory([row['pose']], occupancy, known,
                ExploreNode._world_to_grid, commit=True, motion_pose=row['physical_pose'])
            checks.append((valid, reason))
            assert not np.any(evidence.fixed.unknown & ~original)
            if not valid:
                break
    return checks, evidence, case


def test_controlled_one_centimetre_fixture_retains_its_own_first_inventory():
    # This is deliberately independent of the product configuration: choosing
    # a resolution must not silently choose a different acquisition history.
    checks, evidence, case = replay(.01)
    assert all(valid for valid, _ in checks)
    assert len(checks) == len(case['rows'])
    assert evidence.valid


def test_actual_b172_half_cell_outside_first_inventory_remains_rejected():
    checks, _, case = replay(.02)
    assert not case['expected_valid']
    assert all(valid for valid, _ in checks[:-1])
    assert checks[-1] == (False, 'start_egress_new_unknown_or_obstacle')


def test_one_centimetre_native_start_does_not_exempt_a_real_obstacle():
    checks, _, _ = replay(.01, obstacle=True)
    assert checks[0][0]
    assert checks[-1] == (False, 'start_egress_new_unknown_or_obstacle')


def test_positive_start_fixture_is_explicitly_not_same_whole_acquisition_history():
    meta = json.loads(DATA.with_suffix('.json').read_text())
    assert 'not identical full acquisition history' in meta['kind']
    assert 'not exact scan/timing replay' in meta['cases']['0.01']['kind']
