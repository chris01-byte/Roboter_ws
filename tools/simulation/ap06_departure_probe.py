"""Simulation-only experiment: record and defer hypothetical next-leg proof.

The original predictor runs first. Its False may be deferred only with fresh
unchanged stop checks, the actual controller contract and a publicly observed
current padded body. Actual leg/stop geometry, private egress, observations,
sources and the next actual leg still use every original product check.
"""
import hashlib
import itertools
import json
from pathlib import Path
import threading
import time

from ap06_concept_experiment import require_isolation


def validate_experiment_options(args):
    require_isolation()
    if not getattr(args, 'ideal_lidar', False):
        raise ValueError('concept deferred departure requires explicit --ideal-lidar')
    if any(getattr(args, name, False) for name in (
            'profile_selection', 'capture_decisions', 'capture_geometry', 'diagnostic_beams')):
        raise ValueError('concept deferred departure cannot combine with other diagnostic wrappers')


def public_current_body(node, inputs):
    from explore.metric_frontier import footprint_clear
    public = node._metric_public_inputs(inputs)
    return all(footprint_clear(*public[2], grid, mask, node._world_to_grid,
        node._grid_to_world, node._metric_bounds, heading_half_angle=.05,
        center_deviation_m=.02) for grid, mask in ((public[0], public[3]), (public[5], public[6])))


def make_departure_probe(original, journal, public_body_check=public_current_body):
    """Pure wrapping seam for small tests; installing it requires isolation."""
    journal = Path(journal)
    journal.touch(exist_ok=False)
    sequence = itertools.count(1)
    lock = threading.Lock()
    def assessed(node, inputs, route, target, stop_requested):
        points = [[float(v) for v in xy] for xy in route]
        record = dict(schema=1, kind='hypothetical_departure_assessment',
            sequence=next(sequence), entered_monotonic=time.monotonic(),
            original_qualification=False, deferred=False, returned=None,
            pose=[float(v) for v in inputs[2]],
            target={key: float(getattr(target, key)) for key in ('x', 'y', 'yaw')},
            task_id=getattr(target, 'task_id', None),
            route_points=len(points), route_sha256=hashlib.sha256(
                json.dumps(points, separators=(',', ':')).encode()).hexdigest(),
            original_decision=None, stop_after_prediction=None, stop_after_checks=None,
            public_current_body=None, controller_contract=None,
            prior_departure_rejection=node._metric_status.get('departure_plan_rejection'),
            prior_last_route_rejection=getattr(node, '_metric_last_route_rejection', None))
        phase = 'original_prediction'
        try:
            original_decision = original(node, inputs, route, target, stop_requested)
            record.update(original_returned_monotonic=time.monotonic(),
                original_decision=original_decision,
                departure_rejection_at_original_return=node._metric_status.get('departure_plan_rejection'),
                last_route_rejection_at_original_return=getattr(node, '_metric_last_route_rejection', None),
                reason_scope='Exact function return; last route rejection may describe a hypothetical query')
            if original_decision is True:
                record['returned'] = True
                return True
            if original_decision is not False:
                raise TypeError('departure predictor must return bool; experiment cannot reinterpret it')
            phase = 'stop_after_prediction'
            record['stop_after_prediction'] = bool(stop_requested())
            if record['stop_after_prediction']:
                record['returned'] = False
                return False
            if getattr(node, '_metric_path_validation', None) != 'rpp_rollout':
                record.update(returned=False, experiment_rejection='unsupported_controller_model')
                return False
            phase = 'controller_contract'
            record['controller_contract'] = node._metric_controller_contract(stop_requested) is True
            if not record['controller_contract']:
                record.update(returned=False, experiment_rejection='actual_controller_contract_invalid')
                return False
            phase = 'public_current_body'
            record['public_current_body'] = public_body_check(node, inputs) is True
            if not record['public_current_body']:
                record.update(returned=False, experiment_rejection='current_padded_body_not_public')
                return False
            phase = 'stop_after_checks'
            record['stop_after_checks'] = bool(stop_requested())
            if record['stop_after_checks']:
                record['returned'] = False
                return False
            record.update(returned=True, deferred=True,
                experiment_decision='future_departure_proof_deferred_to_actual_next_leg')
            return True
        except BaseException as error:
            record.update(exception=dict(phase=phase, type=type(error).__name__, message=str(error)))
            raise
        finally:
            record['finished_monotonic'] = time.monotonic()
            # Close each line before returning the diagnostic decision. Logging
            # errors propagate; missing evidence never enables the experiment.
            with lock, journal.open('a') as stream:
                stream.write(json.dumps(record, sort_keys=True, allow_nan=False)+'\n')
    assessed._ap06_departure_probe = True
    return assessed


def install_departure_probe(journal):
    require_isolation()
    from explore.metric_frontier_runtime import MetricFrontierRuntime
    original = MetricFrontierRuntime._metric_departure_plan_ready
    if getattr(original, '_ap06_departure_probe', False):
        raise ValueError('departure experiment already installed')
    MetricFrontierRuntime._metric_departure_plan_ready = make_departure_probe(original, journal)
