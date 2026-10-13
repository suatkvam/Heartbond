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
          {isPending ? 'Bağlanıyor…' : 'Cüzdan bağla (MetaMask)'}
        </button>
        {error && <span className="err">{error.message.split('\n')[0]}</span>}
      </div>
    )
  return (
    <div className="wallet">
      {chainId !== monad.id ? (
        <button className="warn" disabled={switching} onClick={() => switchChain({ chainId: monad.id })}>
          {switching ? 'Geçiliyor…' : "Yanlış ağ — Monad Testnet'e geç"}
        </button>
      ) : (
        <span className="pill ok">Monad Testnet</span>
      )}
      <a href={addrUrl(address!)} target="_blank" rel="noreferrer" className="mono">{short(address)}</a>
      <span className="mono">{balance ? `${Number(formatEther(balance.value)).toFixed(4)} MON` : '… MON'}</span>
      <button onClick={() => disconnect()}>Çık</button>
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
          <a href="#/" className={!route ? 'active' : ''}>Kiralamalar</a>
          <a href="#/create" className={route === 'create' ? 'active' : ''}>Kiralama oluştur</a>
          <a href="#/withdraw" className={route === 'withdraw' ? 'active' : ''}>Withdraw</a>
        </nav>
        <Wallet />
      </header>

      {MOCK && (
        <div className="banner">
          Mock veri: kontrat henüz deploy edilmedi (<code>shared/deployments/monad-testnet.json</code> içinde <code>address: null</code>).
          Ekranlar örnek veriyle çalışıyor, işlem gönderilmez.
        </div>
      )}

      <main>{screen}</main>

      <footer>
        <p>
          Uptime verisi ekibin çalıştırdığı reporter anahtarlarından gelir: tek bir güven kaynağı var, bağımsız doğrulama yok.
          Settle ve finalize'ı herhangi bir cüzdan tetikleyebilir. İtirazlar yalnızca kayda geçer (objection log), sonucu değiştirmez.
          Testnet MON — gerçek değeri yoktur.
        </p>
        {ADDRESS && (
          <p>
            Kontrat: <a href={addrUrl(ADDRESS)} target="_blank" rel="noreferrer" className="mono">{ADDRESS}</a>
          </p>
        )}
      </footer>
    </div>
  )
}
