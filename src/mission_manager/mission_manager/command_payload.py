"""Validation for the JSON payload received from the GUI/LLM topic."""

import json
from typing import Dict, Optional, Tuple


def decode_command_payload(data: str) -> Tuple[Optional[Dict], Optional[str]]:
    try:
        decoded = json.loads(data)
    except json.JSONDecodeError as exc:
        return None, f'Ungueltiges JSON: {exc}'
    if not isinstance(decoded, dict):
        return None, 'JSON-Auftrag muss ein Objekt sein'
    return decoded, None
