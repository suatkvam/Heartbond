"""F-rules, P-rules and the finalize side of timing T-4 (SPEC §3). Red until settle(),
finalize() and withdraw() are implemented (T-004).

Every revert test violates only the rule under test: the rental is Proposed and
the challenge window has closed (F), or the caller holds a credit (P), unless stated.

Balances are compared directly: boa's gas price is 0, so a caller's balance
changes only by the MON it receives.
"""
import boa
import pytest

from conftest import CHALLENGE_WINDOW, HELPERS, INTERVAL, PRICE, REPORT_GRACE, THRESHOLD, last_event, now, warp_to

ACTORS = ["renter", "provider", "stranger", "reporter"]
RUNS = [(4, True), (2, False)]  # (slots Up of 4 at threshold 75, compliant)

balance = boa.env.get_balance


# -------------------------------------------------------------------- F-1
@pytest.mark.parametrize("where", ["running", "settleable", "long after"])
def test_F_1_active_rental_reverts(escrow, make_rental, finalize, renter, provider, where):
    rid, start, end = make_rental()
    warp_to({"running": start + INTERVAL, "settleable": end + REPORT_GRACE + 1, "long after": end + 10 * 24 * 3600}[where])
    with boa.reverts("not proposed"):
        finalize(rid)
    assert escrow.rentals(rid).status == 1
    assert escrow.credits(renter) == escrow.credits(provider) == 0


@pytest.mark.parametrize("rid", [0, 1, 99])
def test_F_1_nonexistent_rental_reverts(escrow, finalize, rid):
    with boa.reverts("not proposed"):
        finalize(rid)
    assert escrow.credits("0x" + "00" * 20) == 0


@pytest.mark.parametrize("ups, compliant", RUNS)
def test_F_1_double_finalize_reverts(escrow, finalized, finalize, renter, provider, ups, compliant):
    rid = finalized(ups)
    before = escrow.rentals(rid)
    with boa.reverts("not proposed"):
        finalize(rid)
    warp_to(now() + 1000)
    with boa.reverts("not proposed"):
        finalize(rid)
    assert escrow.rentals(rid) == before
    assert escrow.credits(provider if compliant else renter) == PRICE  # credited once


# ------------------------------------------------------------- F-2 / T-4
def test_F_2_finalize_one_second_before_window_end_reverts(escrow, propose, finalize, renter, provider):
    rid, proposed_at = propose(4)
    before = escrow.rentals(rid)
    warp_to(proposed_at + CHALLENGE_WINDOW - 1)
    with boa.reverts("window open"):
        finalize(rid)
    assert escrow.rentals(rid) == before  # still Proposed
    assert escrow.credits(renter) == escrow.credits(provider) == 0


def test_F_2_finalize_at_window_end_succeeds(escrow, propose, finalize, provider):
    rid, proposed_at = propose(4)
    warp_to(proposed_at + CHALLENGE_WINDOW)
    finalize(rid)
    assert escrow.rentals(rid).status == 3
    assert escrow.credits(provider) == PRICE


def test_F_2_finalize_in_same_second_as_settle_reverts(escrow, propose, finalize):
    rid, proposed_at = propose(4)
    assert now() == proposed_at
    with boa.reverts("window open"):
        finalize(rid)
    assert escrow.rentals(rid).status == 2


def test_F_2_finalize_long_after_window_succeeds(escrow, propose, finalize, provider):
    rid, proposed_at = propose(4)
    warp_to(proposed_at + 30 * 24 * 3600)
    finalize(rid)
    assert escrow.credits(provider) == PRICE


def test_F_2_window_counts_from_proposed_at_not_from_end(escrow, make_rental, settle, finalize, renter):
    rid, _, end = make_rental()
    late = end + 3600  # settled an hour late: finalize still waits the full window
    warp_to(late)
    settle(rid)
    warp_to(late + CHALLENGE_WINDOW - 1)
    with boa.reverts("window open"):
        finalize(rid)
    warp_to(late + CHALLENGE_WINDOW)
    finalize(rid)
    assert escrow.credits(renter) == PRICE  # no reports: refund


def test_T_4_objection_and_finalize_windows_never_overlap(escrow, propose, objection, finalize, renter, provider):
    rid, proposed_at = propose(4)
    warp_to(proposed_at + CHALLENGE_WINDOW - 1)  # last second of the window: objection ok, finalize not yet
    with boa.reverts("window open"):
        finalize(rid)
    objection(rid, renter)
    warp_to(proposed_at + CHALLENGE_WINDOW)  # first second after: objection closed, finalize ok
    with boa.reverts("window closed"):
        objection(rid, provider)
    finalize(rid)
    r = escrow.rentals(rid)
    assert (r.status, r.renter_objected, r.provider_objected) == (3, True, False)


# -------------------------------------------------------------------- F-3
@pytest.mark.parametrize("ups", [4, 2])
def test_F_3_status_becomes_settled_and_nothing_else_changes(escrow, propose, finalize, ups):
    rid, proposed_at = propose(ups)
    before, slots, preview = escrow.rentals(rid), escrow.get_slots(rid), escrow.payout_preview(rid)
    warp_to(proposed_at + CHALLENGE_WINDOW)
    finalize(rid)
    assert escrow.rentals(rid) == before._replace(status=3)  # proposed_at, compliant, flags untouched
    assert escrow.get_slots(rid) == slots
    assert escrow.payout_preview(rid) == preview
    assert escrow.phase(rid) == 7


def test_F_3_settled_rental_cannot_be_credited_again(escrow, finalized, finalize, settle, provider):
    # Settled is terminal: no path leads back to a second credit for the same rental.
    rid = finalized(4)
    for call, reason in ((finalize, "not proposed"), (settle, "not active")):
        with boa.reverts(reason):
            call(rid)
    assert escrow.credits(provider) == PRICE
    assert balance(escrow.address) == PRICE


# -------------------------------------------------------------------- F-4
@pytest.mark.parametrize("ups, compliant", RUNS)
def test_F_4_credits_payee_with_price(escrow, finalized, renter, provider, stranger, ups, compliant):
    finalized(ups)  # settle and finalize both sent by `stranger`
    payee, loser = (provider, renter) if compliant else (renter, provider)
    assert escrow.credits(payee) == PRICE
    assert escrow.credits(loser) == 0
    assert escrow.credits(stranger) == 0  # triggering earns nothing


@pytest.mark.parametrize("ups", [4, 2])
def test_F_4_finalize_transfers_nothing(escrow, propose, finalize, renter, provider, stranger, ups):
    rid, proposed_at = propose(ups)
    warp_to(proposed_at + CHALLENGE_WINDOW)
    wallets = (escrow.address, renter, provider, stranger)
    before = [balance(a) for a in wallets]
    finalize(rid)
    assert [balance(a) for a in wallets] == before  # pull payment: credit only
    assert balance(escrow.address) == PRICE


@pytest.mark.parametrize("ups, compliant", RUNS)
def test_F_4_settlement_finalized_event(escrow, make_rental, propose, finalize, renter, provider, stranger, ups, compliant):
    make_rental()  # so the event id is not the default
    rid, proposed_at = propose(ups)
    warp_to(proposed_at + CHALLENGE_WINDOW)
    finalize(rid)
    ev = last_event(escrow, "SettlementFinalized")  # before any view call
    assert rid == 2
    assert ev.rental_id == 2
    assert ev.payee == (provider if compliant else renter)
    assert ev.amount == PRICE
    assert ev.caller == stranger


@pytest.mark.parametrize("who", ACTORS)
def test_F_4_anyone_can_finalize(escrow, propose, finalize, actor, provider, who):
    rid, proposed_at = propose(4)
    warp_to(proposed_at + CHALLENGE_WINDOW)
    finalize(rid, by=actor(who))
    ev = last_event(escrow, "SettlementFinalized")
    assert (ev.payee, ev.amount, ev.caller) == (provider, PRICE, actor(who))
    assert escrow.credits(provider) == PRICE  # the payee is frozen, whoever calls


def test_F_4_credits_accumulate_over_two_rentals(escrow, finalized, withdraw, renter, provider):
    # F-4 is `+=`: the provider wins two rentals before withdrawing once.
    first, second = 3 * 10**15, 7 * 10**15
    finalized(4, price=first)
    assert escrow.credits(provider) == first
    finalized(4, price=second)
    assert escrow.credits(provider) == first + second
    assert escrow.credits(renter) == 0
    assert balance(escrow.address) == first + second

    had = balance(provider)
    withdraw(provider)
    assert last_event(escrow, "Withdrawn").amount == first + second
    assert balance(provider) == had + first + second
    assert escrow.credits(provider) == 0
    assert balance(escrow.address) == 0


def test_F_4_one_address_credited_as_provider_and_as_renter(escrow, finalized, renter, provider, withdraw):
    # `provider` wins rental 1; in rental 2 the roles are swapped and it is refunded as renter.
    boa.env.set_balance(provider, 10**18)
    finalized(4)
    start = now() + 15
    with boa.env.prank(provider):
        rid = escrow.create_rental(renter, THRESHOLD, INTERVAL, start, start + INTERVAL, b"\x00" * 32, value=2 * PRICE)
    warp_to(start + INTERVAL + REPORT_GRACE + 1)
    with boa.env.prank(renter):
        escrow.settle(rid)  # no reports: non-compliant, refund to the renter of rental 2
    warp_to(now() + CHALLENGE_WINDOW)
    with boa.env.prank(renter):
        escrow.finalize(rid)
    assert escrow.credits(provider) == 3 * PRICE
    assert escrow.credits(renter) == 0


# -------------------------------------------------------------------- P-1
def test_P_1_no_credit_reverts(escrow, withdraw, stranger):
    with boa.reverts("nothing to withdraw"):
        withdraw(stranger)


@pytest.mark.parametrize("ups, compliant", RUNS)
def test_P_1_losing_party_and_bystanders_have_nothing_to_withdraw(escrow, finalized, withdraw, actor, renter, provider, ups, compliant):
    finalized(ups)
    loser = renter if compliant else provider
    for who in (loser, actor("stranger"), actor("reporter")):
        with boa.reverts("nothing to withdraw"):
            withdraw(who)
    assert balance(escrow.address) == PRICE  # the payee's MON is still there


def test_P_1_payee_cannot_withdraw_before_finalize(escrow, propose, withdraw, provider):
    _, proposed_at = propose(4)
    with boa.reverts("nothing to withdraw"):
        withdraw(provider)  # Proposed: nothing credited yet
    warp_to(proposed_at + CHALLENGE_WINDOW)
    with boa.reverts("nothing to withdraw"):
        withdraw(provider)  # window over but nobody called finalize
    assert balance(escrow.address) == PRICE


@pytest.mark.parametrize("ups, compliant", RUNS)
def test_P_1_withdraw_sends_exactly_the_credit(escrow, finalized, withdraw, renter, provider, ups, compliant):
    finalized(ups)
    payee = provider if compliant else renter
    had = balance(payee)
    withdraw(payee)
    assert balance(payee) == had + PRICE
    assert balance(escrow.address) == 0  # dropped by exactly PRICE
    assert escrow.credits(payee) == 0


def test_P_1_withdraw_takes_only_the_callers_credit(escrow, finalized, withdraw, renter, provider):
    refund, payment = 4 * 10**15, 9 * 10**15
    finalized(2, price=refund)   # renter refunded
    finalized(4, price=payment)  # provider paid
    assert balance(escrow.address) == refund + payment
    had = balance(provider)
    withdraw(provider)
    assert balance(provider) == had + payment
    assert balance(escrow.address) == refund  # dropped by exactly the provider's credit
    assert escrow.credits(renter) == refund   # the renter's credit is untouched
    had = balance(renter)
    withdraw(renter)
    assert balance(renter) == had + refund
    assert balance(escrow.address) == 0


# -------------------------------------------------------------------- P-2
def test_P_2_credit_zeroed_and_second_withdraw_reverts(escrow, finalized, withdraw, provider):
    finalized(4)
    finalized(2)  # leaves the renter's PRICE in the escrow: a second payout would have MON to take
    withdraw(provider)
    assert escrow.credits(provider) == 0
    had = balance(provider)
    with boa.reverts("nothing to withdraw"):
        withdraw(provider)
    assert balance(provider) == had
    assert balance(escrow.address) == PRICE


def test_P_2_reentrant_payee_gains_nothing(escrow, make_rental, settle, finalize, withdraw, renter, provider):
    attacker = boa.load(str(HELPERS / "ReentrantRenter.vy"))
    honest, start, end = make_rental()  # same window; its PRICE is what a re-entry could steal
    with boa.env.prank(renter):
        rid = attacker.create(escrow.address, provider, THRESHOLD, INTERVAL, start, end, value=PRICE)
    assert escrow.rentals(rid).renter == attacker.address
    warp_to(end + REPORT_GRACE + 1)  # no reports: both rentals refund their renter
    settle(rid)
    settle(honest)
    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    finalize(honest)
    assert escrow.credits(attacker.address) == escrow.credits(renter) == PRICE
    assert balance(escrow.address) == 2 * PRICE
    assert balance(attacker.address) == 0

    try:
        attacker.withdraw()  # its receive hook calls escrow.withdraw() again
    except boa.BoaError:
        # Allowed outcome: the whole withdraw reverted. Then nothing moved at all.
        assert balance(attacker.address) == 0
        assert balance(escrow.address) == 2 * PRICE
        assert escrow.credits(attacker.address) == PRICE
    else:
        assert attacker.attempts() == 1  # the hook did try to re-enter
        assert attacker.reentry_ok() is False
        assert balance(attacker.address) == PRICE  # its credit, nothing more
        assert balance(escrow.address) == PRICE
        assert escrow.credits(attacker.address) == 0

    # The other payee's MON never left the escrow and is still withdrawable.
    assert escrow.credits(renter) == PRICE
    had = balance(renter)
    withdraw(renter)
    assert balance(renter) == had + PRICE


# P-2 names two defences. The tests below make each one observable on its own:
# "zero first" through what the payee can read during the transfer, the lock through a
# nested withdraw() that would otherwise be perfectly valid (a fresh, non-zero credit).
@pytest.fixture
def attacker(escrow, renter, provider):
    """ReentrantRenter plus attacker.rent(price) -> id of a one-slot rental it is the renter of.
    All its rentals share one window; nobody reports, so each one refunds the attacker."""
    a = boa.load(str(HELPERS / "ReentrantRenter.vy"))
    start = now() + 15
    a.end = start + INTERVAL

    def rent(price=PRICE):
        with boa.env.prank(renter):
            return a.create(escrow.address, provider, THRESHOLD, INTERVAL, start, a.end, value=price)
    a.rent = rent
    return a


def locked_plus_credits(escrow, *accounts):
    """What the escrow must hold: prices of Active/Proposed rentals + credits not yet withdrawn."""
    rentals = [escrow.rentals(i) for i in range(1, escrow.next_rental_id())]
    return sum(r.price for r in rentals if r.status in (1, 2)) + sum(escrow.credits(a) for a in accounts)


def test_P_2_credit_reads_zero_during_the_transfer(escrow, attacker, settle, finalize):
    # Zero-first (CEI): while the payee holds control its credit is already gone.
    rid = attacker.rent()
    warp_to(attacker.end + REPORT_GRACE + 1)
    settle(rid)
    warp_to(now() + CHALLENGE_WINDOW)
    finalize(rid)
    assert escrow.credits(attacker.address) == PRICE

    attacker.withdraw()
    assert attacker.attempts() == 1  # the hook ran
    assert attacker.seen_credit() == 0
    assert balance(attacker.address) == PRICE


def test_P_2_nested_withdraw_of_a_fresh_credit_is_locked_out(escrow, attacker, settle, finalize):
    # @nonreentrant: inside the hook the attacker finalizes a second rental that credits
    # it, so the nested withdraw() has a real credit to take. Zero-first alone would pay
    # it; only the lock makes it fail.
    first, second = attacker.rent(), attacker.rent(3 * PRICE)
    warp_to(attacker.end + REPORT_GRACE + 1)
    settle(first)
    settle(second)
    warp_to(now() + CHALLENGE_WINDOW)
    finalize(first)  # `second` stays Proposed with its window closed: finalizable by anyone
    attacker.arm(0, second, 0, "0x" + "00" * 20, 0)
    assert balance(escrow.address) == 4 * PRICE

    attacker.withdraw()
    assert attacker.attempts() == 1
    assert attacker.finalize_ok() is True, "precondition: the hook must obtain the second credit"
    assert escrow.rentals(second).status == 3
    assert attacker.reentry_ok() is False  # the lock
    assert balance(attacker.address) == PRICE
    assert balance(escrow.address) == 3 * PRICE
    assert escrow.credits(attacker.address) == 3 * PRICE  # the fresh credit survived the outer call

    attacker.withdraw()  # a later, separate call (the hook fires only once)
    assert balance(attacker.address) == 4 * PRICE
    assert balance(escrow.address) == 0
    assert escrow.credits(attacker.address) == 0


def test_P_2_cross_function_reentry_keeps_the_escrow_solvent(escrow, attacker, make_rental, settle, finalize, renter, provider, stranger):
    # During the transfer the hook calls settle, finalize, raise_objection and create_rental
    # on other rentals (none of them is locked: SPEC puts @nonreentrant on withdraw only),
    # then withdraw again. Afterwards every wei in the escrow is still accounted for.
    paid = attacker.rent(PRICE)              # finalized: the credit being withdrawn
    matured = attacker.rent(2 * PRICE)       # Proposed, window closed -> hook finalizes it
    objectable = attacker.rent(5 * PRICE)    # Proposed, window open   -> hook objects as its renter
    with boa.env.prank(renter):              # Active, settleable      -> hook settles it
        idle = escrow.create_rental(provider, THRESHOLD, INTERVAL, attacker.end - INTERVAL, attacker.end, b"\x00" * 32, value=3 * PRICE)
    warp_to(attacker.end + REPORT_GRACE + 1)
    settle(paid)
    settle(matured)
    warp_to(now() + CHALLENGE_WINDOW)
    finalize(paid)
    settle(objectable)
    fee = PRICE // 4                         # price of the rental the hook creates from the MON it receives
    attacker.arm(idle, matured, objectable, provider, fee)

    everyone = (attacker.address, renter, provider, stranger)
    wallets = (renter, provider, stranger)
    had = [balance(a) for a in wallets]
    assert balance(escrow.address) == 11 * PRICE == locked_plus_credits(escrow, *everyone)

    attacker.withdraw()
    created = escrow.next_rental_id() - 1
    assert [attacker.settle_ok(), attacker.finalize_ok(), attacker.object_ok(), attacker.create_ok()] == [True] * 4, \
        "precondition: the hook must really have re-entered these functions"
    assert escrow.rentals(idle).status == 2
    assert escrow.rentals(matured).status == 3
    assert escrow.rentals(objectable).renter_objected is True
    new = escrow.rentals(created)
    assert (created, new.renter, new.status, new.price) == (5, attacker.address, 1, fee)

    assert balance(escrow.address) == locked_plus_credits(escrow, *everyone)
    assert escrow.credits(attacker.address) == 2 * PRICE  # from `matured`, not yet withdrawn
    assert attacker.reentry_ok() is False
    assert balance(escrow.address) == 11 * PRICE - PRICE + fee  # out: the one credit; in: the new price
    assert balance(attacker.address) == PRICE - fee
    assert [balance(a) for a in wallets] == had


# -------------------------------------------------------------------- P-3
@pytest.mark.parametrize("ups, compliant", RUNS)
def test_P_3_withdrawn_event(escrow, finalized, withdraw, renter, provider, ups, compliant):
    finalized(ups, price=5 * 10**15)
    payee = provider if compliant else renter
    withdraw(payee)
    ev = last_event(escrow, "Withdrawn")  # before any view call
    assert ev.account == payee
    assert ev.amount == 5 * 10**15


def test_P_3_rejecting_payee_fails_only_its_own_withdraw(escrow, make_rental, settle, finalize, withdraw, renter, provider):
    rejecting = boa.load(str(HELPERS / "RejectingRenter.vy"))
    other, start, end = make_rental()  # a second rental with an ordinary renter, same window
    with boa.env.prank(renter):
        rid = rejecting.create(escrow.address, provider, THRESHOLD, INTERVAL, start, end, value=PRICE)
    assert escrow.rentals(rid).renter == rejecting.address
    warp_to(end + REPORT_GRACE + 1)  # no reports: both rentals refund their renter
    settle(rid)
    settle(other)
    warp_to(now() + CHALLENGE_WINDOW)

    finalize(rid)  # F-4 makes no external call, so a rejecting payee cannot block it
    ev = last_event(escrow, "SettlementFinalized")
    assert (ev.payee, ev.amount) == (rejecting.address, PRICE)
    finalize(other)
    assert escrow.rentals(rid).status == escrow.rentals(other).status == 3
    assert escrow.credits(rejecting.address) == escrow.credits(renter) == PRICE

    for _ in range(2):  # fails every time, and never loses the credit
        with boa.reverts("transfer failed"):
            rejecting.withdraw()
        assert escrow.credits(rejecting.address) == PRICE
        assert balance(escrow.address) == 2 * PRICE
        assert balance(rejecting.address) == 0

    had = balance(renter)
    withdraw(renter)  # nobody else's funds are blocked
    assert last_event(escrow, "Withdrawn").amount == PRICE
    assert balance(renter) == had + PRICE
    assert escrow.credits(renter) == 0
    assert balance(escrow.address) == PRICE  # exactly the rejecting payee's credit remains
    assert escrow.credits(rejecting.address) == PRICE
