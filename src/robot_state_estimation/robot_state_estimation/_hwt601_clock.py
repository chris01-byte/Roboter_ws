"""Private host-receipt clock correlation; no sensor acquisition-time claim."""
import math

from .hwt601_protocol import Hwt601ProtocolError

# At most 1% of the existing 100-ms bias continuity bound, 1/10 of a
# nominal 100-Hz sample interval. This is a measurement bound, not added age.
MAX_BRACKET_NS = 1_000_000
MAX_PAIR_ATTEMPTS = 3


class ClockPairUncertain(Hwt601ProtocolError):
    """Scheduling prevented a bounded correlation; this sample is unusable."""


class ReceiptClockCorrelation:
    """Intersect observed offset spans, never silently establish a new epoch.

    The ROS read happened somewhere in [before, after]. For clocks advancing
    at the same rate, offset lies in [ROS-after, ROS-before]. The intersection
    retains all precise evidence. Its lower bound timestamps receipt at most
    MAX_BRACKET_NS early, never late/future. Disjoint evidence is a hard error,
    even when message stamps would still increase. Wide brackets cannot
    establish/narrow correlation, but can prove a disjoint clock change.
    """

    def __init__(self):
        self.offset_span_ns = None
        self.last_after_s = None
        self.diagnostic = {}

    def project(self, received_s, before_s, ros_ns, after_s):
        if (not all(math.isfinite(v) for v in (before_s, after_s))
                or after_s < before_s
                or (self.last_after_s is not None
                    and before_s < self.last_after_s)):
            raise Hwt601ProtocolError('HWT-Monotonic-Zeit ruecklaeufig/ungueltig')
        self.last_after_s = after_s
        # Outward rounding bounds conversion error; receipt rounds down.
        lower = ros_ns - math.ceil(after_s * 1e9)
        upper = ros_ns - math.floor(before_s * 1e9)
        width = math.ceil((after_s - before_s) * 1e9)
        self.diagnostic = dict(bracket_before_monotonic_s=before_s,
            bracket_after_monotonic_s=after_s, ros_clock_ns=ros_ns,
            bracket_width_ns=width, max_bracket_ns=MAX_BRACKET_NS,
            observed_offset_span_ns=[lower, upper],
            accepted_offset_span_ns=self.offset_span_ns,
            classification='clock_pair_uncertain')
        if self.offset_span_ns is not None:
            lo, hi = self.offset_span_ns
            if upper < lo or lower > hi:
                self.diagnostic['classification'] = 'clock_basis_changed'
                raise Hwt601ProtocolError('HWT-Zeitbasis hat sich geaendert')
            lower, upper = max(lo, lower), min(hi, upper)
        if width > MAX_BRACKET_NS:
            raise ClockPairUncertain('HWT-Uhrpaarung zu unsicher')
        self.offset_span_ns = (lower, upper)
        self.diagnostic.update(classification='clock_pair_valid',
            accepted_offset_span_ns=self.offset_span_ns,
            stamp_uncertainty_ns=upper-lower)
        return math.floor(received_s * 1e9) + lower
