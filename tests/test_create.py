"""C-rules. Red until create_rental is implemented — that is your first task."""
import boa


def test_C_1_10_happy_path(escrow, make_rental, renter, provider):
    rid, start, end = make_rental()
    assert rid == 1
    r = escrow.rentals(rid)
    assert (r.renter, r.provider, r.n_slots, r.status) == (renter, provider, 4, 1)
    assert boa.env.get_balance(escrow.address) == 10**16
    assert escrow.phase(rid) == 1  # Scheduled


def test_C_1_4_duration_not_multiple_reverts(escrow, renter, provider):
    start = boa.env.evm.patch.timestamp + 15
    with boa.env.prank(renter), boa.reverts("not multiple"):
        escrow.create_rental(provider, 75, 30, start, start + 100, b"\x00" * 32, value=1)


def test_C_1_7_renter_is_provider_reverts(escrow, renter):
    start = boa.env.evm.patch.timestamp + 15
    with boa.env.prank(renter), boa.reverts("renter is provider"):
        escrow.create_rental(renter, 75, 30, start, start + 120, b"\x00" * 32, value=1)

# TODO(test-engineer): C-1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 1.9
