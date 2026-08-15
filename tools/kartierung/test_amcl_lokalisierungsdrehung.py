from types import SimpleNamespace

import amcl_lokalisierungsdrehung as search


class ImmediateFuture:
    def done(self):
        return True

    def result(self):
        return object()


class FakeClient:
    def __init__(self, available=True):
        self.available = available
        self.calls = 0

    def wait_for_service(self, timeout_sec):
        assert timeout_sec == 5.0
        return self.available

    def call_async(self, request):
        self.calls += 1
        return ImmediateFuture()


def test_nomotion_updates_stop_after_localization_ready(monkeypatch):
    node = SimpleNamespace(ready=False, nomotion_client=FakeClient())

    def mark_ready(fake_node, timeout_sec):
        assert timeout_sec == 0.05
        fake_node.ready = True

    monkeypatch.setattr(search.rclpy, 'ok', lambda: True)
    monkeypatch.setattr(search.rclpy, 'spin_once', mark_ready)

    assert search.request_nomotion_updates(node, 20)
    assert node.nomotion_client.calls == 1


def test_nomotion_updates_fail_closed_without_amcl_service():
    node = SimpleNamespace(ready=False, nomotion_client=FakeClient(False))

    assert not search.request_nomotion_updates(node, 20)
    assert node.nomotion_client.calls == 0
