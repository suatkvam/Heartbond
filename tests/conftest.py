import boa
import pytest

INTERVAL = 30
N_SLOTS = 4
THRESHOLD = 75
PRICE = 10**16  # 0.01 MON


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
            rid = escrow.create_rental(provider, threshold, interval, start, end, b"\x00" * 32, value=price)
        return rid, start, end
    return _make
