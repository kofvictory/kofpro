// ============================================================================
// Agent tools — let the avatar agent read & write the lifelog database.
//
// Each tool is defined once in a neutral JSON-schema shape, then adapted to
// both the Anthropic and the OpenAI/Ollama tool-calling formats.
// `executeTool` runs the actual Supabase query for a given tool name.
// ============================================================================
import { supabase } from '@/lib/supabase'

export type ToolDef = {
  name: string
  description: string
  parameters: {
    type: 'object'
    properties: Record<string, unknown>
    required?: string[]
  }
}

const STATUS_VALUES = ['inbox', 'adopted', 'declined', 'someday', 'done', 'archived']
const KIND_VALUES = ['task', 'idea', 'log', 'note', 'decision', 'event']

export const TOOLS: ToolDef[] = [
  {
    name: 'list_entries',
    description:
      'タスク/アイデア等のエントリーを一覧取得する。status で絞り込める。' +
      'inbox=未判断, adopted=着手中, done=完了。期限や優先度の確認にも使う。',
    parameters: {
      type: 'object',
      properties: {
        status: { type: 'string', enum: STATUS_VALUES, description: '絞り込む状態' },
        kind: { type: 'string', enum: KIND_VALUES, description: '絞り込む種別' },
        limit: { type: 'number', description: '最大件数 (既定20)' },
      },
    },
  },
  {
    name: 'search_entries',
    description: 'キーワードでエントリーをタイトル/本文から検索する。',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string', description: '検索キーワード' },
        limit: { type: 'number', description: '最大件数 (既定20)' },
      },
      required: ['query'],
    },
  },
  {
    name: 'create_entry',
    description:
      '新しいエントリー(タスク/アイデア/予定など)を作成する。' +
      'ユーザーが「〜を追加して」「〜の予定を入れて」と言ったときに使う。',
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string', description: 'タイトル(必須)' },
        kind: { type: 'string', enum: KIND_VALUES, description: '種別(既定idea)' },
        body: { type: 'string', description: '詳細メモ' },
        priority: {
          type: 'string',
          enum: ['low', 'medium', 'high', 'urgent'],
          description: '優先度',
        },
        due_at: { type: 'string', description: '期限 (ISO8601, 例 2026-07-01T14:00:00)' },
        area_slug: {
          type: 'string',
          description: '領域のslug(任意)。list_areasで取得できる',
        },
      },
      required: ['title'],
    },
  },
  {
    name: 'update_entry',
    description:
      'エントリーを更新する。status変更(着手=adopted/見送り=declined/完了=done)や、' +
      'next_action(次の一手)・優先度・期限の設定に使う。id は list/search で取得する。',
    parameters: {
      type: 'object',
      properties: {
        id: { type: 'string', description: '対象エントリーのUUID(必須)' },
        status: { type: 'string', enum: STATUS_VALUES, description: '新しい状態' },
        next_action: { type: 'string', description: '次にやる具体的な1アクション' },
        priority: {
          type: 'string',
          enum: ['low', 'medium', 'high', 'urgent'],
          description: '優先度',
        },
        due_at: { type: 'string', description: '期限 (ISO8601)' },
      },
      required: ['id'],
    },
  },
  {
    name: 'list_areas',
    description: '領域(area)の一覧を取得する。create_entry の area_slug を決めるのに使う。',
    parameters: { type: 'object', properties: {} },
  },
]

// --- Format adapters -------------------------------------------------------

export function anthropicTools() {
  return TOOLS.map((t) => ({
    name: t.name,
    description: t.description,
    input_schema: t.parameters,
  }))
}

export function openaiTools() {
  return TOOLS.map((t) => ({
    type: 'function' as const,
    function: { name: t.name, description: t.description, parameters: t.parameters },
  }))
}

// --- Executor --------------------------------------------------------------

type ToolInput = Record<string, unknown>

const ENTRY_FIELDS = 'id, kind, title, status, priority, effort, next_action, due_at, created_at'

export async function executeTool(name: string, input: ToolInput): Promise<unknown> {
  switch (name) {
    case 'list_entries': {
      let q = supabase.from('entries').select(ENTRY_FIELDS)
      if (typeof input.status === 'string') q = q.eq('status', input.status)
      if (typeof input.kind === 'string') q = q.eq('kind', input.kind)
      const limit = typeof input.limit === 'number' ? input.limit : 20
      const { data, error } = await q.order('created_at', { ascending: false }).limit(limit)
      if (error) return { error: error.message }
      return { count: data?.length ?? 0, entries: data ?? [] }
    }

    case 'search_entries': {
      const query = String(input.query ?? '')
      const limit = typeof input.limit === 'number' ? input.limit : 20
      const { data, error } = await supabase
        .from('entries')
        .select(ENTRY_FIELDS)
        .or(`title.ilike.%${query}%,body.ilike.%${query}%`)
        .order('created_at', { ascending: false })
        .limit(limit)
      if (error) return { error: error.message }
      return { count: data?.length ?? 0, entries: data ?? [] }
    }

    case 'create_entry': {
      let areaId: string | null = null
      if (typeof input.area_slug === 'string') {
        const { data: area } = await supabase
          .from('areas')
          .select('id')
          .eq('slug', input.area_slug)
          .maybeSingle()
        areaId = area?.id ?? null
      }
      const row = {
        title: String(input.title),
        kind: (input.kind as string) ?? 'idea',
        body: (input.body as string) ?? null,
        priority: (input.priority as string) ?? null,
        due_at: (input.due_at as string) ?? null,
        area_id: areaId,
        source: 'agent',
        created_by: 'agent',
      }
      // Supabase v2 typing for Insert mis-infers as never; cast through unknown.
      const { data, error } = await supabase
        .from('entries')
        .insert(row as never)
        .select('id, title, kind, status')
        .single()
      if (error) return { error: error.message }
      return { created: data }
    }

    case 'update_entry': {
      const id = String(input.id ?? '')
      if (!id) return { error: 'id is required' }
      const patch: Record<string, unknown> = {}
      if (typeof input.status === 'string') patch.status = input.status
      if (typeof input.next_action === 'string') patch.next_action = input.next_action
      if (typeof input.priority === 'string') patch.priority = input.priority
      if (typeof input.due_at === 'string') patch.due_at = input.due_at
      if (Object.keys(patch).length === 0) return { error: 'no fields to update' }
      const { data, error } = await supabase
        .from('entries')
        .update(patch as never)
        .eq('id', id)
        .select('id, title, status, next_action, priority, due_at')
        .single()
      if (error) return { error: error.message }
      return { updated: data }
    }

    case 'list_areas': {
      const { data, error } = await supabase
        .from('areas')
        .select('slug, name')
        .order('sort_order')
      if (error) return { error: error.message }
      return { areas: data ?? [] }
    }

    default:
      return { error: `unknown tool: ${name}` }
  }
}
