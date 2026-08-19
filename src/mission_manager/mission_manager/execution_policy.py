"""Side-effect-free mission execution policy."""

import math
from typing import Any, Iterable, Optional, Set, Tuple


GO_TO_ROOM_SIMULATION_STATUS = 'simulation_only_no_navigation'
GO_TO_ROOM_NAV2_STATUS = 'nav2_explicit_opt_in'


def go_to_room_execution_status(real_navigation_enabled: bool) -> str:
    """Expose whether the separately guarded Nav2 path is enabled."""
    return (
        GO_TO_ROOM_NAV2_STATUS
        if real_navigation_enabled
        else GO_TO_ROOM_SIMULATION_STATUS
    )


def effective_real_types(
        configured_types: Iterable[str], *, enable_real_explore: bool = False
        ) -> Set[str]:
    """Return action-backed types with navigation types fail-closed."""
    blocked = {'go_to_room'}
    if enable_real_explore is not True:
        blocked.add('explore')
    return {str(value) for value in configured_types if str(value) not in blocked}


def execution_mode(command_type: str, real_types: Iterable[str]) -> str:
    """Select ``real`` or ``sim`` without ever activating go_to_room."""
    if command_type == 'go_to_room':
        return 'sim'
    return 'real' if command_type in set(real_types) else 'sim'


def pick_and_place_room_allowed(
        requested_room: Any,
        configured_rooms: Iterable[str]) -> bool:
    """Keep user-declared rooms out of the existing real BT allowlist.

    The current pick-and-place tree ignores ``goal.room`` and drives to a
    separately configured placement pose. A newly drawn semantic room must
    therefore not unlock that real action until a later reviewed BT contract
    explicitly consumes the room binding.
    """
    return isinstance(requested_room, str) and requested_room in set(configured_rooms)


def localization_loss_state(
        ready: bool,
        *,
        now: float,
        loss_started: Optional[float],
        grace_s: float) -> Tuple[Optional[float], bool]:
    """Qualify a localization loss before canceling a running Nav2 action.

    The independent velocity gate still stops motion as soon as ``ready`` is
    false. This state machine only prevents a single short status glitch from
    turning that immediate stop into an irreversible mission cancellation.
    """
    if not math.isfinite(now):
        raise ValueError('now muss endlich sein')
    if not math.isfinite(grace_s) or grace_s <= 0.0:
        raise ValueError('grace_s muss endlich und > 0 sein')
    if ready is True:
        return None, False
    if loss_started is None or not math.isfinite(loss_started) or loss_started > now:
        return now, False
    return loss_started, now - loss_started >= grace_s
