'use client'

import { useState } from 'react'

interface Props {
  entryTitle: string
  onConfirm: (nextAction: string) => void
  onCancel: () => void
}

export default function NextActionModal({ entryTitle, onConfirm, onCancel }: Props) {
  const [nextAction, setNextAction] = useState('')

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Escape') onCancel()
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onConfirm(nextAction)
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={e => { if (e.target === e.currentTarget) onCancel() }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onKeyDown={handleKey}>
        <h2 className="text-base font-semibold text-gray-800 mb-1">着手 — 次のアクション</h2>
        <p className="text-sm text-gray-400 mb-4 truncate">{entryTitle}</p>
        <textarea
          value={nextAction}
          onChange={e => setNextAction(e.target.value)}
          placeholder="次に具体的にやること（例: 仕入れ先にメールする）"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
          rows={3}
          autoFocus
        />
        <p className="text-xs text-gray-400 mt-1">空のままでも着手できます。⌘Enter で確定。</p>
        <div className="flex gap-2 mt-4 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md"
          >
            キャンセル
          </button>
          <button
            onClick={() => onConfirm(nextAction)}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
          >
            着手する
          </button>
        </div>
      </div>
    </div>
  )
}
