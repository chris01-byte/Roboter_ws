#!/usr/bin/env python3
"""Independently audit only the CLOSED joined-a trace; never alter a run."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'joined-a'/'door68_start_a'
OUTPUT = ROOT/'joined-a-join-independent-audit.json'
REPO = Path('/workspace/Roboter_ws-ap06')


def main():
    if OUTPUT.exists():
        raise FileExistsError('Never overwrite a completed audit')
    result = json.loads((RUN/'result.json').read_text())
    metadata = json.loads((RUN/'events.jsonl.gz.meta.json').read_text())
    experiment = json.loads((RUN.parent/'experiment.json').read_text())
    trace = RUN/'events.jsonl.gz'
    before = trace.stat()
    topics, transitions, actions = Counter(), [], []
    alignment, joins, join_stops = {}, {}, []
    digest, size, previous = hashlib.sha256(), 0, None
    with gzip.open(trace, 'rb') as stream:
        for line in stream:
            digest.update(line); size += len(line)
            event = json.loads(line)
            topic = event['topic']; topics[topic] += 1
            if topic.endswith('/_action/status'):
                actions.append(event)
            if topic != '/explore/status_json':
                continue
            status = event['data']; metric = status.get('metric_exploration', {})
            for field, target in (('departure_alignment', alignment), ('map_join_rejection', joins)):
                if isinstance(metric.get(field), dict):
                    target.setdefault(str(metric[field].get('checked_at')), metric[field])
            if metric.get('map_join_stop') and metric['map_join_stop'] not in join_stops:
                join_stops.append(metric['map_join_stop'])
            key = (status.get('phase'), metric.get('state'), metric.get('attempt'),
                   metric.get('reason'), len(metric.get('chain', [])))
            if key != previous:
                transitions.append(dict(at=event['at'], published_unix_s=status.get('time'),
                    phase=status.get('phase'), state=metric.get('state'), attempt=metric.get('attempt'),
                    reason=metric.get('reason'), chain_entries=len(metric.get('chain', [])),
                    active_goal=metric.get('active_goal')))
                previous = key
    after = trace.stat()
    assert (size == metadata['uncompressed_bytes'] and digest.hexdigest() == metadata['sha256']
        and before.st_size == metadata['compressed_bytes']
        and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)), 'Trace identity mismatch'
    sources = {}
    for name in ('src/explore/explore/metric_frontier_runtime.py',
                 'src/explore/explore/explore_node.py', 'src/explore/config/explore_params.yaml'):
        actual = hashlib.sha256((REPO/name).read_bytes()).hexdigest()
        expected = experiment['source_identity']['files'][name]
        sources[name] = dict(inspected_sha256=actual, executed_manifest_sha256=expected, matches=actual == expected)
    audit = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        result_sha256=hashlib.sha256((RUN/'result.json').read_bytes()).hexdigest(),
        trace=dict(path=str(trace), uncompressed_bytes=size, uncompressed_sha256=digest.hexdigest(),
            compressed_bytes=before.st_size, verified=True), inspected_sources=sources,
        topics=dict(topics), status_transitions=transitions, action_transitions=actions,
        alignment_receipts=list(alignment.values()), join_rejections=list(joins.values()), join_stops=join_stops,
        terminal={key: result['metric'].get(key) for key in ('state','reason','arrivals','observations','attempts','failures')},
        terminal_decision_snapshot={key: value for key, value in result['metric']['decision_snapshot'].items()
            if key != 'encoder_state'},
        sensor_result=json.loads((RUN/'sensor_result.json').read_text()),
        source_semantics=dict(scan_timeout_s=.5,
            selected_at_entry='One immutable _door_lidar_scan_snapshot selected before body, mask and egress processing; its callback received_at must already be within [0,0.5] seconds.',
            rejected_at_exit='completed - the SAME selected scan.received_at exceeds the unchanged 0.5 second limit.',
            timestamp_origin='explore_node._on_door_lidar_scan sets received_at=time.monotonic() in the callback, not the LaserScan source stamp.',
            processing_bound='processing elapsed > 0.5 - selected initial receipt age; not necessarily processing elapsed > 0.5 seconds.'),
        established_findings=[
            'No map_join_stop was recorded and neither completed child was canceled for a map join.',
            'The one join rejection is an earlier optional-scan no_active_child transition with private_permit=false and pending_age_s=0.0010480350174475461.',
            'That old join rejection is not the terminal cause; first_rejecting_predicate retained its older map_status_join_pending value.',
            'All three observed departure alignments were controller_owned. The new external rotation branch was not exercised.',
            'The last Navigate child was active from 172135.112396865 through 172136.566999113; Explorer became terminal at 172138.469670511.',
            'The final operating snapshot at 172138.281969407 reports safe, standstill and HWT HEALTHY. This later snapshot does not recover the rejected immutable scan timestamps.'
        ],
        evidence_limits=[
            'The trace has no LaserScan messages, scan callback receipts or per-call geometry timing.',
            'Exact selected scan age, exact processing duration, latest concurrently received scan and callback-delivery gaps are unobserved.',
            'The 2442 produced sensor messages and zero withheld_stale_plant count do not prove Explorer DDS receipt freshness at the rejecting call.',
            'Do not infer a LiDAR outage, a >0.5 second geometry duration, or a specific hot function from this trace alone.',
            'The terminal reason alone does not distinguish the stop callback rejection from a subsequent post-stop input recheck of the same kind.',
            'This finite-unmasked concept run is not an original masked-sensor mission or hardware qualification.'
        ])
    with OUTPUT.open('x') as stream:
        json.dump(audit, stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps(dict(output=str(OUTPUT), verified=True,
        source_identity_matches=all(row['matches'] for row in sources.values()),
        alignment_receipts=len(alignment), join_stops=len(join_stops))))


if __name__ == '__main__':
    main()
