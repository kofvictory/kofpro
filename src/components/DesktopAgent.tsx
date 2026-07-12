'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRefresh } from '@/lib/refresh-context'

type AgentState = 'idle' | 'thinking' | 'talking'
type Backend = 'ollama' | 'anthropic'
type Message = { role: 'user' | 'assistant'; content: string; backend?: Backend }

// Floating window sizes (kept in sync with electron/main.ts initial size).
const FLOAT_CLOSED = { width: 112, height: 112 }
const FLOAT_OPEN = { width: 360, height: 600 }

declare global {
  interface Window {
    kofproFloating?: {
      setSize: (width: number, height: number) => void
      dragStart: () => void
      dragEnd: () => void
    }
  }
}

// EP06完成形コフ。不変コア(シルエット・アンテナ・まる目・まる手・配置)は絶対に変えず、
// 可変外皮(配色・光・潤み・血色)だけを backend で振る:
//   ollama = 常駐する機械の器(紫・寒色・均一な光) / anthropic = 灯った生命の火(オレンジ・暖色・脈打つ光)
function AvatarFace({
  state,
  backend,
  size = 60,
  handsVisible = false,
}: {
  state: AgentState
  backend: Backend
  size?: number
  handsVisible?: boolean
}) {
  const squintY = state === 'thinking' ? 2 : 5
  // 「火が灯っているか」。外皮の分岐はすべてこの1点から引く(コアの形状には一切触れない)
  const warm = backend === 'anthropic'
  const headFill = warm ? 'url(#headGradWarm)' : 'url(#headGradCool)'
  const antennaColor = warm ? '#fdba74' : '#a78bfa'
  // 口も外皮: 頭色に馴染む暗色(寒=濃紺 / 暖=焦げ茶)で同じ形のまま体温だけ変える
  const inkColor = warm ? '#431407' : '#1e1b4b'
  return (
    <svg
      viewBox="0 0 60 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={(size * 80) / 60}
    >
      {/* Antenna stem */}
      <line x1="30" y1="11" x2="30" y2="4" stroke={antennaColor} strokeWidth="2.5" strokeLinecap="round" />
      {/* 魂モードだけの光暈: 冷たい均一光との対比で「温かい光が脈打つ」を作る(thinking中は黄パルスに譲る) */}
      {warm && state !== 'thinking' && (
        <circle
          cx="30"
          cy="3"
          r="5.5"
          fill="#fb923c"
          opacity="0.3"
          style={{ animation: 'pulse 2.6s ease-in-out infinite' }}
        />
      )}
      {/* Antenna tip — pulses yellow while thinking (思考の記号は両モード共通=不変コア) */}
      <circle
        cx="30"
        cy="3"
        r="3"
        fill={state === 'thinking' ? '#fbbf24' : antennaColor}
        style={state === 'thinking' ? { animation: 'pulse 1s ease-in-out infinite' } : undefined}
      />

      {/* Head — 同じ形・同じグラデ構造(35%/30%光源)で色だけ器⇄魂に振る */}
      <circle cx="30" cy="36" r="22" fill={headFill} />

      {/* Left eye */}
      <ellipse cx="22" cy="34" rx="5" ry={squintY} fill="white" />
      <circle cx="23" cy="34" r="2.5" fill="#312e81" />
      <circle cx="23.8" cy="33" r={warm ? 1.2 : 1} fill="white" />
      {/* 潤み層(魂モードのみ): 下瞼の水膜+瞳の底の二次光で「目が潤む=生きている」を出す */}
      {warm && (
        <>
          <circle cx="22.2" cy="35.2" r="0.6" fill="white" opacity="0.85" />
          <ellipse cx="22" cy={34 + squintY - 0.8} rx="3.4" ry="0.8" fill="white" opacity="0.35" />
        </>
      )}

      {/* Right eye */}
      <ellipse cx="38" cy="34" rx="5" ry={squintY} fill="white" />
      <circle cx="39" cy="34" r="2.5" fill="#312e81" />
      <circle cx="39.8" cy="33" r={warm ? 1.2 : 1} fill="white" />
      {warm && (
        <>
          <circle cx="38.2" cy="35.2" r="0.6" fill="white" opacity="0.85" />
          <ellipse cx="38" cy={34 + squintY - 0.8} rx="3.4" ry="0.8" fill="white" opacity="0.35" />
        </>
      )}

      {/* Mouth */}
      {state === 'talking' ? (
        <ellipse cx="30" cy="43" rx="5.5" ry="3.5" fill={inkColor} opacity="0.65" />
      ) : (
        <path
          d="M 24 42 Q 30 47 36 42"
          stroke={inkColor}
          strokeWidth="1.8"
          strokeLinecap="round"
          fill="none"
          opacity="0.65"
        />
      )}

      {/* Cheeks — 器では淡く残し(愛せる機械=無機物にしない)、魂では血色が灯る */}
      <circle cx="13" cy="40" r="5" fill={warm ? '#fb7185' : '#f9a8d4'} opacity={warm ? 0.5 : 0.35} />
      <circle cx="47" cy="40" r="5" fill={warm ? '#fb7185' : '#f9a8d4'} opacity={warm ? 0.5 : 0.35} />

      {/* まる手2つ — 体幹に繋がらない浮遊球(=データの記号)。頭と同じグラデ=同じ存在の一部。
          待機時はしまう: 非表示時も DOM に残し、opacity+沈み込みで出し入れの気配を作る */}
      <g
        style={{
          opacity: handsVisible ? 1 : 0,
          transform: handsVisible ? 'translateY(0)' : 'translateY(6px)',
          transition: 'opacity 0.3s ease, transform 0.3s ease',
        }}
      >
        <circle cx="9" cy="66" r="6" fill={headFill} />
        <circle cx="51" cy="66" r="6" fill={headFill} />
        {/* 手のハイライト: 頭と同じ左上光源に揃えて球体として同居させる */}
        <circle cx="7.5" cy="64" r="1.4" fill="white" opacity="0.45" />
        <circle cx="49.5" cy="64" r="1.4" fill="white" opacity="0.45" />
      </g>

      <defs>
        {/* 両モードのグラデを常備: 外皮の切替は fill の参照先を変えるだけ(構造は共通) */}
        <radialGradient id="headGradCool" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#ddd6fe" />
          <stop offset="55%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#5b21b6" />
        </radialGradient>
        <radialGradient id="headGradWarm" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#fed7aa" />
          <stop offset="55%" stopColor="#fb923c" />
          <stop offset="100%" stopColor="#c2410c" />
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

// `floating` = rendered inside the dedicated always-on-top Electron window.
// The component then drives the window size on open/close and exposes a
// drag region around the avatar / panel (border strip + header).
export default function DesktopAgent({ floating = false }: { floating?: boolean }) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [agentState, setAgentState] = useState<AgentState>('idle')
  // Smart mode = route to the cloud model (Claude) for the best quality.
  const [smartMode, setSmartMode] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const talkingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { trigger } = useRefresh()
  // アバター外皮は賢いモードに連動: 器(ollama)⇄魂(anthropic)
  const avatarBackend: Backend = smartMode ? 'anthropic' : 'ollama'

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, agentState])

  useEffect(() => {
    if (isOpen) inputRef.current?.focus()
  }, [isOpen])

  const toggleOpen = useCallback(() => {
    setIsOpen((open) => {
      const next = !open
      if (floating) {
        // Grow the window before showing the panel; shrink after hiding it.
        const size = next ? FLOAT_OPEN : FLOAT_CLOSED
        window.kofproFloating?.setSize(size.width, size.height)
      }
      return next
    })
  }, [floating])

  // Wipe the conversation. Long histories (especially ones containing a small
  // model's earlier hallucinations) drag later answers into skipping tools —
  // a fresh chat restores reliable tool-calling.
  const clearChat = useCallback(() => {
    setMessages([])
    setInput('')
    setAgentState('idle')
    inputRef.current?.focus()
  }, [])

  // コフ本体を掴んで動かす / そのままクリックで開閉。
  // mousedown後に4px以上動いたらドラッグ(移動は main process がカーソル追従)、
  // 動かず離したらクリック扱いにする。
  const dragRef = useRef<{ startX: number; startY: number; dragging: boolean } | null>(null)

  const handleAvatarMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!floating || e.button !== 0) return
      dragRef.current = { startX: e.screenX, startY: e.screenY, dragging: false }

      const onMove = (ev: MouseEvent) => {
        const d = dragRef.current
        if (!d || d.dragging) return
        if (Math.abs(ev.screenX - d.startX) + Math.abs(ev.screenY - d.startY) > 4) {
          d.dragging = true
          window.kofproFloating?.dragStart()
        }
      }
      const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
        const wasDragging = dragRef.current?.dragging
        dragRef.current = null
        if (wasDragging) {
          window.kofproFloating?.dragEnd()
        } else {
          toggleOpen()
        }
      }
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    },
    [floating, toggleOpen]
  )

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
          body: JSON.stringify({
            // Send only what the model needs (strip UI fields like `backend`).
            messages: next.map((m) => ({ role: m.role, content: m.content })),
            prefer: smartMode ? 'anthropic' : undefined,
          }),
        })
        const data = await res.json()
        const reply = data.error ?? data.content ?? 'エラーが発生しました。'
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: reply, backend: data.backend },
        ])
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
    [messages, agentState, trigger, smartMode]
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
          className={`fixed bottom-24 right-4 z-50 w-80 bg-white rounded-2xl shadow-2xl border flex flex-col overflow-hidden app-no-drag ${
            smartMode ? 'border-amber-200' : 'border-purple-100'
          }`}
          style={{ maxHeight: 'calc(100vh - 130px)' }}
        >
          {/* Header — colour flips with the mode so the switch reads on camera.
              In the floating window the header doubles as a drag handle. */}
          <div
            className={`px-4 py-3 flex items-center gap-3 flex-shrink-0 transition-colors duration-300 ${
              floating ? 'app-drag' : ''
            } ${
              smartMode
                ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                : 'bg-gradient-to-r from-violet-600 to-purple-600'
            }`}
          >
            <AvatarFace state={agentState} backend={avatarBackend} handsVisible={agentState === 'talking'} size={34} />
            <div className="min-w-0">
              <div className="text-white font-semibold text-sm">コフ</div>
              <div
                className={`text-xs truncate ${smartMode ? 'text-amber-100' : 'text-purple-200'}`}
              >
                {agentState === 'thinking'
                  ? '考え中...'
                  : smartMode
                    ? '賢い (Claude)'
                    : 'ローカル (Ollama)'}
              </div>
            </div>
            <button
              onClick={() => setSmartMode((s) => !s)}
              title={smartMode ? '賢いモード: ON (Claudeを使用)' : '賢いモード: OFF (ローカル)'}
              className={`ml-auto flex-shrink-0 text-xs font-medium px-2 py-1 rounded-full transition-colors app-no-drag ${
                smartMode
                  ? 'bg-white text-amber-600 shadow-sm'
                  : 'bg-white/15 text-purple-100 hover:bg-white/25'
              }`}
            >
              🧠 賢い
            </button>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                title="会話をクリア（履歴をリセット）"
                className={`flex-shrink-0 text-base leading-none transition-colors app-no-drag ${
                  smartMode ? 'text-amber-100 hover:text-white' : 'text-purple-200 hover:text-white'
                }`}
                aria-label="会話をクリア"
              >
                🗑
              </button>
            )}
            <button
              onClick={toggleOpen}
              className={`transition-colors text-xl leading-none flex-shrink-0 app-no-drag ${
                smartMode ? 'text-amber-100 hover:text-white' : 'text-purple-200 hover:text-white'
              }`}
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
                className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'bg-violet-600 text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {m.content}
                </div>
                {/* Which brain answered — makes fallback/smart mode visible */}
                {m.role === 'assistant' && m.backend && (
                  <span
                    className={`mt-0.5 px-1.5 text-[10px] leading-4 rounded-full ${
                      m.backend === 'anthropic'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {m.backend === 'anthropic' ? 'Claude' : 'ローカル'}
                  </span>
                )}
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

      {/* Floating avatar button — in the floating window コフ itself is both
          the click target (open/close) and the drag handle (move window). */}
      <button
        onClick={floating ? undefined : toggleOpen}
        onMouseDown={handleAvatarMouseDown}
        className={`fixed bottom-6 right-4 z-50 w-16 h-16 rounded-full shadow-xl transition-transform duration-200 hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 app-no-drag ${
          isOpen ? 'scale-95' : ''
        } ${floating ? 'cursor-grab active:cursor-grabbing' : ''}`}
        style={
          agentState === 'idle' && !isOpen
            ? { animation: 'avatarFloat 3s ease-in-out infinite' }
            : undefined
        }
        aria-label="AIアシスタントを開く"
      >
        <AvatarFace state={agentState} backend={avatarBackend} handsVisible={agentState === 'talking'} size={64} />
      </button>
    </>
  )
}
