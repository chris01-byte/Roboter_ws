#!/usr/bin/env python3
"""Isolated finite-sensor concept experiments; never an AP-06 qualification.

The baseline and finite-sensor comparisons use the existing whole product
harness. An explicit third profile records and defers hypothetical next-leg
proof; actual leg/source/stop checks remain. No hardware or budget extension.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys


MANIFEST_SHA256 = '54132aaaca7ccee8412d5a5078410f49cb2f388da08c8f18899e5493ab4021da'
CASES = ('door68_start_a', 'door68_start_b', 'door80_start_c', 'cancel', 'gyro_hold')
PROFILES = ('native-mask', 'finite-unmasked', 'finite-unmasked-deferred-departure')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


def require_isolation():
    """Reject hardware/export use before importing ROS or launching anything."""
    devices = [Path('/dev') / name for name in ('ttyUSB_BASE', 'ttyUSB_HWT601')]
    for pattern in ('ttyUSB*', 'ttyACM*', 'i2c-*'):
        devices.extend(Path('/dev').glob(pattern))
    if (os.environ.get('AP06_SIMULATION') != '1'
            or os.environ.get('ROS_LOCALHOST_ONLY') != '1'
            or not Path('/.dockerenv').is_file()
            or Path('/etc/nv_tegra_release').exists()
            or any(p.exists() or p.is_symlink() for p in devices)):
        raise ValueError('device-free container, AP06_SIMULATION=1 and ROS_LOCALHOST_ONLY=1 required')
    try:
        domain = int(os.environ.get('ROS_DOMAIN_ID', '-1'))
    except ValueError as error:
        raise ValueError('dedicated simulation ROS domain 100..200 required') from error
    if not 100 <= domain <= 200:
        raise ValueError('dedicated simulation ROS domain 100..200 required')


def source_identity(repo, declared_revision=None):
    if declared_revision is not None and not re.fullmatch('[0-9a-fA-F]{40}', declared_revision):
        raise ValueError('--source-revision must be a full 40-character Git SHA')
    git_revision = None
    dirty = None
    # An exported source directory must not accidentally inherit a parent repo.
    if (repo/'.git').exists():
        git_revision = subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(
            ['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=all'], text=True).splitlines()
    if git_revision and declared_revision and git_revision != declared_revision.lower():
        raise ValueError('declared revision disagrees with source checkout HEAD')
    if not git_revision and not declared_revision:
        raise ValueError('exported sources require --source-revision; actual files are hashed separately')
    files = {}
    for directory in ('src', 'tools'):
        for path in sorted((repo/directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo'):
                files[str(path.relative_to(repo))] = digest(path)
    if not files:
        raise ValueError('no source files found')
    tree = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return dict(revision=git_revision or declared_revision.lower(),
                revision_origin='git' if git_revision else 'operator_declared_export',
                git_dirty=bool(dirty) if dirty is not None else None,
                git_status=dirty, actual_source_tree_sha256=tree, files=files,
                installed_binary_identity_verified=False)


def command(repo, output, case, profile, tf_probe):
    if case not in CASES or profile not in PROFILES:
        raise ValueError('unknown case or experiment profile')
    argv = [sys.executable, str(repo/'tools/simulation/ap06_closed_product.py'),
            '--repo', str(repo), '--output', str(output), '--case', case,
            '--tf-probe', str(tf_probe), '--manifest',
            str(repo/'tools/simulation/ap06_product_scenarios.json'), '--save-partial']
    if profile != 'native-mask':
        argv.append('--ideal-lidar')
    if profile == 'finite-unmasked-deferred-departure':
        argv.append('--concept-defer-departure')
    return argv


def summarize(result_path, returncode, profile, case, acceptance):
    """Keep raw grading visible, but never transfer it to original qualification."""
    summary = dict(case=case, profile=profile, passed=False,
                   original_qualification=False, hardware_qualified=False,
                   harness_returncode=returncode, raw_result_path=str(result_path),
                   diagnostic_status='missing_result', raw_harness_passed=None)
    if not result_path.is_file():
        return summary
    summary['raw_result_sha256'] = digest(result_path)
    try:
        raw = json.loads(result_path.read_text())
        if not isinstance(raw, dict):
            raise ValueError('result must be a JSON object')
        metric, manager, oracle = (raw.get(k, {}) for k in ('metric', 'manager', 'map_oracle'))
        if not all(isinstance(item, dict) for item in (metric, manager, oracle)):
            raise ValueError('invalid metric/manager/oracle object')
    except (ValueError, OSError) as error:
        summary.update(diagnostic_status='invalid_result', result_error=str(error))
        return summary
    actual_case = raw.get('case')
    actual_id = actual_case.get('id') if isinstance(actual_case, dict) else None
    expected_sensor = 'native_mast_mask' if profile == 'native-mask' else 'ideal_full_360'
    identity_errors = []
    for field, actual, expected in (
            ('case.id', actual_id, case),
            ('sensor_profile', raw.get('sensor_profile'), expected_sensor),
            ('actual_lidar_beams', raw.get('actual_lidar_beams'), 2160),
            ('concept_deferred_departure', raw.get('concept_deferred_departure', False),
                profile == 'finite-unmasked-deferred-departure'),
            ('manifest_compatible', raw.get('manifest_compatible'), profile == 'native-mask')):
        if actual != expected or (field in ('manifest_compatible', 'concept_deferred_departure')
                                  and not isinstance(actual, bool)):
            identity_errors.append(dict(field=field, actual=actual, expected=expected))
    summary.update(raw_harness_passed=raw.get('passed'),
        raw_manifest_compatible=raw.get('manifest_compatible'),
        identity_errors=identity_errors,
        diagnostic_status=('identity_mismatch' if identity_errors else
            'criteria_met' if raw.get('passed') is True and returncode == 0 else 'criteria_not_met'),
        reasons={key: value for key, value in {
            'harness': raw.get('error'), 'terminal': metric.get('reason'),
            'first_rejecting_predicate': metric.get('first_rejecting_predicate'),
            'planning_stop_reason': metric.get('planning_stop_reason'),
            'planning_route_rejection': metric.get('planning_route_rejection'),
            'completion_blocker': metric.get('completion_blocker')}.items() if value is not None},
        measurements={key: raw.get(key) for key in ('travel_m', 'rear_cleared',
            'minimum_padded_clearance_m', 'map_growth', 'map_save', 'checkpoint_after_save',
            'action_active_at_terminal', 'command_values_at_terminal')})
    summary['measurements'].update(metric={key: metric.get(key) for key in (
        'state', 'arrivals', 'observations', 'attempt', 'attempts', 'failures', 'reachable_boundary_cells',
        'unknown_cells_in_scope', 'completion_blocker')}, manager_state=manager.get('state'),
        map_oracle=oracle)
    def at_least(value, target):
        return value >= target if isinstance(value, (int, float)) and math.isfinite(value) else None
    fraction, error = oracle.get('reference_observed_fraction'), oracle.get('maximum_occupied_wall_error_m')
    criteria = dict(explorer_success=metric.get('state') == 'success' if 'state' in metric else None,
        manager_success=manager.get('state') == 'success' if 'state' in manager else None,
        three_arrivals=at_least(metric.get('arrivals'), 3),
        three_observations=at_least(metric.get('observations'), 3),
        rear_cleared_both_doors=raw.get('rear_cleared'), map_growth=raw.get('map_growth'),
        reference_observed_fraction=at_least(fraction, acceptance['min_reference_observed_fraction']),
        maximum_map_error=(error <= acceptance['max_map_truth_error_m']
            if isinstance(error, (int, float)) and math.isfinite(error) else None))
    summary['positive_mission_criteria'] = criteria
    summary['criteria_score'] = dict(met=sum(v is True for v in criteria.values()),
        failed=sum(v is False for v in criteria.values()), unavailable=sum(v is None for v in criteria.values()),
        total=len(criteria), applicable_to_case=case not in ('cancel', 'gyro_hold'))
    return summary


def run(args):
    require_isolation()
    repo, out, tf_probe = args.repo.resolve(), args.output.resolve(), args.tf_probe.resolve()
    if out == repo or repo in out.parents:
        raise ValueError('experiment evidence must be outside the source repository')
    if len(set(args.case)) != len(args.case):
        raise ValueError('each case can run once per experiment; no automatic retry series')
    manifest_path = repo/'tools/simulation/ap06_product_scenarios.json'
    if digest(manifest_path) != MANIFEST_SHA256:
        raise ValueError('original AP-06 manifest changed; no undeclared budget/scenario change allowed')
    if not tf_probe.is_file() or not os.access(tf_probe, os.X_OK):
        raise ValueError('executable TF ownership probe required')
    identity = source_identity(repo, args.source_revision)
    manifest = json.loads(manifest_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    profile = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        name=args.profile, cases=args.case, original_qualification=False, hardware_qualified=False,
        change=('unchanged finite native-mask baseline' if args.profile == 'native-mask' else
                'finite LiDAR mast mask removed; all 2160 beams still measured from simulated plant'),
        future_departure_proof=('logged original prediction, deferred only after unchanged stop/controller/public-body checks'
            if args.profile == 'finite-unmasked-deferred-departure' else 'unchanged'),
        product_guards=('actual leg, stop, source, observation and private-egress checks unchanged; future-departure prediction deferred'
            if args.profile == 'finite-unmasked-deferred-departure' else 'unchanged'),
        budgets=manifest['budgets'], original_manifest_sha256=MANIFEST_SHA256,
        source_identity=identity, wrapper_sha256=digest(Path(__file__)),
        tf_probe_sha256=digest(tf_probe), ros_domain_id=os.environ['ROS_DOMAIN_ID'])
    write_json(out/'experiment.json', profile)
    (out/'original_manifest.json').write_bytes(manifest_path.read_bytes())
    summaries = []
    child = None
    def interrupt(_signum, _frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        for case in args.case:
            argv = command(repo, out/case, case, args.profile, tf_probe)
            write_json(out/(case+'.command.json'), argv)
            code = None
            try:
                with (out/(case+'.log')).open('w') as log:
                    # Terminal Ctrl-C reaches this wrapper only. Forward it to
                    # the harness once; the harness signals each owned child.
                    child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                             start_new_session=True)
                    code = child.wait()
            except KeyboardInterrupt:
                if child is not None and child.poll() is None:
                    child.send_signal(signal.SIGINT)
                    code = child.wait()  # original harness owns ordered direct-child teardown
                raise
            finally:
                summary = summarize(out/case/'result.json', code, args.profile, case, manifest['acceptance'])
                write_json(out/(case+'.summary.json'), summary)
                summaries.append(summary)
                child = None
    finally:
        signal.signal(signal.SIGTERM, previous)
        write_json(out/'summary.json', dict(schema=1, profile=args.profile, passed=False,
            original_qualification=False, hardware_qualified=False, cases=summaries,
            diagnostic_criteria_met=sum(s['diagnostic_status'] == 'criteria_met' for s in summaries),
            completed_cases=sum(s['harness_returncode'] is not None for s in summaries),
            recorded_cases=len(summaries), requested_cases=len(args.case),
            original_qualified_missions=0, experiment_sha256=digest(out/'experiment.json')))
    return 0 if all(s['diagnostic_status'] == 'criteria_met' for s in summaries) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new directory, never overwrite prior evidence')
    parser.add_argument('--tf-probe', type=Path, required=True)
    parser.add_argument('--case', action='append', required=True, choices=CASES)
    parser.add_argument('--profile', required=True, choices=PROFILES)
    parser.add_argument('--source-revision', help='full Git SHA for an exported source directory')
    return run(parser.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
