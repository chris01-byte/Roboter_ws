"""Explorer SIGINT ordering on Humble must preserve the ROS context."""

from pathlib import Path
import signal
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import explore.explore_node as module  # noqa: E402


def test_signal_stops_executor_before_context(monkeypatch):
    events = []
    handlers = {}
    original = object()

    def set_handler(signum, handler):
        handlers[signum] = handler
        events.append(('handler', signum, handler))

    monkeypatch.setattr(module.signal, 'getsignal', lambda _signum: original)
    monkeypatch.setattr(module.signal, 'signal', set_handler)
    monkeypatch.setattr(module.rclpy, 'init',
                        lambda **kwargs: events.append(('init', kwargs)))
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    monkeypatch.setattr(module.rclpy, 'shutdown',
                        lambda: events.append(('context_shutdown',)))

    class FakeNode:
        def __init__(self):
            events.append(('node_init',))

        def destroy_node(self):
            events.append(('node_destroy',))

    class FakeExecutor:
        def __init__(self):
            events.append(('executor_init',))

        def add_node(self, _node):
            events.append(('add_node',))

        def spin_once(self, timeout_sec):
            assert timeout_sec <= 0.1
            events.append(('spin_once',))
            handlers[signal.SIGINT](signal.SIGINT, None)

        def shutdown(self, timeout_sec):
            assert timeout_sec == 5.0
            events.append(('executor_shutdown',))

        def remove_node(self, _node):
            events.append(('remove_node',))

    monkeypatch.setattr(module, 'ExploreNode', FakeNode)
    monkeypatch.setattr(module, 'MultiThreadedExecutor', FakeExecutor)
    module.main()

    names = [event[0] for event in events]
    assert names.index('executor_shutdown') < names.index('node_destroy')
    assert names.index('node_destroy') < names.index('context_shutdown')
    assert events[2][1]['signal_handler_options'] == module.SignalHandlerOptions.NO
    assert handlers[signal.SIGINT] is original
    assert handlers[signal.SIGTERM] is original


def test_unexpected_executor_error_is_not_swallowed(monkeypatch):
    events = []
    monkeypatch.setattr(module.signal, 'getsignal', lambda _signum: None)
    monkeypatch.setattr(module.signal, 'signal', lambda *_args: None)
    monkeypatch.setattr(module.rclpy, 'init', lambda **_kwargs: None)
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    monkeypatch.setattr(module.rclpy, 'shutdown',
                        lambda: events.append('context_shutdown'))

    class FakeNode:
        def destroy_node(self):
            events.append('node_destroy')

    class FakeExecutor:
        def add_node(self, _node):
            pass

        def spin_once(self, timeout_sec):
            raise RuntimeError('unexpected wait-set error')

        def shutdown(self, timeout_sec):
            events.append('executor_shutdown')

        def remove_node(self, _node):
            pass

    monkeypatch.setattr(module, 'ExploreNode', FakeNode)
    monkeypatch.setattr(module, 'MultiThreadedExecutor', FakeExecutor)
    with pytest.raises(RuntimeError, match='unexpected wait-set error'):
        module.main()
    assert events == ['executor_shutdown', 'node_destroy', 'context_shutdown']
