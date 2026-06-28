'use client'

import NavTabs from '@/components/NavTabs'
import QuickCapture from '@/components/QuickCapture'
import { RefreshProvider } from '@/lib/refresh-context'

export default function ClientLayout({ children }: { children: React.ReactNode }) {
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
    </RefreshProvider>
  )
}
