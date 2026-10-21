'use client'

import AuthGate from '@/components/AuthGate'
import NavTabs from '@/components/NavTabs'
import QuickCapture from '@/components/QuickCapture'
import { RefreshProvider } from '@/lib/refresh-context'
import { supabase } from '@/lib/supabase'

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <RefreshProvider>
        <div className="max-w-2xl mx-auto px-4">
          <header className="py-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <h1 className="text-xl font-bold text-gray-800">KofPro</h1>
              <button
                onClick={() => supabase.auth.signOut()}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                ログアウト
              </button>
            </div>
            <NavTabs />
          </header>
          <div className="py-4">
            <QuickCapture />
          </div>
          <main>{children}</main>
        </div>
      </RefreshProvider>
    </AuthGate>
  )
}
