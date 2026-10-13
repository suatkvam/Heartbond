"""C-rules (SPEC §3 C, revert strings §3 E).

Every revert test builds inputs that violate only the rule under test. The deliberate
exception is the `test_C_order_*` group at the end: each violates two rules at once to pin
the SPEC v1.2 check order (C-1.1..C-1.9, then C-1.11, then C-1.12; the earlier rule's
string is returned).
"""
import boa
import pytest

from conftest import CHALLENGE_WINDOW, INTERVAL, N_SLOTS, PRICE, REPORT_GRACE, SPEC_REF, THRESHOLD, last_event, now

ZERO = "0x" + "00" * 20


@pytest.fixture
def create(escrow, renter, provider):
    """create_rental with valid demo parameters; override any argument by keyword."""
    def _create(**kw):
        start = kw.get("start", now() + 15)
        end = kw.get("end", start + INTERVAL * N_SLOTS)
        with boa.env.prank(kw.get("sender", renter)):
            return escrow.create_rental(
                kw.get("provider", provider),
                kw.get("threshold", THRESHOLD),
                kw.get("interval", INTERVAL),
                start,
                end,
                kw.get("spec_ref", SPEC_REF),
                value=kw.get("value", PRICE),
            )
    return _create


def assert_nothing_created(escrow):
    assert escrow.next_rental_id() == 1
    assert escrow.rentals(1).status == 0
    assert boa.env.get_balance(escrow.address) == 0


# ------------------------------------------------------------------ C-1.1
def test_C_1_1_start_in_past_reverts(escrow, create):
    with boa.reverts("start in past"):
        create(start=now() - 1)
    assert_nothing_created(escrow)


def test_C_1_1_start_equal_to_now_accepted(escrow, create):
    start = now()
    rid = create(start=start)
    assert rid == 1
    assert escrow.rentals(rid).start == start
    assert escrow.phase(rid) == 2  # Running immediately


# ------------------------------------------------------------------ C-1.2
def test_C_1_2_end_equal_to_start_reverts(escrow, create):
    start = now() + 15
    with boa.reverts("end before start"):
        create(start=start, end=start)
    assert_nothing_created(escrow)


def test_C_1_2_end_before_start_reverts(escrow, create):
    start = now() + 150
    with boa.reverts("end before start"):
        create(start=start, end=start - INTERVAL)  # end still in the future
    assert_nothing_created(escrow)


# ------------------------------------------------------------------ C-1.3
def test_C_1_3_zero_interval_reverts(escrow, create):
    with boa.reverts("zero interval"):
        create(interval=0)
    assert_nothing_created(escrow)


# ------------------------------------------------------------------ C-1.4
def test_C_1_4_duration_not_multiple_reverts(escrow, renter, provider):
    start = boa.env.evm.patch.timestamp + 15
    with boa.env.prank(renter), boa.reverts("not multiple"):
        escrow.create_rental(provider, 75, 30, start, start + 100, b"\x00" * 32, value=1)


@pytest.mark.parametrize("off_by", [-1, 1])
def test_C_1_4_duration_off_by_one_second_reverts(escrow, create, off_by):
    start = now() + 15
    with boa.reverts("not multiple"):
        create(start=start, end=start + INTERVAL * N_SLOTS + off_by)
    assert_nothing_created(escrow)


def test_C_1_4_duration_shorter_than_interval_reverts(escrow, create):
    start = now() + 15
    with boa.reverts("not multiple"):
        create(start=start, end=start + INTERVAL - 1)


# ------------------------------------------------------------------ C-1.5
@pytest.mark.parametrize("threshold", [0, 101])
def test_C_1_5_threshold_out_of_range_reverts(escrow, create, threshold):
    with boa.reverts("bad threshold"):
        create(threshold=threshold)
    assert_nothing_created(escrow)


@pytest.mark.parametrize("threshold", [1, 100])
def test_C_1_5_threshold_boundary_accepted(escrow, create, threshold):
    rid = create(threshold=threshold)
    assert escrow.rentals(rid).threshold == threshold


# ------------------------------------------------------------------ C-1.6
def test_C_1_6_zero_provider_reverts(escrow, create):
    with boa.reverts("zero provider"):
        create(provider=ZERO)
    assert_nothing_created(escrow)


# ------------------------------------------------------------------ C-1.7
def test_C_1_7_renter_is_provider_reverts(escrow, renter):
    start = boa.env.evm.patch.timestamp + 15
    with boa.env.prank(renter), boa.reverts("renter is provider"):
        escrow.create_rental(renter, 75, 30, start, start + 120, b"\x00" * 32, value=1)


# ------------------------------------------------------------------ C-1.8
def test_C_1_8_no_value_reverts(escrow, create):
    with boa.reverts("no value"):
        create(value=0)
    assert_nothing_created(escrow)


def test_C_1_8_price_is_msg_value(escrow, create):
    assert escrow.rentals(create(value=1)).price == 1  # 1 wei is enough
    assert escrow.rentals(create(value=3 * 10**18)).price == 3 * 10**18


# ------------------------------------------------------------------ C-1.9
def test_C_1_9_max_slots_256_accepted(escrow, create):
    start = now() + 15
    rid = create(interval=1, start=start, end=start + 256)
    assert escrow.rentals(rid).n_slots == 256
    assert escrow.get_slots(rid) == [0] * 256


def test_C_1_9_257_slots_reverts(escrow, create):
    start = now() + 15
    with boa.reverts("too many slots"):
        create(interval=1, start=start, end=start + 257)
    assert_nothing_created(escrow)


def test_C_1_9_n_slots_is_duration_over_interval(escrow, create):
    start = now() + 15
    rid = create(interval=7, start=start, end=start + 7 * 13)
    assert escrow.rentals(rid).n_slots == 13
    assert escrow.get_slots(rid) == [0] * 13


# ----------------------------------------------------------------- C-1.10
def test_C_1_10_happy_path(escrow, make_rental, renter, provider):
    rid, start, end = make_rental()
    assert rid == 1
    r = escrow.rentals(rid)
    assert (r.renter, r.provider, r.n_slots, r.status) == (renter, provider, 4, 1)
    assert boa.env.get_balance(escrow.address) == 10**16
    assert escrow.phase(rid) == 1  # Scheduled


def test_C_1_10_ids_increment_from_one(escrow, create):
    assert escrow.next_rental_id() == 1
    for expected in (1, 2, 3):
        assert create() == expected
        assert escrow.next_rental_id() == expected + 1
        assert escrow.rentals(expected).status == 1  # Active
    assert escrow.rentals(4).status == 0  # not created yet


def test_C_1_10_all_fields_stored(escrow, create, renter, provider):
    start = now() + 15
    end = start + 20 * 6
    spec_ref = bytes(range(32))
    rid = create(threshold=90, interval=20, start=start, end=end, spec_ref=spec_ref, value=12345)
    r = escrow.rentals(rid)
    assert r.renter == renter
    assert r.provider == provider
    assert r.price == 12345
    assert r.threshold == 90
    assert r.interval == 20
    assert r.start == start
    assert r.end == end
    assert r.n_slots == 6
    assert r.up_count == 0
    assert r.reported_count == 0
    assert r.status == 1  # Active
    assert r.proposed_at == 0
    assert r.compliant is False
    assert r.renter_objected is False
    assert r.provider_objected is False
    assert r.spec_ref == spec_ref
    assert escrow.get_slots(rid) == [0] * 6


def test_C_1_10_balance_grows_by_exactly_msg_value(escrow, create, renter):
    renter_before = boa.env.get_balance(renter)
    create(value=PRICE)
    assert boa.env.get_balance(escrow.address) == PRICE
    create(value=7)
    assert boa.env.get_balance(escrow.address) == PRICE + 7
    assert renter_before - boa.env.get_balance(renter) == PRICE + 7
    assert escrow.credits(renter) == 0  # creation credits nobody


def test_C_1_10_rental_created_event(escrow, create, renter, provider):
    start = now() + 15
    end = start + INTERVAL * N_SLOTS
    spec_ref = b"\xab" * 32
    create()  # so the asserted id is not the default 1
    rid = create(start=start, end=end, spec_ref=spec_ref, value=PRICE)
    ev = last_event(escrow, "RentalCreated")
    assert rid == 2
    assert ev.rental_id == 2
    assert ev.renter == renter
    assert ev.provider == provider
    assert ev.price == PRICE
    assert ev.threshold == THRESHOLD
    assert ev.interval == INTERVAL
    assert ev.start == start
    assert ev.end == end
    assert ev.n_slots == N_SLOTS
    assert ev.spec_ref == spec_ref


def test_C_1_10_different_renters_get_their_own_rental(escrow, create, renter, provider, stranger):
    boa.env.set_balance(stranger, 10**18)
    a = create()
    b = create(sender=stranger, provider=renter, value=5)  # roles are per rental
    assert (a, b) == (1, 2)
    assert (escrow.rentals(a).renter, escrow.rentals(a).provider) == (renter, provider)
    assert (escrow.rentals(b).renter, escrow.rentals(b).provider) == (stranger, renter)
    assert boa.env.get_balance(escrow.address) == PRICE + 5


# ----------------------------------------------------------------- C-1.11
MAX_START_DELAY = 30 * 86400  # SPEC §2
MAX_INTERVAL = 86400  # SPEC §2


def test_C_1_11_start_exactly_30_days_ahead_accepted(escrow, create):
    start = now() + MAX_START_DELAY
    rid = create(start=start)
    assert escrow.rentals(rid).start == start
    assert escrow.phase(rid) == 1  # Scheduled


def test_C_1_11_start_30_days_plus_one_second_reverts(escrow, create):
    with boa.reverts("start too far"):
        create(start=now() + MAX_START_DELAY + 1)
    assert_nothing_created(escrow)


def test_C_1_11_huge_start_reverts_with_string_not_panic(escrow, create):
    # end = start + 120 (default): end > start, valid multiple, 4 slots, interval 30.
    with boa.reverts("start too far"):
        create(start=2**255)
    assert_nothing_created(escrow)


# ----------------------------------------------------------------- C-1.12
@pytest.mark.parametrize("n", [1, 256])
def test_C_1_12_interval_one_day_accepted(escrow, create, n):
    start = now() + 15
    rid = create(interval=MAX_INTERVAL, start=start, end=start + MAX_INTERVAL * n)
    r = escrow.rentals(rid)
    assert (r.interval, r.n_slots) == (MAX_INTERVAL, n)


@pytest.mark.parametrize("n", [1, 256])
def test_C_1_12_interval_one_day_plus_one_second_reverts(escrow, create, n):
    start = now() + 15
    with boa.reverts("interval too long"):
        create(interval=MAX_INTERVAL + 1, start=start, end=start + (MAX_INTERVAL + 1) * n)
    assert_nothing_created(escrow)


def test_C_1_12_end_max_uint_one_slot_reverts_with_string_not_panic(escrow, create):
    # The input from the 2026-10-13 security review: start = now, end = 2**256 - 1, one slot.
    # n_slots == 1 and start == now, so C-1.12 is the only rule violated.
    start, end = now(), 2**256 - 1
    with boa.reverts("interval too long"):
        create(interval=end - start, start=start, end=end, value=1)
    assert_nothing_created(escrow)


# ------------------------------------------- C-1.9 + C-1.11 + C-1.12 maxima
def test_C_1_12_max_size_rental_settles_and_refunds_without_overflow(escrow, create, report, renter, provider, stranger):
    # Largest rental the C rules allow: start 30 days ahead, 256 one-day slots.
    start = now() + MAX_START_DELAY
    end = start + MAX_INTERVAL * 256
    paid_before = boa.env.get_balance(renter)
    rid = create(interval=MAX_INTERVAL, start=start, end=end)
    assert escrow.rentals(rid).n_slots == 256
    assert escrow.phase(rid) == 1  # Scheduled
    assert escrow.get_slots(rid) == [0] * 256
    assert escrow.payout_preview(rid) == (False, renter, PRICE)

    # O-5 at its largest values: slot 255 completes at start + 256 * 86400 == end.
    boa.env.time_travel(seconds=end - 1 - now())
    with boa.reverts("slot not done"):
        report(rid, 255, True)
    boa.env.time_travel(seconds=1)
    assert now() == end
    report(rid, 255, True)
    slots = [0] * 255 + [1]
    assert escrow.get_slots(rid) == slots
    r = escrow.rentals(rid)
    assert (r.up_count, r.reported_count) == (1, 1)
    # One Up slot of 256 at threshold 75: 100 * 1 < 75 * 256, so still non-compliant and
    # the renter stays the payee. The refund path below is unchanged by the report.
    assert escrow.payout_preview(rid) == (False, renter, PRICE)

    boa.env.time_travel(seconds=REPORT_GRACE + 1)
    assert escrow.phase(rid) == 4  # Settleable
    assert escrow.get_slots(rid) == slots
    with boa.env.prank(stranger):
        escrow.settle(rid)
    ev = last_event(escrow, "SettlementProposed")
    assert (ev.up_count, ev.n_slots, ev.compliant, ev.payee, ev.amount) == (1, 256, False, renter, PRICE)
    assert escrow.payout_preview(rid) == (False, renter, PRICE)

    # The escrow is not locked: the renter gets the whole price back.
    boa.env.time_travel(seconds=CHALLENGE_WINDOW)
    with boa.env.prank(stranger):
        escrow.finalize(rid)
    with boa.env.prank(renter):
        escrow.withdraw()
    assert boa.env.get_balance(renter) == paid_before
    assert boa.env.get_balance(escrow.address) == 0


# ------------------------------------------------- check order (SPEC v1.2 §3 C)
# Double violations on purpose: the rule that comes first in the SPEC order wins.
def test_C_order_too_many_slots_wins_over_start_too_far(escrow, create):
    start = now() + MAX_START_DELAY + 1  # C-1.11 violated
    with boa.reverts("too many slots"):
        create(interval=1, start=start, end=start + 257)  # C-1.9 violated
    assert_nothing_created(escrow)


def test_C_order_too_many_slots_wins_over_interval_too_long(escrow, create):
    start = now() + 15  # within 30 days
    interval = MAX_INTERVAL + 1  # C-1.12 violated
    with boa.reverts("too many slots"):
        create(interval=interval, start=start, end=start + 257 * interval)  # C-1.9 violated
    assert_nothing_created(escrow)


@pytest.mark.parametrize("n", [1, 256])
def test_C_order_start_too_far_wins_over_interval_too_long(escrow, create, n):
    start = now() + MAX_START_DELAY + 1  # C-1.11 violated
    interval = MAX_INTERVAL + 1  # C-1.12 violated, n_slots <= 256
    with boa.reverts("start too far"):
        create(interval=interval, start=start, end=start + n * interval)
    assert_nothing_created(escrow)


def test_C_order_end_before_start_wins_over_zero_interval(escrow, create):
    start = now() + 15
    with boa.reverts("end before start"):
        create(interval=0, start=start, end=start)  # C-1.2 and C-1.3 violated
    assert_nothing_created(escrow)


def test_C_order_start_in_past_wins_over_bad_threshold(escrow, create):
    with boa.reverts("start in past"):
        create(start=now() - 1, threshold=0)  # C-1.1 and C-1.5 violated
    assert_nothing_created(escrow)
