#!/usr/bin/env python3
"""Read only the closed phase-a run; write a new independently verified audit."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'phase-a' / 'door68_start_a'
OUT = ROOT / 'phase-a-join-independent-audit.json'
REPO = Path('/workspace/Roboter_ws-ap06')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError('The independent report already exists; never overwrite evidence')
    result = json.loads((RUN / 'result.json').read_text())
    meta = json.loads((RUN / 'events.jsonl.gz.meta.json').read_text())
    experiment = json.loads((RUN.parent / 'experiment.json').read_text())
    trace = RUN / 'events.jsonl.gz'
    before = trace.stat()
    digest, size = hashlib.sha256(), 0
    topics, transitions, actions, receipts = Counter(), [], [], {}
    previous = None
    with gzip.open(trace, 'rb') as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            event = json.loads(line)
            topic = event['topic']
            topics[topic] += 1
            if topic.endswith('/_action/status'):
                actions.append(event)
            if topic != '/explore/status_json':
                continue
            status = event['data']
            metric = status.get('metric_exploration', {})
            goal = metric.get('active_goal', {})
            receipt = metric.get('departure_alignment')
            if isinstance(receipt, dict):
                receipts.setdefault(str(receipt.get('checked_at')), receipt)
            key = (status.get('phase'), metric.get('state'), metric.get('attempt'),
                   metric.get('first_rejecting_predicate'), len(metric.get('chain', [])),
                   metric.get('reason'), goal.get('revision'))
            if key != previous:
                transitions.append(dict(at=event['at'], published_unix_s=status.get('time'),
                    phase=status.get('phase'), state=metric.get('state'),
                    attempt=metric.get('attempt'), arrivals=metric.get('arrivals'),
                    observations=metric.get('observations'), chain_entries=len(metric.get('chain', [])),
                    first_rejecting_predicate=metric.get('first_rejecting_predicate'),
                    reason=metric.get('reason'), active_goal=goal,
                    scan_progress_rad=metric.get('scan_progress_rad'),
                    scan_join_revalidate=metric.get('scan_join_revalidate')))
                previous = key
    after = trace.stat()
    if (size != meta['uncompressed_bytes'] or digest.hexdigest() != meta['sha256']
            or before.st_size != meta['compressed_bytes']
            or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
        raise ValueError('Closed trace identity mismatch')
    sources = {}
    for relative in ('src/explore/explore/metric_frontier_runtime.py',
                     'src/explore/explore/metric_frontier.py'):
        observed = sha(REPO / relative)
        recorded = experiment['source_identity']['files'][relative]
        sources[relative] = dict(current_sha256=observed,
            executed_manifest_sha256=recorded, matches=observed == recorded)
    report = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        trace=dict(path=str(trace), uncompressed_sha256=digest.hexdigest(),
            uncompressed_bytes=size, compressed_bytes=before.st_size, verified=True),
        artifact_hashes={name: sha(RUN / name) for name in ('result.json',
            'events.jsonl.gz.meta.json', 'controller_server.log', 'explorer.log', 'maps.log')},
        inspected_sources=sources, topic_counts=dict(topics),
        status_transitions=transitions, action_transitions=actions,
        all_observed_alignment_receipts=list(receipts.values()),
        final_start_reference=result['metric'].get('start_reference'),
        measured_outcome=dict(state=result['metric']['state'], reason=result['metric']['reason'],
            arrivals=result['metric']['arrivals'], observations=result['metric']['observations'],
            attempts=result['metric']['attempts'], failures=result['metric']['failures'],
            travel_m=result['travel_m'], map_oracle=result['map_oracle'],
            minimum_padded_clearance_m=result['minimum_padded_clearance_m'],
            rear_cleared=result['rear_cleared'],
            action_active_at_terminal=result['action_active_at_terminal'],
            command_values_at_terminal=result['command_values_at_terminal']),
        established_findings=[
            'Two active Task-2 navigation attempts were canceled for map/status join; one intervening attempt produced a real arrival and partial observation.',
            'The three Task-2 dispatches exhaust the configured retry_limit + 1 tries, even though aggregate mission failures remain zero.',
            'The terminal rejected attempt exits before chain.append at the retry limit, so chain omits that final canceled leg.',
            'All recorded departure_alignment receipts are controller_owned; this run did not exercise the new external rotation validation branch.',
            'The reported private reference has valid=[true,true] but empty retained/projected cell counts and zero retained area.',
        ],
        source_supported_hypothesis=dict(
            predicate='metric_frontier_runtime.py:583: any(e.valid for e in _metric_egress)',
            finding='The existing raw-first public withdrawal fallback rejects valid-but-empty private evidence; valid is not equivalent to usable private authority.',
            limit='No exact join-rejection receipt or historical raw/status pairs were logged, so the particular branch at either historical cancellation cannot be proven from this trace alone.'),
        evidence_limits=[
            'Neither /map nor /robot_map_manager/status_json is present in the event journal; historical fingerprint pairs, pending durations, and callback ordering cannot be reconstructed.',
            'The first_rejecting_predicate field remains map_status_join_pending from the early scan onward. It is stale diagnostic state, not a timestamp of each later rejection.',
            'The active_goal.revision values 27, 149 and 235 belong to selected proposals, not a log of every current raw/status correlation.',
            'Final raw/costmap snapshots cannot establish historical maps at either canceled leg.',
            'No hardware or original masked-LiDAR qualification follows from this finite-unmasked simulation.'
        ])
    with OUT.open('x') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(OUT), trace_verified=True,
        alignment_receipts=len(receipts), source_identity_matches=all(s['matches'] for s in sources.values()))))


if __name__ == '__main__':
    main()
