-- ============================================================================
-- 梅雨時売上回復プロジェクト 統合シードSQL(Supabase SQL Editor 貼り付け用)
-- 生成日: 2026-07-04 / 以下のマイグレーションを順に連結したもの:
--   * 20260702000000_trattoria_rainy_season_project.sql
--   * 20260703000000_trattoria_lunch_delivery_ig_ads.sql
--   * 20260703120000_trattoria_ue_lunch_activation.sql
--   * 20260703180000_trattoria_ue_baseline_data.sql
--   * 20260704000000_trattoria_beyond_restaurant_ideas.sql
-- 前提: lifelog_schema.sql 適用済みのプロジェクトであること。
-- 全文が冪等なので、誤って2回実行しても重複しない。
-- ============================================================================


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


-- ============================================================================
-- 梅雨時売上回復プロジェクト 追加シード:
--   Phase 2b: ランチタイム Uber Eats 出店
--   Phase 4 : Instagram広告テスト
--
-- 戦略: docs/trattoria/rainy-season-2026-strategy.md(柱B-2 / 柱E)
-- 計画: docs/trattoria/rainy-season-2026-project-plan.md
--
-- 前提: 20260702000000_trattoria_rainy_season_project.sql 適用済み。
-- 方針は前回と同じ(スキーマ変更なし・inbox投入・タイトル存在チェックで冪等)。
-- ============================================================================

-- 1. 追加タグ
insert into tags (slug, name) values
  ('delivery', 'デリバリー'),
  ('ads',      '広告')
on conflict (slug) do nothing;

-- 2. 既存アイデア「デリバリープラットフォーム出店の損益シミュレーション」を
--    ランチ特化の損益分析タスクに格上げ(方針決定: ランチ帯Uber Eats展開)。
--    タイトルは前回マイグレーションの冪等ガードに使われているため変更しない。
--    status はユーザーのトリアージ判断に委ねるため変更しない。
update entries set
  kind        = 'task',
  priority    = 'high',
  effort      = 'short',
  due_at      = timestamptz '2026-07-08 22:00+09',
  body        = 'ランチ帯Uber Eats展開の前提となるユニットエコノミクス分析。手取り=価格×(1−手数料35%)、貢献利益=手取り−食材原価−包材費 で全候補メニューを検算し、デリバリー専用価格(店内比+30〜40%)を決める。詳細は戦略ドキュメント柱B-2。',
  next_action = '候補メニューごとに手数料35%込みの貢献利益を表計算で出す',
  metadata    = metadata || '{"phase": 2, "upgraded_to": "lunch-delivery-analysis"}'::jsonb
where title = 'デリバリープラットフォーム出店の損益シミュレーション'
  and metadata->>'project_slug' = 'rainy-season-recovery-2026'
  and metadata->>'upgraded_to' is null;

-- 3. 新規タスク/アイデアの投入(inbox 直行 → /triage で判断)
with proj as (
  select p.id as project_id, p.area_id
  from projects p
  where p.title = '梅雨時売上回復プロジェクト'
),
seed(kind, title, body, priority, effort, next_action, due_at, phase) as (
  values
    -- ---- Phase 2b: ランチタイム Uber Eats(7/7〜8/14) ----
    ('task'::text,
     'Uber Eatsランチ専用メニューの設計(30分放置テスト+専用価格)',
     '配達30分後でも品質が保てる品に限定(オイル系/ラグー系パスタ・冷菜・ドルチェ)。クリーム系・揚げ物は載せない。全候補品で30分放置テストを実施し、損益分析で決めたデリバリー専用価格を設定する。',
     'high'::text, 'short'::text,
     '候補メニューを調理して30分後の状態を試食チェック',
     timestamptz '2026-07-10 22:00+09', 2),
    ('task',
     'Uber Eats出店申請とストア設定(ランチ帯・写真・説明文)',
     '営業時間はランチ帯のみで設定(ディナーのホール品質を守る)。料理写真は明るい自然光で撮り直し。店舗説明文にトラットリアの物語を一言入れる。',
     'medium', 'short',
     'Uber Eatsレストランパートナー登録フォームを送信する',
     timestamptz '2026-07-13 22:00+09', 2),
    ('task',
     'ランチピーク時のデリバリーオペレーション設計',
     '同時受注上限・調理動線・配達員の受け渡し場所を事前に決める。ピーク時にホール品質を守れないときは受注一時停止を躊躇しないルールをスタッフと共有。',
     'medium', 'quick',
     '同時受注上限の数字をキッチンと相談して決める',
     timestamptz '2026-07-16 22:00+09', 2),
    ('idea',
     '出店直後のUber内プロモ集中投下(初回割引・レビュー獲得)',
     '出店直後はプラットフォーム内の露出が優遇される期間。初回割引などのUber内プロモをこの期間に集中させ、レビュー件数と★4.5以上の評価を確保する。',
     'medium', 'quick',
     '出店承認が下りたらUber管理画面でプロモメニューを確認',
     null::timestamptz, 2),
    ('task',
     'デリバリー4週間レビュー(注文数×貢献利益で継続/撤退判断)',
     '稼働4週間の実績を集計: 注文数/日・客単価・貢献利益/月。月間貢献利益が手間と包材在庫に見合わなければ撤退または縮小。撤退基準を先に決めてあるので感情で延長しない。',
     'high', 'short',
     'Uber管理画面から4週間の注文データをエクスポート',
     timestamptz '2026-08-14 22:00+09', 2),

    -- ---- Phase 4: Instagram広告テスト(7/9〜7/27) ----
    ('task',
     'Meta広告アカウント/ビジネス設定(IGプロアカウント確認含む)',
     'Instagramがプロアカウントになっているか確認し、Metaビジネスポートフォリオと広告アカウント・支払い方法を設定。予約リンク(またはリンクツリー)をプロフィールに整備。',
     'high', 'short',
     'IGアカウント設定でプロアカウント状態を確認する',
     timestamptz '2026-07-09 22:00+09', 4),
    ('task',
     '広告クリエイティブ2種制作(料理リール動画+静止画のA/B)',
     '15〜30秒の料理リール動画(調理シズル+店内の雰囲気)と静止画1枚を用意しA/Bテスト。リールの方がCPM効率が良い傾向。文言には雨の日特典も入れて柱Aと連動させる。',
     'high', 'short',
     '看板パスタの調理シーンをスマホで撮影する',
     timestamptz '2026-07-12 22:00+09', 4),
    ('task',
     'IG広告の少額テスト配信開始(日予算1,000〜2,000円・2週間)',
     'ターゲティング: 店舗半径3〜5km・25〜54歳。目的: プロフィール誘導+予約リンク誘導。日予算1,000〜2,000円で2週間、途中で予算をいじらない(学習期間を壊さない)。',
     'high', 'quick',
     '広告マネージャでキャンペーンを作成し半径ターゲティングを設定',
     timestamptz '2026-07-13 22:00+09', 4),
    ('task',
     'IG広告の効果測定とスケール判断(CPM/CTR/予約CPA)',
     '2週間の結果からCPM・CTR・プロフィール訪問単価・フォロワー獲得単価・予約CPAを算出。スケール条件: 予約CPA ≦ 客単価×粗利率(目安2,000円以下なら増額)。未達ならまずクリエイティブを差し替える。',
     'high', 'quick',
     '広告マネージャのレポートと予約台帳を突き合わせる',
     timestamptz '2026-07-27 22:00+09', 4),
    ('idea',
     '雨予報日の広告ブースト配信ルール化',
     '雨予報の日はIG広告の日予算を引き上げ、雨の日クーポン(柱A)のクリエイティブに差し替える天候連動運用。テスト配信で基礎CPAが取れてから導入。',
     'medium', 'quick',
     '天気予報チェック→予算変更の手順を1枚にまとめる',
     null::timestamptz, 4)
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
     'デリバリープラットフォーム出店の損益シミュレーション',
     'Uber Eatsランチ専用メニューの設計(30分放置テスト+専用価格)',
     'Uber Eats出店申請とストア設定(ランチ帯・写真・説明文)',
     'ランチピーク時のデリバリーオペレーション設計',
     '出店直後のUber内プロモ集中投下(初回割引・レビュー獲得)',
     'デリバリー4週間レビュー(注文数×貢献利益で継続/撤退判断)'))
  or (t.slug = 'genka' and e.title in (
     'デリバリープラットフォーム出店の損益シミュレーション',
     'Uber Eatsランチ専用メニューの設計(30分放置テスト+専用価格)'))
  or (t.slug = 'ads' and e.title in (
     'Meta広告アカウント/ビジネス設定(IGプロアカウント確認含む)',
     '広告クリエイティブ2種制作(料理リール動画+静止画のA/B)',
     'IG広告の少額テスト配信開始(日予算1,000〜2,000円・2週間)',
     'IG広告の効果測定とスケール判断(CPM/CTR/予約CPA)',
     '雨予報日の広告ブースト配信ルール化'))
  or (t.slug = 'rainyday' and e.title = '雨予報日の広告ブースト配信ルール化')
where e.metadata->>'project_slug' = 'rainy-season-recovery-2026'
on conflict do nothing;


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


-- ============================================================================
-- 梅雨時売上回復プロジェクト: ディナー帯実績データの反映(2026-07-03)
--
-- オーナー提供の6月実績(4週間): 5件 / ¥25,950 / 客単価¥5,190
--   6/1-6/6: 0件, 6/8-6/13: 0件, 6/15-6/20: 3件¥19,130, 6/22-6/27: 2件¥6,820
-- 分析: docs/trattoria/ue-dinner-baseline-2026-06.md
--
-- 実績棚卸しタスクは「残る確認事項」に絞り込み、実測値は metadata に保存する。
-- ============================================================================

update entries set
  body        = E'週次実績はオーナー確認済み(metadata参照。4週間で5件・¥25,950・客単価¥5,190)。分析は docs/trattoria/ue-dinner-baseline-2026-06.md。\n\n残る確認事項(すべてスマホのManagerアプリで可能):\n1. 契約中の実際の手数料率\n2. 店舗表示回数/閲覧数(露出問題の確定診断)\n3. 6/1〜6/13に店舗がオンラインだったか(一時停止の有無)\n4. 5件の注文日と雨天の突き合わせ\n5. 売れた5件のメニュー内訳(2人前セット設計の材料)',
  next_action = 'Managerアプリで店舗の表示回数と契約手数料率を確認する',
  metadata    = metadata || jsonb_build_object(
    'baseline_2026_06', jsonb_build_object(
      'weeks', jsonb_build_array(
        jsonb_build_object('period', '6/1-6/6',   'orders', 0, 'sales_jpy', 0),
        jsonb_build_object('period', '6/8-6/13',  'orders', 0, 'sales_jpy', 0),
        jsonb_build_object('period', '6/15-6/20', 'orders', 3, 'sales_jpy', 19130),
        jsonb_build_object('period', '6/22-6/27', 'orders', 2, 'sales_jpy', 6820)
      ),
      'total_orders', 5,
      'total_sales_jpy', 25950,
      'avg_order_value_jpy', 5190,
      'source', 'owner-report 2026-07-03'
    )
  )
where title = 'ディナー帯Uber Eats実績の棚卸し(注文数・客単価・人気メニュー・評価)'
  and metadata->>'project_slug' = 'rainy-season-recovery-2026'
  and metadata->'baseline_2026_06' is null;


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
