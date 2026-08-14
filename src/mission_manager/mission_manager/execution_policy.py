"""Side-effect-free mission execution policy."""

from typing import Any, Iterable, Set


GO_TO_ROOM_EXECUTION_STATUS = 'simulation_only_no_navigation'


def effective_real_types(configured_types: Iterable[str]) -> Set[str]:
    """Return action-backed types while keeping go_to_room fail-closed."""
    return {str(value) for value in configured_types if str(value) != 'go_to_room'}


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
