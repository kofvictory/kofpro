// ENUM types — mirror the Postgres ENUMs in lifelog_schema.sql
export type EntryKind = 'task' | 'idea' | 'log' | 'note' | 'decision' | 'event'
export type TriageStatus = 'inbox' | 'adopted' | 'declined' | 'someday' | 'done' | 'archived'
export type PriorityLevel = 'low' | 'medium' | 'high' | 'urgent'
export type EffortSize = 'quick' | 'short' | 'deep'

// Table row types
export interface Area {
  id: string
  slug: string
  name: string
  color: string | null
  sort_order: number
  created_at: string
}

export interface Project {
  id: string
  area_id: string | null
  title: string
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface Entry {
  id: string
  kind: EntryKind
  title: string
  body: string | null
  area_id: string | null
  project_id: string | null
  status: TriageStatus
  priority: PriorityLevel | null
  effort: EffortSize | null
  next_action: string | null
  source: string
  external_url: string | null
  due_at: string | null
  occurred_at: string | null
  decided_at: string | null
  metadata: Record<string, unknown>
  created_by: string
  created_at: string
  updated_at: string
}

// View row types — match exactly the SELECT columns in the SQL views
export interface InboxView {
  id: string
  kind: EntryKind
  title: string
  body: string | null
  area: string | null
  project: string | null
  priority: PriorityLevel | null
  effort: EffortSize | null
  source: string
  created_at: string
}

export interface ActiveView {
  id: string
  kind: EntryKind
  title: string
  next_action: string | null
  area: string | null
  project: string | null
  priority: PriorityLevel | null
  due_at: string | null
}

export interface TodayView {
  id: string
  title: string
  next_action: string | null
  area: string | null
  due_at: string | null
  priority: PriorityLevel | null
}

// Supabase Database generic — used with createClient<Database>()
export type Database = {
  public: {
    Tables: {
      entries: {
        Row: Entry
        Insert: {
          id?: string
          kind?: EntryKind
          title: string
          body?: string | null
          area_id?: string | null
          project_id?: string | null
          status?: TriageStatus
          priority?: PriorityLevel | null
          effort?: EffortSize | null
          next_action?: string | null
          source?: string
          external_url?: string | null
          due_at?: string | null
          occurred_at?: string | null
          metadata?: Record<string, unknown>
          created_by?: string
        }
        Update: Partial<Entry>
      }
      areas: {
        Row: Area
        Insert: Omit<Area, 'id' | 'created_at'> & { id?: string }
        Update: Partial<Area>
      }
      projects: {
        Row: Project
        Insert: Omit<Project, 'id' | 'created_at' | 'updated_at'> & { id?: string }
        Update: Partial<Project>
      }
    }
    Views: {
      inbox_view: { Row: InboxView }
      active_view: { Row: ActiveView }
      today_view: { Row: TodayView }
    }
    Functions: Record<string, never>
    Enums: {
      entry_kind: EntryKind
      triage_status: TriageStatus
      priority_level: PriorityLevel
      effort_size: EffortSize
    }
  }
}
