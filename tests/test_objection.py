"""X-rules and the objection side of timing T-4 (SPEC §3). Red until settle() and
raise_objection() are implemented (T-004).

Every revert test violates only the rule under test where the state machine
allows it: the rental is Proposed, the clock is inside the challenge window,
the caller is a party and has not objected, unless stated.

Unavoidable overlaps (SPEC lists X-1 first, so "not proposed" is expected):
an Active rental has proposed_at == 0, so X-2 fails too; a Settled rental is
always past its window; a nonexistent rental has no parties.
"""
import boa
import pytest

from conftest import CHALLENGE_WINDOW, INTERVAL, PRICE, REPORT_GRACE, SPEC_REF, THRESHOLD, last_event, now, warp_to

PARTIES = ["renter", "provider"]
FLAG = {"renter": "renter_objected", "provider": "provider_objected"}


def flags(escrow, rid):
    r = escrow.rentals(rid)
    return r.renter_objected, r.provider_objected


# -------------------------------------------------------------------- X-1
@pytest.mark.parametrize("who", PARTIES)
@pytest.mark.parametrize("where", ["running", "grace", "settleable"])
def test_X_1_active_rental_reverts(escrow, make_rental, objection, actor, who, where):
    rid, start, end = make_rental()
    warp_to({"running": start + INTERVAL, "grace": end + REPORT_GRACE, "settleable": end + REPORT_GRACE + 1}[where])
    with boa.reverts("not proposed"):
        objection(rid, actor(who))
    assert flags(escrow, rid) == (False, False)


@pytest.mark.parametrize("who", PARTIES)
def test_X_1_settled_rental_reverts(escrow, finalized, objection, actor, who):
    rid = finalized(4)
    before = escrow.rentals(rid)
    with boa.reverts("not proposed"):
        objection(rid, actor(who))
    assert escrow.rentals(rid) == before


@pytest.mark.parametrize("rid", [0, 1, 99])
def test_X_1_nonexistent_rental_reverts(escrow, objection, renter, rid):
    with boa.reverts("not proposed"):
        objection(rid, renter)


# ------------------------------------------------------------- X-2 / T-4
@pytest.mark.parametrize("who", PARTIES)
def test_X_2_objection_in_last_second_of_window_succeeds(escrow, propose, objection, actor, who):
    rid, proposed_at = propose(4)
    warp_to(proposed_at + CHALLENGE_WINDOW - 1)
    objection(rid, actor(who))
    assert last_event(escrow, "ObjectionRaised").by == actor(who)
    assert getattr(escrow.rentals(rid), FLAG[who]) is True


@pytest.mark.parametrize("who", PARTIES)
def test_X_2_objection_at_window_end_reverts(escrow, propose, objection, actor, who):
    rid, proposed_at = propose(4)
    before = escrow.rentals(rid)
    warp_to(proposed_at + CHALLENGE_WINDOW)
    with boa.reverts("window closed"):
        objection(rid, actor(who))
    assert escrow.rentals(rid) == before  # still Proposed, no flag set


def test_X_2_objection_in_same_second_as_settle_succeeds(escrow, propose, objection, renter):
    rid, proposed_at = propose(4)
    assert now() == proposed_at
    objection(rid, renter)
    assert flags(escrow, rid) == (True, False)


def test_X_2_objection_long_after_window_reverts(escrow, propose, objection, provider):
    rid, proposed_at = propose(4)
    warp_to(proposed_at + 30 * 24 * 3600)  # nobody finalized: still Proposed
    with boa.reverts("window closed"):
        objection(rid, provider)
    assert flags(escrow, rid) == (False, False)


def test_X_2_window_counts_from_proposed_at_not_from_end(escrow, make_rental, settle, objection, renter):
    rid, _, end = make_rental()
    late = end + 3600  # settled an hour late: the window still lasts the full 60 s
    warp_to(late)
    settle(rid)
    warp_to(late + CHALLENGE_WINDOW - 1)
    objection(rid, renter)
    assert flags(escrow, rid) == (True, False)


# -------------------------------------------------------------------- X-3
@pytest.mark.parametrize("who", ["stranger", "reporter"])
def test_X_3_non_party_reverts(escrow, propose, objection, actor, who):
    rid, _ = propose(4)
    before = escrow.rentals(rid)
    with boa.reverts("not a party"):
        objection(rid, actor(who))
    assert escrow.rentals(rid) == before


def test_X_3_settle_caller_is_not_a_party(escrow, propose, objection, stranger):
    rid, _ = propose(4, by=stranger)
    with boa.reverts("not a party"):
        objection(rid, stranger)
    assert flags(escrow, rid) == (False, False)


def test_X_3_party_of_another_rental_reverts(escrow, make_rental, settle, objection, renter, provider):
    other_renter = boa.env.generate_address("other renter")
    other_provider = boa.env.generate_address("other provider")
    boa.env.set_balance(other_renter, 10**18)
    a, start, end = make_rental()
    with boa.env.prank(other_renter):
        b = escrow.create_rental(other_provider, THRESHOLD, INTERVAL, start, end, SPEC_REF, value=PRICE)
    warp_to(end + REPORT_GRACE + 1)
    settle(a)
    settle(b)
    for outsider in (other_renter, other_provider):
        with boa.reverts("not a party"):
            objection(a, outsider)
    for outsider in (renter, provider):
        with boa.reverts("not a party"):
            objection(b, outsider)
    assert flags(escrow, a) == flags(escrow, b) == (False, False)
    objection(a, renter)  # each is still a party of its own rental
    objection(b, other_provider)
    assert flags(escrow, a) == (True, False)
    assert flags(escrow, b) == (False, True)


# -------------------------------------------------------------------- X-4
@pytest.mark.parametrize("who", PARTIES)
def test_X_4_second_objection_by_same_party_reverts(escrow, propose, objection, actor, who):
    rid, proposed_at = propose(4)
    objection(rid, actor(who))
    before = escrow.rentals(rid)
    with boa.reverts("already objected"):
        objection(rid, actor(who))
    warp_to(proposed_at + CHALLENGE_WINDOW - 1)  # still inside the window
    with boa.reverts("already objected"):
        objection(rid, actor(who))
    assert escrow.rentals(rid) == before


def test_X_4_both_parties_can_each_object_once(escrow, propose, objection, renter, provider):
    rid, _ = propose(4)
    objection(rid, renter)
    assert flags(escrow, rid) == (True, False)
    objection(rid, provider)  # the renter's flag does not block the provider
    assert flags(escrow, rid) == (True, True)
    for party in (renter, provider):
        with boa.reverts("already objected"):
            objection(rid, party)
    assert flags(escrow, rid) == (True, True)


def test_X_4_provider_first_then_renter(escrow, propose, objection, renter, provider):
    rid, _ = propose(2)
    objection(rid, provider)
    assert flags(escrow, rid) == (False, True)
    objection(rid, renter)
    assert flags(escrow, rid) == (True, True)


@pytest.mark.parametrize("who", PARTIES)
def test_X_4_objection_raised_event(escrow, make_rental, propose, objection, actor, who):
    make_rental()  # so the event id is not the default
    rid, _ = propose(4)
    objection(rid, actor(who))
    ev = last_event(escrow, "ObjectionRaised")  # before any view call
    assert rid == 2
    assert ev.rental_id == 2
    assert ev.by == actor(who)
    assert ev.is_renter is (who == "renter")


@pytest.mark.parametrize("who", PARTIES)
@pytest.mark.parametrize("ups", [4, 2])
def test_X_4_changes_nothing_but_the_callers_flag(escrow, propose, objection, actor, renter, provider, who, ups):
    rid, proposed_at = propose(ups)
    before, slots, preview = escrow.rentals(rid), escrow.get_slots(rid), escrow.payout_preview(rid)
    balance = boa.env.get_balance(escrow.address)

    warp_to(proposed_at + 10)  # a later second, so a rewritten proposed_at would show
    objection(rid, actor(who))

    assert escrow.rentals(rid) == before._replace(**{FLAG[who]: True})  # status, proposed_at, compliant untouched
    assert escrow.get_slots(rid) == slots
    assert escrow.payout_preview(rid) == preview
    assert escrow.phase(rid) == 5
    assert boa.env.get_balance(escrow.address) == balance == PRICE
    assert escrow.credits(renter) == escrow.credits(provider) == 0


# ------------------------------------- §6: objection has no effect on payout
@pytest.mark.parametrize("objectors", [(), ("renter",), ("provider",), ("renter", "provider")])
@pytest.mark.parametrize("ups, compliant", [(4, True), (2, False)])
def test_X_4_objection_does_not_change_payee_or_amount(escrow, propose, objection, finalize, actor, renter, provider, objectors, ups, compliant):
    rid, proposed_at = propose(ups)
    warp_to(proposed_at + CHALLENGE_WINDOW - 1)  # as late as an objection can be
    for who in objectors:
        objection(rid, actor(who))
    warp_to(proposed_at + CHALLENGE_WINDOW)  # the window is not extended by an objection
    finalize(rid)
    ev = last_event(escrow, "SettlementFinalized")
    payee, loser = (provider, renter) if compliant else (renter, provider)
    assert (ev.payee, ev.amount) == (payee, PRICE)
    assert escrow.credits(payee) == PRICE
    assert escrow.credits(loser) == 0
    r = escrow.rentals(rid)
    assert (r.status, r.compliant) == (3, compliant)
    assert (r.renter_objected, r.provider_objected) == ("renter" in objectors, "provider" in objectors)
