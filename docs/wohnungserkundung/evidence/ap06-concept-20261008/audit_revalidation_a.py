#!/usr/bin/env python3
"""Read-only audit of closed c5 traces and exact stop receipts."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Completed audits are never overwritten')
    result = json.loads((args.run/'result.json').read_text())
    meta = json.loads((args.run/'events.jsonl.gz.meta.json').read_text())
    fields = ('departure_alignment', 'map_join_rejection', 'map_join_stop',
              'geometry_snapshot_rejection', 'geometry_snapshot_stop')
    receipts = {key: {} for key in fields}
    topics, digest, size = Counter(), hashlib.sha256(), 0
    trace = args.run/'events.jsonl.gz'
    before = trace.stat()
    with gzip.open(trace, 'rb') as stream:
        for line in stream:
            digest.update(line); size += len(line)
            event = json.loads(line)
            topics[event['topic']] += 1
            if event['topic'] != '/explore/status_json':
                continue
            metric = event['data'].get('metric_exploration', {})
            for field in fields:
                value = metric.get(field)
                if isinstance(value, dict) and value:
                    receipts[field].setdefault(json.dumps(value, sort_keys=True), value)
    after = trace.stat()
    assert (size == meta['uncompressed_bytes'] and digest.hexdigest() == meta['sha256']
            and before.st_size == meta['compressed_bytes']
            and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns))
    chain = [{k: entry[k] for k in ('task', 'target', 'result', 'decision',
        'stop_reason', 'terminal_child', 'arrived', 'observed_cells',
        'geometry_snapshot_rejection', 'map_join_rejection') if k in entry}
        for entry in result['metric']['chain']]
    recoveries = []
    for i, entry in enumerate(chain):
        if entry.get('decision') != 'geometry_snapshot_revalidate':
            continue
        following = next((later for later in chain[i+1:]
                          if later.get('task') == entry.get('task')), None)
        recoveries.append(dict(trigger=entry, next_same_task_entry=following,
            subsequent_arrival=bool(following and following.get('arrived'))))
    metric = result['metric']
    data = dict(schema=1, diagnostic_only=True, original_mission_qualified=False,
        trace_verified=True, uncompressed_bytes=size, uncompressed_sha256=digest.hexdigest(),
        result_sha256=hashlib.sha256((args.run/'result.json').read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        topics=dict(topics), receipts={k: list(v.values()) for k, v in receipts.items()},
        chain=chain, recovery_followups=recoveries,
        terminal={key: metric.get(key) for key in
            ('state', 'reason', 'arrivals', 'observations', 'attempts', 'failures')},
        terminal_actions=result['action_active_at_terminal'],
        terminal_commands=result['command_values_at_terminal'],
        checkpoint=result['checkpoint_after_save'],
        limits=['No hardware or original masked-sensor mission acceptance.',
                'A later arrival proves one successful recovery, not whole-mission completion.',
                'Elapsed processing includes scheduling/waiting; no exact CPU hot function is inferred.',
                'The failures counter excludes these revalidation cancellations.'])
    with args.output.open('x') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')
    print(json.dumps(dict(output=str(args.output), trace_verified=True,
        receipt_counts={k: len(v) for k,v in receipts.items()},
        recovered_arrivals=sum(v['subsequent_arrival'] for v in recoveries))))


if __name__ == '__main__':
    main()
