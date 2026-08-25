from types import SimpleNamespace

from semantic_perception.semantic_perception_node import SemanticPerception


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


def test_stub_backend_is_the_only_backend_allowed_to_simulate_a_pose():
    expected = ('simulated-pose', 0.8)
    node, calls = _subject('stub', stub_result=expected)

    assert SemanticPerception._detect(node, 'Tasse') == expected
    assert calls == {'model': 0, 'stub': 1}


def test_yoloworld_returns_a_real_model_result():
    expected = ('model-pose', 0.91)
    node, calls = _subject(
        'yoloworld', model_result=expected, stub_result=('fake', 0.8))

    assert SemanticPerception._detect(node, 'Tasse') == expected
    assert calls == {'model': 1, 'stub': 0}


def test_yoloworld_failure_never_falls_back_to_a_simulated_pose():
    node, calls = _subject(
        'yoloworld', model_result=None, stub_result=('fake', 0.8))

    assert SemanticPerception._detect(node, 'Tasse') is None
    assert calls == {'model': 1, 'stub': 0}


def test_unknown_or_placeholder_backend_fails_closed():
    for backend in ('owlvit', 'unknown'):
        node, calls = _subject(backend, stub_result=('fake', 0.8))

        assert SemanticPerception._detect(node, 'Tasse') is None
        assert calls == {'model': 0, 'stub': 0}


def test_empty_query_never_calls_any_backend():
    node, calls = _subject('stub', stub_result=('fake', 0.8))

    assert SemanticPerception._detect(node, '') is None
    assert calls == {'model': 0, 'stub': 0}
