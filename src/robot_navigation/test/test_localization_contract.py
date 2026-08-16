import json
import math
from array import array

from robot_navigation.localization_contract import (
    covariance_hysteresis_limits,
    covariance_quality,
    decode_global_scan_match,
    decode_map_manager_binding,
    decode_semantic_binding,
    initialization_matches_bindings,
    matching_bindings,
    pose_matches_global_scan,
    transform_stability_hysteresis_limits,
    transform_window_motion,
    transform_window_stable,
)


FINGERPRINT = 'a' * 64
INITIALIZATION_ID = '1' * 32


def map_status(*, publisher_count=1, fingerprint=FINGERPRINT, ok=True):
    return json.dumps({
        'schema_version': 1,
        'ok': ok,
        'map': {
            'snapshot_available': True,
            'publisher_count': publisher_count,
            'summary': {'fingerprint': fingerprint, 'frame_id': 'map'},
        },
    })


def semantic_status(*, fingerprint=FINGERPRINT, observed=FINGERPRINT):
    return json.dumps({
        'schema_version': 1,
        'ok': True,
        'semantic_map': {
            'editable': True,
            'map_ref': {'fingerprint': fingerprint, 'frame_id': 'map'},
        },
        'map_manager': {'observed_fingerprint': observed},
    })


def global_scan_status(**overrides):
    payload = {
        'schema_version': 1,
        'ok': True,
        'state': 'accepted',
        'map_fingerprint': FINGERPRINT,
        'global_initialization_generation': 3,
        'global_initialization_id': INITIALIZATION_ID,
        'pose': {'x_m': 1.25, 'y_m': -1.15, 'yaw_rad': 0.7},
        'score': 0.98,
        'endpoint_within_0_15_m_ratio': 0.99,
        'score_ratio': 1.28,
    }
    payload.update(overrides)
    return json.dumps(payload)


def decode_scan(data):
    return decode_global_scan_match(
        data,
        expected_fingerprint=FINGERPRINT,
        expected_generation=3,
        expected_initialization_id=INITIALIZATION_ID,
        minimum_score=0.85,
        minimum_endpoint_ratio=0.85,
        minimum_score_ratio=1.15)


def test_matching_live_map_and_semantics_are_bound_by_fingerprint():
    metric, metric_error = decode_map_manager_binding(map_status())
    semantic, semantic_error = decode_semantic_binding(semantic_status())
    assert metric_error is None
    assert semantic_error is None
    assert matching_bindings(metric, semantic)


def test_duplicate_map_publishers_and_cross_map_semantics_fail_closed():
    binding, error = decode_map_manager_binding(
        map_status(publisher_count=2))
    assert binding is None
    assert 'genau einen Publisher' in error

    semantic, error = decode_semantic_binding(
        semantic_status(observed='b' * 64))
    assert semantic is None
    assert 'stimmen nicht ueberein' in error

    metric, _ = decode_map_manager_binding(map_status())
    semantic, _ = decode_semantic_binding(
        semantic_status(fingerprint='b' * 64, observed='b' * 64))
    assert not matching_bindings(metric, semantic)


def test_global_initialization_is_bound_to_the_current_map_fingerprint():
    metric, _ = decode_map_manager_binding(map_status())
    semantic, _ = decode_semantic_binding(semantic_status())
    assert initialization_matches_bindings(metric, semantic, FINGERPRINT)
    assert not initialization_matches_bindings(metric, semantic, 'b' * 64)
    assert not initialization_matches_bindings(metric, semantic, None)

    changed_semantic, _ = decode_semantic_binding(
        semantic_status(fingerprint='b' * 64, observed='b' * 64))
    assert not initialization_matches_bindings(
        metric, changed_semantic, FINGERPRINT)


def test_global_scan_match_is_bound_to_map_generation_and_unique_reset():
    match, error = decode_scan(global_scan_status())
    assert error is None
    assert match.fingerprint == FINGERPRINT
    assert match.generation == 3

    for changed, expected_reason in (
            ({'map_fingerprint': 'b' * 64}, 'aktuellen Karte'),
            ({'global_initialization_generation': 4}, 'Reset-Generation'),
            ({'global_initialization_id': '2' * 32}, 'Global-Reset')):
        match, error = decode_scan(global_scan_status(**changed))
        assert match is None
        assert expected_reason in error


def test_global_scan_quality_and_amcl_seed_confirmation_are_fail_closed():
    for changed, expected_reason in (
            ({'score': 0.84}, 'Gesamtscore'),
            ({'endpoint_within_0_15_m_ratio': 0.84}, 'Wandtrefferquote'),
            ({'score_ratio': 1.14}, 'nicht eindeutig')):
        match, error = decode_scan(global_scan_status(**changed))
        assert match is None
        assert expected_reason in error

    match, error = decode_scan(global_scan_status())
    assert error is None
    confirmed, reason = pose_matches_global_scan(
        1.27, -1.16, 0.72, match,
        maximum_position_error_m=0.30,
        maximum_yaw_error_rad=math.radians(12.0))
    assert confirmed, reason

    confirmed, reason = pose_matches_global_scan(
        0.70, 0.38, math.radians(-123.0), match,
        maximum_position_error_m=0.30,
        maximum_yaw_error_rad=math.radians(12.0))
    assert not confirmed
    assert 'entfernt' in reason


def test_covariance_uses_planar_standard_deviations():
    covariance = array('d', [0.0] * 36)
    covariance[0] = 0.01
    covariance[7] = 0.0225
    covariance[35] = math.radians(5.0) ** 2
    quality, error = covariance_quality(
        covariance,
        maximum_position_stddev_m=0.20,
        maximum_yaw_stddev_rad=math.radians(10.0))
    assert error is None
    assert quality.x_stddev_m == 0.1
    assert math.isclose(quality.y_stddev_m, 0.15)

    covariance[0] = 0.25
    quality, error = covariance_quality(
        covariance,
        maximum_position_stddev_m=0.20,
        maximum_yaw_stddev_rad=math.radians(10.0))
    assert quality is not None
    assert 'Positionsunsicherheit' in error


def test_covariance_hysteresis_is_strict_to_acquire_and_wider_to_release():
    acquire = covariance_hysteresis_limits(
        False,
        acquire_position_stddev_m=0.20,
        acquire_yaw_stddev_rad=math.radians(10.0),
        release_position_stddev_m=0.30,
        release_yaw_stddev_rad=math.radians(15.0))
    maintain = covariance_hysteresis_limits(
        True,
        acquire_position_stddev_m=0.20,
        acquire_yaw_stddev_rad=math.radians(10.0),
        release_position_stddev_m=0.30,
        release_yaw_stddev_rad=math.radians(15.0))
    assert acquire == (0.20, math.radians(10.0))
    assert maintain == (0.30, math.radians(15.0))

    # Im Realtest erreichte AMCL waehrend korrekter Fahrt kurz 0,202 m und
    # 10,76 Grad. Das darf eine zuvor bestaetigte Pose nicht flappend sperren.
    covariance = array('d', [0.0] * 36)
    covariance[0] = 0.1975 ** 2
    covariance[7] = 0.2024 ** 2
    covariance[35] = math.radians(10.76) ** 2
    _, acquire_error = covariance_quality(
        covariance,
        maximum_position_stddev_m=acquire[0],
        maximum_yaw_stddev_rad=acquire[1])
    _, maintain_error = covariance_quality(
        covariance,
        maximum_position_stddev_m=maintain[0],
        maximum_yaw_stddev_rad=maintain[1])
    assert acquire_error
    assert maintain_error is None


def test_covariance_hysteresis_rejects_inverted_or_invalid_limits():
    for release_position, release_yaw in (
            (0.19, math.radians(15.0)),
            (0.30, math.radians(9.0)),
            (float('nan'), math.radians(15.0))):
        try:
            covariance_hysteresis_limits(
                False,
                acquire_position_stddev_m=0.20,
                acquire_yaw_stddev_rad=math.radians(10.0),
                release_position_stddev_m=release_position,
                release_yaw_stddev_rad=release_yaw)
        except ValueError:
            pass
        else:
            raise AssertionError('ungueltige Hysteresegrenzen akzeptiert')


def test_map_to_odom_must_cover_a_stable_real_time_window():
    stable = [
        (index * 0.4, 1.0 + index * 0.002, -0.5, math.radians(179.0))
        for index in range(9)
    ]
    ok, reason = transform_window_stable(
        stable,
        minimum_duration_s=3.0,
        minimum_samples=8,
        maximum_translation_m=0.08,
        maximum_yaw_rad=math.radians(5.0))
    assert ok, reason

    unstable = list(stable)
    unstable[-1] = (3.2, 1.20, -0.5, math.radians(-179.0))
    ok, reason = transform_window_stable(
        unstable,
        minimum_duration_s=3.0,
        minimum_samples=8,
        maximum_translation_m=0.08,
        maximum_yaw_rad=math.radians(5.0))
    assert not ok
    assert 'Position' in reason


def test_transform_stability_hysteresis_allows_measured_motion_corrections():
    acquire = transform_stability_hysteresis_limits(
        False,
        acquire_translation_m=0.08,
        acquire_yaw_rad=math.radians(5.0),
        release_translation_m=0.20,
        release_yaw_rad=math.radians(12.0))
    maintain = transform_stability_hysteresis_limits(
        True,
        acquire_translation_m=0.08,
        acquire_yaw_rad=math.radians(5.0),
        release_translation_m=0.20,
        release_yaw_rad=math.radians(12.0))
    assert acquire == (0.08, math.radians(5.0))
    assert maintain == (0.20, math.radians(12.0))

    # Realfahrt vom 15.08.2026: langsamer begrenzter Bogen, 640 TF-Messpunkte.
    # Normaler AMCL-Ausgleich erreichte in drei Sekunden 0,1601 m / 8,32 Grad.
    measured = [(0.0, 0.0, 0.0, 0.0),
                (3.0, 0.1601, 0.0, math.radians(8.32))]
    _, acquire_reason = transform_window_stable(
        measured, minimum_duration_s=2.4, minimum_samples=2,
        maximum_translation_m=acquire[0], maximum_yaw_rad=acquire[1])
    maintain_ok, maintain_reason = transform_window_stable(
        measured, minimum_duration_s=2.4, minimum_samples=2,
        maximum_translation_m=maintain[0], maximum_yaw_rad=maintain[1])
    assert 'Position' in acquire_reason
    assert maintain_ok, maintain_reason
    assert transform_window_motion(measured) == (
        3.0, 0.1601, math.radians(8.32))


def test_transform_stability_hysteresis_rejects_bad_limits():
    for release_translation, release_yaw in (
            (0.07, math.radians(12.0)),
            (0.20, math.radians(4.0)),
            (float('nan'), math.radians(12.0))):
        try:
            transform_stability_hysteresis_limits(
                False,
                acquire_translation_m=0.08,
                acquire_yaw_rad=math.radians(5.0),
                release_translation_m=release_translation,
                release_yaw_rad=release_yaw)
        except ValueError:
            pass
        else:
            raise AssertionError('ungueltige TF-Hysteresegrenzen akzeptiert')


def test_malformed_and_error_statuses_never_create_bindings():
    for payload in ('not json', json.dumps({'schema_version': 1, 'ok': False})):
        binding, error = decode_map_manager_binding(payload)
        assert binding is None
        assert error
