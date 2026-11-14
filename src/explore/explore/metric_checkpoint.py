"""Versioned passive metric checkpoint using the existing map-bound repository."""
from dataclasses import asdict
import math
import re

from .metric_frontier import MetricAttempt, MetricTaskPolicy


def validate_checkpoint(state):
    if (type(state.get('schema_version')) is not int or state.get('schema_version') not in (1,2) or state.get('strategy') != 'metric_frontier'
            or state.get('resume_authorizes_motion') is not False or state.get('outcome') not in
            ('in_progress','metric_complete','usable_partial','blocked_help_required','error','user_canceled')):
        raise ValueError('metric_checkpoint_schema_unsupported')
    context = state['context']
    for name in ('session_id', 'map_id', 'frame_id'):
        if not isinstance(context[name], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', context[name]):
            raise ValueError('metric_checkpoint_context_invalid')
    if state['saved_map_id'] != 'map-'+state['fingerprint']:
        raise ValueError('metric_checkpoint_map_id_mismatch')
    if not re.fullmatch('[0-9a-f]{64}', state['fingerprint']):
        raise ValueError('metric_checkpoint_fingerprint_invalid')
    for name in ('remaining_s', 'saved_wall_time', 'observed_area_m2'):
        value = state[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('metric_checkpoint_budget_invalid')
    for name in ('attempts', 'failures', 'arrivals', 'observations'):
        if type(state[name]) is not int or not 0 <= state[name] <= 100000:
            raise ValueError('metric_checkpoint_counter_invalid')
    limits = state['budget_limits']
    for name in ('max_frontier_goals', 'max_failed_goals'):
        if type(limits[name]) is not int or limits[name] < 1:
            raise ValueError('metric_checkpoint_budget_limits_invalid')
    if type(limits['goal_timeout_s']) not in (int, float) or not math.isfinite(limits['goal_timeout_s']) or limits['goal_timeout_s'] <= 0:
        raise ValueError('metric_checkpoint_budget_limits_invalid')
    if type(limits['completion_window_s']) not in (int,float) or not math.isfinite(limits['completion_window_s']) or limits['completion_window_s'] < 3.:
        raise ValueError('metric_checkpoint_completion_window_invalid')
    scope = state['scope']
    if not isinstance(scope['scope_id'], str) or not 3 <= len(scope['vertices']) <= 64:
        raise ValueError('metric_checkpoint_scope_invalid')
    for xy in scope['vertices']:
        if len(xy) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in xy):
            raise ValueError('metric_checkpoint_scope_invalid')
    policy = state['policy']
    if type(policy['retry_limit']) is not int or policy['retry_limit'] < 1:
        raise ValueError('metric_checkpoint_policy_invalid')
    for name in ('radius', 'cooldown_s'):
        if type(policy[name]) not in (int, float) or not math.isfinite(policy[name]) or policy[name] <= 0:
            raise ValueError('metric_checkpoint_policy_invalid')
    if not isinstance(policy['tasks'], dict) or len(policy['tasks']) > 512:
        raise ValueError('metric_checkpoint_task_capacity')
    if type(policy['next_id']) is not int or policy['next_id'] < len(policy['tasks']):
        raise ValueError('metric_checkpoint_task_ids_invalid')
    for key, task in policy['tasks'].items():
        required = {'frontier_xy','target_xy','failures','retry_remaining_s','fingerprint',
                    'completed','reason','tries','evidence_key'}
        if state['schema_version'] == 2:
            required.add('partial_observation')
        if set(task) != required:
            raise ValueError('metric_checkpoint_task_schema_invalid')
        if (state['schema_version'] == 2 and
                (type(task['partial_observation']) is not bool or
                 (task['partial_observation'] and (task['completed'] or not task['tries'])) or
                 (task['reason'] == 'partially_observed' and not task['partial_observation']))):
            raise ValueError('metric_checkpoint_partial_state_invalid')
        if not re.fullmatch(r'metric-task-[1-9][0-9]*', key) or int(key.split('-')[-1]) > policy['next_id']:
            raise ValueError('metric_checkpoint_task_ids_invalid')
        for name in ('frontier_xy', 'target_xy'):
            if len(task[name]) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in task[name]):
                raise ValueError('metric_checkpoint_task_geometry_invalid')
        if (type(task['tries']) is not int or type(task['failures']) is not int or
                not 0 <= task['failures'] <= task['tries'] <= policy['retry_limit']+1 or
                type(task['completed']) is not bool or type(task['retry_remaining_s']) not in (int, float) or
                not math.isfinite(task['retry_remaining_s']) or not 0 <= task['retry_remaining_s'] <= policy['cooldown_s'] or
                not isinstance(task['reason'], str) or len(task['reason']) > 256 or
                (task['tries'] and not re.fullmatch('[0-9a-f]{64}', task['evidence_key']))):
            raise ValueError('metric_checkpoint_task_state_invalid')
    if (state['failures'] > state['attempts'] or state['observations'] > state['arrivals'] or
            sum(t['tries'] for t in policy['tasks'].values()) > state['attempts'] or
            sum(t['failures'] for t in policy['tasks'].values()) > state['failures']):
        raise ValueError('metric_checkpoint_counter_inconsistent')
    return state


def policy_state(policy, now):
    tasks = {}
    for key, attempt in policy.attempts.items():
        task = asdict(attempt)
        task['retry_remaining_s'] = max(0., min(policy.cooldown_s, task.pop('retry_after')-now))
        tasks[key] = task
    return dict(radius=policy.radius, cooldown_s=policy.cooldown_s,
                retry_limit=policy.retry_limit, next_id=policy.next_id, tasks=tasks)


def restore_policy(state, now, wall_time):
    validate_checkpoint(state)
    elapsed = wall_time-state['saved_wall_time']
    if elapsed < 0:
        raise ValueError('metric_checkpoint_clock_regressed')
    data = state['policy']
    policy = MetricTaskPolicy(data['radius'], data['cooldown_s'], data['retry_limit'])
    policy.next_id = data['next_id']
    for key, stored in data['tasks'].items():
        task = dict(stored)
        task['retry_after'] = now+max(0., task.pop('retry_remaining_s')-elapsed)
        task['frontier_xy'], task['target_xy'] = tuple(task['frontier_xy']), tuple(task['target_xy'])
        policy.attempts[key] = MetricAttempt(**task)
    return policy, max(0., state['remaining_s']-elapsed)
