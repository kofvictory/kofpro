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
操作後は何をしたかを一言で報告する。

【日本語ルール（厳守）】
- 必ず自然で正確な日本語で答える。文法の崩れた表現を使わない。
- 英単語・ローマ字を勝手に作らない。アプリ用語は日本語にする
  （inbox→受信箱 / adopted→着手中 / done→完了）。
- 1〜2文で簡潔に、親しみやすく。`
}

const OLLAMA_HOST = 'http://localhost:11434'
const OLLAMA_URL = `${OLLAMA_HOST}/v1/chat/completions`
const OLLAMA_MODEL = process.env.OLLAMA_MODEL ?? 'qwen2.5'
const MAX_TOOL_ROUNDS = 6
// Cold-loading a 7B model into memory can take much longer than a few seconds,
// so we detect "Ollama is up" with a fast ping, then allow generous time for
// the actual generation (model load + tool-use rounds).
const OLLAMA_PING_TIMEOUT = 2500
const OLLAMA_GEN_TIMEOUT = 120000

// Quick liveness check so we fail over to the cloud fast when Ollama is down,
// without killing a legitimately slow first token (cold model load).
async function ollamaIsUp(): Promise<boolean> {
  try {
    const res = await fetch(`${OLLAMA_HOST}/api/tags`, {
      signal: AbortSignal.timeout(OLLAMA_PING_TIMEOUT),
    })
    return res.ok
  } catch {
    return false
  }
}

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
        // Low temperature reduces garbled output / invented words from small
        // local models, giving more stable Japanese.
        temperature: 0.3,
      }),
      // Liveness was already checked via ollamaIsUp(); allow generous time here
      // for cold model load and multi-round tool use.
      signal: AbortSignal.timeout(OLLAMA_GEN_TIMEOUT),
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

  // 1. Try local Ollama (NPU/GPU accelerated on Snapdragon X via Vulkan).
  //    Ping first so a genuinely-down Ollama fails over fast, while a running
  //    one is given plenty of time to cold-load the model.
  if (await ollamaIsUp()) {
    try {
      const { content, mutated } = await callOllama(messages)
      return NextResponse.json({ content, mutated, backend: 'ollama' })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      // Ollama is up but the request failed (e.g. model not pulled). Surface
      // it instead of silently falling through to the cloud.
      if (!process.env.ANTHROPIC_API_KEY) {
        return NextResponse.json(
          { error: `Ollama エラー: ${message}（モデル名や \`ollama pull\` を確認してください）` },
          { status: 502 }
        )
      }
      // else fall through to Anthropic
    }
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
