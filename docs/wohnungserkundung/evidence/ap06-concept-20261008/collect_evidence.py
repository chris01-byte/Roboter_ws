#!/usr/bin/env python3
"""Collect this concept task's closed synthetic evidence, never private profiles.

Prepared for final collection only. Large events.jsonl.gz files stay in scratch;
their compressed and decompressed identities are independently verified here.
No source chmod, mutation, ROS start or search of historical evidence occurs.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess


SOURCE = Path('/workspace/scratch/ap06-concept-20261008')
PHASE_TEST_SOURCE = Path('/workspace/scratch/ap06-phase-tests')
TARGET = Path('/workspace/Roboter_ws-ap06/docs/wohnungserkundung/evidence/ap06-concept-20261008')
CONTAINER = 'ap03-nav2'
ALLOWED_SOURCE_ROOTS = (SOURCE, PHASE_TEST_SOURCE)
ROOT_FILES = (
    'replay_metric_select_c5.py', 'replay_metric_select_c5_initial.py',
    'select-replay-c5-resumed.log', 'select-replay-c5-geometric.log',
    'revalidation-cancel-last-status.json', 'package_handoff.py',
    'capture_selection_product.py', 'run-selection-capture-a.sh',
    'selection-capture-a-intent.json', 'selection-capture-a-supervisor.log',
    'selection-reconstruction-report.json',
    'selection-capture-a-independent-audit.json',
    'selection-capture-a-revalidation-audit.json', 'selection-capture-a.png',

    'experiment-a-intent.json', 'product-identity.json', 'visibility-a.summary.json',
    'visibility_geometry_check.py', 'visibility_geometry_report.json',
    'deferred-a-independent-audit.json', 'deferred-a-status-transitions.json',
    'audit_alignment_run.py', 'audit_phase_a_join.py', 'audit_joined_a.py',
    'phase-a-independent-audit.json', 'phase-a-join-independent-audit.json',
    'joined-a-independent-audit.json', 'joined-a-join-independent-audit.json',
    'revalidation-a-independent-audit.json', 'revalidation-a-join-independent-audit.json',
    'audit_revalidation_a.py',
    'visibility-a.png', 'deferred-a.png', 'phase-a.png', 'joined-a.png', 'render_concept.py',
    'visibility-a.log', 'deferred-a-supervisor.log', 'phase-a-supervisor.log', 'joined-a-supervisor.log',
    'tool-regression.log', 'scope-final-tests.log', 'joined-cli-help.log',
    'phase-build-tests.sh', 'phase-build.log', 'phase-affected-tests.log',
    'phase-colcon-tests.log', 'phase-colcon-results.log', 'phase-binding.log',
    'bind_phase_candidate.py', 'phase-source-identity.json', 'phase-native-identity.json',
    'phase-native-summary.json', 'phase-native.log', 'phase-a-intent.json', 'run-phase-a.sh',
    'joined-build-tests.sh', 'joined-tests.sh', 'joined-build.log',
    'joined-affected-tests-first-launch-fail.log', 'joined-affected-tests.log',
    'joined-colcon-tests.log', 'joined-colcon-results.log', 'joined-binding.log',
    'joined-source-identity.json', 'joined-native-identity.json',
    'joined-native-summary.json', 'joined-native.log', 'bind_final_candidate.py',
    'joined-a-intent-before-discovery-fix.json', 'joined-a-intent.json', 'run-joined-a.sh',
    'map-join-red.log', 'map-join-green.log', 'map-join-green-v2.log', 'map-join-green-v3.log',
    'benchmark_metric_inputs.py', 'inputs-benchmark-e9.log',
    'inputs-benchmark-e9-report.md', 'inputs-benchmark-e9-SHA256SUMS',
    'snapshot-revalidation-before.log', 'snapshot-revalidation-after.log',
    'stationary-revalidation-before.log', 'stationary-revalidation-after.log',
    'stationary-build-tests.sh', 'stationary-build.log', 'stationary-colcon-tests.log',
    'stationary-colcon-results.log', 'stationary-supervisor.log',
    'revalidation-build-tests.sh', 'revalidation-build.log', 'revalidation-affected-tests.log',
    'revalidation-colcon-tests.log', 'revalidation-colcon-results.log', 'revalidation-cli-help.log',
    'revalidation-binding.log', 'revalidation-a-intent.json', 'run-revalidation-a.sh',
    'revalidation-supervisor.log', 'revalidation-a-supervisor.log', 'revalidation-a.png',
    'revalidation-intent.json', 'revalidation-cancel-intent.json', 'revalidation-gyro_hold-intent.json',
    'run-revalidation-cancel.sh', 'run-revalidation-gyro_hold.sh',
    'revalidation-cancel-supervisor.log', 'revalidation-gyro_hold-supervisor.log',
    'revalidation-cancel.log', 'revalidation-gyro_hold.log',
    'launch-test-corrected.log', 'sync-incomplete.json',
    'sync-incomplete-joined-affected-tests.log', 'sync-incomplete-joined-build.log',
    'smoke_metric_scope_ros.py', 'scope-ros-smoke-supervisor.log',
    'scope-ros-smoke-owner-diagnostic-supervisor.log',
    'scope-ros-smoke-discovery-fixed-supervisor.log', 'scope-ros-smoke-complete-supervisor.log',
    'jetson-handoff-draft.md', 'collect_evidence.py',
)
RUNS = ('selection-capture-a', 'visibility-a', 'deferred-a/door68_start_a',
        'phase-a/door68_start_a', 'joined-a/door68_start_a', 'revalidation-a/door68_start_a',
        'revalidation-cancel', 'revalidation-gyro_hold')
RUN_FILES = (
    'result.json', 'manifest.json', 'events.jsonl.gz.meta.json', 'events.jsonl.gz.verified.json',
    'final_global_costmap_geometry.json', 'final_slam_map_geometry.json',
    'final_global_costmap.npy', 'final_slam_map.npy',
    'final_raw_map.cdr', 'final_costmap.cdr', 'final_scan.cdr',
    'device_result.json', 'sensor_result.json', 'storage_preflight.json',
    'departure_assessments.jsonl', 'explorer.log', 'controller_server.log', 'planner_server.log',
    'manager.log', 'maps.log', 'slam.log', 'gate.log', 'safety.log', 'shadow.log',
    'collision_monitor.log', 'velocity_smoother.log', 'bt.log', 'bt_navigator.log',
    'ekf.log', 'tf_probe.log', 'scan_normalizer.log',
    'native_params.yaml', 'device_params.yaml', 'progress.json',
    'commands.jsonl', 'device_executor_latency.jsonl', 'sensor_executor_latency.jsonl',
    'plant.jsonl',  # current runs are 3-6 MiB; render_concept.py requires this exact input
)
WRAPPERS = ('deferred-a', 'phase-a', 'joined-a', 'revalidation-a')
WRAPPER_FILES = ('experiment.json', 'summary.json', 'original_manifest.json',
                 'door68_start_a.command.json', 'door68_start_a.summary.json', 'door68_start_a.log')
NATIVE_CASES = ('blind_start', 'bootstrap', 'detour', 'door56', 'door68',
                'door68_stop', 'door80', 'rotation_narrow', 'unknown_outer')
NATIVE_FILES = ('result.json', 'controller_server.log', 'planner_server.log',
                'params.yaml', 'path.json', 'trace.csv', 'alignment.csv')
SMOKE_RUNS = ('scope-ros-smoke', 'scope-ros-smoke-owner-diagnostic',
              'scope-ros-smoke-discovery-fixed', 'scope-ros-smoke-complete')
SMOKE_FILES = ('result.json', 'supervisor.log', 'positive.stdout.log', 'positive.stderr.log',
    'exclusive-existing-output.stdout.log', 'exclusive-existing-output.stderr.log',
    'negative-existing-action.stdout.log', 'negative-existing-action.stderr.log')
COLCON_ROOTS = ('phase-build-log', 'phase-colcon-log', 'joined-build-log',
                'joined-colcon-log', 'sync-incomplete-joined-build-log',
                'revalidation-build-log', 'revalidation-colcon-log',
                'stationary-build-log', 'stationary-colcon-log')
PACKAGE_LOGS = ('command.log', 'stderr.log', 'stdout.log', 'stdout_stderr.log', 'streams.log')
BENCHMARK_FILES = ('result.json', 'cold_projection.prof', 'cold_projection.txt',
                   'steady.prof', 'steady.txt')
BENCHMARK_SOURCE_FILES = ('identity.json', 'amadeus_map_identity.fingerprint.py',
    'explore.exploration_scope.py', 'explore.explore_node.py',
    'explore.frontier_task_evidence.py', 'explore.metric_egress_reference.py',
    'explore.metric_frontier.py', 'explore.metric_frontier_runtime.py',
    'test_metric_frontier.py')
SNAPSHOT_REVALIDATION_FILES = ('source-sha256.json',
    'src/explore/explore/metric_frontier_runtime.py',
    'src/explore/test/test_metric_snapshot_replan.py',
    'src/explore/test/test_metric_map_lifecycle.py')


def container_path(path):
    path = Path(path)
    if not any(root in path.parents for root in ALLOWED_SOURCE_ROOTS):
        raise ValueError('Source is outside the explicitly allowed scratch roots: '+str(path))
    return '/evidence/'+str(path.relative_to('/workspace/scratch'))


@contextmanager
def source_stream(path):
    """Read one explicit artifact; root-owned smoke directories stay untouched."""
    remote = container_path(path)
    try:
        stream = Path(path).open('rb')
    except PermissionError:
        # Literal argv reads precisely one selected artifact, never a directory.
        process = subprocess.Popen(['docker', 'exec', CONTAINER, 'cat', '--', remote],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            yield process.stdout
            error = process.stderr.read()
            code = process.wait()
            if code:
                exists = subprocess.run(['docker', 'exec', CONTAINER, 'test', '-e', remote],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if exists.returncode == 1:
                    raise FileNotFoundError(str(path))
                raise OSError('Cannot read '+remote+': '+error.decode(errors='replace'))
        finally:
            process.stdout.close(); process.stderr.close()
            if process.poll() is None:
                process.terminate(); process.wait(timeout=5.)
    else:
        with stream:
            yield stream


def read_optional(path):
    try:
        with source_stream(path) as stream:
            return stream.read()
    except FileNotFoundError:
        return None


def bounded_children(path):
    """One directory level only; never traverse private maps/checkpoints."""
    container_path(path/'_boundary_check')
    try:
        return sorted(child.name for child in path.iterdir())
    except FileNotFoundError:
        return []
    except PermissionError:
        program = ('import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); '
            'print(json.dumps(sorted(v.name for v in p.iterdir()) if p.is_dir() else []))')
        command = ['docker', 'exec', CONTAINER, 'python3', '-c', program, container_path(path)]
        return json.loads(subprocess.check_output(command))


def digest_stream(stream):
    digest, size = hashlib.sha256(), 0
    for chunk in iter(lambda: stream.read(1024*1024), b''):
        digest.update(chunk); size += len(chunk)
    return digest.hexdigest(), size


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


def main():
    copied, absent, incomplete, raw_traces = [], [], [], []
    TARGET.mkdir(parents=True, exist_ok=True)

    def copy_artifact(relative, *, root=SOURCE, destination=None):
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Artifact must use a bounded relative path')
        content = read_optional(root/relative)
        if content is None:
            absent.append(str(root/relative))
            return False
        output = TARGET/(relative if destination is None else destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)  # copy bytes, never original chmod/metadata
        copied.append(dict(source=str(root/relative), destination=str(output.relative_to(TARGET)),
            size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest()))
        return True

    for name in ROOT_FILES:
        copy_artifact(name)
    # Current release JSON files plus its exact binding transcript only.
    for prefix in ('release', 'revalidation-release', 'stationary-release'):
        for name in bounded_children(SOURCE/prefix):
            if name.endswith('.json') or name == 'binding.log':
                copy_artifact(Path(prefix)/name)
    for name in ('result.json', 'setup.json', 'selection.prof', 'selection-profile.txt'):
        copy_artifact(Path('select-replay-c5-geometric')/name)
    diagnostic_captures = []
    for name in bounded_children(SOURCE/'selection-capture-a'):
        if name.startswith(('selection-', 'departure-')):
            relative = Path('selection-capture-a')/name
            if name.endswith('.json'):
                copy_artifact(relative)
            elif name.endswith(('.pickle', '.npz')):
                with source_stream(SOURCE/relative) as stream:
                    digest, size = digest_stream(stream)
                diagnostic_captures.append(dict(path=str(SOURCE/relative),
                    relative=str(relative), bytes=size, sha256=digest, stored_in_git=False))
    write_json(TARGET/'local-diagnostic-captures.json', diagnostic_captures)
    for name in BENCHMARK_FILES:
        copy_artifact(Path('inputs-benchmark-e9')/name)
    for name in BENCHMARK_SOURCE_FILES:
        copy_artifact(Path('inputs-benchmark-e9-sources')/name)
    for prefix in ('snapshot-revalidation-before', 'snapshot-revalidation-after'):
        for name in SNAPSHOT_REVALIDATION_FILES:
            copy_artifact(Path(prefix)/name)
    for prefix in ('stationary-revalidation-before', 'stationary-revalidation-after'):
        for name in ('source-sha256.json', 'src/explore/explore/metric_frontier_runtime.py',
                     'src/explore/test/test_metric_snapshot_replan.py'):
            copy_artifact(Path(prefix)/name)
    copy_artifact('launch-test-corrected-source/source-sha256.json')
    for name in ('red-counterexample.log', 'red.log', 'green-initial.log', 'green-final.log'):
        copy_artifact(name, root=PHASE_TEST_SOURCE, destination=Path('regression')/name)

    for prefix in WRAPPERS:
        for name in WRAPPER_FILES:
            copy_artifact(Path(prefix)/name)
    for prefix in RUNS:
        run = SOURCE/prefix
        result_bytes = read_optional(run/'result.json')
        metadata_bytes = read_optional(run/'events.jsonl.gz.meta.json')
        if result_bytes is None or metadata_bytes is None:
            incomplete.append(dict(path=str(run), reason='closed result and trace metadata not both present'))
            continue
        json.loads(result_bytes)
        metadata = json.loads(metadata_bytes)
        for name in RUN_FILES:
            copy_artifact(Path(prefix)/name)
        trace = run/'events.jsonl.gz'
        with source_stream(trace) as stream:
            compressed_hash, compressed_bytes = digest_stream(stream)
        with source_stream(trace) as stream, gzip.GzipFile(fileobj=stream) as decompressed:
            raw_hash, raw_bytes = digest_stream(decompressed)
        if (compressed_bytes != metadata['compressed_bytes']
                or raw_bytes != metadata['uncompressed_bytes'] or raw_hash != metadata['sha256']):
            raise ValueError('Closed trace identity verification failed: '+str(trace))
        verified = dict(path=str(trace), container_path=container_path(trace), stored_in_git=False,
            compressed_bytes=compressed_bytes, compressed_sha256=compressed_hash,
            uncompressed_bytes=raw_bytes, uncompressed_sha256=raw_hash,
            metadata_path=str(run/'events.jsonl.gz.meta.json'), independently_verified=True)
        raw_traces.append(verified)
        write_json(TARGET/prefix/'events.jsonl.gz.collection-verified.json', verified)

    # Only this known synthetic saved error checkpoint and its exact map.
    # Real/private robot recordings are never traversed or collected.
    saved_run = Path('revalidation-a/door68_start_a')
    version = '20261008T072325540920Z-305405243e93'
    copy_artifact(saved_run/'checkpoints'/'amadeus'/version/'state-00000001.json')
    for name in ('metadata.json', 'map.yaml', 'occupancy.bin', 'map.pgm'):
        copy_artifact(saved_run/'maps'/'amadeus'/version/name)

    for prefix in ('phase-native', 'joined-native'):
        for name in ('summary.json', 'result.json'):
            copy_artifact(Path(prefix)/name)
        for case in NATIVE_CASES:
            for name in NATIVE_FILES:
                copy_artifact(Path(prefix)/case/name)
    for prefix in SMOKE_RUNS:
        for name in SMOKE_FILES:
            copy_artifact(Path(prefix)/name)
        # Deliberately omit synthetic scope JSON and private generated YAML.
    for prefix in COLCON_ROOTS:
        for invocation in bounded_children(SOURCE/prefix):
            if not invocation.startswith(('build_', 'test_')):
                continue  # skip latest symlinks, no duplicate or external traversal
            relative = Path(prefix)/invocation
            for name in ('events.log', 'logger_all.log'):
                copy_artifact(relative/name)
            for package in bounded_children(SOURCE/relative):
                if package.endswith('.log'):
                    continue
                for name in PACKAGE_LOGS:
                    copy_artifact(relative/package/name)

    write_json(TARGET/'local-raw-traces.json', raw_traces)
    write_json(TARGET/'collection-report.json', dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        source_roots=[str(path) for path in ALLOWED_SOURCE_ROOTS],
        collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        copied_artifacts=copied, optional_artifacts_absent=absent, incomplete_runs_not_collected=incomplete,
        originals_mutated=False, private_scope_profiles_collected=False,
        offline_benchmark_limit='inputs-benchmark-e9 measures offline processing only; it is not a live source-freshness or mission qualification.',
        note='Earlier negative/intermediate logs are preserved as evidence, not relabeled as passing checks.'))
    # Walk only the destination evidence directory, never source private dirs.
    # README belongs to Root; its current bytes are included without rewriting it.
    files = []
    for directory, names, filenames in os.walk(TARGET, followlinks=False):
        names[:] = [name for name in names if not (Path(directory)/name).is_symlink()]
        for name in filenames:
            path = Path(directory)/name
            if name != 'SHA256SUMS' and not path.is_symlink():
                files.append(path)
    checksums, total_bytes = [], 0
    for path in sorted(files):
        with path.open('rb') as stream:
            digest, size = digest_stream(stream)
        checksums.append(digest+'  '+str(path.relative_to(TARGET))+'\n')
        total_bytes += size
    (TARGET/'SHA256SUMS').write_text(''.join(checksums))
    print(json.dumps(dict(evidence_files=len(files), bytes=total_bytes,
        copied_files=len(copied), verified_raw_traces=len(raw_traces),
        incomplete_runs=len(incomplete), target=str(TARGET))))


if __name__ == '__main__':
    main()
