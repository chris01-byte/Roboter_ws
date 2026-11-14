"""Bounded nonblocking delivery to an existing TF listener, original stamps."""


def receive_latest_sources(subscriptions):
    """Deliver newest queued originals through existing source callbacks.

    Each source uses its existing depth-ten queue and a callback group separate
    from the decision timer. No message means no callback or receipt refresh.
    TF delivery is separate because its queued edges must all be preserved.
    """
    for sub, callback in subscriptions:
        group = sub.callback_group
        if not group.beginning_execution(sub):
            continue
        try:
            latest = None
            for _ in range(10):
                with sub.handle:
                    info = sub.handle.take_message(sub.msg_type, sub.raw)
                if info is None:
                    break
                latest = info[0]
            if latest is not None:
                callback(latest)
        except Exception:
            return False
        finally:
            group.ending_execution(sub)
    return True


def receive_current_tf(listener):
    sub = getattr(listener, 'tf_sub', None)
    if sub is None:
        return False
    group = sub.callback_group
    if not group.beginning_execution(sub):
        return True  # existing callback owns delivery; age checks still apply
    try:
        for _ in range(32):
            with sub.handle:
                info = sub.handle.take_message(sub.msg_type, sub.raw)
            if info is None:
                break
            listener.callback(info[0])
        return True
    except Exception:
        return False
    finally:
        group.ending_execution(sub)
