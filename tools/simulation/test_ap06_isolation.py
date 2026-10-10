"""The simulator may never fall back to the hardware host."""
import json
from pathlib import Path
import pytest
import ap06_isolation as isolation
import ap06_namespace_runtime as runtime


def environment(monkeypatch):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '186')
    original = Path.exists
    monkeypatch.setattr(Path, 'exists', lambda p: False if str(p) in (
        '/.dockerenv', '/dev/ttyUSB_BASE', '/dev/ttyUSB_HWT601', '/etc/nv_tegra_release') else original(p))
    current = {n: n+':[200]' for n in isolation.NAMESPACES}
    parent = {n: n+':[100]' for n in isolation.NAMESPACES}
    monkeypatch.setattr(isolation, 'namespace_ids', lambda: current)
    monkeypatch.setenv('AP06_NAMESPACE_PARENT', json.dumps(parent))
    return parent, current


def test_all_actual_namespace_boundaries_are_required(monkeypatch):
    parent, current = environment(monkeypatch)
    assert isolation.require_isolation()['kind'] == 'bubblewrap'
    for name in isolation.NAMESPACES:
        changed = dict(parent, **{name: current[name]})
        monkeypatch.setenv('AP06_NAMESPACE_PARENT', json.dumps(changed))
        with pytest.raises(RuntimeError, match='separate'):
            isolation.require_isolation()
    for broken in ('{}', 'null', 'invalid'):
        monkeypatch.setenv('AP06_NAMESPACE_PARENT', broken)
        with pytest.raises(RuntimeError): isolation.require_isolation()


@pytest.mark.parametrize('path', ['/dev/ttyUSB_BASE', '/dev/ttyUSB_HWT601', '/etc/nv_tegra_release'])
def test_any_real_hardware_identity_refuses_the_simulator(monkeypatch, path):
    environment(monkeypatch)
    original = Path.exists
    monkeypatch.setattr(Path, 'exists', lambda p: str(p) == path or original(p))
    with pytest.raises(RuntimeError, match='device-free'):
        isolation.require_isolation()


@pytest.mark.parametrize('domain', ['166x', '99', '201'])
def test_domain_is_dedicated_and_valid(monkeypatch, domain):
    environment(monkeypatch); monkeypatch.setenv('ROS_DOMAIN_ID', domain)
    with pytest.raises(RuntimeError): isolation.require_isolation()


def test_namespace_command_whitelists_mounts_and_keeps_arguments_literal(tmp_path, monkeypatch):
    repo, underlay, candidate, output = [tmp_path/n for n in ('repo', 'underlay', 'candidate', 'output')]
    for path in (repo, underlay, candidate, output): path.mkdir()
    script = candidate/'runtime.bash'; script.write_text('true\n')
    monkeypatch.setattr(runtime.shutil, 'which', lambda _: '/usr/bin/bwrap')
    case = 'literal; $(unsafe)'
    argv = runtime.command(repo, script, underlay, output/'case', case)
    assert '--clearenv' in argv and '--unshare-net' in argv and '--unshare-pid' in argv
    assert argv[argv.index('--case')+1] == case
    ro_mounts = [argv[i+1] for i,v in enumerate(argv) if v == '--ro-bind']
    assert '/' not in ro_mounts and '/dev' not in ro_mounts and '/sys' not in ro_mounts
    assert '/run' not in ro_mounts and '/home/p/roboter_ws' not in ro_mounts
    assert '--dev-bind' not in argv and '--share-net' not in argv
    (output/'case').mkdir()
    with pytest.raises(ValueError): runtime.command(repo, script, underlay, output/'case', case)
