'use client'

import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

interface RefreshCtx {
  count: number
  trigger: () => void
}

const RefreshContext = createContext<RefreshCtx>({ count: 0, trigger: () => {} })

// Cross-window channel: the floating コフ window and the main window are
// separate BrowserWindows on the same origin. When one mutates data, it
// broadcasts so task lists in the other window re-fetch too.
const CHANNEL = 'kofpro-refresh'

export function RefreshProvider({ children }: { children: React.ReactNode }) {
  const [count, setCount] = useState(0)
  const bcRef = useRef<BroadcastChannel | null>(null)

  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return
    const bc = new BroadcastChannel(CHANNEL)
    bc.onmessage = () => setCount(c => c + 1)
    bcRef.current = bc
    return () => {
      bcRef.current = null
      bc.close()
    }
  }, [])

  const trigger = useCallback(() => {
    setCount(c => c + 1)
    bcRef.current?.postMessage('refresh')
  }, [])

  return (
    <RefreshContext.Provider value={{ count, trigger }}>
      {children}
    </RefreshContext.Provider>
  )
}

export function useRefresh() {
  return useContext(RefreshContext)
}
