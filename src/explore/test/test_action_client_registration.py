"""Actual Humble DDS responses must survive request-registration concurrency.

The proxy pauses AFTER the real C request has been sent, before rclpy stores
its sequence/future. A newer SDK with its own matching mutex must retain the
response too; only an actually unprotected SDK supplies the red countercase.
No response, Future or server is mocked. Each case owns
an isolated ROS context in a subprocess; rejected goals cannot cause motion.
"""
import os
import ast
import inspect
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest
import rclpy
from action_msgs.msg import GoalStatus
from nav2_msgs.action import ComputePathToPose
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from explore.action_client import SerializedActionClient


def sdk_serializes_registration():
    """Detect the actual installed SDK's matching request/take mutex."""
    def locks(method):
        import textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
        return any(isinstance(n, ast.With) and any(
            isinstance(i.context_expr, ast.Attribute)
            and isinstance(i.context_expr.value, ast.Name)
            and i.context_expr.value.id == 'self' and i.context_expr.attr == '_lock'
            for i in n.items) for n in ast.walk(tree))
    return locks(ActionClient.send_goal_async) and locks(ActionClient.take_data)


@pytest.mark.parametrize('mode,stage,force_waitset', [
    ('original', 'goal', False), ('serialized', 'goal', False),
    ('serialized', 'result', False), ('serialized', 'cancel', False),
    ('serialized', 'cancel', True),
])
def test_real_dds_response_registration(mode, stage, force_waitset):
    assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    assert 200 <= int(os.environ.get('ROS_DOMAIN_ID', '-1')) <= 230
    assert not os.environ.get('CYCLONEDDS_URI')
    run = subprocess.run([sys.executable, str(Path(__file__).resolve()), mode, stage,
                          'waitset' if force_waitset else 'normal'],
                         text=True, capture_output=True, timeout=20.)
    assert run.returncode == 0, run.stdout + run.stderr
    assert f'PASS {mode} {stage}' in run.stdout
    if force_waitset and sdk_serializes_registration():
        assert 'SDK_WAITSET_BLOCKED' in run.stdout
    if mode == 'original' and not sdk_serializes_registration():
        assert 'Ignoring unexpected goal response' in run.stderr
    else:
        assert 'Ignoring unexpected' not in run.stderr


def probe(mode, stage, scheduling='normal'):
    native_protected = sdk_serializes_registration()
    protected = mode == 'serialized' or native_protected
    force_waitset = scheduling == 'waitset'
    sent = threading.Event()
    registration_release = threading.Event()
    receive_barrier_entered = threading.Event()
    take_in_progress = threading.Event()
    processed = threading.Event()
    execute_release = threading.Event()
    request_armed = threading.Event()
    server_entered = threading.Event()
    waitset_prepared = threading.Event()
    waitset_release = threading.Event()
    goals = []
    failures = []
    handles = []

    class Client(SerializedActionClient if mode == 'serialized' else ActionClient):
        def get_num_entities(self):
            if force_waitset and request_armed.is_set() and not waitset_prepared.is_set():
                waitset_prepared.set()
                assert waitset_release.wait(5.), 'wait-set barrier not released'
            self._observe_sdk_waitset_lock()
            return super().get_num_entities()

        def add_to_wait_set(self, wait_set):
            self._observe_sdk_waitset_lock()
            return super().add_to_wait_set(wait_set)

        def _observe_sdk_waitset_lock(self):
            # This installed SDK also serializes wait-set construction on
            # the request mutex. A response need not reach take_data while
            # registration is paused. Prove the actual mutex is unavailable
            # on that executor thread, rather than inventing a take/response.
            if native_protected and request_armed.is_set() and sent.is_set():
                if self._lock.acquire(blocking=False):
                    self._lock.release()
                else:
                    print('SDK_WAITSET_BLOCKED', flush=True)
                    receive_barrier_entered.set()

        def take_data(self):
            take_in_progress.set()
            if request_armed.is_set():
                receive_barrier_entered.set()
            try:
                return super().take_data()
            finally:
                take_in_progress.clear()

        async def execute(self, data):
            await super().execute(data)
            if request_armed.is_set() and stage in data:
                processed.set()

    class PausedRequest:
        def __init__(self, actual):
            self.actual = actual

        def __getattr__(self, name):
            return getattr(self.actual, name)

        def __enter__(self):
            return self.actual.__enter__()

        def __exit__(self, *args):
            return self.actual.__exit__(*args)

        def request(self, name, value, kind):
            sequence = getattr(self.actual, name)(value)
            if request_armed.is_set() and kind == stage:
                sent.set()
                assert registration_release.wait(5.), 'registration barrier not released'
            return sequence

        def send_goal_request(self, value):
            return self.request('send_goal_request', value, 'goal')

        def send_result_request(self, value):
            return self.request('send_result_request', value, 'result')

        def send_cancel_request(self, value):
            return self.request('send_cancel_request', value, 'cancel')

    def goal_callback(goal):
        goals.append(goal)
        server_entered.set()
        return GoalResponse.REJECT if stage == 'goal' else GoalResponse.ACCEPT

    def cancel_callback(handle):
        server_entered.set()
        return CancelResponse.ACCEPT

    def execute_callback(handle):
        handles.append(handle)
        assert execute_release.wait(8.)
        if stage == 'cancel':
            deadline = time.monotonic() + 3.
            while not handle.is_cancel_requested and time.monotonic() < deadline:
                time.sleep(.005)
            assert handle.is_cancel_requested
            handle.canceled()
        else:
            handle.succeed()
        return ComputePathToPose.Result()

    def wait(future):
        deadline = time.monotonic() + 3.
        while not future.done() and time.monotonic() < deadline:
            time.sleep(.005)
        assert future.done(), 'actual DDS Future did not complete'
        return future.result()

    rclpy.init()
    server_node = Node('ap06_registration_server')
    client_node = Node('ap06_registration_client')
    server = ActionServer(server_node, ComputePathToPose, '/ap06_registration',
                          execute_callback=execute_callback, goal_callback=goal_callback,
                          cancel_callback=cancel_callback,
                          callback_group=ReentrantCallbackGroup())
    client = Client(client_node, ComputePathToPose, '/ap06_registration',
                    callback_group=ReentrantCallbackGroup())
    # A paused client take can legitimately hold the executor's wait-set
    # thread on the current SDK mutex. Its real server must keep executing
    # independently; otherwise the harness deadlocks its own response.
    server_executor = MultiThreadedExecutor(num_threads=2)
    server_executor.add_node(server_node)
    server_worker = threading.Thread(target=server_executor.spin, daemon=True)
    server_worker.start()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(client_node)
    worker = threading.Thread(target=executor.spin, daemon=True)
    worker.start()
    sender = None
    try:
        assert client.wait_for_server(timeout_sec=3.)
        initial = None
        if stage != 'goal':
            initial = wait(client.send_goal_async(ComputePathToPose.Goal()))
            assert initial.accepted
            assert server_entered.wait(3.)
            server_entered.clear()
            if stage == 'result':
                execute_release.set()
        actual_handle = client._client_handle
        client._client_handle = PausedRequest(actual_handle)
        request_armed.set()
        if force_waitset:
            executor.wake()
            assert waitset_prepared.wait(3.), 'executor did not build actual wait set'
        futures = []

        def send():
            try:
                if stage == 'goal':
                    futures.append(client.send_goal_async(ComputePathToPose.Goal()))
                elif stage == 'result':
                    futures.append(initial.get_result_async())
                else:
                    futures.append(initial.cancel_goal_async())
            except BaseException as error:
                failures.append(error)

        sender = threading.Thread(target=send, daemon=True)
        sender.start()
        assert sent.wait(3.), 'actual middleware request was not sent'
        waitset_release.set()
        if stage != 'result':
            assert server_entered.wait(3.)
        # The SDK may already be taking a status when the barrier is armed,
        # then block on its request mutex. That is an actual take in progress,
        # not a missing callback; retain the original concurrency assertion.
        if protected and take_in_progress.is_set():
            receive_barrier_entered.set()
        assert receive_barrier_entered.wait(3.), 'executor reached neither actual take nor locked wait-set construction'
        if not protected:
            assert processed.wait(3.), 'original must actually discard the early response'
        else:
            assert not processed.wait(.05), 'response escaped before request registration'
        registration_release.set()
        sender.join(3.)
        assert not sender.is_alive() and not failures
        assert len(futures) == 1
        if not protected:
            time.sleep(.15)
            assert not futures[0].done(), 'red counter must expose the lost acknowledgement'
        else:
            response = wait(futures[0])
            assert processed.wait(3.)
            if stage == 'goal':
                assert not response.accepted
            elif stage == 'result':
                assert response.status == GoalStatus.STATUS_SUCCEEDED
            else:
                assert len(response.goals_canceling) == 1
                assert response.goals_canceling[0].goal_id == initial.goal_id
                execute_release.set()
                terminal = wait(initial.get_result_async())
                assert terminal.status == GoalStatus.STATUS_CANCELED
        assert len(goals) == 1, 'fix must not resend or create a second goal'
        print(f'PASS {mode} {stage}', flush=True)
    finally:
        request_armed.clear()
        waitset_release.set()
        registration_release.set()
        execute_release.set()
        if sender is not None:
            sender.join(3.)
        executor.shutdown(timeout_sec=3.)
        worker.join(3.)
        server_executor.shutdown(timeout_sec=3.)
        server_worker.join(3.)
        client.destroy()
        server.destroy()
        client_node.destroy_node()
        server_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    probe(*sys.argv[1:])
