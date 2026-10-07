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
