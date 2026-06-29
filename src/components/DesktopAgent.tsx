'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRefresh } from '@/lib/refresh-context'

type AgentState = 'idle' | 'thinking' | 'talking'
type Message = { role: 'user' | 'assistant'; content: string }

function AvatarFace({ state, size = 60 }: { state: AgentState; size?: number }) {
  const squintY = state === 'thinking' ? 2 : 5
  return (
    <svg
      viewBox="0 0 60 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
    >
      {/* Antenna stem */}
      <line x1="30" y1="11" x2="30" y2="4" stroke="#a78bfa" strokeWidth="2.5" strokeLinecap="round" />
      {/* Antenna tip — pulses yellow while thinking */}
      <circle
        cx="30"
        cy="3"
        r="3"
        fill={state === 'thinking' ? '#fbbf24' : '#a78bfa'}
        style={state === 'thinking' ? { animation: 'pulse 1s ease-in-out infinite' } : undefined}
      />

      {/* Head */}
      <circle cx="30" cy="36" r="22" fill="url(#headGrad)" />

      {/* Left eye */}
      <ellipse cx="22" cy="34" rx="5" ry={squintY} fill="white" />
      <circle cx="23" cy="34" r="2.5" fill="#312e81" />
      <circle cx="23.8" cy="33" r="1" fill="white" />

      {/* Right eye */}
      <ellipse cx="38" cy="34" rx="5" ry={squintY} fill="white" />
      <circle cx="39" cy="34" r="2.5" fill="#312e81" />
      <circle cx="39.8" cy="33" r="1" fill="white" />

      {/* Mouth */}
      {state === 'talking' ? (
        <ellipse cx="30" cy="43" rx="5.5" ry="3.5" fill="#1e1b4b" opacity="0.65" />
      ) : (
        <path
          d="M 24 42 Q 30 47 36 42"
          stroke="#1e1b4b"
          strokeWidth="1.8"
          strokeLinecap="round"
          fill="none"
          opacity="0.65"
        />
      )}

      {/* Cheeks */}
      <circle cx="13" cy="40" r="5" fill="#f9a8d4" opacity="0.35" />
      <circle cx="47" cy="40" r="5" fill="#f9a8d4" opacity="0.35" />

      <defs>
        <radialGradient id="headGrad" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#ddd6fe" />
          <stop offset="55%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#5b21b6" />
        </radialGradient>
      </defs>
    </svg>
  )
}

function ThinkingDots() {
  return (
    <div className="flex gap-1 py-0.5">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="w-1.5 h-1.5 bg-gray-400 rounded-full"
          style={{ animation: `bounce 1s ease-in-out ${delay}ms infinite` }}
        />
      ))}
    </div>
  )
}

export default function DesktopAgent() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [agentState, setAgentState] = useState<AgentState>('idle')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const talkingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { trigger } = useRefresh()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, agentState])

  useEffect(() => {
    if (isOpen) inputRef.current?.focus()
  }, [isOpen])

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || agentState === 'thinking') return

      const userMsg: Message = { role: 'user', content: text }
      const next = [...messages, userMsg]
      setMessages(next)
      setInput('')
      setAgentState('thinking')

      try {
        const res = await fetch('/api/agent', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: next }),
        })
        const data = await res.json()
        const reply = data.error ?? data.content ?? 'エラーが発生しました。'
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
        // If the agent created/updated tasks, refresh the visible task lists.
        if (data.mutated) trigger()
        setAgentState('talking')
        if (talkingTimerRef.current) clearTimeout(talkingTimerRef.current)
        talkingTimerRef.current = setTimeout(() => setAgentState('idle'), 2500)
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'すみません、接続エラーが発生しました。' },
        ])
        setAgentState('idle')
      }
    },
    [messages, agentState, trigger]
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <>
      {/* Chat panel */}
      {isOpen && (
        <div
          className="fixed bottom-24 right-4 z-50 w-80 bg-white rounded-2xl shadow-2xl border border-purple-100 flex flex-col overflow-hidden"
          style={{ maxHeight: 'calc(100vh - 130px)' }}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-3 flex items-center gap-3 flex-shrink-0">
            <AvatarFace state={agentState} size={34} />
            <div className="min-w-0">
              <div className="text-white font-semibold text-sm">コフ</div>
              <div className="text-purple-200 text-xs truncate">
                {agentState === 'thinking' ? '考え中...' : 'KofPro アシスタント'}
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="ml-auto text-purple-200 hover:text-white transition-colors text-xl leading-none flex-shrink-0"
              aria-label="閉じる"
            >
              ×
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 text-sm py-8 space-y-2">
                <div className="text-2xl">👋</div>
                <div>
                  こんにちは！タスクの相談や
                  <br />
                  アイデア整理をお手伝いします。
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-violet-600 text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {agentState === 'thinking' && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3">
                  <ThinkingDots />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="p-3 border-t border-gray-100 flex-shrink-0"
          >
            <div className="flex gap-2">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="メッセージを入力..."
                className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-violet-400 disabled:bg-gray-50"
                disabled={agentState === 'thinking'}
              />
              <button
                type="submit"
                disabled={!input.trim() || agentState === 'thinking'}
                className="bg-violet-600 text-white rounded-xl px-3 py-2 text-sm font-medium hover:bg-violet-700 disabled:opacity-40 transition-colors"
              >
                送信
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Floating avatar button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className={`fixed bottom-6 right-4 z-50 w-16 h-16 rounded-full shadow-xl transition-transform duration-200 hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${
          isOpen ? 'scale-95' : ''
        }`}
        style={
          agentState === 'idle' && !isOpen
            ? { animation: 'avatarFloat 3s ease-in-out infinite' }
            : undefined
        }
        aria-label="AIアシスタントを開く"
      >
        <AvatarFace state={agentState} size={64} />
      </button>
    </>
  )
}
