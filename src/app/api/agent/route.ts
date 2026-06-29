import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'
import { anthropicTools, openaiTools, executeTool } from '@/lib/agent-tools'

function systemPrompt(): string {
  const today = new Date().toISOString().slice(0, 10)
  return `あなたはKofPro LifeLogのAIアシスタント「コフ」です。ユーザーの仕事と生活の一元管理をサポートします。
今日の日付は ${today} です。

KofProはタスク管理・ライフログアプリで、データはツールを通じて読み書きできます:
- inbox=未判断, adopted=着手中, declined=見送り, someday=保留, done=完了
- ユーザーが「追加して」「予定を入れて」と言ったら create_entry を使う
- 「着手」「完了にして」等の状態変更は update_entry を使う
- 一覧や状況確認は list_entries / search_entries を使う

推測でデータを答えず、必要なら必ずツールで実データを確認すること。
操作後は何をしたかを一言で報告する。日本語で簡潔・親しみやすく回答してください。`
}

const OLLAMA_URL = 'http://localhost:11434/v1/chat/completions'
const OLLAMA_MODEL = process.env.OLLAMA_MODEL ?? 'phi4-mini'
const MAX_TOOL_ROUNDS = 6

// Tools that change data — the UI should refresh task lists after these run.
const MUTATING_TOOLS = new Set(['create_entry', 'update_entry'])

type ChatMessage = { role: string; content: string }
type AgentResult = { content: string; mutated: boolean }

// --- Ollama (OpenAI-compatible) tool-use loop ------------------------------
async function callOllama(messages: ChatMessage[]): Promise<AgentResult> {
  const convo: unknown[] = [
    { role: 'system', content: systemPrompt() },
    ...messages,
  ]
  let mutated = false

  for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
    const res = await fetch(OLLAMA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        messages: convo,
        tools: openaiTools(),
        stream: false,
      }),
      // First round must fail fast if Ollama is down; later rounds can take longer.
      signal: AbortSignal.timeout(round === 0 ? 8000 : 60000),
    })
    if (!res.ok) throw new Error(`Ollama ${res.status}`)

    const data = await res.json()
    const msg = data.choices?.[0]?.message
    if (!msg) throw new Error('Ollama: empty response')

    const toolCalls = msg.tool_calls as
      | { id: string; function: { name: string; arguments: string } }[]
      | undefined

    if (!toolCalls || toolCalls.length === 0) {
      return { content: msg.content ?? '', mutated }
    }

    convo.push(msg)
    for (const tc of toolCalls) {
      let args: Record<string, unknown> = {}
      try {
        args = JSON.parse(tc.function.arguments || '{}')
      } catch {
        /* leave empty */
      }
      if (MUTATING_TOOLS.has(tc.function.name)) mutated = true
      const result = await executeTool(tc.function.name, args)
      convo.push({
        role: 'tool',
        tool_call_id: tc.id,
        content: JSON.stringify(result),
      })
    }
  }
  return { content: '(ツール呼び出しが上限に達しました)', mutated }
}

// --- Anthropic tool-use loop -----------------------------------------------
async function callAnthropic(messages: ChatMessage[]): Promise<AgentResult> {
  const client = new Anthropic()
  const convo: Anthropic.MessageParam[] = messages.map((m) => ({
    role: m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
  }))
  let mutated = false

  for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
    const response = await client.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 1024,
      system: systemPrompt(),
      tools: anthropicTools() as Anthropic.Tool[],
      messages: convo,
    })

    if (response.stop_reason !== 'tool_use') {
      const content = response.content
        .filter((b): b is Anthropic.TextBlock => b.type === 'text')
        .map((b) => b.text)
        .join('')
      return { content, mutated }
    }

    convo.push({ role: 'assistant', content: response.content })
    const toolResults: Anthropic.ToolResultBlockParam[] = []
    for (const block of response.content) {
      if (block.type === 'tool_use') {
        if (MUTATING_TOOLS.has(block.name)) mutated = true
        const result = await executeTool(block.name, block.input as Record<string, unknown>)
        toolResults.push({
          type: 'tool_result',
          tool_use_id: block.id,
          content: JSON.stringify(result),
        })
      }
    }
    convo.push({ role: 'user', content: toolResults })
  }
  return { content: '(ツール呼び出しが上限に達しました)', mutated }
}

export async function POST(req: NextRequest) {
  const { messages } = await req.json()

  // 1. Try local Ollama (NPU/GPU accelerated on Snapdragon X via Vulkan)
  try {
    const { content, mutated } = await callOllama(messages)
    return NextResponse.json({ content, mutated, backend: 'ollama' })
  } catch {
    // Ollama not running — fall through
  }

  // 2. Fall back to Anthropic cloud API
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      {
        error:
          'Ollama が起動していません。`ollama run qwen2.5` を実行するか、' +
          '.env.local に ANTHROPIC_API_KEY を設定してください。',
      },
      { status: 503 }
    )
  }

  try {
    const { content, mutated } = await callAnthropic(messages)
    return NextResponse.json({ content, mutated, backend: 'anthropic' })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: `APIエラー: ${message}` }, { status: 500 })
  }
}
