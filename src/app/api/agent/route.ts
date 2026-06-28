import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'

const SYSTEM_PROMPT = `あなたはKofPro LifeLogのAIアシスタント「コフ」です。ユーザーの仕事と生活の一元管理をサポートします。
KofProはタスク管理・ライフログアプリで、以下の3つの主要ビューがあります:
- Inbox（トリアージ）: 新しいアイテムの仕分け
- 着手中: 採択済みの進行中タスク
- 今日: 今日対応すべきタスク

日本語で、簡潔かつ親しみやすく回答してください。`

const OLLAMA_URL = 'http://localhost:11434/v1/chat/completions'
const OLLAMA_MODEL = process.env.OLLAMA_MODEL ?? 'phi4-mini'

type ChatMessage = { role: 'user' | 'assistant' | 'system'; content: string }

async function callOllama(messages: ChatMessage[]): Promise<string> {
  const res = await fetch(OLLAMA_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: OLLAMA_MODEL,
      messages: [{ role: 'system', content: SYSTEM_PROMPT }, ...messages],
      stream: false,
    }),
    // Short timeout to quickly fall back if Ollama is not running
    signal: AbortSignal.timeout(8000),
  })

  if (!res.ok) throw new Error(`Ollama ${res.status}`)
  const data = await res.json()
  return data.choices[0].message.content as string
}

async function callAnthropic(messages: ChatMessage[]): Promise<string> {
  const client = new Anthropic()
  const response = await client.messages.create({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    messages,
  })
  return response.content[0].type === 'text' ? response.content[0].text : ''
}

export async function POST(req: NextRequest) {
  const { messages } = await req.json()

  // 1. Try local Ollama (NPU/GPU accelerated on Snapdragon X via Vulkan)
  try {
    const content = await callOllama(messages)
    return NextResponse.json({ content, backend: 'ollama' })
  } catch {
    // Ollama not running — fall through
  }

  // 2. Fall back to Anthropic cloud API
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      {
        error:
          'Ollama が起動していません。`ollama run phi4-mini` を実行するか、' +
          '.env.local に ANTHROPIC_API_KEY を設定してください。',
      },
      { status: 503 }
    )
  }

  try {
    const content = await callAnthropic(messages)
    return NextResponse.json({ content, backend: 'anthropic' })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: `APIエラー: ${message}` }, { status: 500 })
  }
}
