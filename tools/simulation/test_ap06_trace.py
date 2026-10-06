"""Trace compression retains every original event and verifies closed journals."""
import gzip
import json
import pytest
from ap06_trace import EventTrace,verify_trace


def test_all_original_event_bytes_survive_interleaved_flush_and_close(tmp_path):
    trace=EventTrace(tmp_path/'events.jsonl')
    rows=[json.dumps({'at':i*.01,'topic':'/explore/status_json',
        'data':{'reason':'Türprüfung – offen','cells':[0,-1,100]*200}},ensure_ascii=False)+'\n'
        for i in range(100)]
    for row in rows:
        assert trace.write(row)==len(row)
        trace.flush()
    trace.close();trace.close()
    with gzip.open(trace.path,'rb') as stream:
        assert stream.read()==''.join(rows).encode('utf-8')
    proof=verify_trace(trace.path)
    assert proof['verified_decompression'] and proof['uncompressed_bytes']>proof['compressed_bytes']
    assert proof['uncompressed_bytes']==len(''.join(rows).encode('utf-8'))


@pytest.mark.parametrize('fault',['digest','truncated'])
def test_missing_or_changed_trace_bytes_cannot_be_verified(tmp_path,fault):
    trace=EventTrace(tmp_path/'events.jsonl');trace.write('{"at":1,"data":"original"}\n');trace.close()
    if fault=='digest':
        path=trace.path.with_suffix('.gz.meta.json');metadata=json.loads(path.read_text())
        metadata['sha256']='0'*64;path.write_text(json.dumps(metadata))
    else:
        trace.path.write_bytes(trace.path.read_bytes()[:-4])
    with pytest.raises((ValueError,EOFError,OSError)):
        verify_trace(trace.path)
    assert not trace.path.with_suffix('.gz.verified.json').exists()


def test_insufficient_space_rejects_run_before_starting_any_runtime(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from pathlib import Path
    import ap06_trace
    import ap06_closed_product as product
    monkeypatch.setenv('ROS_DOMAIN_ID','188')
    monkeypatch.setenv('AP06_SIMULATION','1')
    monkeypatch.setattr(ap06_trace.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    monkeypatch.setattr(product.subprocess,'Popen',lambda *_a,**_k:pytest.fail('runtime started without storage'))
    args=SimpleNamespace(manifest=Path(product.__file__).with_name('ap06_product_scenarios.json'),
        case='door68_start_b',output=tmp_path/'mission',ideal_lidar=False,
        profile_selection=False,capture_decisions=False,capture_geometry=False,diagnostic_beams=None)
    assert product.run(args)==1
    result=json.loads((args.output/'result.json').read_text())
    assert not result['passed'] and 'insufficient mission evidence' in result['error']
    reserve=json.loads((args.output/'storage_preflight.json').read_text())
    assert not reserve['ready'] and reserve['budgets']['map_save_minimum']==536870912
