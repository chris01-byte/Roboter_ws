#!/usr/bin/env python3
"""Bind the committed joined candidate to its execution tree and built install.

Read-only until all checks pass. Writes only two NEW joined identity documents;
V46 identities and original binary/scenario pins are never rewritten. Run on
the cloud host after committing and building the final candidate.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys


BASELINE_CANDIDATE = '2e5e1fd8d8f3241cbb3dfa9c2ee29988b036372f'
MASTER_SHA256 = '030782dc0cce24d23ef730783703f91cac6957ceb4b7305a224342fba74a8a10'
MANIFEST_SHA256 = '54132aaaca7ccee8412d5a5078410f49cb2f388da08c8f18899e5493ab4021da'
EXTRA_PACKAGES = ('robot_bringup', 'semantic_map_manager')
INSTALL_ROOT = '/evidence/ap06-old-product-install'
ADDITIONS = (
    'tools/simulation/ap06_concept_experiment.py',
    'tools/simulation/test_ap06_concept_experiment.py',
    'tools/simulation/ap06_departure_probe.py',
    'tools/simulation/test_ap06_departure_probe.py',
    '.github/workflows/hwt601-we.yml',
    'tools/kartierung/metric_scope_vorbereiten.py',
    'tools/kartierung/test_metric_scope_vorbereiten.py',
)
QUALIFICATION = ('joined source/execution/install identity verified; no whole-mission, '
                 'experiment, hardware or deployment qualification asserted')


class BindingError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise BindingError(message)


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def encoded(document):
    return (json.dumps(document, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def check_output(command):
    try:
        return subprocess.check_output(command, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        raise BindingError(f'command failed ({error.returncode}): {command!r}\n'
                           + error.stderr.decode(errors='replace')) from error


def installed_bytes(path, container):
    """Read only declared original or additional installed/native paths."""
    require(path.startswith('/evidence/'), f'unsupported installed/native path: {path}')
    host = Path('/workspace/scratch') / path.removeprefix('/evidence/')
    try:
        return host.read_bytes()
    except PermissionError:
        return check_output(['docker', 'exec', container, 'cat', path])


def runtime_identity(container, setup, names):
    # Import modules without creating nodes or writing bytecode. Resolve them
    # under the same declared overlay setup used by the whole-product runs.
    program = (
        'import importlib,json,platform,sys; '
        'from ament_index_python.packages import get_package_prefix; '
        f'names={names!r}; extra_packages={EXTRA_PACKAGES!r}; '
        'print(json.dumps(dict(platform=platform.platform(),python=sys.version,'
        'resolved_modules={n:importlib.import_module(n).__file__ for n in names},'
        'extra_package_prefixes={n:get_package_prefix(n) for n in extra_packages})))')
    command = ('source '+shlex.quote(setup)+'\n'
               'export PYTHONDONTWRITEBYTECODE=1\n'
               'python3 -c '+shlex.quote(program))
    result = json.loads(check_output(['docker', 'exec', container, 'bash', '-c', command]))
    result['ros_packages'] = check_output([
        'docker', 'exec', container, 'dpkg-query', '-W', '-f=${Package}\t${Version}\n',
        'ros-humble-rcl', 'ros-humble-rclcpp', 'ros-humble-rclpy']).decode()
    return result


def bind(args):
    repo, execution, baseline, out = (path.resolve() for path in
        (args.repo, args.execution_root, args.baseline, args.output_directory))
    source_path, native_path = out/'joined-source-identity.json', out/'joined-native-identity.json'
    require(out.is_dir(), f'output directory does not exist: {out}')
    require(not source_path.exists() and not native_path.exists(),
            'joined identity already exists; refusing to overwrite either document')
    require(out != repo and repo not in out.parents, 'identity output must be outside the repository')
    source_baseline_path = baseline/'source-identity-v46.json'
    native_baseline_path = baseline/'native-identity-v46-bound.json'
    source_baseline_bytes = source_baseline_path.read_bytes()
    native_baseline_bytes = native_baseline_path.read_bytes()
    source = json.loads(source_baseline_bytes)
    native = json.loads(native_baseline_bytes)
    require(source['candidate'] == native['candidate'] == BASELINE_CANDIDATE,
            'V46 baseline candidate identity changed')
    require(len(source['files']) == 494, 'V46 source inventory no longer has 494 files')
    require(len(native['source_installed_equal']) == 137,
            'V46 installed Python inventory no longer has 137 entries')
    require(len(native['native_binaries']) == 9, 'V46 native inventory no longer has nine binaries')
    candidate = check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip()
    dirty = check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=all',
                          '--', 'src', 'tools', '.github/workflows/hwt601-we.yml']).decode().strip()
    require(not dirty, 'commit the candidate source/tools/workflow before binding:\n'+dirty)
    tracked = set(check_output(['git', '-C', str(repo), 'ls-files', '-z']).decode().split('\0'))
    source = copy.deepcopy(source)
    native = copy.deepcopy(native)
    # Gitlinks are commit references, not files whose nonexistent bytes can
    # be compared. The current uninitialized external dependency remains
    # explicit; its actual running native binaries retain their original pins.
    gitlinks = {}
    records = check_output(['git', '-C', str(repo), 'ls-files', '--stage', '-z',
                            '--', 'src', 'tools', '.github/workflows/hwt601-we.yml'])
    for record in records.decode().split('\0'):
        if not record:
            continue
        metadata, relative = record.split('\t', 1)
        mode, blob, stage = metadata.split()
        require(stage == '0', f'unmerged candidate file: {relative}')
        if mode == '160000':
            gitlinks[relative] = dict(commit=blob, source_bytes_checked=False,
                reason='gitlink only; submodule contents are not in this source inventory')
            continue
        require(mode in ('100644', '100755'), f'unsupported candidate file mode: {relative}: {mode}')
        source['files'].setdefault(relative, {})
    source['gitlinks'] = gitlinks
    for relative in ADDITIONS:
        require(relative in source['files'], f'required candidate addition is not tracked: {relative}')
    require(set(source['files']) <= tracked,
            'identity contains files not tracked by the candidate: '+repr(sorted(set(source['files'])-tracked)))
    installed_entries = {entry['source']: entry for entry in native['source_installed_equal']}
    require(len(installed_entries) == 137, 'duplicate source in V46 installed inventory')
    declared_installed = {name: entry['installed'] for name, entry in source['files'].items()
                          if entry.get('installed')}
    require(declared_installed == {name: entry['installed'] for name, entry in installed_entries.items()},
            'source/native installed inventories disagree')
    # Match these two packages' existing setup.py data_files/packages rules;
    # setup.py itself is build input, never an alleged installed runtime file.
    added_installed = []
    for package in EXTRA_PACKAGES:
        package_root = f'src/{package}/'
        for relative in sorted(source['files']):
            if not relative.startswith(package_root):
                continue
            local = relative.removeprefix(package_root)
            installed = None
            if local.startswith(package+'/') and local.endswith('.py'):
                installed = f'{INSTALL_ROOT}/{package}/lib/python3.10/site-packages/{local}'
            elif local in ('package.xml', 'README.md'):
                installed = f'{INSTALL_ROOT}/{package}/share/{package}/{local}'
            elif local.startswith('launch/') and local.endswith('.launch.py'):
                installed = f'{INSTALL_ROOT}/{package}/share/{package}/{local}'
            elif local.startswith('config/') and (package == 'robot_bringup' or local.endswith('.yaml')):
                installed = f'{INSTALL_ROOT}/{package}/share/{package}/{local}'
            elif local == f'resource/{package}':
                installed = f'{INSTALL_ROOT}/{package}/share/ament_index/resource_index/packages/{package}'
            if installed is None:
                continue
            require(relative not in installed_entries, f'additional install already in V46 inventory: {relative}')
            source['files'][relative]['installed'] = installed
            entry = dict(source=relative, installed=installed)
            installed_entries[relative] = entry
            added_installed.append(relative)
    require(added_installed, 'additional package install inventory is empty')
    native['source_installed_equal'] = list(installed_entries.values())
    changed = []
    for relative, entry in source['files'].items():
        original = (repo/relative).read_bytes()
        require(original == (execution/relative).read_bytes(), f'execution source mismatch: {relative}')
        current_sha = sha(original)
        previous_sha = entry.get('sha256')
        if previous_sha != current_sha:
            changed.append(dict(path=relative, baseline_sha256=previous_sha, sha256=current_sha))
        entry.update(sha256=current_sha, source_execution_equal=True)
        if entry.get('installed'):
            require(original == installed_bytes(entry['installed'], args.container),
                    f'installed module mismatch: {relative} -> {entry["installed"]}')
            entry['source_execution_installed_equal'] = True
            installed_entries[relative]['sha256'] = current_sha
    for name, expected in (
            ('docs/wohnungserkundung/MASTERPLAN.md', MASTER_SHA256),
            ('tools/simulation/ap06_product_scenarios.json', MANIFEST_SHA256)):
        require(sha((repo/name).read_bytes()) == expected, f'original pin changed in source: {name}')
        require(sha((execution/name).read_bytes()) == expected, f'original pin changed in execution: {name}')
    require(source['masterplan_sha256'] == MASTER_SHA256 and source['manifest_sha256'] == MANIFEST_SHA256,
            'V46 manifest/masterplan pin changed')
    for entry in source['native_plugins'] + native['native_binaries']:
        require(sha(installed_bytes(entry['path'], args.container)) == entry['sha256'],
                f'original native binary pin mismatch: {entry["path"]}')
        if entry.get('source'):
            require(sha((repo/entry['source']).read_bytes()) == entry['source_sha256'],
                    f'original native arithmetic source changed: {entry["source"]}')
    arithmetic = source['additional_native_arithmetic']
    require(any(entry == arithmetic for entry in native['native_binaries']),
            'V46 arithmetic binding disagrees between source/native identities')
    current_runtime = runtime_identity(args.container, args.setup,
        list(native['resolved_modules'])+list(EXTRA_PACKAGES))
    for key in ('platform', 'python', 'ros_packages'):
        require(current_runtime[key] == native[key], f'actual runtime identity changed: {key}')
    for name, path in native['resolved_modules'].items():
        require(current_runtime['resolved_modules'][name] == path,
                f'actual original module resolution changed: {name}')
    for package in EXTRA_PACKAGES:
        expected_prefix = f'{INSTALL_ROOT}/{package}'
        require(current_runtime['extra_package_prefixes'][package] == expected_prefix,
                f'additional package resolves outside current install: {package}')
        require(current_runtime['resolved_modules'][package] ==
                f'{expected_prefix}/lib/python3.10/site-packages/{package}/__init__.py',
                f'additional Python package resolves outside current install: {package}')
    native['resolved_modules'] = current_runtime['resolved_modules']
    native['extra_package_prefixes'] = current_runtime['extra_package_prefixes']
    # Guard against editing/committing while hashing hundreds of files.
    require(check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip() == candidate,
            'candidate HEAD changed during binding')
    require(not check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=all',
                              '--', 'src', 'tools', '.github/workflows/hwt601-we.yml']).strip(),
            'candidate source changed during binding')
    created = datetime.now(timezone.utc).isoformat()
    provenance = dict(created_utc=created, candidate=candidate,
        source_repository=str(repo), execution_repository=str(execution),
        container=args.container, setup=args.setup,
        baseline_candidate=BASELINE_CANDIDATE,
        baseline_source_identity_sha256=sha(source_baseline_bytes),
        baseline_native_identity_sha256=sha(native_baseline_bytes),
        binder_sha256=sha(Path(__file__).read_bytes()), original_qualified_missions=0,
        hardware_qualified=False, changes_from_v46=changed,
        baseline_source_files=494, baseline_installed_files=137,
        additional_installed_sources=added_installed, gitlinks=gitlinks)
    for document in (source, native):
        document.update(candidate=candidate, qualification=QUALIFICATION, binding=provenance)
    native['joined_source_identity'] = source_path.name
    native_bytes = encoded(native)
    source['joined_native_identity_sha256'] = sha(native_bytes)
    source_bytes = encoded(source)
    # Exclusive creation protects originals and concurrent runs. All validation
    # above finishes before either file is created; partial pairs are explicit.
    with native_path.open('xb') as stream:
        stream.write(native_bytes)
    with source_path.open('xb') as stream:
        stream.write(source_bytes)
    print(json.dumps(dict(candidate=candidate, source_files=len(source['files']),
        installed_files=len(installed_entries), native_binaries=len(native['native_binaries']),
        native_plugins=len(source['native_plugins']), changed_source_files=len(changed),
        source_identity=str(source_path), source_identity_sha256=sha(source_bytes),
        native_identity=str(native_path), native_identity_sha256=sha(native_bytes),
        manifest_sha256=MANIFEST_SHA256, masterplan_sha256=MASTER_SHA256), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('/workspace/Roboter_ws-ap06'))
    parser.add_argument('--execution-root', type=Path, default=Path('/workspace/scratch/ap06-repo'))
    parser.add_argument('--baseline', type=Path, default=Path('/workspace/scratch/ap06-missions-20261005'))
    parser.add_argument('--output-directory', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--container', default='ap03-nav2')
    parser.add_argument('--setup', default='/evidence/ap06-missions-20261005/old-whole-setup.sh')
    try:
        bind(parser.parse_args())
    except (BindingError, OSError, ValueError, KeyError) as error:
        print('JOINED BINDING FAILED: '+str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
