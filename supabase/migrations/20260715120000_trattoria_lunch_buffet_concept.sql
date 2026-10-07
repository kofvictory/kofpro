-- ============================================================================
-- 梅雨時売上回復プロジェクト: ランチ・ビュッフェ構想(2026-07-15)
--
-- オーナー構想: 来年のランチ形態としてビュッフェスタイルを試運転。
-- 単価2,000〜3,000円、焼きたてパン・カットピザ・一品料理を店員が回って提供。
-- 人件費と工数の削減も兼ねる。分析: docs/trattoria/lunch-buffet-concept.md
--
-- 方針は従来どおり(スキーマ変更なし・タイトル存在チェックで冪等)。
-- ============================================================================

insert into tags (slug, name) values
  ('buffet', 'ビュッフェ'),
  ('lunch',  'ランチ')
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
  'idea'::entry_kind,
  'ランチ・ビュッフェスタイルの試運転(来年に向けて)',
  E'来年のランチ形態としてビュッフェスタイルを試運転する構想。単価¥2,000〜3,000、焼きたてパン・カットピザ・一品料理を店員が回って提供する形で、人件費と工数の削減も兼ねる。詳細分析: docs/trattoria/lunch-buffet-concept.md\n\n要点:\n- 「パティシエの焼きたて食べ放題」は沼津の競合(生パスタ系¥970-1,600)と土俵が違う差別化。現ランチ¥1,000-1,999からの客単価アップ(柱C)にも直結。\n- 工数削減の本丸は厨房(固定メニューのバッチ製造=オーブン稼働と好相性)。「回って提供」方式はホール人件費が単純には減らない代わりに、盛りすぎ・食べ残しを制御して食材ロスを抑える=人件費↔ロスのバランス設計。\n- 最大リスクは食材ロス。予約制+席数上限+時間制(例90分)で仕込み量を確定し廃棄を抑える。余りパンはテイクアウト転用。\n- KAIZUKA等のシグネチャーは「+単品追加」で残し来店理由を両立。\n- 固定メニューは売上・必要人数が読みやすく、自動化①(売上データ)②(売上連動シフト)と最も好相性。\n\n試運転設計: まず週1日/閑散曜日・予約制・席数上限で1〜2ヶ月。原価率・人件費率・客単価・回転・満足度を通常ランチと比較して本格導入可否を判断。',
  proj.area_id,
  proj.project_id,
  'inbox',
  'medium'::priority_level,
  'deep'::effort_size,
  '試運転の曜日・価格・メニュー・席数上限を1案に固める',
  'agent',
  'claude-code',
  jsonb_build_object(
    'project_slug', 'rainy-season-recovery-2026',
    'concept', 'lunch-buffet',
    'target_year', 2027,
    'price_band_jpy', jsonb_build_array(2000, 3000),
    'doc', 'docs/trattoria/lunch-buffet-concept.md'
  )
from proj
where not exists (
  select 1 from entries e where e.title = 'ランチ・ビュッフェスタイルの試運転(来年に向けて)'
);

-- タグ付け(ビュッフェ/ランチ/原価/シグネチャー)
insert into entry_tags (entry_id, tag_id)
select e.id, t.id
from entries e
join tags t on t.slug in ('buffet', 'lunch', 'genka', 'signature')
where e.title = 'ランチ・ビュッフェスタイルの試運転(来年に向けて)'
on conflict do nothing;
