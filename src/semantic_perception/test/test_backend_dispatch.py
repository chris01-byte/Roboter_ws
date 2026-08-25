from types import SimpleNamespace
import unittest

from semantic_perception.semantic_perception_node import SemanticPerception


class _Values:
    def __init__(self, values):
        self._values = values

    def __getitem__(self, index):
        return self._values[index]

    def tolist(self):
        return list(self._values)


class _Box:
    def __init__(self, class_index, confidence, xyxy):
        self.cls = _Values([class_index])
        self.conf = _Values([confidence])
        self.xyxy = [_Values(xyxy)]


class _Result:
    def __init__(self, names, boxes):
        self.names = names
        self.boxes = boxes


def _subject(backend, model_result=None, stub_result=None):
    calls = {'model': 0, 'stub': 0}

    def detect_with_model(_query):
        calls['model'] += 1
        return model_result

    def detect_stub(_query):
        calls['stub'] += 1
        return stub_result

    node = SimpleNamespace(
        _backend=backend,
        _detect_with_model=detect_with_model,
        _detect_stub=detect_stub,
    )
    return node, calls


class BackendDispatchTests(unittest.TestCase):
    def test_stub_backend_is_the_only_backend_allowed_to_simulate_a_pose(self):
        expected = ('simulated-pose', 0.8)
        node, calls = _subject('stub', stub_result=expected)

        self.assertEqual(SemanticPerception._detect(node, 'Tasse'), expected)
        self.assertEqual(calls, {'model': 0, 'stub': 1})

    def test_yoloworld_returns_a_real_model_result(self):
        expected = ('model-pose', 0.91)
        node, calls = _subject(
            'yoloworld', model_result=expected, stub_result=('fake', 0.8))

        self.assertEqual(SemanticPerception._detect(node, 'Tasse'), expected)
        self.assertEqual(calls, {'model': 1, 'stub': 0})

    def test_yoloworld_failure_never_falls_back_to_a_simulated_pose(self):
        node, calls = _subject(
            'yoloworld', model_result=None, stub_result=('fake', 0.8))

        self.assertIsNone(SemanticPerception._detect(node, 'Tasse'))
        self.assertEqual(calls, {'model': 1, 'stub': 0})

    def test_unknown_or_placeholder_backend_fails_closed(self):
        for backend in ('owlvit', 'unknown'):
            with self.subTest(backend=backend):
                node, calls = _subject(backend, stub_result=('fake', 0.8))

                self.assertIsNone(SemanticPerception._detect(node, 'Tasse'))
                self.assertEqual(calls, {'model': 0, 'stub': 0})

    def test_empty_query_never_calls_any_backend(self):
        node, calls = _subject('stub', stub_result=('fake', 0.8))

        self.assertIsNone(SemanticPerception._detect(node, ''))
        self.assertEqual(calls, {'model': 0, 'stub': 0})

    def test_query_is_resolved_to_a_configured_canonical_class(self):
        node = SimpleNamespace(
            _class_queries=['Tasse', 'Flasche'],
        )

        self.assertEqual(
            SemanticPerception._canonical_class(node, 'finde die TASSE bitte'),
            'Tasse',
        )
        self.assertEqual(
            SemanticPerception._canonical_class(node, 'flasch'),
            'Flasche',
        )
        self.assertIsNone(SemanticPerception._canonical_class(node, 'Schuh'))

    def test_best_box_filters_by_actual_class_before_confidence(self):
        results = [
            _Result(
                {0: 'Tasse', 1: 'Flasche'},
                [
                    _Box(1, 0.99, [0.0, 0.0, 20.0, 20.0]),
                    _Box(0, 0.65, [10.0, 20.0, 30.0, 40.0]),
                    _Box(0, 0.80, [20.0, 30.0, 60.0, 70.0]),
                ],
            ),
        ]

        self.assertEqual(
            SemanticPerception._best_box(results, 'Tasse'),
            (40.0, 50.0, 0.80),
        )
        self.assertIsNone(SemanticPerception._best_box(results, 'Werkzeug'))
