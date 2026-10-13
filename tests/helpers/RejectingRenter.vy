# pragma version ~=0.4.3
"""
@title Test helper — a renter contract that cannot receive MON.
@dev   No `__default__`, so any plain transfer to it reverts (SPEC P-3, §6
       "withdraw by a contract that rejects MON fails only for itself").
"""

interface Escrow:
    def create_rental(provider: address, threshold: uint256, interval: uint256, start: uint256, end: uint256, spec_ref: bytes32) -> uint256: payable
    def withdraw(): nonpayable

escrow: public(address)


@external
@payable
def create(escrow: address, provider: address, threshold: uint256, interval: uint256, start: uint256, end: uint256) -> uint256:
    """@notice Creates a rental with this contract as the renter, paying msg.value."""
    self.escrow = escrow
    return extcall Escrow(escrow).create_rental(provider, threshold, interval, start, end, empty(bytes32), value=msg.value)


@external
def withdraw():
    extcall Escrow(self.escrow).withdraw()
