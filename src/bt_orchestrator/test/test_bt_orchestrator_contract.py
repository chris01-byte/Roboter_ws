from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_topic_conditions_get_bounded_warmup_before_first_tick():
    source = (
        PACKAGE_ROOT / 'src' / 'bt_orchestrator_main.cpp'
    ).read_text(encoding='utf-8')
    params = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'bt_params.yaml').read_text(encoding='utf-8')
    )['bt_orchestrator']['ros__parameters']

    assert params['mission_subscription_warmup_s'] == 1.0
    assert 'mission_tick_ready_at_' in source
    assert source.index(
        'std::chrono::steady_clock::now() < mission_tick_ready_at_'
    ) < source.index('status = tree_->tickOnce()')
    assert 'subscription_warmup_s_ <= 0.0' in source


def test_explore_tree_keeps_continuous_estop_guard():
    tree = (
        PACKAGE_ROOT / 'bt_xml' / 'explore.xml'
    ).read_text(encoding='utf-8')

    assert '<ReactiveSequence' in tree
    assert '<IsEstopClear/>' in tree
    assert tree.index('<IsEstopClear/>') < tree.index('<Explore ')
