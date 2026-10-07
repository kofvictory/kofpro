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
