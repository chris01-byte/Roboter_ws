"""Keep Humble action replies behind their request registration.

rclpy 3.3.17 publishes a request before adding its sequence/future maps.
A fast server can answer during that gap and execute discards the reply as
unexpected. Serialize registration with response taking, not with async
feedback execution. No request is retried and no deadline is extended.
"""
import threading
from rclpy.action import ActionClient


class SerializedActionClient(ActionClient):
    def __init__(self, *args, **kwargs):
        self._request_lock = threading.RLock()
        super().__init__(*args, **kwargs)

    def send_goal_async(self, *args, **kwargs):
        with self._request_lock:
            return super().send_goal_async(*args, **kwargs)

    def _get_result_async(self, *args, **kwargs):
        with self._request_lock:
            return super()._get_result_async(*args, **kwargs)

    def _cancel_goal_async(self, *args, **kwargs):
        with self._request_lock:
            return super()._cancel_goal_async(*args, **kwargs)

    def take_data(self):
        with self._request_lock:
            return super().take_data()
