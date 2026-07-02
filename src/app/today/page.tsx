'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRefresh } from '@/lib/refresh-context'
import type { TodayView } from '@/types/database'

const PRIORITY_CLS: Record<string, string> = {
  urgent: 'text-red-600', high: 'text-orange-600',
  medium: 'text-yellow-600', low: 'text-gray-400',
}

export default function TodayPage() {
  const [entries, setEntries] = useState<TodayView[]>([])
  const [loading, setLoading] = useState(true)
  const { count } = useRefresh()

  useEffect(() => {
    supabase
      .from('today_view')
      .select('*')
      .then(({ data }) => {
        setEntries(data ?? [])
        setLoading(false)
      })
  }, [count]) // re-fetch when QuickCapture or コフ mutates entries

  if (loading) {
    return <p className="text-sm text-gray-400 py-8 text-center">読み込み中…</p>
  }

  if (entries.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-gray-400 text-sm">今日の予定はありません</p>
        <p className="text-gray-300 text-xs mt-1">due_at を設定すると表示されます</p>
      </div>
    )
  }

  return (
    <div className="space-y-3 pb-10">
      <p className="text-xs text-gray-400">{entries.length} 件 — 今日やること</p>
      {entries.map(entry => (
        <article
          key={entry.id}
          className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-orange-400 p-4 shadow-sm"
        >
          <div className="flex items-center justify-between mb-1">
            {entry.due_at && (
              <time className="text-xs text-orange-600">
                {new Date(entry.due_at).toLocaleDateString('ja-JP')}
              </time>
            )}
            {entry.priority && (
              <span className={`text-xs font-medium ml-auto ${PRIORITY_CLS[entry.priority]}`}>
                {entry.priority}
              </span>
            )}
          </div>
          <h3 className="text-sm font-medium text-gray-800">{entry.title}</h3>
          {entry.next_action && (
            <p className="text-xs text-green-700 mt-1">→ {entry.next_action}</p>
          )}
          {entry.area && (
            <p className="text-xs text-gray-400 mt-1">{entry.area}</p>
          )}
        </article>
      ))}
    </div>
  )
}
