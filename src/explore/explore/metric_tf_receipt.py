"""Bounded reception through the existing TF listener, without new sources."""


def receive_pending_tf(listener):
    """Deliver queued original messages before choosing a wheel-bound pose.

    TF2 already permits concurrent listener callbacks. Use those same callbacks
    and their existing group, subscriptions, QoS and buffer. At most the normal
    listener's 100-message keep-last capacity is taken from each subscription;
    there is no wait, timestamp substitution or transform constructed here.
    """
    received = 0
    try:
        for sub, callback in ((listener.tf_sub, listener.callback),
                              (listener.tf_static_sub, listener.static_callback)):
            group = sub.callback_group
            if not group.beginning_execution(sub):
                continue
            try:
                for _ in range(min(sub.qos_profile.depth, 100)):
                    with sub.handle:
                        taken = sub.handle.take_message(sub.msg_type, sub.raw)
                    if taken is None or taken[0] is None:
                        break
                    callback(taken[0])
                    received += 1
            finally:
                group.ending_execution(sub)
    except Exception as exc:
        # A failed receive must not fall back to an apparently fresh old pose.
        raise ValueError('self_body_anchor_tf_receive_failed') from exc
    return received
