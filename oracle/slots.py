"""Per-slot uptime verdict (SPEC H-3, H-5, T-1). Pure logic: no I/O and no clock.

Every timestamp is an argument. The service passes chain time, so probes and slot
completion share one time base. A probe is attributed by the time its caller passes
(the service passes the time the probe started).
"""
from __future__ import annotations

from dataclasses import dataclass, field


def slot_index(start: int, end: int, interval: int, ts: int) -> int | None:
    """Slot k = [start + k*interval, start + (k+1)*interval); None outside [start, end)."""
    if ts < start or ts >= end:
        return None
    return (ts - start) // interval


@dataclass
class Rental:
    rental_id: int
    provider: str
    start: int
    end: int
    interval: int
    probes: dict[int, list[int]] = field(default_factory=dict)  # slot -> [ok, total]
    forced_down: set[int] = field(default_factory=set)

    @property
    def n_slots(self) -> int:
        return (self.end - self.start) // self.interval

    def record(self, ts: int, ok: bool) -> int | None:
        """Count one probe taken at `ts`; returns its slot, or None if it is in no slot."""
        slot = slot_index(self.start, self.end, self.interval, ts)
        if slot is not None:
            counts = self.probes.setdefault(slot, [0, 0])
            counts[0] += bool(ok)
            counts[1] += 1
        return slot

    def force_down(self, slots) -> None:
        self.forced_down.update(slots)

    def clear_force_down(self, slots=None) -> None:
        """Clear the given slots, or every mark on this rental when `slots` is None."""
        if slots is None:
            self.forced_down.clear()
        else:
            self.forced_down.difference_update(slots)

    def verdict(self, slot: int) -> bool:
        """Up iff not forced down, at least one probe ran, and every probe was ok (H-3)."""
        ok, total = self.probes.get(slot, (0, 0))
        return slot not in self.forced_down and total > 0 and ok == total
