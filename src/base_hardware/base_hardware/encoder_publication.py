"""Isolate DDS output from encoder acquisition; never own the serial bus."""
import multiprocessing
import queue
import time


def _send(context, slots, stop, ready, node_name, cpu_affinity, sensor_data_topics=()):
    # Spawn, never fork an initialized DDS participant or serial descriptor.
    import os
    import rclpy
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    from rclpy.qos import qos_profile_sensor_data
    if cpu_affinity:
        os.sched_setaffinity(0, set(cpu_affinity))
    rclpy.init(args=[])
    node = rclpy.create_node(node_name)
    publishers = [(node.create_publisher(get_message(kind), topic,
                   qos_profile_sensor_data if topic in sensor_data_topics else 10),
                   get_message(kind), slot) for topic, kind, slot in slots]
    trace_dir = os.environ.get('AP06_OUTPUT_TRACE_DIR')
    timing = {topic: dict(sent=0, discarded=0, max_queue_age_s=0.,
                         max_publish_duration_s=0.,
                         qos_depth=publisher.qos_profile.depth,
                         qos_reliability=int(publisher.qos_profile.reliability))
              for (publisher, _, _), (topic, _, _) in zip(publishers, slots)}
    ready.set()
    try:
        while not stop.is_set() and rclpy.ok():
            work = False
            for (publisher, kind, slot), (topic, _, _) in zip(publishers, slots):
                try:
                    data, queued = slot.get_nowait()
                except queue.Empty:
                    continue
                work = True
                # Never stamp a queued measurement as new. A stale message is
                # unnecessary: consumer source freshness still closes the gate.
                age = time.monotonic() - queued
                stat = timing[topic]
                stat['max_queue_age_s'] = max(stat['max_queue_age_s'], age)
                if age <= context:
                    started = time.monotonic()
                    publisher.publish(deserialize_message(data, kind))
                    stat['sent'] += 1
                    stat['max_publish_duration_s'] = max(
                        stat['max_publish_duration_s'], time.monotonic()-started)
                else:
                    stat['discarded'] += 1
            if not work:
                stop.wait(.002)
    finally:
        if trace_dir:
            import json
            from pathlib import Path
            Path(trace_dir, f'{node_name}-{os.getpid()}-timing.json').write_text(
                json.dumps(timing, indent=2)+'\n')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


class _Publisher:
    def __init__(self, slot):
        self._slot = slot

    def publish(self, message):
        from rclpy.serialization import serialize_message
        item = (serialize_message(message), time.monotonic())
        try:
            self._slot.put_nowait(item)
        except queue.Full:
            try:
                self._slot.get_nowait()
            except queue.Empty:
                pass
            try:
                self._slot.put_nowait(item)
            except queue.Full:
                pass  # bounded, never wait for a blocked DDS writer


class EncoderPublication:
    """Single publisher owner; one pending item per existing encoder topic."""
    def __init__(self, topics, max_age_s,
                 node_name='hwt601_encoder_shadow_output', cpu_affinity=(),
                 sensor_data_topics=()):
        # Humble imports native message support lazily at first serialization.
        # On this Jetson the first Odometry took 196 ms, later calls .2 ms:
        # initializing it inside acquisition invalidates the encoder interval.
        # Load all parent serializers before the caller establishes its first
        # baseline/timer. Discard these bytes locally; never enqueue or publish
        # a warm-up measurement, alter stamps, or extend the timing contract.
        from rclpy.serialization import serialize_message
        from rosidl_runtime_py.utilities import get_message
        topics = tuple(topics)
        sensor_data_topics = tuple(sensor_data_topics)
        if not set(sensor_data_topics).issubset(topic for topic, _ in topics):
            raise ValueError('Sensor QoS requires an existing output topic')
        for kind in dict.fromkeys(kind for _, kind in topics):
            serialize_message(get_message(kind)())
        ctx = multiprocessing.get_context('spawn')
        self._stop = ctx.Event()
        self._ready = ctx.Event()
        self._slots = [(topic, kind, ctx.Queue(maxsize=1))
                       for topic, kind in topics]
        self._process = ctx.Process(
            target=_send, args=(max_age_s, self._slots, self._stop, self._ready,
                               node_name, tuple(cpu_affinity), sensor_data_topics),
            name='encoder_dds_output', daemon=True)
        self._process.start()
        if not self._ready.wait(10.):
            self.close()
            raise RuntimeError('Encoder DDS output did not initialize')

    @property
    def alive(self):
        return self._process.is_alive()

    @property
    def pid(self):
        return self._process.pid

    def publisher(self, topic):
        return _Publisher(next(slot for name, _, slot in self._slots
                               if name == topic))

    def close(self):
        self._stop.set()
        self._process.join(timeout=2.)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2.)
        for _, _, slot in self._slots:
            slot.cancel_join_thread()
            slot.close()
