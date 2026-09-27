"""The existing Explore action remains owned by Mission Manager on HWT hold."""

import json
from types import SimpleNamespace

from std_msgs.msg import String

from mission_manager.mission_manager_node import MissionManager


def test_hwt_hold_and_resume_keep_explore_command_and_action_epoch():
    published = []
    command = {'type': 'explore', 'request_id': 'same-mission'}
    manager = SimpleNamespace(
        state='running', mode='real', active_command=command,
        _cancel_requested=False, _hwt_seen_sequence=0,
        _hwt_session_floor=0, _hwt_hold_active=False,
        _active_action_epoch=7, phase='Explore', progress=0.2,
        _publish_status=lambda: published.append(True),
    )
    for phase, expected in (
            ('we_hwt_hold', 'HWT_HOLD'),
            ('we_hwt_recovery_validation', 'HWT_RECOVERING')):
        MissionManager._on_explore_status(
            manager, String(data=json.dumps({
                'phase': phase, 'hwt_recovery_sequence': 1})))
        assert manager.phase == expected
        assert manager.active_command is command
        assert manager._active_action_epoch == 7
        assert manager.state == 'running'
    MissionManager._on_mission_feedback(
        manager, SimpleNamespace(feedback=SimpleNamespace(
            phase='Explore', progress=0.3)), 7)
    assert manager.phase == 'HWT_RECOVERING'
    MissionManager._on_explore_status(
        manager, String(data=json.dumps({
            'phase': 'we_hwt_resumed', 'hwt_recovery_sequence': 1})))
    assert manager.phase == 'Explore'
    assert manager.active_command is command
    assert manager._active_action_epoch == 7
    assert len(published) >= 3


def test_old_explorer_status_cannot_hold_a_new_mission():
    manager = SimpleNamespace(
        state='running', mode='real',
        active_command={'type': 'explore'}, _cancel_requested=False,
        _hwt_seen_sequence=2, _hwt_session_floor=2,
        _hwt_hold_active=False, phase='Explore',
        _publish_status=lambda: None,
    )
    MissionManager._on_explore_status(
        manager, String(data=json.dumps({
            'phase': 'we_hwt_hold', 'hwt_recovery_sequence': 2})))
    assert manager.phase == 'Explore'
    assert manager._hwt_hold_active is False
