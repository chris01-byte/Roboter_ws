"""No ROS imports/processes: experiment identity, isolation and honest grading."""
import json
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

import ap06_concept_experiment as experiment


ACCEPTANCE = dict(min_reference_observed_fraction=.95, max_map_truth_error_m=.1)


def raw_success(case='door68_start_a', profile='finite-unmasked'):
    return dict(passed=True, manifest_compatible=profile == 'native-mask',
        case=dict(id=case), actual_lidar_beams=2160,
        sensor_profile='native_mast_mask' if profile == 'native-mask' else 'ideal_full_360',
        concept_deferred_departure=profile == 'finite-unmasked-deferred-departure',
        metric=dict(state='success', arrivals=3, observations=3),
        manager=dict(state='success'), travel_m=6., rear_cleared=True, map_growth=True,
        map_oracle=dict(reference_observed_fraction=.97, maximum_occupied_wall_error_m=.04))


@pytest.mark.parametrize('profile', experiment.PROFILES)
def test_raw_success_never_becomes_original_or_hardware_qualification(tmp_path, profile):
    result = tmp_path/'result.json'
    raw = raw_success(profile=profile)
    result.write_text(json.dumps(raw))
    original_bytes = result.read_bytes()
    summary = experiment.summarize(result, 0, profile, experiment.CASES[0], ACCEPTANCE)
    assert summary['diagnostic_status'] == 'criteria_met'
    assert summary['raw_harness_passed'] is True
    assert not summary['passed'] and not summary['original_qualification']
    assert not summary['hardware_qualified']
    assert summary['criteria_score'] == dict(met=8, failed=0, unavailable=0, total=8, applicable_to_case=True)
    assert result.read_bytes() == original_bytes


def test_failed_partial_progress_and_original_reason_survive(tmp_path):
    result = tmp_path/'result.json'
    raw = raw_success(experiment.CASES[1])
    raw.update(passed=False, error='AP06 acceptance not met: hwt_terminal', rear_cleared=False)
    raw['metric'].update(state='failed', reason='hwt_terminal', first_rejecting_predicate='encoder_stale')
    raw['manager']['state'] = 'failed'
    result.write_text(json.dumps(raw))
    summary = experiment.summarize(result, 1, 'finite-unmasked', experiment.CASES[1], ACCEPTANCE)
    assert summary['diagnostic_status'] == 'criteria_not_met'
    assert summary['measurements']['metric']['arrivals'] == 3
    assert summary['reasons']['first_rejecting_predicate'] == 'encoder_stale'
    assert summary['criteria_score']['failed'] == 3
    assert summary['harness_returncode'] == 1


@pytest.mark.parametrize('contents, expected', [
    (None, 'missing_result'), ('not json', 'invalid_result'), ('[]', 'invalid_result'),
    ('{"metric": []}', 'invalid_result'), ('{}', 'identity_mismatch')])
def test_missing_or_incomplete_result_cannot_imply_progress(tmp_path, contents, expected):
    result = tmp_path/'result.json'
    if contents is not None:
        result.write_text(contents)
    summary = experiment.summarize(result, 1, 'finite-unmasked', experiment.CASES[0], ACCEPTANCE)
    assert summary['diagnostic_status'] == expected
    assert not summary['passed'] and not summary['original_qualification']
    if contents == '{}':
        assert summary['criteria_score']['unavailable'] == 8


def test_nonzero_process_exit_preserved_even_with_raw_passed(tmp_path):
    result = tmp_path/'result.json'
    result.write_text(json.dumps(raw_success()))
    summary = experiment.summarize(result, -9, 'finite-unmasked', experiment.CASES[0], ACCEPTANCE)
    assert summary['raw_harness_passed'] is True
    assert summary['diagnostic_status'] == 'criteria_not_met'
    assert summary['harness_returncode'] == -9


@pytest.mark.parametrize('field, wrong', [
    ('case', {'id': 'door80_start_c'}), ('sensor_profile', 'native_mast_mask'),
    ('manifest_compatible', True), ('manifest_compatible', 0), ('actual_lidar_beams', 720)])
def test_wrong_case_or_sensor_result_cannot_pass_experiment(tmp_path, field, wrong):
    result = tmp_path/'result.json'
    raw = raw_success()
    raw[field] = wrong
    result.write_text(json.dumps(raw))
    summary = experiment.summarize(result, 0, 'finite-unmasked', experiment.CASES[0], ACCEPTANCE)
    assert summary['diagnostic_status'] == 'identity_mismatch'
    assert summary['identity_errors']
    assert summary['raw_harness_passed'] is True
    assert not summary['passed']


def test_only_declared_sensor_comparison_changes_harness_command(tmp_path):
    args = (tmp_path, tmp_path/'output', experiment.CASES[0])
    baseline = experiment.command(*args, 'native-mask', tmp_path/'probe')
    comparison = experiment.command(*args, 'finite-unmasked', tmp_path/'probe')
    assert comparison == baseline + ['--ideal-lidar']
    assert '--save-partial' in baseline
    assert not any('timeout' in part or 'budget' in part or 'bypass' in part for part in comparison)
    with pytest.raises(ValueError, match='unknown'):
        experiment.command(*args, 'hardware', tmp_path/'probe')


def test_deferred_profile_requires_both_explicit_harness_flags(tmp_path):
    args = (tmp_path, tmp_path/'output', experiment.CASES[0])
    comparison = experiment.command(*args, 'finite-unmasked', tmp_path/'probe')
    deferred = experiment.command(*args, 'finite-unmasked-deferred-departure', tmp_path/'probe')
    assert deferred == comparison + ['--concept-defer-departure']


def test_undeclared_departure_ablation_cannot_be_reported_as_sensor_only(tmp_path):
    result = tmp_path/'result.json'
    result.write_text(json.dumps(raw_success(profile='finite-unmasked-deferred-departure')))
    summary = experiment.summarize(result, 0, 'finite-unmasked', experiment.CASES[0], ACCEPTANCE)
    assert summary['diagnostic_status'] == 'identity_mismatch'
    assert summary['identity_errors'] == [dict(field='concept_deferred_departure', actual=True, expected=False)]


@pytest.fixture
def exported_repo(tmp_path):
    repo = tmp_path/'repo'
    simulation = repo/'tools/simulation'
    simulation.mkdir(parents=True)
    (repo/'src').mkdir()
    (repo/'src/product.py').write_text('original_product = True\n')
    (simulation/'ap06_closed_product.py').write_text('# unit-test placeholder; never executed\n')
    manifest = Path(experiment.__file__).with_name('ap06_product_scenarios.json')
    (simulation/manifest.name).write_bytes(manifest.read_bytes())
    probe = tmp_path/'tf_probe'
    probe.write_text('#!/bin/false\n')
    probe.chmod(0o700)
    return SimpleNamespace(repo=repo, output=tmp_path/'experiment', tf_probe=probe,
        case=[experiment.CASES[0]], profile='finite-unmasked', source_revision='a'*40)


def test_export_revision_honesty_and_actual_source_mutation_identity(exported_repo):
    args = exported_repo
    with pytest.raises(ValueError, match='require --source-revision'):
        experiment.source_identity(args.repo)
    first = experiment.source_identity(args.repo, args.source_revision)
    assert first['revision_origin'] == 'operator_declared_export'
    assert first['git_dirty'] is None and first['git_status'] is None
    assert not first['installed_binary_identity_verified']
    (args.repo/'src/product.py').write_text('original_product = False\n')
    second = experiment.source_identity(args.repo, args.source_revision)
    assert first['actual_source_tree_sha256'] != second['actual_source_tree_sha256']
    assert first['files']['src/product.py'] != second['files']['src/product.py']


@pytest.mark.parametrize('variable, value', [
    ('AP06_SIMULATION', '0'), ('ROS_LOCALHOST_ONLY', '0'), ('ROS_DOMAIN_ID', '99'),
    ('ROS_DOMAIN_ID', '201'), ('ROS_DOMAIN_ID', 'invalid')])
def test_unguarded_environment_rejected_before_any_launch(exported_repo, monkeypatch, variable, value):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '187')
    monkeypatch.setenv(variable, value)
    monkeypatch.setattr(experiment.subprocess, 'Popen', lambda *a, **k: pytest.fail('unguarded launch'))
    with pytest.raises(ValueError):
        experiment.run(exported_repo)
    assert not exported_repo.output.exists()


def test_exposed_robot_device_rejected_before_launch(exported_repo, monkeypatch):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '187')
    original = Path.exists
    monkeypatch.setattr(Path, 'exists', lambda path: str(path) == '/dev/ttyUSB_BASE' or original(path))
    monkeypatch.setattr(experiment.subprocess, 'Popen', lambda *a, **k: pytest.fail('physical device launch'))
    with pytest.raises(ValueError, match='device-free'):
        experiment.run(exported_repo)
    assert not exported_repo.output.exists()


def test_changed_original_manifest_is_not_run(exported_repo, monkeypatch):
    monkeypatch.setattr(experiment, 'require_isolation', lambda: None)
    path = exported_repo.repo/'tools/simulation/ap06_product_scenarios.json'
    path.write_text(path.read_text()+'\n')
    monkeypatch.setattr(experiment.subprocess, 'Popen', lambda *a, **k: pytest.fail('modified manifest launched'))
    with pytest.raises(ValueError, match='manifest changed'):
        experiment.run(exported_repo)
    assert not exported_repo.output.exists()


def test_existing_output_never_overwritten(exported_repo, monkeypatch):
    monkeypatch.setattr(experiment, 'require_isolation', lambda: None)
    exported_repo.output.mkdir()
    evidence = exported_repo.output/'original.txt'
    evidence.write_text('preserve')
    monkeypatch.setattr(experiment.subprocess, 'Popen', lambda *a, **k: pytest.fail('old output launched'))
    with pytest.raises(FileExistsError):
        experiment.run(exported_repo)
    assert evidence.read_text() == 'preserve'


def test_output_inside_source_repository_rejected_before_launch(exported_repo, monkeypatch):
    monkeypatch.setattr(experiment, 'require_isolation', lambda: None)
    exported_repo.output = exported_repo.repo/'massive-logs'
    monkeypatch.setattr(experiment.subprocess, 'Popen', lambda *a, **k: pytest.fail('output inside repository'))
    with pytest.raises(ValueError, match='outside the source repository'):
        experiment.run(exported_repo)
    assert not exported_repo.output.exists()


def test_three_successful_experiments_still_zero_original_qualifications(exported_repo, monkeypatch):
    args = exported_repo
    args.case = list(experiment.CASES[:3])
    monkeypatch.setattr(experiment, 'require_isolation', lambda: None)
    monkeypatch.setenv('ROS_DOMAIN_ID', '187')
    commands = []
    class FakeChild:
        def __init__(self, argv, **kwargs):
            commands.append(argv)
            out = Path(argv[argv.index('--output')+1])
            out.mkdir()
            case = argv[argv.index('--case')+1]
            (out/'result.json').write_text(json.dumps(raw_success(case)))
        def wait(self):
            return 0
    monkeypatch.setattr(experiment.subprocess, 'Popen', FakeChild)
    assert experiment.run(args) == 0  # experiment CLI status only
    summary = json.loads((args.output/'summary.json').read_text())
    assert summary['diagnostic_criteria_met'] == summary['completed_cases'] == 3
    assert summary['original_qualified_missions'] == 0
    assert not summary['passed'] and not summary['original_qualification']
    assert len(commands) == 3 and all('--ideal-lidar' in argv for argv in commands)
    profile = json.loads((args.output/'experiment.json').read_text())
    assert profile['budgets'] == dict(startup_s=60, mission_s=900, goal_s=150, cancel_s=3, stop_s=1)
    assert profile['product_guards'] == 'unchanged'


def test_interrupt_signals_only_harness_once_and_keeps_result(exported_repo, monkeypatch):
    monkeypatch.setattr(experiment, 'require_isolation', lambda: None)
    monkeypatch.setenv('ROS_DOMAIN_ID', '187')
    signals = []
    class InterruptedChild:
        waits = 0
        def __init__(self, argv, **kwargs):
            assert kwargs['start_new_session'] is True
            self.out = Path(argv[argv.index('--output')+1])
            self.out.mkdir()
        def wait(self):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            (self.out/'result.json').write_text(json.dumps({'passed': False, 'error': 'user cancel'}))
            return 1
        def poll(self):
            return None
        def send_signal(self, value):
            signals.append(value)
    monkeypatch.setattr(experiment.subprocess, 'Popen', InterruptedChild)
    with pytest.raises(KeyboardInterrupt):
        experiment.run(exported_repo)
    assert signals == [signal.SIGINT]
    summary = json.loads((exported_repo.output/'summary.json').read_text())
    assert summary['cases'][0]['harness_returncode'] == 1
    assert summary['cases'][0]['reasons']['harness'] == 'user cancel'
    assert not summary['passed']
