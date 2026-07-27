"""Pure helpers for interpreting ROS 2 action cancellation and results."""

from typing import Iterable, Optional


def cancel_was_accepted(
    return_code: int,
    goal_ids_canceling: Iterable[object],
    requested_goal_id: object,
    *,
    success_code: int,
) -> bool:
    """Accept only a successful response that lists the requested goal."""
    return (
        return_code == success_code
        and requested_goal_id in goal_ids_canceling
    )


def terminal_state(
    status: int,
    result_success: bool,
    *,
    succeeded_status: int,
    canceled_status: int,
    aborted_status: int,
) -> Optional[str]:
    """Map the authoritative action status/result to the public mission state."""
    if status == canceled_status:
        return 'canceled'
    if status == succeeded_status:
        return 'success' if result_success else 'failed'
    if status == aborted_status:
        return 'failed'
    return None
