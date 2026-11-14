"""Static finite-ray coverage diagnostic; no ROS, movement or map edits.

Reads the preserved A227 private start geometry and A244 missing-cell list.
This computes segment/cell intersection against finite modeled scan returns.
It does not establish actual SLAM clearing or real sensor visibility.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path('/workspace/Roboter_ws-ap06'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    sources = {
        'a227_geometry': repo/'src/explore/test/data/ap06_a227_start_selection.json',
        'a227_cdr_and_masks': repo/'src/explore/test/data/ap06_a227_start_selection.npz',
        'a244_missing_cells': repo/'docs/wohnungserkundung/evidence/ap06-missions-20261005/a244-start-coverage.json',
        'finite_world': repo/'tools/simulation/ap06_world.py',
        'product_manifest': repo/'tools/simulation/ap06_product_scenarios.json',
        'diagnostic_script': Path(__file__).resolve(),
    }
    a227 = json.loads(sources['a227_geometry'].read_text())
    a244 = json.loads(sources['a244_missing_cells'].read_text())
    manifest = json.loads(sources['product_manifest'].read_text())
    case = next(case for case in manifest['positive'] if case['id'] == 'door68_start_a')
    sys.path.insert(0, str(repo/'tools/simulation'))
    from ap06_world import World

    evidence = a227['evidence'][0]
    left, right, bottom, top = evidence['bounds']
    polygon = np.asarray(evidence['initial_polygon'], dtype=float)
    # A227 is at zero pose/reference with axis-aligned raw raster. Derive
    # its float32-origin/resolution values from the ORIGINAL polygon formula:
    # width_in_cells=(body_width+.02)/res+sqrt(2).
    assert a227['pose'] == [0.0, 0.0, 0.0]
    assert a227['reference'] == [0.0, 0.0, 0.0]
    assert polygon[0, 1] == polygon[1, 1]
    assert polygon[1, 0] == polygon[2, 0]
    resolution = ((right-left)+.02)/((polygon[1, 0]-polygon[0, 0])-math.sqrt(2))
    reserve = resolution/math.sqrt(2)+.01
    grid_origin_local = np.array([
        left-reserve-polygon[0, 0]*resolution,
        bottom-reserve-polygon[0, 1]*resolution,
    ])
    world = World(case['door_m'], case['start'])
    beams = manifest['sensor']['lidar_beams']
    angles, full_ranges = world.laser(beams, mask=False)
    native_angles, native_ranges = world.laser(beams, mask=True)
    assert np.array_equal(angles, native_angles)
    sensor_origin = world.pose[:2]+np.array([.245, 0.])
    grid_origin = grid_origin_local+world.pose[:2]
    cells = a244['raw']['cells']
    records = []
    for row, col in cells:
        low = grid_origin+np.array([col, row])*resolution
        high = low+resolution
        center = (low+high)/2
        angle = (math.atan2(*(center-sensor_origin)[::-1])-math.pi/2) % (2*math.pi)
        index = int(round(angle/(2*math.pi/beams))) % beams
        direction = np.array([math.cos(angles[index]+math.pi/2),
                              math.sin(angles[index]+math.pi/2)])
        with np.errstate(divide='ignore'):
            first, second = (low-sensor_origin)/direction, (high-sensor_origin)/direction
        enter = max(0., float(np.minimum(first, second).max()))
        leave = float(np.maximum(first, second).min())
        crossed = bool(leave >= enter and enter < full_ranges[index] and leave > .05)
        records.append({
            'cell': [row, col],
            'center_local_m': (center-world.pose[:2]).tolist(),
            'center_sensor_distance_m': float(np.linalg.norm(center-sensor_origin)),
            'center_laser_angle_deg': math.degrees(angle),
            'actual_beam_index': index,
            'actual_beam_angle_deg': math.degrees(float(angles[index])),
            'actual_finite_return_m': float(full_ranges[index]),
            'segment_enters_cell_m': enter,
            'segment_leaves_cell_m': leave,
            'full360_segment_crosses_cell': crossed,
            'native_beam_masked': bool(not math.isfinite(native_ranges[index])),
            'return_beyond_cell_m': float(full_ranges[index]-leave),
        })
    centres = np.asarray([record['center_local_m'] for record in records])
    claimed_bbox = np.asarray(a244['raw']['missing_cell_centres_bbox_m'])
    actual_bbox = np.vstack([centres.min(axis=0), centres.max(axis=0)])
    assert np.allclose(actual_bbox, claimed_bbox, atol=1e-12, rtol=0.)
    result = {
        'kind': 'Static finite sensor visibility diagnostic only; no runtime or physical qualification',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python': platform.python_version(),
        'numpy': np.__version__,
        'source_sha256': {name: {'path': str(path), 'sha256': sha256(path)}
                          for name, path in sources.items()},
        'derivation': {
            'start': case,
            'beam_count': beams,
            'sensor_mount_local_m': [.245, 0.],
            'sensor_yaw_rad': math.pi/2,
            'scan_range_min_m': .05,
            'grid_resolution_m_derived_from_original_polygon': resolution,
            'grid_origin_local_m_derived_from_original_polygon': grid_origin_local.tolist(),
            'missing_cell_bbox_matches_a244_with_absolute_tolerance_m': 1e-12,
            'algorithm': 'Nearest actual discrete beam; finite first-return segment intersects complete square cell using slab intervals',
        },
        'summary': {
            'missing_raw_cells': len(records),
            'full360_segments_intersect': sum(record['full360_segment_crosses_cell'] for record in records),
            'full360_misses': sum(not record['full360_segment_crosses_cell'] for record in records),
            'selected_native_beams_masked': sum(record['native_beam_masked'] for record in records),
            'center_sensor_distance_minmax_m': [min(record['center_sensor_distance_m'] for record in records), max(record['center_sensor_distance_m'] for record in records)],
            'center_laser_angle_minmax_deg': [min(record['center_laser_angle_deg'] for record in records), max(record['center_laser_angle_deg'] for record in records)],
            'minimum_finite_return_beyond_cell_m': min(record['return_beyond_cell_m'] for record in records),
        },
        'limits': [
            'No ROS or SLAM invocation; segment/cell intersection does not prove occupancy publication or qualified observation.',
            'World contains static floor-to-ceiling obstacle rectangles and no 3-D robot self-occlusion beyond the optional angular mast mask.',
            'Full360 variant intentionally removes that mask; it is not a validated real sensor installation.',
            'Some cells are close to the mask edge: one unmasked beam crossing a cell does not imply current SLAM marked the full cell free.',
            'Original A227 start geometry and A244 list are component evidence, not the initial map from the new live concept mission.',
            'Actual unchanged guard results, finite-source freshness, observed map, full mission completion, and physical tests remain separate.',
        ],
        'cells': records,
    }
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output': str(args.output), 'summary': result['summary']}, indent=2))


if __name__ == '__main__':
    main()
