'use client'

import { useState } from 'react'
import type { InboxView, TriageStatus } from '@/types/database'
import { supabase } from '@/lib/supabase'
import NextActionModal from './NextActionModal'

interface Props {
  entry: InboxView
  onTriaged: (id: string) => void
}

const KIND_LABELS: Record<string, string> = {
  task: 'タスク', idea: 'アイデア', log: 'ログ',
  note: 'ノート', decision: '決定', event: 'イベント',
}

const PRIORITY_CLS: Record<string, string> = {
  urgent: 'bg-red-100 text-red-700',
  high:   'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low:    'bg-gray-100 text-gray-500',
}

const EFFORT_LABELS: Record<string, string> = {
  quick: '15分', short: '1時間', deep: 'じっくり',
}

export default function TriageCard({ entry, onTriaged }: Props) {
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState(false)

  async function applyStatus(status: TriageStatus, nextAction?: string) {
    setLoading(true)
    await supabase
      .from('entries')
      .update(nextAction !== undefined
        ? { status, next_action: nextAction || null }
        : { status },
      )
      .eq('id', entry.id)
    onTriaged(entry.id)
    // loading reset not needed — card unmounts after onTriaged
  }

  async function handleAdoptConfirm(nextAction: string) {
    setShowModal(false)
    await applyStatus('adopted', nextAction)
  }

  return (
    <>
      <article className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        {/* header row */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
              {KIND_LABELS[entry.kind] ?? entry.kind}
            </span>
            {entry.priority && (
              <span className={`text-xs px-2 py-0.5 rounded ${PRIORITY_CLS[entry.priority]}`}>
                {entry.priority}
              </span>
            )}
            {entry.effort && (
              <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded">
                {EFFORT_LABELS[entry.effort] ?? entry.effort}
              </span>
            )}
          </div>
          <time className="text-xs text-gray-400 whitespace-nowrap shrink-0">
            {new Date(entry.created_at).toLocaleDateString('ja-JP')}
          </time>
        </div>

        {/* title */}
        <h3 className="text-sm font-medium text-gray-800">{entry.title}</h3>

        {/* body preview */}
        {entry.body && (
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{entry.body}</p>
        )}

        {/* area / project */}
        {(entry.area || entry.project) && (
          <p className="text-xs text-gray-400 mt-1">
            {entry.area}{entry.project && ` / ${entry.project}`}
          </p>
        )}

        {/* source */}
        {entry.source !== 'manual' && (
          <p className="text-xs text-gray-300 mt-0.5">source: {entry.source}</p>
        )}

        {/* triage buttons */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => setShowModal(true)}
            disabled={loading}
            className="flex-1 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-40"
          >
            着手
          </button>
          <button
            onClick={() => applyStatus('declined')}
            disabled={loading}
            className="flex-1 py-1.5 text-xs bg-red-50 text-red-700 rounded hover:bg-red-100 disabled:opacity-40"
          >
            見送り
          </button>
          <button
            onClick={() => applyStatus('someday')}
            disabled={loading}
            className="flex-1 py-1.5 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-40"
          >
            保留
          </button>
        </div>
      </article>

      {showModal && (
        <NextActionModal
          entryTitle={entry.title}
          onConfirm={handleAdoptConfirm}
          onCancel={() => setShowModal(false)}
        />
      )}
    </>
  )
}
