'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRefresh } from '@/lib/refresh-context'
import type { InboxView } from '@/types/database'
import TriageCard from '@/components/TriageCard'

export default function TriagePage() {
  const [entries, setEntries] = useState<InboxView[]>([])
  const [loading, setLoading] = useState(true)
  const { count } = useRefresh()

  useEffect(() => {
    setLoading(true)
    supabase
      .from('inbox_view')
      .select('*')
      .then(({ data }) => {
        setEntries(data ?? [])
        setLoading(false)
      })
  }, [count]) // re-fetch when QuickCapture triggers a refresh

  function handleTriaged(id: string) {
    setEntries(prev => prev.filter(e => e.id !== id))
  }

  if (loading) {
    return <p className="text-sm text-gray-400 py-8 text-center">読み込み中…</p>
  }

  if (entries.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-gray-400 text-sm">Inbox は空です</p>
        <p className="text-gray-300 text-xs mt-1">クイックキャプチャで追加しましょう</p>
      </div>
    )
  }

  return (
    <div className="space-y-3 pb-10">
      <p className="text-xs text-gray-400">{entries.length} 件のトリアージ待ち</p>
      {entries.map(entry => (
        <TriageCard key={entry.id} entry={entry} onTriaged={handleTriaged} />
      ))}
    </div>
  )
}
