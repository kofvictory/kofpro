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
const EFFORT_VALUES = ['quick', 'short', 'deep'] // 15分 / 1時間 / じっくり

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
        effort: {
          type: 'string',
          enum: EFFORT_VALUES,
          description: '稼働量で絞込 (quick=15分/short=1時間/deep=じっくり)',
        },
        limit: { type: 'number', description: '最大件数 (既定20)' },
      },
    },
  },
  {
    name: 'list_today',
    description:
      '今日やるべきタスクを取得する。着手中(adopted)かつ期限が今日以前のものを' +
      '期限順で返す。「今日やることは？」「今日のタスク」と聞かれたら使う。',
    parameters: { type: 'object', properties: {} },
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
        effort: {
          type: 'string',
          enum: EFFORT_VALUES,
          description: '稼働量 (quick=15分/short=1時間/deep=じっくり)',
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
        effort: {
          type: 'string',
          enum: EFFORT_VALUES,
          description: '稼働量 (quick=15分/short=1時間/deep=じっくり)',
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
  {
    name: 'list_projects',
    description:
      'プロジェクトの一覧を取得する。「〇〇プロジェクト関連を見せて」等で、' +
      'まず対象プロジェクトを特定するのに使う。',
    parameters: { type: 'object', properties: {} },
  },
  {
    name: 'set_entry_project',
    description:
      'エントリーをプロジェクトに紐付ける。project_title はlist_projectsの' +
      'タイトル(部分一致可)。「これを〇〇プロジェクトに入れて」で使う。',
    parameters: {
      type: 'object',
      properties: {
        id: { type: 'string', description: '対象エントリーのUUID(必須)' },
        project_title: { type: 'string', description: 'プロジェクト名(部分一致可、必須)' },
      },
      required: ['id', 'project_title'],
    },
  },
  {
    name: 'list_tags',
    description: 'タグの一覧を取得する。タグ付けや検索の前に存在するタグを確認するのに使う。',
    parameters: { type: 'object', properties: {} },
  },
  {
    name: 'tag_entry',
    description:
      'エントリーにタグを付ける。tag_slug が未登録なら自動作成する。' +
      '「これに#〇〇を付けて」で使う。',
    parameters: {
      type: 'object',
      properties: {
        id: { type: 'string', description: '対象エントリーのUUID(必須)' },
        tag_slug: { type: 'string', description: 'タグのslug(英数字, 必須)' },
        tag_name: { type: 'string', description: 'タグ表示名(省略時はslugを使用)' },
      },
      required: ['id', 'tag_slug'],
    },
  },
  {
    name: 'find_entries_by_tag',
    description: '指定したタグが付いたエントリーを検索する。「#〇〇のメモを全部出して」で使う。',
    parameters: {
      type: 'object',
      properties: {
        tag_slug: { type: 'string', description: 'タグのslug(必須)' },
      },
      required: ['tag_slug'],
    },
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
      if (typeof input.effort === 'string') q = q.eq('effort', input.effort)
      const limit = typeof input.limit === 'number' ? input.limit : 20
      const { data, error } = await q.order('created_at', { ascending: false }).limit(limit)
      if (error) return { error: error.message }
      return { count: data?.length ?? 0, entries: data ?? [] }
    }

    case 'list_today': {
      // today_view: adopted かつ due_at が今日以前のものを期限順で返す
      const { data, error } = await supabase
        .from('today_view')
        .select('id, title, next_action, area, due_at, priority')
      if (error) return { error: error.message }
      return { count: data?.length ?? 0, today: data ?? [] }
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
        effort: (input.effort as string) ?? null,
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
      if (typeof input.effort === 'string') patch.effort = input.effort
      if (typeof input.due_at === 'string') patch.due_at = input.due_at
      if (Object.keys(patch).length === 0) return { error: 'no fields to update' }
      const { data, error } = await supabase
        .from('entries')
        .update(patch as never)
        .eq('id', id)
        .select('id, title, status, next_action, priority, effort, due_at')
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

    case 'list_projects': {
      const { data, error } = await supabase
        .from('projects')
        .select('id, title, description, status, area_id')
        .order('created_at', { ascending: false })
      if (error) return { error: error.message }
      return { count: data?.length ?? 0, projects: data ?? [] }
    }

    case 'set_entry_project': {
      const id = String(input.id ?? '')
      const title = String(input.project_title ?? '')
      if (!id || !title) return { error: 'id と project_title は必須です' }
      const { data: proj } = await supabase
        .from('projects')
        .select('id, title')
        .ilike('title', `%${title}%`)
        .limit(1)
        .maybeSingle()
      if (!proj) return { error: `プロジェクトが見つかりません: ${title}` }
      const { data, error } = await supabase
        .from('entries')
        .update({ project_id: proj.id } as never)
        .eq('id', id)
        .select('id, title, project_id')
        .single()
      if (error) return { error: error.message }
      return { updated: data, project: proj.title }
    }

    case 'list_tags': {
      const { data, error } = await supabase.from('tags').select('slug, name').order('name')
      if (error) return { error: error.message }
      return { tags: data ?? [] }
    }

    case 'tag_entry': {
      const id = String(input.id ?? '')
      const slug = String(input.tag_slug ?? '')
      if (!id || !slug) return { error: 'id と tag_slug は必須です' }
      // Ensure the tag exists (create on demand).
      let { data: tag } = await supabase.from('tags').select('id').eq('slug', slug).maybeSingle()
      if (!tag) {
        const name = (input.tag_name as string) ?? slug
        const { data: created, error: tagErr } = await supabase
          .from('tags')
          .insert({ slug, name } as never)
          .select('id')
          .single()
        if (tagErr) return { error: tagErr.message }
        tag = created
      }
      // Link entry <-> tag (idempotent via upsert on the composite PK).
      const { error } = await supabase
        .from('entry_tags')
        .upsert({ entry_id: id, tag_id: tag!.id } as never, { onConflict: 'entry_id,tag_id' })
      if (error) return { error: error.message }
      return { tagged: { entry_id: id, tag_slug: slug } }
    }

    case 'find_entries_by_tag': {
      const slug = String(input.tag_slug ?? '')
      if (!slug) return { error: 'tag_slug は必須です' }
      const { data: tag } = await supabase
        .from('tags')
        .select('id')
        .eq('slug', slug)
        .maybeSingle()
      if (!tag) return { count: 0, entries: [], note: `タグが存在しません: ${slug}` }
      const { data: links } = await supabase
        .from('entry_tags')
        .select('entry_id')
        .eq('tag_id', tag.id)
      const ids = (links ?? []).map((l: { entry_id: string }) => l.entry_id)
      if (ids.length === 0) return { count: 0, entries: [] }
      const { data, error } = await supabase.from('entries').select(ENTRY_FIELDS).in('id', ids)
      if (error) return { error: error.message }
      return { count: data?.length ?? 0, entries: data ?? [] }
    }

    default:
      return { error: `unknown tool: ${name}` }
  }
}
