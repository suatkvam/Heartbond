import { useEffect, useState } from 'react'
import { formatEther } from 'viem'
import { useAccount, useBalance, useConnect, useDisconnect, useSwitchChain } from 'wagmi'
import { ADDRESS, MOCK, addrUrl, monad } from './config'
import { short } from './lib/logic'
import { CreateScreen, DetailScreen, ListScreen, WithdrawScreen } from './screens'

function useHash() {
  const [hash, setHash] = useState(location.hash || '#/')
  useEffect(() => {
    const on = () => setHash(location.hash || '#/')
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return hash
}

/** Screen 1: connect an injected wallet (MetaMask) and switch / add Monad Testnet. */
function Wallet() {
  const { address, isConnected, chainId } = useAccount()
  const { connect, connectors, isPending, error } = useConnect()
  const { disconnect } = useDisconnect()
  const { switchChain, isPending: switching, error: switchError } = useSwitchChain()
  const { data: balance } = useBalance({ address, chainId: monad.id, query: { refetchInterval: 8000 } })

  if (!isConnected)
    return (
      <div className="wallet">
        <button className="primary" disabled={isPending} onClick={() => connect({ connector: connectors[0] })}>
          {isPending ? 'Connecting…' : 'Connect wallet (MetaMask)'}
        </button>
        {error && <span className="err">{error.message.split('\n')[0]}</span>}
      </div>
    )
  return (
    <div className="wallet">
      {chainId !== monad.id ? (
        <button className="warn" disabled={switching} onClick={() => switchChain({ chainId: monad.id })}>
          {switching ? 'Switching…' : 'Wrong network — switch to Monad Testnet'}
        </button>
      ) : (
        <span className="pill ok">Monad Testnet</span>
      )}
      <a href={addrUrl(address!)} target="_blank" rel="noreferrer" className="mono">{short(address)}</a>
      <span className="mono">{balance ? `${Number(formatEther(balance.value)).toFixed(4)} MON` : '… MON'}</span>
      <button onClick={() => disconnect()}>Disconnect</button>
      {switchError && <span className="err">{switchError.message.split('\n')[0]}</span>}
    </div>
  )
}

export function App() {
  const hash = useHash()
  const [, route, param] = hash.split('/')
  let screen = <ListScreen />
  if (route === 'create') screen = <CreateScreen />
  else if (route === 'withdraw') screen = <WithdrawScreen />
  else if (route === 'rental' && /^\d+$/.test(param ?? '')) screen = <DetailScreen id={BigInt(param)} />

  return (
    <div className="app">
      <header>
        <a className="brand" href="#/">GPU SLA Escrow</a>
        <nav>
          <a href="#/" className={!route || route === 'rental' ? 'active' : ''}>Rentals</a>
          <a href="#/create" className={route === 'create' ? 'active' : ''}>Create rental</a>
          <a href="#/withdraw" className={route === 'withdraw' ? 'active' : ''}>Withdraw</a>
        </nav>
        <Wallet />
      </header>

      {MOCK && (
        <div className="notice">
          Mock data: the contract is not deployed yet (<code>address: null</code> in <code>shared/deployments/monad-testnet.json</code>).
          The screens run on sample data and no transaction is sent.
        </div>
      )}

      <main>{screen}</main>

      <footer>
        <p>
          Uptime data comes from reporter keys run by the team: one source of trust, no independent verification.
          Any wallet can trigger settle and finalize. An objection is only a record (objection log) and never changes the payout.
          Testnet MON only — no real value.
        </p>
        {ADDRESS && (
          <p>
            Contract: <a href={addrUrl(ADDRESS)} target="_blank" rel="noreferrer" className="mono">{ADDRESS}</a>
          </p>
        )}
      </footer>
    </div>
  )
}
