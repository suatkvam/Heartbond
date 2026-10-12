# pragma version ~=0.4.3
"""
@title  GpuSlaEscrow — INTERFACE SKELETON (v1.1)
@notice Escrow that pays a GPU provider or refunds a renter based on per-slot
        uptime reports from allow-listed reporter keys. Settlement is
        permissionless to trigger; finality is a fixed timeout.
@dev    This file freezes the PUBLIC INTERFACE (functions, events, storage,
        constants) so the frontend can be built against the ABI today.
        Bodies marked `TODO(<spec id>)` are yours to write — the spec id points
        at docs/SPEC.md. Do not rename/reorder public items without running the
        `interface-sync` agent (it regenerates shared/abi + docs/UI_HANDOFF.md).
"""

# ---------------------------------------------------------------- constants
MAX_SLOTS: constant(uint256) = 256          # SPEC C-1.9 (Vyper needs bounded loops)
MAX_REPORTERS: constant(uint256) = 8        # SPEC R-1

REPORT_GRACE: public(constant(uint256)) = 30       # seconds, SPEC T-2 (demo value)
CHALLENGE_WINDOW: public(constant(uint256)) = 60   # seconds, SPEC T-4 (demo value)

# Rental status (plain uint8 so the UI never has to decode Vyper flags)
STATUS_NONE: constant(uint8) = 0
STATUS_ACTIVE: constant(uint8) = 1
STATUS_PROPOSED: constant(uint8) = 2
STATUS_SETTLED: constant(uint8) = 3

# Slot values returned by get_slots()
SLOT_EMPTY: constant(uint8) = 0     # never reported -> counts as DOWN at settle
SLOT_UP: constant(uint8) = 1
SLOT_DOWN: constant(uint8) = 2

# UI phase values returned by phase() — derived from status + block.timestamp
PHASE_NONE: constant(uint8) = 0          # rental id does not exist
PHASE_SCHEDULED: constant(uint8) = 1     # now < start
PHASE_RUNNING: constant(uint8) = 2       # start <= now < end
PHASE_GRACE: constant(uint8) = 3         # end <= now <= end + REPORT_GRACE
PHASE_SETTLEABLE: constant(uint8) = 4    # Active and now > end + REPORT_GRACE
PHASE_CHALLENGE: constant(uint8) = 5     # Proposed and now < proposed_at + CHALLENGE_WINDOW
PHASE_FINALIZABLE: constant(uint8) = 6   # Proposed and window closed
PHASE_SETTLED: constant(uint8) = 7       # Settled

# ------------------------------------------------------------------ storage
struct Rental:
    renter: address
    provider: address
    price: uint256            # wei of native MON, == msg.value at creation
    threshold: uint256        # whole percent, 1..100
    interval: uint256         # seconds per slot
    start: uint256
    end: uint256
    n_slots: uint256          # (end - start) / interval, fixed at creation
    up_count: uint256         # slots reported UP (M)
    reported_count: uint256   # slots reported at all (UP or DOWN)
    status: uint8
    proposed_at: uint256      # block.timestamp of settle(), 0 before
    compliant: bool           # frozen at settle()
    renter_objected: bool
    provider_objected: bool
    spec_ref: bytes32         # off-chain GPU spec reference, not used by logic

rentals: public(HashMap[uint256, Rental])
next_rental_id: public(uint256)              # ids start at 1; 0 == "none"
is_reporter: public(HashMap[address, bool])  # fixed at deploy, SPEC R-1
credits: public(HashMap[address, uint256])   # pull-payment balances, SPEC P-1

# Per-rental slot storage. Kept separate from any global variable so reports
# for different rentals never touch the same storage slot (SPEC R-3).
_slots: HashMap[uint256, HashMap[uint256, uint8]]

# ------------------------------------------------------------------- events
event RentalCreated:
    rental_id: indexed(uint256)
    renter: indexed(address)
    provider: indexed(address)
    price: uint256
    threshold: uint256
    interval: uint256
    start: uint256
    end: uint256
    n_slots: uint256
    spec_ref: bytes32

event UptimeReported:
    rental_id: indexed(uint256)
    slot: uint256
    up: bool
    reporter: indexed(address)

event SettlementProposed:
    rental_id: indexed(uint256)
    up_count: uint256
    n_slots: uint256
    compliant: bool
    payee: indexed(address)
    amount: uint256
    proposed_at: uint256
    caller: address

event ObjectionRaised:
    rental_id: indexed(uint256)
    by: indexed(address)
    is_renter: bool

event SettlementFinalized:
    rental_id: indexed(uint256)
    payee: indexed(address)
    amount: uint256
    caller: address

event Withdrawn:
    account: indexed(address)
    amount: uint256


# -------------------------------------------------------------- constructor
@deploy
def __init__(reporters: DynArray[address, MAX_REPORTERS]):
    """
    @param reporters Allow-listed oracle reporter keys. All held by the team;
           several keys exist only so reports are sent from independent
           nonces (SPEC R-1, R-2). Not changeable after deploy.
    """
    assert len(reporters) > 0, "no reporters"
    for r: address in reporters:
        assert r != empty(address), "zero reporter"
        self.is_reporter[r] = True
    self.next_rental_id = 1


# ------------------------------------------------------------ state changes
@external
@payable
def create_rental(
    provider: address,
    threshold: uint256,
    interval: uint256,
    start: uint256,
    end: uint256,
    spec_ref: bytes32,
) -> uint256:
    """
    @notice Renter creates an agreement and escrows `msg.value` as the price.
    @return New rental id (>= 1).
    """
    # TODO(C-1.1 .. C-1.10): validate every rule, store Rental, emit RentalCreated
    raise "TODO C-1"


@external
def report_uptime(rental_id: uint256, slot: uint256, up: bool):
    """@notice Reporter-only. One report per completed slot, until end + REPORT_GRACE."""
    # TODO(O-1 .. O-6)
    raise "TODO O"


@external
def settle(rental_id: uint256):
    """@notice Anyone. Freezes M/N/compliance once now > end + REPORT_GRACE."""
    # TODO(S-1 .. S-5)
    raise "TODO S"


@external
def raise_objection(rental_id: uint256):
    """@notice Renter or provider of this rental, once each, inside the window. Event only."""
    # TODO(X-1 .. X-4)
    raise "TODO X"


@external
def finalize(rental_id: uint256):
    """@notice Anyone. After the window: credits the frozen payee (pull-payment)."""
    # TODO(F-1 .. F-4)
    raise "TODO F"


@external
@nonreentrant
def withdraw():
    """@notice Sends msg.sender's whole credit balance. Zero balance reverts."""
    # TODO(P-1 .. P-3)
    raise "TODO P"


# -------------------------------------------------------------- UI helpers
@view
@external
def get_slots(rental_id: uint256) -> DynArray[uint8, MAX_SLOTS]:
    """@notice Slot array of length n_slots: 0 empty, 1 up, 2 down."""
    n: uint256 = self.rentals[rental_id].n_slots
    out: DynArray[uint8, MAX_SLOTS] = []
    for k: uint256 in range(n, bound=MAX_SLOTS):
        out.append(self._slots[rental_id][k])
    return out


@view
@external
def phase(rental_id: uint256) -> uint8:
    """@notice Single number the UI can switch on to decide which buttons to show."""
    r: Rental = self.rentals[rental_id]
    if r.status == STATUS_NONE:
        return PHASE_NONE
    if r.status == STATUS_SETTLED:
        return PHASE_SETTLED
    if r.status == STATUS_PROPOSED:
        if block.timestamp < r.proposed_at + CHALLENGE_WINDOW:
            return PHASE_CHALLENGE
        return PHASE_FINALIZABLE
    # Active
    if block.timestamp < r.start:
        return PHASE_SCHEDULED
    if block.timestamp < r.end:
        return PHASE_RUNNING
    if block.timestamp <= r.end + REPORT_GRACE:
        return PHASE_GRACE
    return PHASE_SETTLEABLE


@view
@external
def payout_preview(rental_id: uint256) -> (bool, address, uint256):
    """
    @notice What settle() WOULD decide right now from the current report record
            (compliant, payee, amount). After settle() this equals the frozen result.
    """
    r: Rental = self.rentals[rental_id]
    ok: bool = 100 * r.up_count >= r.threshold * r.n_slots
    if r.status == STATUS_PROPOSED or r.status == STATUS_SETTLED:
        ok = r.compliant
    if ok:
        return True, r.provider, r.price
    return False, r.renter, r.price
