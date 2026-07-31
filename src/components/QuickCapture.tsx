'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRefresh } from '@/lib/refresh-context'

export default function QuickCapture() {
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const { trigger } = useRefresh()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = title.trim()
    if (!trimmed) return
    setLoading(true)
    const { error } = await supabase.from('entries').insert({
      title: trimmed,
      source: 'manual',
      status: 'inbox',
      kind: 'idea',
    })
    setLoading(false)
    if (error) {
      // Surface failures (e.g. RLS denial) instead of silently clearing.
      alert(`追加に失敗しました: ${error.message}`)
      return
    }
    setTitle('')
    trigger()
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={title}
        onChange={e => setTitle(e.target.value)}
        placeholder="クイックキャプチャ — タイトルだけで inbox に追加"
        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !title.trim()}
        className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        追加
      </button>
    </form>
  )
}
