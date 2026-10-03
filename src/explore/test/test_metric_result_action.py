"""Real ExploreArea DDS contract; synthetic sensors, no Nav2/hardware mission.

The genuine parent loop/candidate engine consumes fresh joined raw callbacks.
This tests the AP-05 result wire, not the full AP-06 product chain.
"""
import copy
import threading
import time

import pytest
import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from robot_interfaces.action import ExploreArea

from test_metric_frontier import require_isolated_ros
from test_metric_progress import parent_fixture, scan
from test_metric_map_lifecycle import status


@pytest.mark.parametrize('cancel',[False,True])
def test_real_dds_result_is_succeeded_or_terminal_canceled(monkeypatch,cancel):
    require_isolated_ros()
    n,g,_,_,_=parent_fixture(monkeypatch,'wall')
    monkeypatch.undo()  # use real clock and real rclpy executor for this test
    rclpy.init()
    owner=Node('ap05_result_contract');group=ReentrantCallbackGroup()
    n.get_clock=owner.get_clock
    observed=[2];original=n._metric_inputs;entered=threading.Event()
    cost=copy.deepcopy(g);cost.data=[0]*10000
    def inputs(*args,**kwargs):
        now=owner.get_clock().now().nanoseconds
        live=copy.deepcopy(g);live.header.stamp.sec=now//10**9;live.header.stamp.nanosec=now%10**9
        n._on_map(live)
        observed[0]+=1
        n._on_metric_map_status(status(live,accepted=2,observed=observed[0],when=time.time()))
        current_cost=copy.deepcopy(cost);current_cost.header.stamp=live.header.stamp
        n._on_global_costmap(current_cost)
        return original(*args,**kwargs)
    n._metric_inputs=inputs
    def actual_scan():
        s=scan(owner.get_clock().now().nanoseconds);s['received_at']=time.monotonic();return s
    n._door_lidar_scan_snapshot=actual_scan
    def execute(handle):
        entered.set()
        return n._execute_metric_frontier(handle,handle.request.timeout_s,.3)
    server=ActionServer(owner,ExploreArea,'/ap05_result_contract',execute_callback=execute,
        cancel_callback=lambda _:CancelResponse.ACCEPT,callback_group=group)
    client=ActionClient(owner,ExploreArea,'/ap05_result_contract',callback_group=group)
    executor=MultiThreadedExecutor(num_threads=3);executor.add_node(owner)
    worker=threading.Thread(target=executor.spin,daemon=True);worker.start()
    def await_future(future,timeout=8.):
        until=time.monotonic()+timeout
        while not future.done() and time.monotonic()<until:time.sleep(.01)
        assert future.done()
        return future.result()
    try:
        assert client.wait_for_server(timeout_sec=3.)
        goal=ExploreArea.Goal();goal.timeout_s=8.
        handle=await_future(client.send_goal_async(goal))
        assert handle.accepted and entered.wait(2.)
        if cancel:
            response=await_future(handle.cancel_goal_async())
            assert response.goals_canceling
        wrapped=await_future(handle.get_result_async())
        assert wrapped.status==(GoalStatus.STATUS_CANCELED if cancel else GoalStatus.STATUS_SUCCEEDED)
        assert wrapped.result.success is (not cancel)
        assert n._metric_status['outcome']==('user_canceled' if cancel else 'metric_complete')
        assert n._wohnungserkundung_active_child is None and n._metric_active is None
        # Existing BT's success predicate remains compatible with this result.
        assert (wrapped.status==GoalStatus.STATUS_SUCCEEDED and wrapped.result.success)==(not cancel)
    finally:
        executor.shutdown(timeout_sec=3.);worker.join(timeout=3.)
        client.destroy();server.destroy();owner.destroy_node();rclpy.shutdown()
