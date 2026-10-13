# pragma version ~=0.4.3
"""
@title Test helper — a renter contract whose receive hook re-enters the escrow.
@dev   The hook runs exactly once, during the first MON transfer it receives. It
         1. records escrow.credits(self) as seen in the middle of the transfer,
         2. calls settle / finalize / raise_objection / create_rental on the rentals
            chosen with arm() (id 0 / value 0 = skip),
         3. calls escrow.withdraw() again.
       Every nested call swallows its failure and records it, so a correct escrow
       (SPEC P-2: credit zeroed before the send + @nonreentrant) still pays this
       contract its credit — and nothing more.
"""

interface Escrow:
    def create_rental(provider: address, threshold: uint256, interval: uint256, start: uint256, end: uint256, spec_ref: bytes32) -> uint256: payable
    def withdraw(): nonpayable
    def credits(account: address) -> uint256: view

escrow: public(address)
attempts: public(uint256)       # 1 once the receive hook has run
seen_credit: public(uint256)    # escrow.credits(self) as read inside the hook
reentry_ok: public(bool)        # True only if the nested withdraw() succeeded

# What the hook calls besides withdraw(); set with arm().
settle_id: uint256
finalize_id: uint256
object_id: uint256
create_provider: address
create_value: uint256
settle_ok: public(bool)
finalize_ok: public(bool)
object_ok: public(bool)
create_ok: public(bool)


@external
@payable
def create(escrow: address, provider: address, threshold: uint256, interval: uint256, start: uint256, end: uint256) -> uint256:
    """@notice Creates a rental with this contract as the renter, paying msg.value."""
    self.escrow = escrow
    return extcall Escrow(escrow).create_rental(provider, threshold, interval, start, end, empty(bytes32), value=msg.value)


@external
def arm(settle_id: uint256, finalize_id: uint256, object_id: uint256, create_provider: address, create_value: uint256):
    self.settle_id = settle_id
    self.finalize_id = finalize_id
    self.object_id = object_id
    self.create_provider = create_provider
    self.create_value = create_value


@external
def withdraw():
    extcall Escrow(self.escrow).withdraw()


@external
@payable
def __default__():
    if self.attempts != 0:
        return
    self.attempts = 1
    esc: address = self.escrow
    self.seen_credit = staticcall Escrow(esc).credits(self)
    if self.settle_id != 0:
        self.settle_ok = raw_call(esc, abi_encode(self.settle_id, method_id=method_id("settle(uint256)")), revert_on_failure=False)
    if self.finalize_id != 0:
        self.finalize_ok = raw_call(esc, abi_encode(self.finalize_id, method_id=method_id("finalize(uint256)")), revert_on_failure=False)
    if self.object_id != 0:
        self.object_ok = raw_call(esc, abi_encode(self.object_id, method_id=method_id("raise_objection(uint256)")), revert_on_failure=False)
    if self.create_value != 0:
        # One 30 s slot starting now, threshold 75, paid from the MON just received.
        self.create_ok = raw_call(
            esc,
            abi_encode(
                self.create_provider, convert(75, uint256), convert(30, uint256), block.timestamp, block.timestamp + 30, empty(bytes32),
                method_id=method_id("create_rental(address,uint256,uint256,uint256,uint256,bytes32)"),
            ),
            value=self.create_value,
            revert_on_failure=False,
        )
    self.reentry_ok = raw_call(esc, method_id("withdraw()"), revert_on_failure=False)
