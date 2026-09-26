-- ============================================================================
-- 梅雨時売上回復プロジェクト: 来年の夏祭り運用メモ(2026-07-15)
--
-- オーナーメモ: 来年の夏祭りは「ランチのみ営業 + 夜だけ外売り(店外販売)」で回す。
-- 判断の背景まで残しておくためのメモ(kind=note)。来年の梅雨明け前に見返す想定。
-- 方針は従来どおり(スキーマ変更なし・タイトル存在チェックで冪等)。
-- ============================================================================

insert into tags (slug, name) values
  ('matsuri', '夏祭り/イベント')
on conflict (slug) do nothing;

with proj as (
  select p.id as project_id, p.area_id
  from projects p
  where p.title = '梅雨時売上回復プロジェクト'
)
insert into entries
  (kind, title, body, area_id, project_id, status,
   priority, effort, next_action, source, created_by, metadata)
select
  'note'::entry_kind,
  '【メモ】来年の夏祭りはランチのみ営業+夜は外売り',
  E'来年の夏祭り当日の運用方針メモ。\n\n方針: 昼はランチのみ店内営業、夜は店内ディナーを閉めて「外売り(店外販売)」に切り替える。\n\n狙い/背景:\n- 夏祭りの夜は人通りが最大化する一方、店内ディナーは通行の妨げ・回転の悪さで機会損失になりやすい。\n- 夜は屋台形式の外売りにすることで、祭りの人流をそのまま売上に変換できる(客単価より件数・現金商売)。\n- 昼はランチのみに絞ることで、夜の外売り仕込みに厨房・人員を寄せられる。\n\n来年の準備で決めること(見返し用チェック):\n- 外売りの品目(片手で食べられるもの・Batonの焼き菓子など劣化しない商材が有力)\n- 保健所への臨時営業/露店許可の要否と申請期限\n- 夜の店内クローズをいつ告知するか(常連・予約客への周知)\n- 昼ランチと夜外売りの人員シフト(Airシフトの必要人数提案と連動)\n- 昨年比の売上比較のため、当日の外売り売上を別計上できるようにする',
  proj.area_id,
  proj.project_id,
  'someday',
  'low'::priority_level,
  'quick'::effort_size,
  '来年の梅雨明け前(6月頃)にこのメモを見返し、準備タスクへ展開する',
  'agent',
  'claude-code',
  jsonb_build_object(
    'project_slug', 'rainy-season-recovery-2026',
    'memo_type', 'summer-festival',
    'target_year', 2027,
    'plan', jsonb_build_object('lunch', 'dine-in only', 'night', 'outdoor stall / takeout only')
  )
from proj
where not exists (
  select 1 from entries e where e.title = '【メモ】来年の夏祭りはランチのみ営業+夜は外売り'
);

-- タグ付け
insert into entry_tags (entry_id, tag_id)
select e.id, t.id
from entries e
join tags t on t.slug in ('matsuri', 'takeout')
where e.title = '【メモ】来年の夏祭りはランチのみ営業+夜は外売り'
on conflict do nothing;
