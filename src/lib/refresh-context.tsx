'use client'

import { createContext, useContext, useState, useCallback } from 'react'

interface RefreshCtx {
  count: number
  trigger: () => void
}

const RefreshContext = createContext<RefreshCtx>({ count: 0, trigger: () => {} })

export function RefreshProvider({ children }: { children: React.ReactNode }) {
  const [count, setCount] = useState(0)
  const trigger = useCallback(() => setCount(c => c + 1), [])
  return (
    <RefreshContext.Provider value={{ count, trigger }}>
      {children}
    </RefreshContext.Provider>
  )
}

export function useRefresh() {
  return useContext(RefreshContext)
}
