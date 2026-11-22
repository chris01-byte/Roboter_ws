"""Radsensor-Zustand: die Angaben der Encoder-Zeitwache in Klartext."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'werkzeuge'))

from radsensor_zustand import radsensor_zeilen  # noqa: E402


def gesperrt():
    # Felder wie in base_hardware (shadow_status_payload), Werte erfunden
    return {
        'encoder_feedback_ok': False, 'encoder_stale': True,
        'encoder_feedback_age_s': 73.2, 'x_m': 1.5, 'y_m': -0.2,
        'encoder_timing_recovery': {
            'state': 'fault_latched', 'fault_reason': 'encoder_timing_continuity_unproven',
            'timing_recovery_count': 1, 'timing_recovery_attempt_limit': 2,
            'continuity_max_gap_s': 0.18,
            'first_timing_rejection': {
                'reason': 'encoder_luecke_nicht_ueberbrueckbar', 'pair_duration_s': 0.046,
                'sample_gap_s': 0.2512, 'read_end_age_s': 0.274},
            'last_timing_rejection': None,
            'complete_pair_count': 512, 'rejected_pair_count': 3,
            'fc03_pair_error_count': 0, 'maximum_pair_duration_s': 0.0966,
            'maximum_attempted_pair_duration_s': 0.0966,
            'x_m': 1.5, 'y_m': -0.2, 'yaw_rad': 0.3,
        },
    }


def test_gesperrter_radsensor_in_klartext():
    zeilen = radsensor_zeilen(gesperrt())
    assert zeilen[0] == 'Radsensor: Messung frisch: nein; letzte Messung vor 73.2 s.'
    assert "Zustand 'fault_latched'" in zeilen[1]
    assert "Grund 'encoder_timing_continuity_unproven'" in zeilen[1]
    assert 'Überbrückungsversuche 1 von 2' in zeilen[1] and '180.0 ms' in zeilen[1]
    assert zeilen[2] == ("Erste Lücke: 'encoder_luecke_nicht_ueberbrueckbar', Abstand der "
                         "Lesungen 251.2 ms, Lesepaar 46.0 ms, Alter am Leseende 274.0 ms.")
    assert zeilen[3] == 'Letzte Lücke: keine.'
    assert '512 gültig, 3 verworfen, Lesefehler 0' in zeilen[4]
    assert 'längstes Lesepaar 96.6 ms' in zeilen[4]


def test_keine_lage_des_roboters_in_der_ausgabe():
    text = '\n'.join(radsensor_zeilen(gesperrt()))
    assert '1.5' not in text and '-0.2' not in text and 'yaw' not in text


def test_ohne_nachricht_oder_ohne_zeitwache():
    assert radsensor_zeilen(None) == ['Radsensor: keine Nachricht von base_hardware empfangen.']
    zeilen = radsensor_zeilen({'encoder_feedback_ok': True, 'encoder_stale': False})
    assert zeilen[0] == 'Radsensor: Messung frisch: ja.'
    assert zeilen[1].startswith('Zeitwache: keine Angaben')
