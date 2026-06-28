import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'

const SYSTEM_PROMPT = `あなたはKofPro LifeLogのAIアシスタント「コフ」です。ユーザーの仕事と生活の一元管理をサポートします。
KofProはタスク管理・ライフログアプリで、以下の3つの主要ビューがあります:
- Inbox（トリアージ）: 新しいアイテムの仕分け
- 着手中: 採択済みの進行中タスク
- 今日: 今日対応すべきタスク

日本語で、簡潔かつ親しみやすく回答してください。`

export async function POST(req: NextRequest) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { error: 'ANTHROPIC_API_KEY が設定されていません。.env.local を確認してください。' },
      { status: 500 }
    )
  }

  const { messages } = await req.json()

  const client = new Anthropic()

  const response = await client.messages.create({
    model: 'claude-haiku-4-5-20251001',
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    messages,
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : ''
  return NextResponse.json({ content: text })
}
