"""Versioned result telemetry enriches, but cannot finish/unlock, a BT mission."""
import json
from types import SimpleNamespace
import time

import pytest
from std_msgs.msg import String
from mission_manager.mission_manager_node import MissionManager


@pytest.mark.parametrize('outcome',['metric_complete','usable_partial','blocked_help_required','error','user_canceled'])
def test_actual_consumer_preserves_metric_result_without_inventing_terminal_action(outcome):
    now=time.time();published=[]
    n=SimpleNamespace(state='running',mode='real',active_command={'type':'explore'},
        _cancel_requested=False,_explore_started_wall=now-1.,_active_action_epoch=7,
        _publish_status=lambda:published.append(True))
    metric=dict(schema_version=1,outcome=outcome,started_wall_time=now-.5)
    MissionManager._on_explore_status(n,String(data=json.dumps(dict(time=now,metric_exploration=metric))))
    assert n._metric_exploration_result==metric and n.state=='running'
    assert n._active_action_epoch==7 and published==[True]
    for bad in (dict(time=now-10.,metric_exploration=metric),
                dict(time=now,metric_exploration=dict(metric,started_wall_time=now-2.)),
                dict(time=now,metric_exploration=dict(metric,schema_version=99))):
        MissionManager._on_explore_status(n,String(data=json.dumps(bad)))
    assert published==[True] and n._metric_exploration_result==metric
    n._cancel_requested=True
    MissionManager._on_explore_status(n,String(data=json.dumps(dict(time=now,metric_exploration=dict(metric,outcome='metric_complete')))))
    assert n._metric_exploration_result==metric and published==[True]
