"""Real framed pipe: get_nowait may block after only a header is readable."""
import json,multiprocessing,struct,threading,time
from pathlib import Path
from std_msgs.msg import String
from rclpy.serialization import serialize_message,deserialize_message
from base_hardware.encoder_publication import _Publisher


def test_full_queue_with_partial_framed_write_never_blocks_acquisition(tmp_path):
    ctx=multiprocessing.get_context('spawn')
    slot=ctx.Queue(maxsize=1)
    header_written,release=threading.Event(),threading.Event()
    original=slot._send_bytes
    first=True
    def partial(data):
        nonlocal first
        if first and len(data)>16384:
            first=False
            slot._writer._send(struct.pack('!i',len(data)))
            header_written.set()
            assert release.wait(3.)
            slot._writer._send(data)
        else:
            original(data)
    slot._send_bytes=partial
    message=String(data='original source payload '+('x'*20000))
    serialize_message(message)  # native support warmed before source baseline
    publisher=_Publisher(slot)
    timer=None
    try:
        first_began=time.monotonic()
        publisher.publish(message)
        first_finished=time.monotonic()
        assert header_written.wait(3.)
        timer=threading.Timer(.35,release.set); timer.start()
        began=time.monotonic(); publisher.publish(message); elapsed=time.monotonic()-began
        (tmp_path/'partial-write.json').write_text(json.dumps(dict(elapsed=elapsed,payload_bytes=len(serialize_message(message)),partial_header_seen=True)))
        assert elapsed < .18
        release.set(); timer.join(1.)
        data,queued=slot.get(timeout=2.)
        assert deserialize_message(data,String)==message
        assert first_began <= queued <= first_finished  # never refresh a pending original
    finally:
        release.set()
        if timer:timer.join(1.)
        slot.cancel_join_thread();slot.close()
