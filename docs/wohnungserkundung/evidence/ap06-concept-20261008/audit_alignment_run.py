#!/usr/bin/env python3
"""Audit a CLOSED concept run, without altering any original artifact.

Only result.json plus a closed events.jsonl.gz.meta.json permits reading the
trace. No ROS imports, subprocesses, live polling or execution of product code.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def alignment_windows(result, journal):
    windows = []
    for index, entry in enumerate(result.get('metric', {}).get('chain', [])):
        receipt = entry.get('alignment')
        if not isinstance(receipt, dict):
            continue
        end = receipt.get('checked_at')
        target = entry.get('target')
        if not finite_number(end) or not isinstance(target, list) or len(target) != 2:
            continue
        matching = [row for row in journal
                    if row.get('task_id') == entry.get('task')
                    and finite_number(row.get('finished_monotonic'))
                    and row['finished_monotonic'] <= end
                    and all(math.isclose(row.get('target', {}).get(axis, math.inf), value,
                                         rel_tol=0., abs_tol=1e-9)
                            for axis, value in zip(('x', 'y'), target))]
        prediction = max(matching, key=lambda row: row['finished_monotonic']) if matching else None
        windows.append(dict(
            chain_index=index, task_id=entry.get('task'), target=target,
            alignment_receipt=receipt,
            original_future_prediction=None if prediction is None else prediction.get('original_decision'),
            future_prediction_deferred=None if prediction is None else prediction.get('deferred'),
            prediction_sequence=None if prediction is None else prediction.get('sequence'),
            start_monotonic=None if prediction is None else prediction['finished_monotonic'],
            end_monotonic=end,
            observed_prealignment_phase_begin=None,
            window_definition=('Post-prediction return through exact alignment receipt; includes alignment preparation and stop confirmation'
                if prediction is not None else
                'First observed metric_prealign status for the exact task/attempt through exact alignment receipt; includes planning/preparation and stop confirmation, and may omit time before the first status publication'),
            entry_result=entry.get('result'), entry_decision=entry.get('decision'),
            actual_stop_reason=entry.get('stop_reason'), child_dispatched=entry.get('child_dispatched'),
            planning_rejection=entry.get('planning_rejection'),
            planning_rejection_warning=('May be an older attempt status; do not use as the alignment cause'
                if entry.get('result') != 'planning_failed' and entry.get('planning_rejection') else None),
            samples=[]))
    return windows


def sample_summary(rows):
    if not rows:
        return dict(samples=0, unavailable_reason='No base samples in the bound closed interval')
    pulses, pulse = [], []
    for row in rows:
        if abs(row['command_w_radps']) > 1e-6:
            pulse.append(row)
        elif pulse:
            pulses.append(pulse)
            pulse = []
    if pulse:
        pulses.append(pulse)
    intervals = [b[0]['at']-a[0]['at'] for a, b in zip(pulses, pulses[1:])]
    duration = rows[-1]['at']-rows[0]['at']
    # Sum wrapped increments instead of subtracting two headings across pi.
    yaw_delta = sum(math.atan2(math.sin(b['yaw_rad']-a['yaw_rad']),
                               math.cos(b['yaw_rad']-a['yaw_rad']))
                    for a, b in zip(rows, rows[1:]))
    active_rows = ([row for row in rows if pulses[0][0]['at'] <= row['at'] <= pulses[-1][-1]['at']]
                   if pulses else [])
    return dict(
        samples=len(rows), first_sample_monotonic=rows[0]['at'], last_sample_monotonic=rows[-1]['at'],
        observed_interval_s=duration,
        all_encoder_samples_valid=all(row['encoder_valid'] for row in rows),
        zero_command_sample_fraction=sum(abs(row['command_w_radps']) <= 1e-6 for row in rows)/len(rows),
        watchdog_timed_out_samples=sum(row['timed_out'] for row in rows),
        active_span_zero_command_sample_fraction=(
            sum(abs(row['command_w_radps']) <= 1e-6 for row in active_rows)/len(active_rows)
            if active_rows else None),
        max_abs_arriving_base_command_radps=max(abs(row['command_w_radps']) for row in rows),
        encoder_yaw_delta_rad=yaw_delta,
        mean_encoder_yaw_rate_radps=yaw_delta/duration if duration > 0. else None,
        pulse_count=len(pulses),
        pulse_start_intervals_min_median_max_s=(
            [min(intervals), statistics.median(intervals), max(intervals)] if intervals else None),
        pulses=[dict(start=items[0]['at'], end=items[-1]['at'],
                     observed_duration_s=items[-1]['at']-items[0]['at'],
                     max_abs_command_radps=max(abs(row['command_w_radps']) for row in items))
                for items in pulses])


def mission_summary(result, manifest):
    metric, oracle = result.get('metric', {}), result.get('map_oracle', {})
    minimum = result.get('minimum_padded_clearance_m')
    fraction, error = oracle.get('reference_observed_fraction'), oracle.get('maximum_occupied_wall_error_m')
    acceptance = manifest['acceptance']
    actions = result.get('action_active_at_terminal')
    commands = result.get('command_values_at_terminal')
    return dict(
        harness_passed=result.get('passed'), manifest_compatible=result.get('manifest_compatible'),
        sensor_profile=result.get('sensor_profile'), concept_deferred_departure=result.get('concept_deferred_departure', False),
        original_qualification=False, hardware_qualified=False,
        terminal={key: metric.get(key) for key in (
            'state', 'reason', 'outcome', 'arrivals', 'observations', 'attempts', 'failures',
            'route_rejection', 'planning_route_rejection', 'planning_stop_reason', 'completion_blocker')},
        travel_m=result.get('travel_m'), rear_cleared=result.get('rear_cleared'),
        minimum_padded_clearance_m=minimum, map_oracle=oracle,
        map_save=result.get('map_save'), checkpoint_after_save=result.get('checkpoint_after_save'),
        criteria=dict(
            explorer_success=metric.get('state') == 'success',
            manager_success=result.get('manager', {}).get('state') == 'success',
            three_arrivals=metric.get('arrivals', 0) >= 3,
            three_observations=metric.get('observations', 0) >= 3,
            rear_cleared_both_doors=result.get('rear_cleared') is True,
            map_growth=result.get('map_growth') is True,
            observed_fraction_sufficient=(fraction >= acceptance['min_reference_observed_fraction']
                if finite_number(fraction) else None),
            wall_error_acceptable=(error <= acceptance['max_map_truth_error_m']
                if finite_number(error) else None),
            positive_independent_padded_clearance=(minimum > 0. if finite_number(minimum) else None),
            terminal_actions_empty=(not any(actions.values()) if isinstance(actions, dict) and actions else None),
            terminal_four_command_chains_zero=(
                len(commands) == 4 and all(abs(value) < 1e-9 for pair in commands.values() for value in pair)
                if isinstance(commands, dict) else None)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--baseline-audit', type=Path,
        default=Path(__file__).with_name('deferred-a-independent-audit.json'))
    parser.add_argument('--comparison-run', type=Path,
        default=Path(__file__).parent/'visibility-a',
        help='Primary whole-run reference with unchanged future-departure proof')
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; never overwrite evidence')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Die Ausgabedatei existiert bereits und wird nicht überschrieben.')
    run = args.run.resolve()
    paths = {name: run/name for name in ('result.json', 'manifest.json',
        'events.jsonl.gz', 'events.jsonl.gz.meta.json')}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        parser.error('Der Lauf ist nicht vollständig abgeschlossen; fehlende Artefakte: '+', '.join(missing))
    result, manifest = read_json(paths['result.json']), read_json(paths['manifest.json'])
    journal_path = run/'departure_assessments.jsonl'
    journal = []
    if journal_path.is_file():
        paths['departure_assessments.jsonl'] = journal_path
        journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
    windows = alignment_windows(result, journal)
    trace_path = paths['events.jsonl.gz']
    initial_stat = trace_path.stat()
    trace_meta = read_json(paths['events.jsonl.gz.meta.json'])
    digest, size = hashlib.sha256(), 0
    base_samples = []
    active_phase_key = None
    with gzip.open(trace_path, 'rb') as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            if b'"topic": "/explore/status_json"' in line[:160]:
                event = json.loads(line)
                state = event['data']
                metric = state.get('metric_exploration', {})
                active = metric.get('active_goal', {})
                if state.get('phase') == 'metric_prealign':
                    phase_key = (metric.get('attempt'), active.get('task_id'), active.get('x'), active.get('y'))
                    if phase_key != active_phase_key:
                        for window in windows:
                            if (metric.get('attempt') == window['alignment_receipt'].get('attempt')
                                    and active.get('task_id') == window['task_id']
                                    and event['at'] <= window['end_monotonic']):
                                # Revalidation can retain the same task/attempt.
                                # Use the latest observed entry, not an earlier
                                # prealignment followed by actual navigation.
                                window['observed_prealignment_phase_begin'] = event['at']
                                if window['prediction_sequence'] is None:
                                    window['start_monotonic'] = event['at']
                    active_phase_key = phase_key
                else:
                    active_phase_key = None
                continue
            if b'"topic": "/base_hardware/state_json"' not in line[:160]:
                continue
            event = json.loads(line)
            state = event['data']
            base_samples.append(dict(at=event['at'], command_w_radps=state['cmd_w_radps'],
                timed_out=state['timed_out'], yaw_rad=state['yaw'],
                encoder_valid=state['encoder_feedback_ok'] and not state['encoder_stale']))
    final_stat = trace_path.stat()
    if (size != trace_meta['uncompressed_bytes'] or digest.hexdigest() != trace_meta['sha256']
            or initial_stat.st_size != trace_meta['compressed_bytes']
            or (initial_stat.st_size, initial_stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns)):
        raise ValueError('Das abgeschlossene Ereignisjournal besteht die Identitätsprüfung nicht.')
    for window in windows:
        begin = window['start_monotonic']
        window.pop('samples')
        samples = ([row for row in base_samples if begin <= row['at'] <= window['end_monotonic']]
                   if begin is not None else [])
        window['base_command_measurements'] = sample_summary(samples)
    del base_samples
    baseline = read_json(args.baseline_audit)
    baseline_windows = []
    for original in baseline.get('alignment_windows', []):
        row = dict(original)
        row['pulse_count'] = len(row.pop('pulses', []))
        row['window_definition'] = 'Older run: post-prediction return through later decision snapshot; exact internal alignment return was not recorded'
        baseline_windows.append(row)
    comparison_result = args.comparison_run/'result.json'
    comparison_manifest = args.comparison_run/'manifest.json'
    comparison = dict(
        result_path=str(comparison_result.resolve()), result_sha256=sha(comparison_result),
        manifest_sha256=sha(comparison_manifest),
        mission=mission_summary(read_json(comparison_result), read_json(comparison_manifest)),
        interpretation='Primary whole-run comparison; the original future-departure proof was retained. Different trajectories and timing mean this is not an identical-input benchmark.')
    output = dict(
        schema=1, kind='Independent closed-run alignment and whole-mission audit',
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        script=dict(path=str(Path(__file__).resolve()), sha256=sha(Path(__file__))),
        sources={name: dict(path=str(path), sha256=sha(path)) for name, path in paths.items()
                 if name != 'events.jsonl.gz'},
        trace=dict(path=str(trace_path), uncompressed_bytes=size,
                   uncompressed_sha256=digest.hexdigest(), compressed_bytes=initial_stat.st_size, verified=True),
        mission=mission_summary(result, manifest), alignment_windows=windows,
        prediction_counts=(dict(total=len(journal), original_true=sum(row['original_decision'] is True for row in journal),
                               deferred=sum(row['deferred'] is True for row in journal)) if journal_path.is_file() else None),
        prediction_journal_available=journal_path.is_file(),
        primary_whole_run_comparison=comparison,
        earlier_pulse_reference=dict(path=str(args.baseline_audit.resolve()), sha256=sha(args.baseline_audit),
                                    mission=baseline.get('observed_result'), terminal=baseline.get('terminal'),
                                    alignment_windows=baseline_windows),
        limits=[
            'This audit does not turn a concept profile into original AP-06 qualification or hardware acceptance.',
            'Base command pulse intervals are observed at the base, not publisher callback execution times.',
            'Alignment preparation/stop time is included; old and new window endpoints differ as documented.',
            'Without a predictor journal, an observed metric_prealign phase also contains plan queries; its first publication is not the exact turn-start timestamp.',
            'The earlier pulse reference used the deferred-departure profile. Its two alignment intervals had original positive predictions, but task identity is not asserted across whole runs.',
            'Compare actual receipt status, sustained pulses and achieved angle; different targets/maps are not an identical-input benchmark.',
            'An old planning-rejection status must not be substituted for an actual alignment receipt or final child stop reason.',
            'No callback hot stack or proof of a specific first violating contour cell is inferred.'
        ])
    with args.output.open('x') as stream:
        stream.write(json.dumps(output, indent=2, allow_nan=False)+'\n')
    summary = dict(output=str(args.output), trace_verified=True, mission=output['mission'],
                   alignments=[dict(task=row['task_id'], status=row['alignment_receipt'].get('status'),
                                    achieved_angle_rad=row['alignment_receipt'].get('achieved_angle_rad'),
                                    pulses=row['base_command_measurements'].get('pulse_count')) for row in windows])
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
