import json
from pathlib import Path
import sys
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_PACKAGE = SOURCE_ROOT / "semantic_map_manager"
if str(SEMANTIC_PACKAGE) not in sys.path:
    sys.path.insert(0, str(SEMANTIC_PACKAGE))

from mission_manager.semantic_room_goal import (  # noqa: E402
    decode_semantic_map_status,
    resolve_room_goal,
)
from semantic_map_manager.semantic_core import (  # noqa: E402
    MapReference,
    Room,
    SemanticDocument,
    public_document,
)


class SemanticConsumerCrossContractTests(unittest.TestCase):
    def test_backend_document_is_resolved_by_mission_consumer(self):
        fingerprint = "a" * 64
        map_ref = MapReference.from_dict({
            "name": "wohnung",
            "version": "20260814T120000000000Z-abcdef123456",
            "fingerprint": fingerprint,
            "frame_id": "map",
            "width": 100,
            "height": 80,
            "resolution": 0.1,
            "origin": {
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "yaw": 0.0,
            },
        })
        room = Room.from_dict({
            "id": "room-wohnzimmer",
            "name": "Wohnzimmer",
            "color": "#4FB3A5",
            "polygon": [
                {"x": 1.0, "y": 1.0},
                {"x": 4.0, "y": 1.0},
                {"x": 4.0, "y": 3.0},
                {"x": 1.0, "y": 3.0},
            ],
            "navigation_goal": {"x": 2.0, "y": 2.0, "yaw": 0.5},
        }, map_ref=map_ref)
        document = SemanticDocument(
            map_ref=map_ref,
            revision=4,
            rooms=(room,),
            updated_at="2026-08-14T12:00:00Z",
        )
        envelope = {
            "schema_version": 1,
            "event": "status",
            "ok": True,
            "request_id": None,
            "message": "bereit",
            "semantic_map": {
                **public_document(document),
                "editable": True,
            },
        }

        snapshot, error = decode_semantic_map_status(json.dumps(envelope))
        self.assertIsNone(error)
        goal, error = resolve_room_goal(snapshot, room_id="room-wohnzimmer")
        self.assertIsNone(error)
        self.assertEqual(goal.map_fingerprint, fingerprint)
        self.assertEqual(goal.map_revision, 4)
        self.assertEqual((goal.x, goal.y, goal.yaw), (2.0, 2.0, 0.5))


if __name__ == "__main__":
    unittest.main()
