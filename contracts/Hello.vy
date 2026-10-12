# pragma version ~=0.4.3
"""@notice Day-0 smoke test: proves Vyper compiles, deploys, emits events and is verifiable on Monad Testnet."""

event Greeted:
    who: indexed(address)
    count: uint256

greetings: public(uint256)

@external
def greet():
    self.greetings += 1
    log Greeted(who=msg.sender, count=self.greetings)
