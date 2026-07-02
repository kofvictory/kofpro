'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import NavTabs from '@/components/NavTabs'
import QuickCapture from '@/components/QuickCapture'
import DesktopAgent from '@/components/DesktopAgent'
import { RefreshProvider } from '@/lib/refresh-context'

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // In Electron, コフ lives in the dedicated floating window (/floating),
  // so the in-app avatar is hidden to avoid two コフ on screen at once.
  // In a plain browser (npm run dev) the in-app avatar still appears.
  const [showInAppAgent, setShowInAppAgent] = useState(false)
  useEffect(() => {
    setShowInAppAgent(!navigator.userAgent.includes('Electron'))
  }, [])

  // The floating window renders コフ alone — no app chrome. The window is
  // transparent, so the page background must be transparent too.
  const isFloating = pathname === '/floating'
  useEffect(() => {
    if (isFloating) document.documentElement.classList.add('floating')
    return () => document.documentElement.classList.remove('floating')
  }, [isFloating])

  if (isFloating) {
    return <RefreshProvider>{children}</RefreshProvider>
  }

  return (
    <RefreshProvider>
      <div className="max-w-2xl mx-auto px-4">
        <header className="py-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800 mb-3">KofPro</h1>
          <NavTabs />
        </header>
        <div className="py-4">
          <QuickCapture />
        </div>
        <main>{children}</main>
      </div>
      {showInAppAgent && <DesktopAgent />}
    </RefreshProvider>
  )
}
