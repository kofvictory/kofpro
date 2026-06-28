'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { ActiveView } from '@/types/database'

const KIND_LABELS: Record<string, string> = {
  task: 'タスク', idea: 'アイデア', log: 'ログ',
  note: 'ノート', decision: '決定', event: 'イベント',
}

const PRIORITY_CLS: Record<string, string> = {
  urgent: 'text-red-600', high: 'text-orange-600',
  medium: 'text-yellow-600', low: 'text-gray-400',
}

export default function ActivePage() {
  const [entries, setEntries] = useState<ActiveView[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase
      .from('active_view')
      .select('*')
      .then(({ data }) => {
        setEntries(data ?? [])
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <p className="text-sm text-gray-400 py-8 text-center">読み込み中…</p>
  }

  if (entries.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-gray-400 text-sm">着手中のエントリーはありません</p>
        <p className="text-gray-300 text-xs mt-1">Inbox からトリアージして着手しましょう</p>
      </div>
    )
  }

  return (
    <div className="space-y-3 pb-10">
      <p className="text-xs text-gray-400">{entries.length} 件 — 着手中</p>
      {entries.map(entry => (
        <article key={entry.id} className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-1.5">
              <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                {KIND_LABELS[entry.kind] ?? entry.kind}
              </span>
              {entry.priority && (
                <span className={`text-xs font-medium ${PRIORITY_CLS[entry.priority]}`}>
                  {entry.priority}
                </span>
              )}
            </div>
            {entry.due_at && (
              <time className="text-xs text-orange-600">
                期限: {new Date(entry.due_at).toLocaleDateString('ja-JP')}
              </time>
            )}
          </div>
          <h3 className="text-sm font-medium text-gray-800">{entry.title}</h3>
          {entry.next_action && (
            <p className="text-xs text-green-700 mt-1">→ {entry.next_action}</p>
          )}
          {(entry.area || entry.project) && (
            <p className="text-xs text-gray-400 mt-1">
              {entry.area}{entry.project && ` / ${entry.project}`}
            </p>
          )}
        </article>
      ))}
    </div>
  )
}
