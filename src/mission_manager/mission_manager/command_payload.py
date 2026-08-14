"""Validation for the JSON payload received from the GUI/LLM topic."""

import json
from typing import Dict, Optional, Tuple


MAXIMUM_COMMAND_BYTES = 64 * 1024


def decode_command_payload(data: str) -> Tuple[Optional[Dict], Optional[str]]:
    if not isinstance(data, str):
        return None, 'JSON-Auftrag muss Text sein'
    try:
        encoded_size = len(data.encode('utf-8'))
    except UnicodeError:
        return None, 'JSON-Auftrag enthaelt ungueltiges Unicode'
    if encoded_size > MAXIMUM_COMMAND_BYTES:
        return None, f'JSON-Auftrag ist groesser als {MAXIMUM_COMMAND_BYTES} Bytes'
    try:
        decoded = json.loads(data)
    except (json.JSONDecodeError, TypeError, RecursionError) as exc:
        return None, f'Ungueltiges JSON: {exc}'
    if not isinstance(decoded, dict):
        return None, 'JSON-Auftrag muss ein Objekt sein'
    return decoded, None
