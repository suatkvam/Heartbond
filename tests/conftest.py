from pathlib import Path

import boa
import pytest

INTERVAL = 30
N_SLOTS = 4
THRESHOLD = 75
PRICE = 10**16  # 0.01 MON
REPORT_GRACE = 30  # SPEC §2
CHALLENGE_WINDOW = 60  # SPEC §2
SPEC_REF = b"\x00" * 32
HELPERS = Path(__file__).parent / "helpers"  # test-only payee contracts


def now():
    return boa.env.evm.patch.timestamp


def warp_to(ts):
    """Move block.timestamp forward to exactly `ts`."""
    delta = ts - now()
    assert delta >= 0, "cannot travel back in time"
    if delta:
        boa.env.time_travel(seconds=delta)
    assert now() == ts


def last_event(contract, name):
    """The single event called `name` emitted by the most recent call."""
    found = [e for e in contract.get_logs() if type(e).__name__ == name]
    assert len(found) == 1, f"expected exactly one {name}, got {found}"
    return found[0]


@pytest.fixture
def reporters():
    return [boa.env.generate_address("reporter1"), boa.env.generate_address("reporter2")]


@pytest.fixture
def renter():
    a = boa.env.generate_address("renter")
    boa.env.set_balance(a, 100 * 10**18)
    return a


@pytest.fixture
def provider():
    return boa.env.generate_address("provider")


@pytest.fixture
def stranger():
    return boa.env.generate_address("stranger")


@pytest.fixture
def escrow(reporters):
    return boa.load("contracts/GpuSlaEscrow.vy", reporters)


@pytest.fixture
def make_rental(escrow, renter, provider):
    """Creates a demo-parameter rental starting 15 s from now; returns (id, start, end)."""
    def _make(threshold=THRESHOLD, interval=INTERVAL, n=N_SLOTS, price=PRICE, delay=15):
        start = boa.env.evm.patch.timestamp + delay
        end = start + interval * n
        with boa.env.prank(renter):
            rid = escrow.create_rental(provider, threshold, interval, start, end, SPEC_REF, value=price)
        return rid, start, end
    return _make


@pytest.fixture
def report(escrow, reporters):
    """report(rental_id, slot, up, by=reporters[0]) -> report_uptime from that caller."""
    def _report(rid, slot, up, by=None):
        with boa.env.prank(by or reporters[0]):
            escrow.report_uptime(rid, slot, up)
    return _report


# ------------------------------------------------- settle / objection / payout
@pytest.fixture
def actor(renter, provider, stranger, reporters):
    """actor("renter" | "provider" | "stranger" | "reporter") -> address, for parametrized callers."""
    return {"renter": renter, "provider": provider, "stranger": stranger, "reporter": reporters[0]}.__getitem__


@pytest.fixture
def settle(escrow, stranger):
    """settle(rental_id, by=stranger): a third wallet unless told otherwise."""
    def _settle(rid, by=None):
        with boa.env.prank(by or stranger):
            escrow.settle(rid)
    return _settle


@pytest.fixture
def objection(escrow):
    def _objection(rid, by):
        with boa.env.prank(by):
            escrow.raise_objection(rid)
    return _objection


@pytest.fixture
def finalize(escrow, stranger):
    """finalize(rental_id, by=stranger): a third wallet unless told otherwise."""
    def _finalize(rid, by=None):
        with boa.env.prank(by or stranger):
            escrow.finalize(rid)
    return _finalize


@pytest.fixture
def withdraw(escrow):
    def _withdraw(by):
        with boa.env.prank(by):
            escrow.withdraw()
    return _withdraw


@pytest.fixture
def propose(escrow, make_rental, report, settle):
    """New rental, first `ups` slots reported Up and the rest Down, settled one second
    after the grace period. Returns (rental_id, proposed_at). The last call is settle()."""
    def _propose(ups=N_SLOTS, by=None, **rental):
        rid, _, end = make_rental(**rental)
        warp_to(end)  # every slot completed, reporting open
        for k in range(rental.get("n", N_SLOTS)):
            report(rid, k, k < ups)
        warp_to(end + REPORT_GRACE + 1)
        settle(rid, by)
        return rid, now()
    return _propose


@pytest.fixture
def finalized(propose, finalize):
    """propose(...) then finalize at the first allowed second. Returns rental_id."""
    def _finalized(ups=N_SLOTS, **rental):
        rid, proposed_at = propose(ups, **rental)
        warp_to(proposed_at + CHALLENGE_WINDOW)
        finalize(rid)
        return rid
    return _finalized
