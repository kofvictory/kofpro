-- ============================================================================
-- 梅雨時売上回復プロジェクト: 脱・薄利多売の収益構想(2026-07-04)
--
-- オーナー意向: デリバリーはコストの割に売上貢献が低い懸念。試算次第で導入見送り。
-- 従来の飲食店形態を超えて利益と社会的恩恵を最大化する取り組みを検討したい。
--
-- 反映内容:
--   1. デリバリー関連タスクに「導入ゲート」を追記(試算が基準未達なら見送り)
--   2. 柱F(脱・薄利多売)の6アイデアを inbox に投入
-- 構想本文: docs/trattoria/beyond-restaurant-ideas.md
-- 方針は従来どおり(スキーマ変更なし・タイトル存在チェックで冪等)。
-- ============================================================================

-- 1. ランチ帯解放タスクに導入ゲートを追記
update entries set
  body     = coalesce(body, '') || E'\n\n[2026-07-04 導入ゲート] オーナー意向により「やる前提」ではない。損益分析(#15)が撤退基準を下回る見込みならランチ帯解放自体を見送る。導入する場合もBaton焼き菓子のみから始める縮小解を優先。背景: docs/trattoria/beyond-restaurant-ideas.md §0',
  priority = 'medium',
  metadata = metadata || '{"gated_on": "unit-economics-15", "gate_added": "2026-07-04"}'::jsonb
where title = 'Uber Eatsランチ帯の解放(営業時間設定+ランチメニュー公開)'
  and metadata->>'project_slug' = 'rainy-season-recovery-2026'
  and metadata->>'gated_on' is null;

-- 2. 損益分析タスクに「ゲートの判定者」であることを明記
update entries set
  body     = coalesce(body, '') || E'\n\n[2026-07-04] このタスクはデリバリー導入可否のゲート。試算結果が撤退基準(月間貢献利益が手間・包材管理に見合う水準)を下回る見込みなら、ランチ帯解放を見送る判断を推奨する。',
  metadata = metadata || '{"role": "delivery-gate"}'::jsonb
where title = 'デリバリープラットフォーム出店の損益シミュレーション'
  and metadata->>'project_slug' = 'rainy-season-recovery-2026'
  and metadata->>'role' is null;

-- 3. タグ追加
insert into tags (slug, name) values
  ('community', '地域/社会'),
  ('kaiin', '会員制/前払い')
on conflict (slug) do nothing;

-- 4. 柱Fの6アイデアを投入(inbox 直行 → /triage で判断)
with proj as (
  select p.id as project_id, p.area_id
  from projects p
  where p.title = '梅雨時売上回復プロジェクト'
),
seed(kind, title, body, priority, effort, next_action, due_at, phase) as (
  values
    ('idea'::text,
     'ダズンクラブ(回数券12+1/月額会員)の設計とテスト販売',
     'Baker''s Dozen=「パン屋の13個(12個買うと1個おまけ)」の由来を会員制に直訳。12回分の料金で13回使える回数券、または月額会員(来店ごとにドルチェ1品+限定メニュー+イベント先行予約)。前払いでキャッシュフロー改善・来店頻度の固定化・天候変動の平準化(=梅雨対策の最終形)。まず紙の回数券30枚をIG告知のみでテスト販売。既存アイデア「常連向けサブスク/回数券の検討」の具体化版。',
     'high'::text, 'short'::text,
     '回数券の価格と特典を1案つくる(12回分の価格で13回)',
     timestamptz '2026-07-15 22:00+09', 5),
    ('idea',
     'パティシエ直伝教室の第1回開催(8月の親子菓子教室)',
     '大人のパスタ教室/親子菓子教室を定休日(日曜)や14-17時のアイドルタイムで開催。1回8名×¥5,000〜8,000で材料原価2〜3割、粗利率はディナー営業超え。参加者は高確率で食事客としてリピート。夏休みの親子回は食育=地域貢献としても明確。IGフォロワー4,300人への告知だけで初回は集まる見込み。',
     'high', 'short',
     '8月の開催候補日を2つ決めてIG告知文を下書きする',
     timestamptz '2026-07-18 22:00+09', 5),
    ('idea',
     '焼き菓子・ソースの沼津市ふるさと納税返礼品登録',
     'Baton焼き菓子缶+自家製ソース瓶を沼津市のふるさと納税返礼品に登録。保存が利くので閑散時間に製造でき廃棄リスク低。マーケ費ゼロで全国リーチ+市の税収に直接貢献(社会的恩恵が制度に組み込まれている)。店頭物販(既存アイデア)の本命出口。',
     'medium', 'short',
     '沼津市サイトで返礼品事業者の募集要項を確認する',
     null::timestamptz, 5),
    ('idea',
     '駿河湾コラボディナー(生産者連携・前売り制)の第1回企画',
     '沼津港の漁師・近隣農家を招く月1回の前売り制コラボディナー(8〜12席・¥10,000〜15,000)。「今夜の貝は◯◯さんが今朝獲ったもの」を生産者本人が語る。前売り完売型で廃棄ゼロ・no-showゼロ。KAIZUKAの物語の事業化であり、エンタメコース(既存プロジェクト)のB2C版。一次産業の販路づくりとして行政・地元メディアの後押しが得やすい。',
     'medium', 'deep',
     'KAIZUKAの貝の仕入元1軒に共催を打診する',
     null::timestamptz, 5),
    ('idea',
     '「13個目のおすそわけ」サスペンデッドミール制度',
     '会計時に+¥500で「13個目」を購入してもらい、地域の子ども・学生などの食事券として積み立てる(イタリアのcaffè sospeso文化の食堂版)。直接利益はゼロだが運用コストもほぼゼロで、店名の由来と完全に一致する社会貢献の看板。他の全施策のブランド価値と「値引きしない理由」を補強する。',
     'medium', 'quick',
     '仕組みを説明する店頭POPの文面を1枚つくる',
     null::timestamptz, 5),
    ('idea',
     'YouTube×焼き菓子通販のオンライン展開',
     '既存のYouTube発信領域と接続し、パティシエのイタリア食堂の仕込み・菓子作りを発信して焼き菓子通販へ誘導。席数の物理限界を完全に超える唯一の軸。ただし手を広げすぎないため、ふるさと納税/物販が立ってから着手する中期案件。',
     'low', 'deep',
     '物販(返礼品)の立ち上がりを待つ — 着手条件を四半期レビューで確認',
     null::timestamptz, 5)
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
  jsonb_build_object('project_slug', 'rainy-season-recovery-2026', 'phase', s.phase, 'pillar', 'F')
from seed s
cross join proj
where not exists (select 1 from entries e where e.title = s.title);

-- 5. タグ付け
insert into entry_tags (entry_id, tag_id)
select e.id, t.id
from entries e
join tags t on
  (t.slug = 'community' and e.title in (
     '焼き菓子・ソースの沼津市ふるさと納税返礼品登録',
     '駿河湾コラボディナー(生産者連携・前売り制)の第1回企画',
     '「13個目のおすそわけ」サスペンデッドミール制度',
     'パティシエ直伝教室の第1回開催(8月の親子菓子教室)'))
  or (t.slug = 'kaiin' and e.title = 'ダズンクラブ(回数券12+1/月額会員)の設計とテスト販売')
  or (t.slug = 'signature' and e.title = '駿河湾コラボディナー(生産者連携・前売り制)の第1回企画')
where e.metadata->>'project_slug' = 'rainy-season-recovery-2026'
on conflict do nothing;
