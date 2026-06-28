-- ============================================================================
-- Unified Life-Log Database (Supabase / Postgres)
-- 仕事〜生活を一元管理し、AIエージェントが読み書きしやすい構造 +
-- 着手(adopted)/見送り(declined) のトリアージ動線を備えた初期スキーマ。
--
-- 設計方針:
--   1. すべての記録は単一の `entries` テーブルに集約する(エージェントが1点を叩けば全体が見える)。
--   2. 状態・種別は ENUM で固定し、自由テキストにしない(エージェントが確実にフィルタできる)。
--   3. 状態変更は triage_decisions に自動記録され、判断履歴が消えない。
--   4. COMMENT を全テーブル/主要カラムに付与(Supabase MCP 経由でエージェントが意味を読める)。
--
-- 適用方法: Supabase SQL Editor に貼り付けて実行、または supabase migration として配置。
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 0. 拡張 & ENUM 型
-- ---------------------------------------------------------------------------
create extension if not exists pgcrypto;  -- gen_random_uuid()

do $$ begin
  create type entry_kind as enum (
    'task',      -- 実行すべきこと
    'idea',      -- 候補。着手/見送りの判断が必要
    'log',       -- 起きたことの記録(撮影・営業・学習セッション等)
    'note',      -- 知識・参照メモ
    'decision',  -- 下した意思決定の記録
    'event'      -- 日時の決まった予定
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type triage_status as enum (
    'inbox',     -- 捕捉済み・未判断(初期値)。ここがトリアージ待ち行列
    'adopted',   -- 着手:やると決めた
    'declined',  -- 見送り:やらないと決めた
    'someday',   -- 保留:今はやらないが後で見直すかも(ソフトな見送り)
    'done',      -- 完了
    'archived'   -- 用済み/対応不要(純粋なログ等)
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type priority_level as enum ('low','medium','high','urgent');
exception when duplicate_object then null; end $$;

do $$ begin
  create type effort_size as enum ('quick','short','deep');  -- 15分 / 1時間 / じっくり
exception when duplicate_object then null; end $$;

-- ---------------------------------------------------------------------------
-- 共通: updated_at 自動更新 & 状態変更時に decided_at をセット
-- ---------------------------------------------------------------------------
create or replace function set_timestamps() returns trigger as $$
begin
  new.updated_at := now();
  if (tg_op = 'UPDATE' and new.status is distinct from old.status) then
    new.decided_at := now();
  end if;
  return new;
end; $$ language plpgsql;

-- ---------------------------------------------------------------------------
-- 1. areas: 生活の領域(レストラン・写真・言語 等)
-- ---------------------------------------------------------------------------
create table if not exists areas (
  id          uuid primary key default gen_random_uuid(),
  slug        text not null unique,           -- エージェント参照用の安定キー
  name        text not null,
  color       text,                           -- UI 表示用 (#hex)
  sort_order  smallint not null default 0,
  created_at  timestamptz not null default now()
);
comment on table areas is '生活/仕事の領域。entries を分類する最上位の軸。';

-- ---------------------------------------------------------------------------
-- 2. projects: area 配下のまとまり(任意)
-- ---------------------------------------------------------------------------
create table if not exists projects (
  id          uuid primary key default gen_random_uuid(),
  area_id     uuid references areas(id) on delete set null,
  title       text not null,
  description text,
  status      text not null default 'active', -- active / paused / done / archived
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
comment on table projects is '領域内の継続的なまとまり(例: 自転車組写真コンペ, 在庫管理アプリ)。';
create trigger trg_projects_ts before update on projects
  for each row execute function set_timestamps();

-- ---------------------------------------------------------------------------
-- 3. entries: 中核。あらゆる記録の最小単位
-- ---------------------------------------------------------------------------
create table if not exists entries (
  id           uuid primary key default gen_random_uuid(),
  kind         entry_kind   not null default 'idea',
  title        text         not null,
  body         text,                              -- 詳細/生キャプチャ(markdown 可)
  area_id      uuid references areas(id)    on delete set null,
  project_id   uuid references projects(id) on delete set null,

  status       triage_status not null default 'inbox',
  priority     priority_level,
  effort       effort_size,

  next_action  text,                              -- 着手する場合の具体的な次の一手
  source       text not null default 'manual',    -- manual / voice / photo / email / agent / web
  external_url text,

  due_at       timestamptz,                        -- task/event の期限
  occurred_at  timestamptz,                        -- log が「いつ起きたか」
  decided_at   timestamptz,                        -- 着手/見送りを決めた時刻(自動)

  metadata     jsonb not null default '{}'::jsonb, -- エージェント拡張用の構造化フィールド
  created_by   text  not null default 'user',      -- user / claude-code / <agent名>
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
comment on table entries is '一元化された記録の最小単位。task/idea/log/note/decision/event を1テーブルに集約。';
comment on column entries.status is 'トリアージ状態。inbox=未判断, adopted=着手, declined=見送り。変更すると履歴が triage_decisions に自動記録される。';
comment on column entries.next_action is '着手と決めた際の「次にやる具体的な1アクション」。エージェントが実行支援に使う。';
comment on column entries.metadata is 'エージェントが自由に使える構造化メタデータ(JSON)。スキーマを変えずに拡張できる。';

create index if not exists idx_entries_status   on entries(status);
create index if not exists idx_entries_area     on entries(area_id);
create index if not exists idx_entries_project  on entries(project_id);
create index if not exists idx_entries_due      on entries(due_at);
create index if not exists idx_entries_kind     on entries(kind);
create index if not exists idx_entries_metadata on entries using gin(metadata);

create trigger trg_entries_ts before update on entries
  for each row execute function set_timestamps();

-- ---------------------------------------------------------------------------
-- 4. tags + entry_tags: 横断的なラベル(多対多)
-- ---------------------------------------------------------------------------
create table if not exists tags (
  id         uuid primary key default gen_random_uuid(),
  slug       text not null unique,
  name       text not null,
  created_at timestamptz not null default now()
);
comment on table tags is '領域をまたぐ横断ラベル(例: #コンペ #原価 #多言語)。';

create table if not exists entry_tags (
  entry_id uuid not null references entries(id) on delete cascade,
  tag_id   uuid not null references tags(id)    on delete cascade,
  primary key (entry_id, tag_id)
);

-- ---------------------------------------------------------------------------
-- 5. triage_decisions: 着手/見送りの判断履歴(自動記録)
-- ---------------------------------------------------------------------------
create table if not exists triage_decisions (
  id          uuid primary key default gen_random_uuid(),
  entry_id    uuid not null references entries(id) on delete cascade,
  decision    triage_status not null,    -- その時セットされた状態
  reason      text,                       -- なぜそう判断したか(任意・エージェント学習に有用)
  decided_by  text not null default 'user',
  decided_at  timestamptz not null default now()
);
comment on table triage_decisions is 'entries.status の変更履歴。なぜ着手/見送りしたかの判断ログ。';
create index if not exists idx_triage_entry on triage_decisions(entry_id);

-- entries の状態が変わるたびに自動で履歴を残す
create or replace function log_triage() returns trigger as $$
begin
  if (tg_op = 'INSERT') then
    insert into triage_decisions(entry_id, decision, decided_by, reason)
    values (new.id, new.status, new.created_by, 'initial capture');
  elsif (new.status is distinct from old.status) then
    insert into triage_decisions(entry_id, decision, decided_by)
    values (new.id, new.status, new.created_by);
  end if;
  return null;
end; $$ language plpgsql;

create trigger trg_entries_triage after insert or update on entries
  for each row execute function log_triage();

-- ---------------------------------------------------------------------------
-- 6. entry_relations: エントリー同士のリンク
-- ---------------------------------------------------------------------------
create table if not exists entry_relations (
  from_entry_id uuid not null references entries(id) on delete cascade,
  to_entry_id   uuid not null references entries(id) on delete cascade,
  relation_type text not null default 'relates_to', -- relates_to/blocks/part_of/inspired_by/duplicates
  created_at    timestamptz not null default now(),
  primary key (from_entry_id, to_entry_id, relation_type)
);
comment on table entry_relations is 'エントリー間の関係。エージェントが文脈を辿るのに使う(例: ideaがlogにinspired_by)。';

-- ---------------------------------------------------------------------------
-- 7. attachments: 画像/音声/ファイル(Supabase Storage パス)
-- ---------------------------------------------------------------------------
create table if not exists attachments (
  id           uuid primary key default gen_random_uuid(),
  entry_id     uuid not null references entries(id) on delete cascade,
  kind         text not null default 'image',  -- image / audio / file
  storage_path text not null,
  caption      text,
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 8. agent_actions: AIエージェントの操作監査ログ
-- ---------------------------------------------------------------------------
create table if not exists agent_actions (
  id         uuid primary key default gen_random_uuid(),
  entry_id   uuid references entries(id) on delete set null,
  agent      text not null,                 -- 'claude-code' 等
  action     text not null,                 -- created / updated / suggested / completed ...
  detail     jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
comment on table agent_actions is 'エージェントが何をしたかの監査ログ。AI連携の透明性確保用。';

-- ---------------------------------------------------------------------------
-- 9. ビュー: トリアージ/エージェント参照を簡単にする
-- ---------------------------------------------------------------------------
-- 未判断キュー(ここをチェックして着手/見送りを決める)
create or replace view inbox_view as
  select e.id, e.kind, e.title, e.body, a.name as area, p.title as project,
         e.priority, e.effort, e.source, e.created_at
  from entries e
  left join areas a    on a.id = e.area_id
  left join projects p on p.id = e.project_id
  where e.status = 'inbox'
  order by e.created_at desc;
comment on view inbox_view is 'トリアージ待ち(未判断)のエントリー。着手/見送りの判断対象。';

-- 着手中
create or replace view active_view as
  select e.id, e.kind, e.title, e.next_action, a.name as area,
         p.title as project, e.priority, e.due_at
  from entries e
  left join areas a    on a.id = e.area_id
  left join projects p on p.id = e.project_id
  where e.status = 'adopted'
  order by e.priority desc nulls last, e.due_at asc nulls last;
comment on view active_view is '着手中(adopted)で未完了のエントリー。';

-- 今日やること(着手中で期限が今日以前)
create or replace view today_view as
  select e.id, e.title, e.next_action, a.name as area, e.due_at, e.priority
  from entries e
  left join areas a on a.id = e.area_id
  where e.status = 'adopted'
    and e.due_at is not null
    and e.due_at < (current_date + interval '1 day')
  order by e.due_at asc;
comment on view today_view is '着手中かつ期限が今日以前(=今日着手すべき)。';

-- ---------------------------------------------------------------------------
-- 10. RLS(個人利用前提の最小ポリシー。マルチユーザ化時は要強化)
-- ---------------------------------------------------------------------------
alter table entries          enable row level security;
alter table projects         enable row level security;
alter table areas            enable row level security;
alter table tags             enable row level security;
alter table entry_tags       enable row level security;
alter table triage_decisions enable row level security;
alter table entry_relations  enable row level security;
alter table attachments      enable row level security;
alter table agent_actions    enable row level security;

do $$
declare t text;
begin
  foreach t in array array['entries','projects','areas','tags','entry_tags',
                           'triage_decisions','entry_relations','attachments','agent_actions']
  loop
    execute format(
      'create policy %I_authenticated on %I for all to authenticated using (true) with check (true);',
      t, t);
  end loop;
exception when duplicate_object then null;
end $$;

-- ---------------------------------------------------------------------------
-- 11. 初期データ(あなたの領域・代表プロジェクト・タグ)
-- ---------------------------------------------------------------------------
insert into areas (slug, name, color, sort_order) values
  ('restaurant', 'トラットリア運営', '#b3541e', 1),
  ('baton',      'Baton(菓子工房)', '#d8a657', 2),
  ('photography','写真',            '#3a3a3a', 3),
  ('language',   '言語',            '#4f6d7a', 4),
  ('philosophy', '仏教哲学',         '#7a5c9e', 5),
  ('youtube',    'YouTube発信',      '#cc3333', 6),
  ('dev',        '開発',            '#2d7d5a', 7),
  ('personal',   '生活/健康',        '#888888', 8)
on conflict (slug) do nothing;

insert into projects (area_id, title, description) values
  ((select id from areas where slug='photography'), '自転車組写真コンペ', 'symbol→memory→absence の弧で10点超の組写真'),
  ((select id from areas where slug='photography'), '地球の記憶',        '長期ドキュメントプロジェクト'),
  ((select id from areas where slug='dev'),         '在庫管理アプリ',     'React/Supabase/Netlify。請求書スキャン・ラベル印刷'),
  ((select id from areas where slug='restaurant'),  'エンタメコース設計', '12,000円コース + B2B営業')
on conflict do nothing;

insert into tags (slug, name) values
  ('compe','コンペ'), ('genka','原価'), ('haccp','衛生'), ('b2b','B2B営業'),
  ('multilingual','多言語'), ('signature','シグネチャー')
on conflict (slug) do nothing;
