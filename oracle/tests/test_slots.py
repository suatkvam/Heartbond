"""SPEC H-3, H-5, T-1: slot attribution and per-slot verdict."""
import inspect

from oracle import slots
from oracle.slots import Rental, slot_index

START, INTERVAL, N = 1000, 30, 4
END = START + N * INTERVAL


def rental():
    return Rental(rental_id=7, provider="0xabc", start=START, end=END, interval=INTERVAL)


def test_all_probes_ok_is_up():
    r = rental()
    for ts in (START, START + 5, START + 10):
        r.record(ts, True)
    assert r.verdict(0) is True


def test_single_ok_probe_is_up():
    r = rental()
    r.record(START + 3, True)
    assert r.verdict(0) is True


def test_zero_probes_is_down():
    r = rental()
    assert r.verdict(0) is False
    r.record(START, True)  # a probe in slot 0 says nothing about slot 1
    assert r.verdict(1) is False


def test_one_failure_among_successes_is_down():
    r = rental()
    for ts, ok in ((START, True), (START + 5, False), (START + 10, True)):
        r.record(ts, ok)
    assert r.verdict(0) is False
    assert r.probes[0] == [2, 3]


def test_failure_in_one_slot_does_not_affect_another():
    r = rental()
    r.record(START, False)
    r.record(START + INTERVAL, True)
    assert r.verdict(0) is False
    assert r.verdict(1) is True


def test_force_down_overrides_successes():
    r = rental()
    r.record(START, True)
    r.record(START + INTERVAL, True)
    r.force_down([0])
    assert r.verdict(0) is False
    assert r.verdict(1) is True  # only the marked slot


def test_clear_force_down_restores_probe_verdict():
    r = rental()
    for k in range(3):
        r.record(START + k * INTERVAL, k != 2)  # slot 2 has a failed probe
    r.force_down([0, 1, 2])
    r.clear_force_down([0])
    assert r.verdict(0) is True
    assert r.verdict(1) is False  # still marked
    r.clear_force_down()
    assert r.verdict(1) is True
    assert r.verdict(2) is False  # clearing restores the probe verdict, not Up


def test_force_down_is_per_rental():
    a, b = rental(), rental()
    a.record(START, True)
    b.record(START, True)
    a.force_down([0])
    assert a.verdict(0) is False
    assert b.verdict(0) is True


def test_slot_boundaries():
    def idx(ts):
        return slot_index(START, END, INTERVAL, ts)

    assert idx(START - 1) is None  # before start: no slot
    assert idx(START) == 0  # exactly start + k*interval belongs to slot k
    assert idx(START + INTERVAL - 1) == 0
    assert idx(START + INTERVAL) == 1
    assert idx(START + 2 * INTERVAL - 1) == 1
    assert idx(END - 1) == N - 1
    assert idx(END) is None  # at end: no slot
    assert idx(END + 1) is None


def test_probe_outside_rental_is_not_counted():
    r = rental()
    assert r.record(START - 1, True) is None
    assert r.record(END, True) is None
    assert r.probes == {}
    assert not any(r.verdict(k) for k in range(N))


def test_probe_attributed_to_slot_containing_its_time():
    r = rental()
    assert r.record(START + INTERVAL - 1, False) == 0
    assert r.record(START + INTERVAL, True) == 1
    assert r.verdict(0) is False
    assert r.verdict(1) is True


def test_slots_module_reads_no_clock():
    src = inspect.getsource(slots)
    assert "import time" not in src and "datetime" not in src
