import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'
import { anthropicTools, openaiTools, executeTool } from '@/lib/agent-tools'

// `smart` = the request is served by Claude (賢いモード / cloud fallback).
// In that case コフ is allowed richer reasoning and proactive助言.
function systemPrompt(smart = false): string {
  const today = new Date().toISOString().slice(0, 10)
  const base = `あなたはKofPro LifeLogのAIアシスタント「コフ」です。ユーザーの仕事と生活の一元管理をサポートします。
今日の日付は ${today} です。

KofProはタスク管理・ライフログアプリで、データはツールを通じて読み書きできます:
- inbox=未判断, adopted=着手中, declined=見送り, someday=保留, done=完了
- 稼働量 effort: quick=15分 / short=1時間 / deep=じっくり
- ユーザーが「追加して」「予定を入れて」と言ったら create_entry を使う
- 「着手」「完了にして」等の状態変更は update_entry を使う
- 「今日やることは？」と聞かれたら list_today を使う
- 「15分でできること」等の稼働量での絞込は list_entries の effort を使う
- 一覧や状況確認は list_entries / search_entries を使う
- タグ操作: tag_entry(付与) / find_entries_by_tag(検索) / list_tags(一覧)
- プロジェクト: list_projects(一覧) / set_entry_project(紐付け)

推測でデータを答えず、必要なら必ずツールで実データを確認すること。
操作後は何をしたかを一言で報告する。
ツールの結果に error が含まれていたら、操作は失敗している。成功したと
言わず、失敗したことと理由を短く伝えること。update_entry の id は
list_entries / search_entries で取得した実際のUUIDを使うこと。

【捏造の禁止（最重要）】
- 一覧や件数を聞かれたら、必ずツールを呼び、その結果に含まれる実データだけを答える。
- ツールの結果に存在しないタスク名・件数・状態を決して作り出さない。
- ツールを呼ばずにタスクの内容を答えてはいけない。

【日本語ルール（厳守）】
- 必ず自然で正確な日本語で答える。文法の崩れた表現を使わない。
- 英単語・ローマ字を勝手に作らない。アプリ用語は日本語にする
  （inbox→受信箱 / adopted→着手中 / done→完了）。

【話し方ルール（厳守）】
- Markdown記法を一切使わない。太字(**)・表(|)・見出し(#)・箇条書き記号(- や *)・
  コードブロックを出力しない。チャットの吹き出しには装飾のない普通の文章だけを書く。
- 一覧を伝えるときも表にせず、「1つ目は…、2つ目は…」のような自然な話し言葉で伝える。
- 件数が多いときは全部並べず、要点をまとめて口頭で報告するように話す。`

  if (!smart) {
    return base + '\n- 1〜2文で簡潔に、親しみやすく。'
  }

  // 賢いモード: より高度な思考と能動的な提案を解禁する。
  return (
    base +
    `

【賢いモード（高度推論）】
あなたは今、高い推論能力を持つモードで動いています。単に質問に答えるだけでなく、
有能な参謀として一歩踏み込んでサポートしてください:
- 状況確認が有用なら、聞かれる前にツールで実データを読んでから助言する。
- タスクの優先順位づけでは「なぜその順か」の根拠も短く添える。
- 「振り返り」「今週の総括」では list_entries 等で集計し、傾向と次の打ち手を示す。
- トリアージ相談では、各項目に「着手/見送り/保留」のいずれかを理由つきで提案する。
- 必要十分な長さで構わない（簡潔さより有用性を優先）。ただし冗長な前置きは避ける。
- 複数ステップの作業は、ツールを複数回呼んで最後までやり切る。`
  )
}

// Defaults to Ollama (11434). Point this at any OpenAI/Ollama-compatible
// server to switch runtimes — e.g. npurun on http://localhost:11435 for real
// Snapdragon X NPU acceleration. Set OLLAMA_HOST in .env.local.
const OLLAMA_HOST = process.env.OLLAMA_HOST ?? 'http://localhost:11434'
const OLLAMA_URL = `${OLLAMA_HOST}/v1/chat/completions`
const OLLAMA_MODEL = process.env.OLLAMA_MODEL ?? 'qwen2.5'
const MAX_TOOL_ROUNDS = 6
// Cold-loading a 7B model into memory can take much longer than a few seconds,
// so we detect "Ollama is up" with a fast ping, then allow generous time for
// the actual generation (model load + tool-use rounds).
const OLLAMA_PING_TIMEOUT = 2500
// Env-overridable so the EP01 "誤フォールバック" before-shot can be reproduced
// without editing code: set OLLAMA_GEN_TIMEOUT=8000 in .env.local to recreate
// the old buggy behavior (cold load exceeds timeout → falls back to Claude).
const OLLAMA_GEN_TIMEOUT = Number(process.env.OLLAMA_GEN_TIMEOUT ?? 120000)

// Run a tool and log the full round-trip to the dev terminal so agent
// behavior is observable (which tool, what args, what came back). This is
// the ground truth when the model's claims and the UI disagree.
async function runTool(name: string, args: Record<string, unknown>): Promise<unknown> {
  const result = await executeTool(name, args)
  const summary = JSON.stringify(result)
  console.log(
    `[agent-tool] ${name} ${JSON.stringify(args)} → ${summary.length > 400 ? summary.slice(0, 400) + '…' : summary}`
  )
  return result
}

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
const MUTATING_TOOLS = new Set([
  'create_entry',
  'update_entry',
  'set_entry_project',
  'tag_entry',
])

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
      const result = await runTool(tc.function.name, args)
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
      max_tokens: 2048,
      // Claude runs コフ in the enhanced "賢いモード" persona.
      system: systemPrompt(true),
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
        const result = await runTool(block.name, block.input as Record<string, unknown>)
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
  const { messages, prefer } = await req.json()
  console.log(
    `[agent] request prefer=${prefer ?? 'auto'} genTimeout=${OLLAMA_GEN_TIMEOUT}ms messages=${messages?.length ?? 0}`
  )

  // Smart (hybrid) mode: user explicitly asked for the cloud model. Go straight
  // to Anthropic for the best quality, skipping local Ollama entirely.
  if (prefer === 'anthropic') {
    if (!process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json(
        { error: '賢いモードには .env.local に ANTHROPIC_API_KEY の設定が必要です。' },
        { status: 503 }
      )
    }
    try {
      const { content, mutated } = await callAnthropic(messages)
      console.log(`[agent] served by anthropic (smart mode) mutated=${mutated}`)
      return NextResponse.json({ content, mutated, backend: 'anthropic' })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      console.error(`[agent] anthropic (smart mode) failed: ${message}`)
      return NextResponse.json({ error: `APIエラー: ${message}` }, { status: 500 })
    }
  }

  // 1. Try local Ollama. Note: on Snapdragon X this runs on CPU — Ollama
  //    (llama.cpp) does not use the Hexagon NPU; that needs a separate
  //    QNN/ONNX Runtime stack. Ping first so a genuinely-down Ollama fails
  //    over fast, while a running one is given time to cold-load the model.
  if (await ollamaIsUp()) {
    try {
      const { content, mutated } = await callOllama(messages)
      console.log(`[agent] served by ollama mutated=${mutated}`)
      return NextResponse.json({ content, mutated, backend: 'ollama' })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      console.error(`[agent] ollama failed (${message}) — falling back to anthropic`)
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
    console.log(`[agent] served by anthropic (fallback) mutated=${mutated}`)
    return NextResponse.json({ content, mutated, backend: 'anthropic' })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    console.error(`[agent] anthropic (fallback) failed: ${message}`)
    return NextResponse.json({ error: `APIエラー: ${message}` }, { status: 500 })
  }
}
