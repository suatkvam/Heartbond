"""SPEC §6 end-to-end scenarios with the §5 demo parameters (interval 30, N 4,
threshold 75, price 0.01 MON). Red until settle / raise_objection / finalize /
withdraw are implemented (T-004).

Other §6 scenarios live next to their rule:
  rejecting withdrawer   -> test_finalize_withdraw.py::test_P_3_rejecting_payee_fails_only_its_own_withdraw
  re-entrant withdrawer  -> test_finalize_withdraw.py::test_P_2_reentrant_payee_gains_nothing
  credit from 2 rentals  -> test_finalize_withdraw.py::test_F_4_credits_accumulate_over_two_rentals
"""
import boa
import pytest

from conftest import CHALLENGE_WINDOW, INTERVAL, N_SLOTS, PRICE, REPORT_GRACE, last_event, now, warp_to

balance = boa.env.get_balance


def run_slots(report, rid, start, pattern, by=None):
    """Report slot k right when it completes; None in `pattern` leaves the slot unreported."""
    for k, up in enumerate(pattern):
        warp_to(start + (k + 1) * INTERVAL)
        if up is not None:
            report(rid, k, up, by=by)


def test_scenario_compliant_run_provider_withdraws_price(escrow, make_rental, report, settle, finalize, withdraw, renter, provider, stranger):
    rid, start, end = make_rental()
    assert escrow.phase(rid) == 1
    assert balance(escrow.address) == PRICE

    run_slots(report, rid, start, [True, True, True, True])
    assert escrow.get_slots(rid) == [1, 1, 1, 1]
    assert escrow.phase(rid) == 3
    assert escrow.payout_preview(rid) == (True, provider, PRICE)

    warp_to(end + REPORT_GRACE + 1)
    assert escrow.phase(rid) == 4
    settle(rid)  # third wallet
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee, ev.amount, ev.caller) == (4, 4, True, provider, PRICE, stranger)
    assert escrow.phase(rid) == 5

    warp_to(now() + CHALLENGE_WINDOW)
    assert escrow.phase(rid) == 6
    finalize(rid)  # third wallet
    ev = last_event(escrow, "SettlementFinalized")
    assert (ev.payee, ev.amount, ev.caller) == (provider, PRICE, stranger)
    assert escrow.phase(rid) == 7
    assert escrow.credits(provider) == PRICE
    assert balance(escrow.address) == PRICE  # not paid out yet

    had = balance(provider)
    withdraw(provider)
    ev = last_event(escrow, "Withdrawn")
    assert (ev.account, ev.amount) == (provider, PRICE)
    assert balance(provider) == had + PRICE
    assert balance(escrow.address) == 0
    with boa.reverts("nothing to withdraw"):
        withdraw(renter)  # the renter gets nothing back


def test_scenario_non_compliant_run_renter_refunded(escrow, make_rental, report, settle, finalize, withdraw, renter, provider, stranger):
    rid, start, end = make_rental()
    paid = balance(renter)

    run_slots(report, rid, start, [True, True, False, False])  # node stopped for 2 slots
    assert escrow.get_slots(rid) == [1, 1, 2, 2]
    assert escrow.payout_preview(rid) == (False, renter, PRICE)  # 200 < 300

    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee, ev.amount, ev.caller) == (2, 4, False, renter, PRICE, stranger)

    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    ev = last_event(escrow, "SettlementFinalized")
    assert (ev.payee, ev.amount, ev.caller) == (renter, PRICE, stranger)
    assert escrow.credits(renter) == PRICE
    assert escrow.credits(provider) == 0

    withdraw(renter)
    assert balance(renter) == paid + PRICE  # full refund
    assert balance(escrow.address) == 0
    with boa.reverts("nothing to withdraw"):
        withdraw(provider)
    assert balance(provider) == 0


def test_scenario_boundary_three_of_four_at_75_passes(escrow, make_rental, report, settle, finalize, withdraw, provider):
    rid, start, end = make_rental()
    run_slots(report, rid, start, [True, False, True, True])  # 100 * 3 == 75 * 4
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee) == (3, 4, True, provider)
    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    withdraw(provider)
    assert balance(provider) == PRICE
    assert balance(escrow.address) == 0


def test_scenario_unreported_slots_count_as_down(escrow, make_rental, report, settle, finalize, withdraw, renter):
    rid, start, end = make_rental()
    paid = balance(renter)
    run_slots(report, rid, start, [True, True, True, None])  # oracle never reports slot 3
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    assert last_event(escrow, "SettlementProposed").compliant is True  # 3/4 still meets 75
    assert escrow.get_slots(rid) == [1, 1, 1, 0]

    rid, start, end = make_rental()
    run_slots(report, rid, start, [True, True, None, None])  # two slots missing: 2/4 fails
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.compliant, ev.payee) == (2, False, renter)
    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    assert escrow.credits(renter) == PRICE
    assert balance(renter) == paid - PRICE  # second rental's price, refundable by withdraw


@pytest.mark.parametrize("pattern, payee_is_provider", [([True] * 4, True), ([True, True, False, False], False)])
def test_scenario_objection_by_each_party_has_no_effect(escrow, make_rental, report, settle, objection, finalize, withdraw, renter, provider, pattern, payee_is_provider):
    rid, start, end = make_rental()
    run_slots(report, rid, start, pattern)
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    proposed = escrow.rentals(rid)
    payee, loser = (provider, renter) if payee_is_provider else (renter, provider)

    objection(rid, loser)
    ev = last_event(escrow, "ObjectionRaised")
    assert (ev.rental_id, ev.by, ev.is_renter) == (rid, loser, loser == renter)
    objection(rid, payee)
    assert escrow.rentals(rid) == proposed._replace(renter_objected=True, provider_objected=True)
    assert escrow.payout_preview(rid) == (payee_is_provider, payee, PRICE)

    warp_to(proposed.proposed_at + CHALLENGE_WINDOW)  # finality is the timeout, objections or not
    finalize(rid)
    ev = last_event(escrow, "SettlementFinalized")
    assert (ev.payee, ev.amount) == (payee, PRICE)
    had = balance(payee)
    withdraw(payee)
    assert balance(payee) == had + PRICE
    with boa.reverts("nothing to withdraw"):
        withdraw(loser)


def test_scenario_third_wallet_settles_and_finalizes(escrow, make_rental, report, withdraw, provider, stranger):
    assert not escrow.is_reporter(stranger)
    rid, start, end = make_rental()
    run_slots(report, rid, start, [True] * N_SLOTS)
    warp_to(end + REPORT_GRACE + 1)
    with boa.env.prank(stranger):
        escrow.settle(rid)
    assert last_event(escrow, "SettlementProposed").caller == stranger
    warp_to(now() + CHALLENGE_WINDOW)
    with boa.env.prank(stranger):
        escrow.finalize(rid)
    assert last_event(escrow, "SettlementFinalized").caller == stranger
    assert escrow.credits(stranger) == 0
    assert balance(stranger) == 0  # triggering pays the trigger nothing
    with boa.reverts("nothing to withdraw"):
        withdraw(stranger)
    withdraw(provider)  # only the payee can pull the MON
    assert balance(provider) == PRICE


def test_scenario_same_result_when_settled_much_later(escrow, make_rental, report, settle, finalize, withdraw, provider):
    rid, start, end = make_rental()
    run_slots(report, rid, start, [True] * N_SLOTS)
    warp_to(end + 7 * 24 * 3600)  # nobody triggers for a week
    assert escrow.phase(rid) == 4
    settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee, ev.amount) == (4, 4, True, provider, PRICE)
    warp_to(now() + 7 * 24 * 3600)  # and again for the finalize
    assert escrow.phase(rid) == 6
    finalize(rid)
    withdraw(provider)
    assert balance(provider) == PRICE


def test_scenario_double_settle_finalize_withdraw_revert(escrow, make_rental, report, settle, finalize, withdraw, provider):
    rid, start, end = make_rental()
    run_slots(report, rid, start, [True] * N_SLOTS)
    make_rental(price=5 * PRICE)  # unrelated MON in the escrow that a double payout could take

    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    with boa.reverts("not active"):
        settle(rid)

    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    with boa.reverts("not proposed"):
        finalize(rid)
    assert escrow.credits(provider) == PRICE

    withdraw(provider)
    with boa.reverts("nothing to withdraw"):
        withdraw(provider)
    assert balance(provider) == PRICE
    assert balance(escrow.address) == 5 * PRICE


def test_scenario_report_after_settle_reverts_not_active(escrow, make_rental, report, settle, finalize, reporters):
    # SPEC lists O-2 before O-3: once settled the answer is "not active", not "reporting closed".
    rid, start, end = make_rental()
    run_slots(report, rid, start, [True, True, None, None])
    warp_to(end + REPORT_GRACE + 1)
    settle(rid)
    proposed, slots = escrow.rentals(rid), escrow.get_slots(rid)
    for key in reporters:
        with boa.reverts("not active"):
            report(rid, 2, True, by=key)  # Proposed: an Empty slot can no longer be filled
    assert escrow.rentals(rid) == proposed
    assert escrow.get_slots(rid) == slots == [1, 1, 0, 0]

    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    with boa.reverts("not active"):
        report(rid, 3, True)  # Settled
    assert escrow.get_slots(rid) == [1, 1, 0, 0]
    assert escrow.rentals(rid).up_count == 2


def test_scenario_two_rentals_two_keys_settle_independently(escrow, make_rental, report, settle, finalize, withdraw, reporters, renter, provider):
    price_a, price_b = 3 * 10**15, 8 * 10**15
    a, start, end = make_rental(price=price_a)
    b, start_b, _ = make_rental(price=price_b)
    assert (a, b) == (1, 2) and start == start_b
    paid = balance(renter)

    for k in range(N_SLOTS):  # each rental has its own reporter key (R-2), same timestamps
        warp_to(start + (k + 1) * INTERVAL)
        report(a, k, True, by=reporters[0])
        report(b, k, k < 2, by=reporters[1])
    assert escrow.get_slots(a) == [1, 1, 1, 1]
    assert escrow.get_slots(b) == [1, 1, 2, 2]

    warp_to(end + REPORT_GRACE + 1)
    settle(a)
    assert last_event(escrow, "SettlementProposed").payee == provider
    assert escrow.rentals(a).status == 2
    assert escrow.rentals(b).status == 1  # settling a does not settle b
    a_proposed_at = now()

    warp_to(a_proposed_at + 20)
    settle(b)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.rental_id, ev.up_count, ev.compliant, ev.payee, ev.amount) == (b, 2, False, renter, price_b)

    warp_to(a_proposed_at + CHALLENGE_WINDOW)  # a's window is over, b's is not
    with boa.reverts("window open"):
        finalize(b)
    finalize(a)
    assert (escrow.phase(a), escrow.phase(b)) == (7, 5)
    assert escrow.credits(provider) == price_a
    assert escrow.credits(renter) == 0

    warp_to(a_proposed_at + 20 + CHALLENGE_WINDOW)
    finalize(b)
    assert escrow.credits(renter) == price_b
    assert escrow.credits(provider) == price_a  # b's finalize does not touch a's payee

    withdraw(provider)
    assert balance(provider) == price_a
    assert balance(escrow.address) == price_b
    withdraw(renter)
    assert balance(renter) == paid + price_b
    assert balance(escrow.address) == 0


def test_scenario_far_future_end_rejected_and_normal_rental_runs_full_lifecycle(escrow, finalized, withdraw, renter, provider):
    # D-12 (C-1.11 / C-1.12): a rental whose `end` is the largest uint256 used to be accepted
    # and could never be settled (`end + REPORT_GRACE` overflowed). It must now be refused
    # with a SPEC table E string, not an arithmetic panic, and take no MON.
    # One slot, start == now: C-1.12 is the only rule violated.
    start, end = now(), 2**256 - 1
    paid = balance(renter)
    with boa.env.prank(renter), boa.reverts("interval too long"):
        escrow.create_rental(provider, 75, end - start, start, end, b"\x00" * 32, value=1)
    assert escrow.next_rental_id() == 1
    assert escrow.phase(1) == 0
    assert balance(escrow.address) == 0
    assert balance(renter) == paid

    rid = finalized(4)  # a normal rental created afterwards: full compliant lifecycle
    assert rid == 1
    assert escrow.phase(rid) == 7
    assert escrow.credits(provider) == PRICE
    had = balance(provider)
    withdraw(provider)
    assert balance(provider) == had + PRICE
    assert balance(escrow.address) == 0  # nothing is left locked
