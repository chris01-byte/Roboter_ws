"""Actual lifecycle state can prove completion after a lost acknowledgement."""
import threading
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.node import Node
from rclpy.task import Future
from lifecycle_msgs.srv import ChangeState, GetState
from ap06_closed_product import transition_lifecycle


def test_lost_acknowledgement_queries_real_server_without_repeating_transition(monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID', '187')
    rclpy.init(args=[])
    class Server(LifecycleNode):
        configurations = 0
        def on_configure(self, state):
            self.configurations += 1
            return TransitionCallbackReturn.SUCCESS
    server = Server('ap06_lifecycle_regression')
    observer = Node('ap06_lifecycle_observer')
    client = observer.create_client(ChangeState, '/ap06_lifecycle_regression/change_state')
    states = observer.create_client(GetState, '/ap06_lifecycle_regression/get_state')
    class LostAcknowledgement:
        calls = 0
        real_future = None
        def call_async(self, request):
            self.calls += 1
            self.real_future = client.call_async(request)  # actual server transition
            return Future()  # transport countercase drops only the acknowledgement
        def remove_pending_request(self, _future):
            client.remove_pending_request(self.real_future)
    missing = LostAcknowledgement()
    executor = SingleThreadedExecutor(); executor.add_node(server); executor.add_node(observer)
    stopped = threading.Event()
    def spin():
        while not stopped.is_set():
            executor.spin_once(timeout_sec=.02)
    thread = threading.Thread(target=spin); thread.start()
    try:
        assert client.wait_for_service(timeout_sec=5.) and states.wait_for_service(timeout_sec=5.)
        proof = transition_lifecycle(missing, states, 1, 5.)
        assert proof == dict(transition=1, actual_state=2, acknowledgement_received=False)
        assert missing.calls == server.configurations == 1
        assert transition_lifecycle(client, states, 3, 5.)['actual_state'] == 3
        assert server.configurations == 1
    finally:
        stopped.set(); thread.join(2.); executor.shutdown(timeout_sec=1.)
        observer.destroy_node(); server.destroy_node(); rclpy.shutdown()
