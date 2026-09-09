from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'start_hwt601_encoder_shadow.sh'
OBSERVER_WRAPPER = ROOT / 'start_hwt601_encoder_shadow_observer.sh'


def test_wrapper_requires_explicit_stillness_before_any_device_check():
    result = subprocess.run(
        ['bash', str(WRAPPER)],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )

    assert result.returncode == 2
    assert 'AMADEUS_HWT601_ENCODER_STILLSTAND=JA fehlt' in result.stderr


def test_wrapper_requires_stopped_base_stack_before_any_device_check():
    result = subprocess.run(
        ['bash', str(WRAPPER)],
        capture_output=True,
        text=True,
        check=False,
        env={'AMADEUS_HWT601_ENCODER_STILLSTAND': 'JA'},
    )

    assert result.returncode == 2
    assert 'AMADEUS_BASE_STACK_GESTOPPT=JA fehlt' in result.stderr


def test_wrapper_hardens_ports_identity_domain_and_launch_scope():
    source = WRAPPER.read_text()

    assert 'AMADEUS_BASE_STACK_GESTOPPT' in source
    assert 'ID_VENDOR_ID=0403' in source
    assert 'ID_MODEL_ID=6001' in source
    assert 'ID_SERIAL_SHORT=BG03R8RZ' in source
    assert 'ID_VENDOR_ID=1a86' in source
    assert 'ID_MODEL_ID=7523' in source
    assert '2.4.4.4:1.0' in source
    assert 'check_port_free /dev/ttyUSB_HWT601' in source
    assert 'check_port_free "${hwt_device}"' in source
    assert 'check_port_free /dev/ttyUSB_BASE' in source
    assert 'check_port_free "${base_device}"' in source
    assert 'NetworkInterface name="lo"' in source
    assert 'RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' in source
    assert 'ros2 node list --no-daemon 2>&1' in source
    assert (
        'expected_observer="/hwt601_encoder_shadow_stillstand_observer"'
        in source
    )
    assert '"${existing_nodes}" != "${expected_observer}"' in source
    assert 'hwt601_encoder_sources_shadow.launch.py' in source
    assert 'operator_stationary_confirmed:=true' in source
    assert 'base_hardware.launch.py' not in source
    assert 'cmd_vel' in source  # It is mentioned only in the no-control notice.


def test_observer_wrapper_requires_one_absolute_new_output_directory():
    missing = subprocess.run(
        ['bash', str(OBSERVER_WRAPPER)],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )
    relative = subprocess.run(
        ['bash', str(OBSERVER_WRAPPER), 'relative-output'],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )

    assert missing.returncode == 2
    assert 'absoluter/lokaler/Ausgabeordner' in missing.stderr
    assert relative.returncode == 2
    assert 'muss absolut sein' in relative.stderr


def test_observer_wrapper_is_loopback_only_and_starts_no_source_or_hardware():
    source = OBSERVER_WRAPPER.read_text()

    assert 'hwt601_encoder_shadow_stillstand.py' in source
    assert '--duration 600' in source
    assert 'ros2 node list --no-daemon 2>&1' in source
    assert 'NetworkInterface name="lo"' in source
    assert 'RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' in source
    assert 'Reale Messdaten duerfen nicht im Repository liegen' in source
    assert 'ros2 launch' not in source
    assert '/dev/tty' not in source
    assert 'cmd_vel' not in source


def test_observer_wrapper_rejects_dotdot_alias_back_into_repository():
    workspace = ROOT.parents[1]
    disguised_repo_path = (
        f'{workspace}/../{workspace.name}/observer-real-data')

    result = subprocess.run(
        ['bash', str(OBSERVER_WRAPPER), disguised_repo_path],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )

    assert result.returncode == 2
    assert 'duerfen nicht im Repository liegen' in result.stderr


def test_observer_wrapper_rejects_repository_through_workspace_symlink(
    tmp_path,
):
    workspace = ROOT.parents[1]
    workspace_alias = tmp_path / 'workspace-alias'
    workspace_alias.symlink_to(workspace, target_is_directory=True)
    wrapper_alias = (
        workspace_alias / 'tools' / 'sensorfusion'
        / OBSERVER_WRAPPER.name
    )
    real_repo_output = workspace / 'observer-symlink-real-data'

    result = subprocess.run(
        ['bash', str(wrapper_alias), str(real_repo_output)],
        capture_output=True,
        text=True,
        check=False,
        env={},
    )

    assert result.returncode == 2
    assert 'duerfen nicht im Repository liegen' in result.stderr
