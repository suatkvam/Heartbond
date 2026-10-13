"""Views (SPEC §3 V) and R-1 deploy checks. The views are implemented in the skeleton;
tests that need settle()/finalize() to reach a phase are red until T-004."""
import boa
import pytest

from conftest import CHALLENGE_WINDOW, N_SLOTS, PRICE, REPORT_GRACE, now, warp_to

ZERO = "0x" + "00" * 20


def test_V_unknown_rental_is_phase_none(escrow):
    assert escrow.phase(1) == 0
    assert escrow.get_slots(1) == []


def test_V_ids_start_at_one(escrow):
    assert escrow.next_rental_id() == 1


def test_V_constants(escrow):
    assert escrow.REPORT_GRACE() == 30
    assert escrow.CHALLENGE_WINDOW() == 60


def test_R_1_reporters_allow_listed(escrow, reporters, stranger):
    assert all(escrow.is_reporter(r) for r in reporters)
    assert not escrow.is_reporter(stranger)


def test_R_1_empty_reporter_list_reverts():
    with boa.reverts("no reporters"):
        boa.load("contracts/GpuSlaEscrow.vy", [])


@pytest.mark.parametrize("position", [0, 1, 2])
def test_R_1_zero_address_reporter_reverts(position):
    keys = [boa.env.generate_address("k1"), boa.env.generate_address("k2")]
    keys.insert(position, ZERO)
    with boa.reverts("zero reporter"):
        boa.load("contracts/GpuSlaEscrow.vy", keys)


def test_R_1_only_zero_address_reverts():
    with boa.reverts("zero reporter"):
        boa.load("contracts/GpuSlaEscrow.vy", [ZERO])


# ------------------------------------------------------------------- phase
def test_V_phase_both_sides_of_start_end_and_grace(escrow, make_rental):
    rid, start, end = make_rental()
    for ts, phase in [
        (start - 1, 1),                # Scheduled
        (start, 2),                    # Running
        (end - 1, 2),
        (end, 3),                      # Grace
        (end + REPORT_GRACE, 3),
        (end + REPORT_GRACE + 1, 4),   # Settleable
        (end + 30 * 24 * 3600, 4),     # stays Settleable until someone settles
    ]:
        warp_to(ts)
        assert escrow.phase(rid) == phase, ts - start


def test_V_phase_does_not_depend_on_reports(escrow, make_rental, report):
    rid, _, end = make_rental()
    warp_to(end)
    for k in range(N_SLOTS):
        report(rid, k, True)
    assert escrow.phase(rid) == 3  # fully reported, still Grace until the clock passes it
    warp_to(end + REPORT_GRACE + 1)
    assert escrow.phase(rid) == 4


def test_V_phase_both_sides_of_challenge_window_and_settled(escrow, propose, finalize):
    rid, proposed_at = propose(4)
    assert escrow.phase(rid) == 5      # Challenge, from the settle second on
    warp_to(proposed_at + CHALLENGE_WINDOW - 1)
    assert escrow.phase(rid) == 5
    warp_to(proposed_at + CHALLENGE_WINDOW)
    assert escrow.phase(rid) == 6      # Finalizable
    warp_to(proposed_at + 30 * 24 * 3600)
    assert escrow.phase(rid) == 6      # stays Finalizable until someone finalizes
    finalize(rid)
    assert escrow.phase(rid) == 7      # Settled
    warp_to(now() + 30 * 24 * 3600)
    assert escrow.phase(rid) == 7


def test_V_phase_settled_after_withdraw(escrow, finalized, withdraw, provider):
    rid = finalized(4)
    withdraw(provider)
    assert escrow.phase(rid) == 7


# ---------------------------------------------------------- payout_preview
def test_V_payout_preview_unknown_rental(escrow):
    # threshold 0, n_slots 0: 0 >= 0. The UI must check phase() != 0 first.
    assert escrow.payout_preview(99) == (True, ZERO, 0)


def test_V_payout_preview_tracks_reports_before_settle(escrow, make_rental, report, renter, provider):
    rid, _, end = make_rental()
    assert escrow.payout_preview(rid) == (False, renter, PRICE)  # 0 of 4
    warp_to(end)
    report(rid, 0, True)
    report(rid, 1, True)
    assert escrow.payout_preview(rid) == (False, renter, PRICE)  # 200 < 300
    report(rid, 2, False)
    assert escrow.payout_preview(rid) == (False, renter, PRICE)  # a Down report changes nothing
    report(rid, 3, True)
    assert escrow.payout_preview(rid) == (True, provider, PRICE)  # 300 == 300
    warp_to(end + REPORT_GRACE + 1)
    assert escrow.payout_preview(rid) == (True, provider, PRICE)  # what settle() would decide now


@pytest.mark.parametrize("ups, compliant", [(4, True), (3, True), (2, False), (0, False)])
def test_V_payout_preview_frozen_after_settle(escrow, propose, objection, finalize, withdraw, renter, provider, ups, compliant):
    rid, proposed_at = propose(ups)
    payee = provider if compliant else renter
    frozen = (compliant, payee, PRICE)
    assert escrow.payout_preview(rid) == frozen
    assert escrow.rentals(rid).compliant is compliant
    objection(rid, renter)
    objection(rid, provider)
    assert escrow.payout_preview(rid) == frozen
    warp_to(proposed_at + CHALLENGE_WINDOW)
    assert escrow.payout_preview(rid) == frozen
    finalize(rid)
    assert escrow.payout_preview(rid) == frozen
    withdraw(payee)
    assert escrow.payout_preview(rid) == frozen  # amount is the rental price, not the remaining credit


# ----------------------------------------------------------------- credits
def test_V_credits_zero_until_finalize(escrow, propose, finalize, renter, provider):
    rid, proposed_at = propose(4)
    assert escrow.credits(provider) == escrow.credits(renter) == 0
    warp_to(proposed_at + CHALLENGE_WINDOW)
    assert escrow.credits(provider) == 0  # the window closing credits nobody by itself
    finalize(rid)
    assert escrow.credits(provider) == PRICE
