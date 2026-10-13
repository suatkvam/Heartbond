"""O-rules, R-1, R-3, timing T-1/T-2 (SPEC §3). Red until create_rental and report_uptime exist.

Every revert test builds a call that violates only the rule under test:
the rental is Active, the caller is a reporter, the slot exists, is completed
and Empty, and the clock is inside the reporting window unless stated.
"""
import boa
import pytest

from conftest import INTERVAL, N_SLOTS, REPORT_GRACE, last_event, warp_to


def counts(escrow, rid):
    r = escrow.rentals(rid)
    return r.up_count, r.reported_count


# -------------------------------------------------------------------- O-1
def test_O_1_stranger_reverts(escrow, make_rental, report, stranger):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    with boa.reverts("not reporter"):
        report(rid, 0, True, by=stranger)
    assert escrow.get_slots(rid) == [0, 0, 0, 0]
    assert counts(escrow, rid) == (0, 0)


def test_O_1_renter_and_provider_are_not_reporters(escrow, make_rental, report, renter, provider):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    for party in (renter, provider):
        with boa.reverts("not reporter"):
            report(rid, 0, True, by=party)
    assert escrow.get_slots(rid) == [0, 0, 0, 0]


@pytest.mark.parametrize("key", [0, 1])
def test_O_1_either_allow_listed_reporter_accepted(escrow, make_rental, report, reporters, key):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, True, by=reporters[key])
    assert last_event(escrow, "UptimeReported").reporter == reporters[key]  # before any view call
    assert escrow.get_slots(rid) == [1, 0, 0, 0]


def test_O_1_two_reporters_can_share_one_rental(escrow, make_rental, report, reporters):
    rid, start, _ = make_rental()
    warp_to(start + 2 * INTERVAL)
    report(rid, 0, True, by=reporters[0])
    report(rid, 1, False, by=reporters[1])
    assert escrow.get_slots(rid) == [1, 2, 0, 0]
    assert counts(escrow, rid) == (1, 2)


# -------------------------------------------------------------------- O-2
@pytest.mark.parametrize("rid", [0, 1, 99])
def test_O_2_nonexistent_rental_reverts(escrow, report, rid):
    with boa.reverts("not active"):
        report(rid, 0, True)


def test_O_2_next_unused_id_reverts(escrow, make_rental, report):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    with boa.reverts("not active"):
        report(rid + 1, 0, True)
    assert counts(escrow, rid) == (0, 0)


# ------------------------------------------------------------- O-3 / T-2
def test_O_3_report_at_end_plus_grace_accepted(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE)
    report(rid, 0, True)
    assert escrow.get_slots(rid) == [1, 0, 0, 0]
    assert counts(escrow, rid) == (1, 1)


def test_O_3_report_one_second_after_grace_reverts(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE + 1)
    with boa.reverts("reporting closed"):
        report(rid, 0, True)
    assert escrow.get_slots(rid) == [0, 0, 0, 0]
    assert counts(escrow, rid) == (0, 0)


def test_O_3_window_closes_between_two_reports(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE)
    report(rid, 3, True)
    warp_to(end + REPORT_GRACE + 1)
    with boa.reverts("reporting closed"):
        report(rid, 2, True)
    assert escrow.get_slots(rid) == [0, 0, 0, 1]


def test_O_3_long_after_end_reverts(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end + 10 * 24 * 3600)
    with boa.reverts("reporting closed"):
        report(rid, 0, False)


# -------------------------------------------------------------------- O-4
def test_O_4_slot_equal_to_n_slots_reverts(escrow, make_rental, report):
    # At end + REPORT_GRACE (grace == interval) slot index N would be "completed"
    # and reporting is still open, so only O-4 is violated.
    rid, start, end = make_rental()
    warp_to(end + REPORT_GRACE)
    assert end + REPORT_GRACE >= start + (N_SLOTS + 1) * INTERVAL
    with boa.reverts("bad slot"):
        report(rid, N_SLOTS, True)
    assert escrow.get_slots(rid) == [0, 0, 0, 0]
    assert counts(escrow, rid) == (0, 0)


def test_O_4_last_slot_accepted(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE)
    report(rid, N_SLOTS - 1, True)
    assert escrow.get_slots(rid) == [0, 0, 0, 1]


# ------------------------------------------------------------- O-5 / T-1
@pytest.mark.parametrize("k", range(N_SLOTS))
def test_O_5_one_second_before_slot_completion_reverts(escrow, make_rental, report, k):
    rid, start, _ = make_rental()
    warp_to(start + (k + 1) * INTERVAL - 1)
    with boa.reverts("slot not done"):
        report(rid, k, True)
    assert escrow.get_slots(rid) == [0, 0, 0, 0]
    assert counts(escrow, rid) == (0, 0)


@pytest.mark.parametrize("k", range(N_SLOTS))
def test_O_5_exactly_at_slot_completion_accepted(escrow, make_rental, report, k):
    rid, start, _ = make_rental()
    warp_to(start + (k + 1) * INTERVAL)
    report(rid, k, False)
    assert escrow.get_slots(rid)[k] == 2
    assert counts(escrow, rid) == (0, 1)


def test_O_5_running_slot_reverts(escrow, make_rental, report):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)  # slot 0 done, slot 1 just started
    with boa.reverts("slot not done"):
        report(rid, 1, True)
    report(rid, 0, True)  # the completed one is fine at the same instant
    assert escrow.get_slots(rid) == [1, 0, 0, 0]


def test_O_5_future_slot_reverts(escrow, make_rental, report):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    with boa.reverts("slot not done"):
        report(rid, N_SLOTS - 1, True)


def test_O_5_before_start_reverts(escrow, make_rental, report):
    rid, start, _ = make_rental()  # Scheduled: now == start - 15
    with boa.reverts("slot not done"):
        report(rid, 0, True)
    warp_to(start)
    with boa.reverts("slot not done"):
        report(rid, 0, True)


# -------------------------------------------------------------------- O-6
@pytest.mark.parametrize("first", [True, False])
@pytest.mark.parametrize("second", [True, False])
def test_O_6_duplicate_reverts_and_changes_nothing(escrow, make_rental, report, first, second):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, first)
    slots, before = escrow.get_slots(rid), escrow.rentals(rid)
    with boa.reverts("already reported"):
        report(rid, 0, second)
    assert escrow.get_slots(rid) == slots  # never overwritten
    assert escrow.rentals(rid) == before
    assert counts(escrow, rid) == ((1, 1) if first else (0, 1))


def test_O_6_duplicate_from_other_reporter_reverts(escrow, make_rental, report, reporters):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, False, by=reporters[0])
    with boa.reverts("already reported"):
        report(rid, 0, True, by=reporters[1])
    assert escrow.get_slots(rid) == [2, 0, 0, 0]
    assert counts(escrow, rid) == (0, 1)


def test_O_6_duplicate_later_in_grace_reverts(escrow, make_rental, report):
    rid, start, end = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, True)
    warp_to(end + REPORT_GRACE)
    with boa.reverts("already reported"):
        report(rid, 0, False)
    assert escrow.get_slots(rid) == [1, 0, 0, 0]
    assert counts(escrow, rid) == (1, 1)


# -------------------------------------------------------- success effects
def test_O_success_up_stores_1_and_counts(escrow, make_rental, report):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, True)
    assert escrow.get_slots(rid) == [1, 0, 0, 0]
    assert counts(escrow, rid) == (1, 1)


def test_O_success_down_stores_2_and_does_not_count_up(escrow, make_rental, report):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, False)
    assert escrow.get_slots(rid) == [2, 0, 0, 0]
    assert counts(escrow, rid) == (0, 1)


def test_O_success_changes_only_counts(escrow, make_rental, report):
    rid, start, _ = make_rental()
    before = escrow.rentals(rid)
    balance = boa.env.get_balance(escrow.address)
    warp_to(start + INTERVAL)
    report(rid, 0, True)
    assert escrow.rentals(rid) == before._replace(up_count=1, reported_count=1)
    assert boa.env.get_balance(escrow.address) == balance


@pytest.mark.parametrize("up", [True, False])
def test_O_success_emits_uptime_reported(escrow, make_rental, report, reporters, up):
    make_rental()
    rid, start, _ = make_rental()  # id 2, so the event id is not the default
    warp_to(start + 3 * INTERVAL)
    report(rid, 2, up, by=reporters[1])
    ev = last_event(escrow, "UptimeReported")
    assert rid == 2
    assert ev.rental_id == 2
    assert ev.slot == 2
    assert ev.up is up
    assert ev.reporter == reporters[1]


def test_O_full_run_slot_by_slot(escrow, make_rental, report):
    rid, start, end = make_rental()
    pattern = [True, False, True, True]
    for k, up in enumerate(pattern):
        warp_to(start + (k + 1) * INTERVAL)
        report(rid, k, up)
    assert escrow.get_slots(rid) == [1, 2, 1, 1]
    assert counts(escrow, rid) == (3, 4)
    assert escrow.rentals(rid).status == 1  # still Active
    assert escrow.payout_preview(rid)[0] is True  # 3/4 at threshold 75


# --------------------------------------------------------------- backfill
def test_O_backfill_earlier_empty_slot_accepted(escrow, make_rental, report):
    rid, start, _ = make_rental()
    warp_to(start + 3 * INTERVAL)
    report(rid, 2, True)  # newest completed slot first
    report(rid, 0, False)  # then an older Empty one
    assert escrow.get_slots(rid) == [2, 0, 1, 0]
    assert counts(escrow, rid) == (1, 2)


def test_O_backfill_all_slots_in_reverse_at_grace_deadline(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE)
    for k in reversed(range(N_SLOTS)):
        report(rid, k, True)
    assert escrow.get_slots(rid) == [1, 1, 1, 1]
    assert counts(escrow, rid) == (4, 4)


# ---------------------------------------------------------- R-1 (deploy)
def test_R_1_eight_reporters_accepted():
    keys = [boa.env.generate_address(f"k{i}") for i in range(8)]
    escrow = boa.load("contracts/GpuSlaEscrow.vy", keys)
    assert all(escrow.is_reporter(k) for k in keys)


def test_R_1_nine_reporters_rejected():
    keys = [boa.env.generate_address(f"k{i}") for i in range(9)]
    with boa.reverts():
        boa.load("contracts/GpuSlaEscrow.vy", keys)


def test_R_1_reporter_set_unchanged_by_create_and_report(escrow, make_rental, report, reporters, renter, provider, stranger):
    rid, start, _ = make_rental()
    warp_to(start + INTERVAL)
    report(rid, 0, True)
    assert all(escrow.is_reporter(r) for r in reporters)
    assert not any(escrow.is_reporter(a) for a in (renter, provider, stranger))


# --------------------------------------------- R-3 / §6 two rentals, two keys
def test_R_two_rentals_reported_by_two_keys(escrow, make_rental, report, reporters):
    a, start, _ = make_rental()
    b, start_b, _ = make_rental()
    assert (a, b) == (1, 2) and start == start_b
    warp_to(start + 2 * INTERVAL)  # same timestamp for every report below
    report(a, 0, True, by=reporters[0])
    report(b, 0, False, by=reporters[1])
    report(a, 1, False, by=reporters[0])
    report(b, 1, True, by=reporters[1])
    assert escrow.get_slots(a) == [1, 2, 0, 0]
    assert escrow.get_slots(b) == [2, 1, 0, 0]
    assert counts(escrow, a) == (1, 2)
    assert counts(escrow, b) == (1, 2)


def test_R_3_report_touches_only_its_own_rental(escrow, make_rental, report, reporters):
    a, start, _ = make_rental()
    b, _, _ = make_rental()
    warp_to(start + INTERVAL)
    report(b, 0, False, by=reporters[1])
    b_rental, b_slots = escrow.rentals(b), escrow.get_slots(b)
    next_id = escrow.next_rental_id()
    balance = boa.env.get_balance(escrow.address)

    report(a, 0, True, by=reporters[0])

    assert escrow.rentals(b) == b_rental
    assert escrow.get_slots(b) == b_slots
    assert escrow.next_rental_id() == next_id == 3
    assert boa.env.get_balance(escrow.address) == balance
    assert all(escrow.credits(x) == 0 for x in reporters)
    assert escrow.get_slots(a) == [1, 0, 0, 0]


def test_R_3_same_slot_index_is_independent_per_rental(escrow, make_rental, report):
    a, start, _ = make_rental()
    b, _, _ = make_rental()
    warp_to(start + INTERVAL)
    report(a, 0, True)
    report(b, 0, True)  # not "already reported": slot 0 of a different rental
    assert escrow.get_slots(a) == escrow.get_slots(b) == [1, 0, 0, 0]
