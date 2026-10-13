"""S-rules and timing T-3 (SPEC §3). Red until settle() is implemented (T-004).

Every revert test violates only the rule under test: the rental is Active and
the clock is past `end + REPORT_GRACE` unless stated.
"""
import boa
import pytest

from conftest import CHALLENGE_WINDOW, INTERVAL, N_SLOTS, PRICE, REPORT_GRACE, last_event, now, warp_to

ACTORS = ["renter", "provider", "stranger", "reporter"]
RUNS = [(4, True), (2, False)]  # (slots Up of 4 at threshold 75, compliant)


# -------------------------------------------------------------------- S-1
@pytest.mark.parametrize("rid", [0, 1, 99])
def test_S_1_nonexistent_rental_reverts(escrow, settle, rid):
    # status 0, end 0: the clock is far past 0 + REPORT_GRACE, so only S-1 fails.
    with boa.reverts("not active"):
        settle(rid)


def test_S_1_double_settle_reverts(escrow, propose, settle):
    rid, _ = propose(4)
    before = escrow.rentals(rid)
    with boa.reverts("not active"):
        settle(rid)
    warp_to(now() + 5)
    with boa.reverts("not active"):
        settle(rid)
    assert escrow.rentals(rid) == before  # proposed_at not moved


def test_S_1_settle_after_finalize_reverts(escrow, finalized, settle, provider):
    rid = finalized(4)
    before = escrow.rentals(rid)
    with boa.reverts("not active"):
        settle(rid)
    assert escrow.rentals(rid) == before
    assert escrow.credits(provider) == PRICE


# ------------------------------------------------------------- S-2 / T-3
def test_S_2_settle_at_end_plus_grace_reverts(escrow, make_rental, settle):
    rid, _, end = make_rental()
    before = escrow.rentals(rid)
    warp_to(end + REPORT_GRACE)
    with boa.reverts("too early"):
        settle(rid)
    assert escrow.rentals(rid) == before  # still Active, proposed_at 0


def test_S_2_settle_one_second_after_grace_succeeds(escrow, make_rental, settle):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    r = escrow.rentals(rid)
    assert r.status == 2
    assert r.proposed_at == end + REPORT_GRACE + 1


@pytest.mark.parametrize("where", ["created", "start", "mid", "end - 1", "end", "end + grace - 1"])
def test_S_2_settle_before_grace_is_over_reverts(escrow, make_rental, settle, where):
    rid, start, end = make_rental()
    warp_to({
        "created": now(),
        "start": start,
        "mid": start + 2 * INTERVAL,
        "end - 1": end - 1,
        "end": end,
        "end + grace - 1": end + REPORT_GRACE - 1,
    }[where])
    with boa.reverts("too early"):
        settle(rid)
    assert escrow.rentals(rid).status == 1


def test_T_3_report_and_settle_windows_never_overlap(escrow, make_rental, report, settle):
    rid, _, end = make_rental()
    warp_to(end + REPORT_GRACE)  # last second of reporting: report ok, settle not yet
    report(rid, 0, True)
    with boa.reverts("too early"):
        settle(rid)
    warp_to(end + REPORT_GRACE + 1)  # first second of settling: report closed, settle ok
    with boa.reverts("reporting closed"):
        report(rid, 1, True)
    settle(rid)
    assert last_event(escrow, "SettlementProposed").up_count == 1
    assert escrow.rentals(rid).status == 2


# -------------------------------------------------------------------- S-3
@pytest.mark.parametrize(
    "threshold, n, ups, compliant",
    [
        (75, 4, 4, True),
        (75, 4, 3, True),    # 300 == 300: boundary passes
        (75, 4, 2, False),
        (76, 4, 3, False),   # 300 < 304
        (100, 4, 4, True),   # 400 == 400
        (100, 4, 3, False),
        (1, 4, 0, False),    # 0 < 4: zero uptime never passes
        (1, 4, 1, True),
        (50, 2, 1, True),    # 100 == 100
        (51, 2, 1, False),
        (33, 3, 1, True),    # 100 >= 99
        (34, 3, 1, False),   # 100 < 102
        (66, 3, 2, True),    # 200 >= 198
        (67, 3, 2, False),   # 200 < 201
        (100, 1, 1, True),
        (100, 1, 0, False),
    ],
)
def test_S_3_compliance_is_100_up_ge_threshold_n(escrow, propose, renter, provider, threshold, n, ups, compliant):
    rid, _ = propose(ups, threshold=threshold, n=n)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant) == (ups, n, compliant)
    assert escrow.rentals(rid).compliant is compliant
    assert escrow.payout_preview(rid) == (compliant, provider if compliant else renter, PRICE)


def test_S_3_boundary_equal_is_compliant(escrow, propose, provider):
    rid, _ = propose(3)  # 100 * 3 == 75 * 4
    ev = last_event(escrow, "SettlementProposed")
    assert ev.compliant is True
    assert ev.payee == provider
    assert escrow.rentals(rid).compliant is True


def test_S_3_unreported_slots_count_as_down(escrow, make_rental, report, settle, renter):
    rid, _, end = make_rental()
    warp_to(end)
    report(rid, 0, True)
    report(rid, 1, True)  # slots 2 and 3 are never reported
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee) == (2, 4, False, renter)
    r = escrow.rentals(rid)
    assert (r.up_count, r.reported_count, r.compliant) == (2, 2, False)
    assert escrow.get_slots(rid) == [1, 1, 0, 0]  # settle does not rewrite Empty slots


def test_S_3_denominator_is_n_slots_not_reported_count(escrow, make_rental, report, settle, renter):
    # 3 of 3 *reported* slots are Up, but the rental has 4 slots: 300 < 400.
    rid, _, end = make_rental(threshold=100)
    warp_to(end)
    for k in range(3):
        report(rid, k, True)
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee) == (3, 4, False, renter)


def test_S_3_no_reports_at_all_refunds_renter(escrow, make_rental, settle, renter):
    rid, _, end = make_rental(threshold=1)  # even the lowest threshold fails with 0 Up
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee, ev.amount) == (0, 4, False, renter, PRICE)
    assert escrow.rentals(rid).compliant is False


# -------------------------------------------------------------------- S-4
@pytest.mark.parametrize("ups, compliant", RUNS)
def test_S_4_stores_status_proposed_at_and_compliant(escrow, make_rental, report, settle, renter, provider, stranger, ups, compliant):
    rid, _, end = make_rental()
    warp_to(end)
    for k in range(N_SLOTS):
        report(rid, k, k < ups)
    before, slots = escrow.rentals(rid), escrow.get_slots(rid)
    balance = boa.env.get_balance(escrow.address)
    assert (before.status, before.proposed_at, before.compliant) == (1, 0, False)

    warp_to(end + REPORT_GRACE + 7)
    settle(rid)

    # exactly three fields change
    assert escrow.rentals(rid) == before._replace(status=2, proposed_at=end + REPORT_GRACE + 7, compliant=compliant)
    assert escrow.get_slots(rid) == slots
    # settle moves no money and credits nobody
    assert boa.env.get_balance(escrow.address) == balance == PRICE
    assert all(escrow.credits(a) == 0 for a in (renter, provider, stranger))


def test_S_4_settle_touches_only_its_own_rental(escrow, make_rental, settle):
    a, _, end = make_rental()
    b, _, _ = make_rental()
    b_before = escrow.rentals(b)
    warp_to(end + REPORT_GRACE + 1)
    settle(a)
    assert escrow.rentals(a).status == 2
    assert escrow.rentals(b) == b_before  # still Active
    assert escrow.next_rental_id() == 3


# -------------------------------------------------------------------- S-5
@pytest.mark.parametrize("ups, compliant", RUNS)
def test_S_5_settlement_proposed_event(escrow, make_rental, propose, renter, provider, stranger, ups, compliant):
    make_rental()  # so the event id is not the default
    rid, proposed_at = propose(ups)
    ev = last_event(escrow, "SettlementProposed")  # before any view call
    assert rid == 2
    assert ev.rental_id == 2
    assert ev.up_count == ups
    assert ev.n_slots == N_SLOTS
    assert ev.compliant is compliant
    assert ev.payee == (provider if compliant else renter)
    assert ev.amount == PRICE
    assert ev.proposed_at == proposed_at == escrow.rentals(rid).proposed_at
    assert ev.caller == stranger


def test_S_5_amount_is_the_rental_price(escrow, propose):
    propose(4, price=123_456_789)
    assert last_event(escrow, "SettlementProposed").amount == 123_456_789


@pytest.mark.parametrize("who", ACTORS)
@pytest.mark.parametrize("ups, compliant", RUNS)
def test_S_5_same_result_for_any_caller(escrow, propose, actor, renter, provider, who, ups, compliant):
    rid, _ = propose(ups, by=actor(who))
    ev = last_event(escrow, "SettlementProposed")
    assert ev.caller == actor(who)
    assert (ev.compliant, ev.payee, ev.amount) == (compliant, provider if compliant else renter, PRICE)
    r = escrow.rentals(rid)
    assert (r.status, r.compliant) == (2, compliant)


@pytest.mark.parametrize("ups, compliant", RUNS)
def test_S_5_same_result_when_settled_much_later(escrow, make_rental, report, settle, renter, provider, ups, compliant):
    rid, _, end = make_rental()
    warp_to(end)
    for k in range(N_SLOTS):
        report(rid, k, k < ups)
    late = end + 30 * 24 * 3600
    warp_to(late)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant) == (ups, N_SLOTS, compliant)
    assert (ev.payee, ev.amount) == (provider if compliant else renter, PRICE)
    assert ev.proposed_at == late  # only the clock value differs
    assert escrow.rentals(rid).proposed_at == late
    assert escrow.phase(rid) == 5  # the challenge window starts at the late settle
    warp_to(late + CHALLENGE_WINDOW)
    assert escrow.phase(rid) == 6
