-- ============================================================================
-- 梅雨時売上回復プロジェクト(トラットリア)のシードデータ
--
-- 戦略: docs/trattoria/rainy-season-2026-strategy.md
-- 計画: docs/trattoria/rainy-season-2026-project-plan.md
--
-- 方針:
--   * スキーマは変更しない(README の指示どおり)。projects / entries / tags への insert のみ。
--   * すべての entries は status = 'inbox' で投入し、採否の判断は /triage 画面でユーザーが行う。
--   * タイトルで存在チェックするため再実行しても重複しない(冪等)。
-- ============================================================================

-- 1. プロジェクト本体(トラットリア運営 領域の配下)
insert into projects (area_id, title, description, status)
select a.id,
       '梅雨時売上回復プロジェクト',
       '梅雨〜盛夏の売上落ち込み対策。雨の日集客・テイクアウト/物販・客単価アップ・B2Bの4本柱。詳細は docs/trattoria/rainy-season-2026-strategy.md',
       'active'
from areas a
where a.slug = 'restaurant'
  and not exists (
    select 1 from projects p where p.title = '梅雨時売上回復プロジェクト'
  );

-- 2. 追加タグ
insert into tags (slug, name) values
  ('rainyday', '雨の日'),
  ('takeout',  'テイクアウト')
on conflict (slug) do nothing;

-- 3. タスク/アイデアの投入(inbox 直行 → /triage で判断)
with proj as (
  select p.id as project_id, p.area_id
  from projects p
  where p.title = '梅雨時売上回復プロジェクト'
),
seed(kind, title, body, priority, effort, next_action, due_at, phase) as (
  values
    -- ---- Phase 1: 即効施策(〜7/10) ----
    ('task'::text,
     '雨の日セット(パスタ+グラスワイン)の設計と店頭告知',
     '雨の日限定「本日のパスタ+グラスワイン」セット。値付けは原価率を確認しつつ通常比▲10%目安。店頭黒板とSNSで告知。',
     'urgent'::text, 'quick'::text,
     'セット内容と価格を決めて黒板に書く',
     timestamptz '2026-07-04 18:00+09', 1),
    ('task',
     '入口の雨の日おもてなし(傘立て・傘袋・タオル)',
     '傘立て・使い捨て傘袋・おしぼりタオルを入口に常備。「雨の日こそ快適な店」の体験を作る。',
     'high', 'quick',
     '傘袋とタオルの在庫を確認し不足分を発注',
     timestamptz '2026-07-04 12:00+09', 1),
    ('task',
     'Googleビジネスプロフィールを梅雨仕様に更新',
     '雨の日特典・最新の営業時間・料理写真を更新。「近くのレストラン」検索での取りこぼしを防ぐ。',
     'high', 'quick',
     'Googleビジネスプロフィールにログインして投稿を1件作成',
     timestamptz '2026-07-05 12:00+09', 1),
    ('task',
     'LINE公式/Instagramで雨の日クーポン配信の仕組みづくり',
     '雨予報の日の午前中に当日限定クーポンを配信できる運用を作る。テンプレ文面と画像を事前に用意しておく。',
     'high', 'short',
     'クーポンのテンプレ文面と画像を1セット作る',
     timestamptz '2026-07-07 12:00+09', 1),
    ('task',
     '過去2年の6〜7月売上データ棚卸し(KPIベースライン)',
     '曜日別・天候別に客数と客単価を分解。戦略ドキュメントのKPI表の「現状」欄を埋め、目標値を確定させる。',
     'high', 'short',
     'レジデータから2024/2025年の6-7月日次売上を抽出する',
     timestamptz '2026-07-08 22:00+09', 1),

    -- ---- Phase 2: テイクアウト・物販(7/6〜7/20) ----
    ('task',
     'テイクアウトメニュー3品の選定と原価計算',
     '看板パスタ・前菜など持ち帰りで品質が落ちにくい3品に絞る。容器コスト込みで原価率を計算(#genka)。',
     'high', 'short',
     '候補5品をリストアップし持ち帰り30分後の状態を試食で確認',
     timestamptz '2026-07-10 22:00+09', 2),
    ('task',
     'テイクアウト容器・包材の調達',
     'メニュー3品確定後に容器・袋・ロゴシールを発注。初回は小ロットで。',
     'medium', 'short',
     '容器サンプルを2〜3社から取り寄せる',
     timestamptz '2026-07-14 12:00+09', 2),
    ('idea',
     '自家製ソース・焼き菓子の物販(Baton連携)',
     '自家製ソースの瓶詰め+Baton(菓子工房)の焼き菓子を店頭販売。来店客の「ついで買い」で客単価を上げ、雨天の売上変動も緩和する。',
     'medium', 'deep',
     'Baton側と品目・卸値・納品サイクルを打ち合わせる',
     null::timestamptz, 2),
    ('idea',
     'デリバリープラットフォーム出店の損益シミュレーション',
     'UberEats等は手数料が重い(30%超)。テイクアウトの実績が出てから、手数料込みで黒字になる価格設定が可能か試算して判断する。',
     'medium', 'short',
     '手数料率と想定注文数で損益分岐点を試算する',
     null::timestamptz, 2),

    -- ---- Phase 3: 客単価・イベント・B2B(7月中旬〜8月) ----
    ('task',
     '季節限定コース開発(初夏食材+白ワインペアリング)',
     '初夏野菜・鮎など「梅雨〜盛夏だから食べたい」食材でコースを構成。白ワインペアリング提案で客単価アップ(#signature)。',
     'high', 'deep',
     'コースの軸になる食材と皿数を決めて試作日を設定',
     timestamptz '2026-07-20 22:00+09', 3),
    ('task',
     'エンタメコース(12,000円)のB2B営業リスト10社作成',
     '既存の「エンタメコース設計」プロジェクトを加速。暑気払い・歓送迎需要のある近隣企業・団体を10社リスト化(#b2b)。',
     'medium', 'short',
     '近隣企業を10社リストアップし窓口担当を調べる',
     timestamptz '2026-07-17 22:00+09', 3),
    ('idea',
     '雨の夜ワイン会/料理教室の月1イベント化',
     '予約制イベントは雨天でもキャンセルされにくい。平日夜の稼働率対策として月1回の定例開催を検討。',
     'medium', 'deep',
     '第1回のテーマと開催候補日を決める',
     null::timestamptz, 3),
    ('idea',
     '常連向けサブスク/回数券の検討',
     'キャッシュフローの先取りと来店頻度の固定化。梅雨・猛暑・閑散期に強い売上構造を作る中期施策。',
     'low', 'deep',
     '他店のサブスク事例を3件調べて損益モデルを整理',
     null::timestamptz, 3),

    -- ---- 運用 ----
    ('task',
     '週次レビューの定例化(毎週月曜)',
     '毎週月曜: 1) KPIと先週売上の突き合わせ 2) /triage のinboxを空にする 3) 今週のdue_atを設定。詳細は docs/trattoria/rainy-season-2026-project-plan.md',
     'high', 'quick',
     '月曜のカレンダーに30分の定例ブロックを入れる',
     timestamptz '2026-07-06 10:00+09', 0)
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

-- 4. タグ付け(雨の日/テイクアウト/原価/B2B/シグネチャー)
insert into entry_tags (entry_id, tag_id)
select e.id, t.id
from entries e
join tags t on
  (t.slug = 'rainyday'  and e.title in (
     '雨の日セット(パスタ+グラスワイン)の設計と店頭告知',
     '入口の雨の日おもてなし(傘立て・傘袋・タオル)',
     'LINE公式/Instagramで雨の日クーポン配信の仕組みづくり',
     '雨の夜ワイン会/料理教室の月1イベント化'))
  or (t.slug = 'takeout' and e.title in (
     'テイクアウトメニュー3品の選定と原価計算',
     'テイクアウト容器・包材の調達',
     'デリバリープラットフォーム出店の損益シミュレーション'))
  or (t.slug = 'genka' and e.title in (
     'テイクアウトメニュー3品の選定と原価計算',
     '雨の日セット(パスタ+グラスワイン)の設計と店頭告知'))
  or (t.slug = 'b2b' and e.title = 'エンタメコース(12,000円)のB2B営業リスト10社作成')
  or (t.slug = 'signature' and e.title = '季節限定コース開発(初夏食材+白ワインペアリング)')
where e.metadata->>'project_slug' = 'rainy-season-recovery-2026'
on conflict do nothing;
