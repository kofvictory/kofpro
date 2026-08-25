-- ============================================================================
-- 梅雨時売上回復プロジェクト 更新シード: Uber Eats の実態反映(2026-07-03)
--
-- オーナー確認事項:
--   * Uber Eats は申請・審査済みで、ディナーの非混雑時のみ解放して稼働中
--   * ランチ帯と併設菓子店(Baton)は導入済みだが未稼働
--
-- 反映内容:
--   1. 「出店申請とストア設定」タスクを done に(申請済みのため)
--   2. 損益分析タスクをディナー帯実績データ起点に更新
--   3. 新タスク: ディナー実績棚卸し / ランチ帯解放 / Baton菓子店稼働
--      新アイデア: 雨の日おやつセット
--
-- 前提: 20260703000000_trattoria_lunch_delivery_ig_ads.sql 適用済み。
-- 方針は従来どおり(スキーマ変更なし・タイトル存在チェックで冪等)。
-- ============================================================================

-- 1. 出店申請タスクは実態として完了済み → done(トリアージ履歴は自動記録される)
update entries set
  status = 'done',
  body   = coalesce(body, '') || E'\n\n[2026-07-03] オーナー確認: 申請・審査済みでディナー非混雑帯にて稼働中のため完了扱い。ランチ帯の解放は別タスクで管理。',
  metadata = metadata || '{"resolved": "already-applied", "confirmed_by_owner": "2026-07-03"}'::jsonb
where title = 'Uber Eats出店申請とストア設定(ランチ帯・写真・説明文)'
  and metadata->>'project_slug' = 'rainy-season-recovery-2026'
  and status <> 'done';

-- 2. 損益分析タスクをディナー帯の実績データ起点に更新
update entries set
  body        = 'ランチ帯解放とBaton菓子店稼働の前提となるユニットエコノミクス分析。既存のディナー帯実績(タスク「ディナー帯Uber Eats実績の棚卸し」)をベースラインに、手取り=価格×(1−手数料率)、貢献利益=手取り−食材原価−包材費 で候補メニューを検算し、デリバリー専用価格(店内比+30〜40%)を決める。契約中の実際の手数料率をUber Eats Managerで確認して使うこと。詳細は戦略ドキュメント柱B-2。',
  next_action = 'Uber Eats Managerで契約中の手数料率とディナー帯実績を確認する',
  metadata    = metadata || '{"baseline": "dinner-actuals"}'::jsonb
where title = 'デリバリープラットフォーム出店の損益シミュレーション'
  and metadata->>'project_slug' = 'rainy-season-recovery-2026'
  and metadata->>'baseline' is null;

-- 3. 新規タスク/アイデアの投入(inbox 直行 → /triage で判断)
with proj as (
  select p.id as project_id, p.area_id
  from projects p
  where p.title = '梅雨時売上回復プロジェクト'
),
seed(kind, title, body, priority, effort, next_action, due_at, phase) as (
  values
    ('task'::text,
     'ディナー帯Uber Eats実績の棚卸し(注文数・客単価・人気メニュー・評価)',
     '既に稼働中のディナー非混雑帯の実績をUber Eats Managerから集計: 注文数/日・客単価・人気メニュー・評価・注文の時間帯分布。ランチ帯解放の需要予測と損益分析のベースラインにする。スマホのManagerアプリで確認可能。',
     'high'::text, 'quick'::text,
     'Uber Eats Managerアプリで直近4週間の実績画面を開く',
     timestamptz '2026-07-06 22:00+09', 2),
    ('task',
     'Uber Eatsランチ帯の解放(営業時間設定+ランチメニュー公開)',
     '審査済みのため設定変更のみで開始できる。ランチ専用メニュー(30分放置テスト済みの品)を公開し、Managerで営業時間にランチ帯を追加。ピーク時のホール品質を守るため、解放は損益分析とオペレーション設計の完了後に行う。',
     'high', 'quick',
     'Managerの営業時間設定画面でランチ帯追加の手順を確認する',
     timestamptz '2026-07-10 22:00+09', 2),
    ('task',
     'Baton菓子店のUber Eatsストア稼働開始(写真・価格・営業時間)',
     '導入済み・未稼働のBatonストアを公開する。焼き菓子は配達での品質劣化がなく雨天の影響も受けないデリバリー最適商材。在宅の午後おやつ需要・手土産需要はランチ/ディナーと競合しない純増。写真・手数料込み価格・営業時間を設定して公開。',
     'high', 'short',
     'Batonの販売候補(焼き菓子セット等)と価格を決める',
     timestamptz '2026-07-12 22:00+09', 2),
    ('idea',
     '雨の日おやつセット(トラットリア×Baton)のデリバリー限定メニュー',
     'トラットリアのドルチェとBatonの焼き菓子を組み合わせたデリバリー限定セット。雨の日の在宅おやつ需要を狙い、雨予報日のIG広告ブースト(柱E)と連動して訴求する。両ストアの相互送客にもなる。',
     'medium', 'short',
     'セット候補の組み合わせと価格帯を2案つくる',
     null::timestamptz, 2)
)
insert into entries
  (kind, title, body, area_id, project_id, status,
   priority, effort, next_action, source, created_by, due_at, metadata)
select
  s.kind::entry_kind,
  s.title,
  s.body,
  proj.area_id,
  proj.project_id,
  'inbox',
  s.priority::priority_level,
  s.effort::effort_size,
  s.next_action,
  'agent',
  'claude-code',
  s.due_at,
  jsonb_build_object('project_slug', 'rainy-season-recovery-2026', 'phase', s.phase)
from seed s
cross join proj
where not exists (select 1 from entries e where e.title = s.title);

-- 4. タグ付け
insert into entry_tags (entry_id, tag_id)
select e.id, t.id
from entries e
join tags t on
  (t.slug = 'delivery' and e.title in (
     'ディナー帯Uber Eats実績の棚卸し(注文数・客単価・人気メニュー・評価)',
     'Uber Eatsランチ帯の解放(営業時間設定+ランチメニュー公開)',
     'Baton菓子店のUber Eatsストア稼働開始(写真・価格・営業時間)',
     '雨の日おやつセット(トラットリア×Baton)のデリバリー限定メニュー'))
  or (t.slug = 'rainyday' and e.title = '雨の日おやつセット(トラットリア×Baton)のデリバリー限定メニュー')
where e.metadata->>'project_slug' = 'rainy-season-recovery-2026'
on conflict do nothing;
