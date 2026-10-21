-- ============================================================================
-- RLS 強化: 各行を所有ユーザー本人だけが読み書きできるようにする
--
-- 変更点:
--   1. areas / projects / entries / tags / agent_actions に user_id を追加
--      (INSERT 時は auth.uid() が自動で入る)。
--   2. 既存行は auth.users の最古ユーザー(=オーナー本人)に割り当てる。
--      → 適用前にアプリで一度ログインしておくこと。
--   3. `using (true)` の全開放ポリシーを削除し、本人限定ポリシーに置き換える。
--      子テーブル(entry_tags 等)は親 entries の所有者で判定する。
--   4. ビューを security_invoker にする。
--      Postgres のビューは既定で所有者(postgres)権限で実行され RLS を素通りするため、
--      anon key だけで inbox_view 等から全エントリーが読めてしまっていた。
--   5. areas.slug / tags.slug の一意制約をユーザー単位に変更する。
--
-- 注意: service_role (Supabase MCP 等) で INSERT する場合は auth.uid() が NULL になるため、
--       user_id を明示的に指定すること。
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. user_id 列の追加
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['areas','projects','entries','tags','agent_actions']
  loop
    execute format(
      'alter table %I add column if not exists user_id uuid default auth.uid() references auth.users(id) on delete cascade;',
      t);
    execute format('create index if not exists idx_%I_user on %I(user_id);', t, t);
  end loop;
end $$;

comment on column entries.user_id is '所有ユーザー。RLS により本人のみ読み書き可能。';

-- ---------------------------------------------------------------------------
-- 2. 既存行をオーナーに割り当て、NOT NULL 化
-- ---------------------------------------------------------------------------
do $$
declare
  t     text;
  owner uuid := (select id from auth.users order by created_at limit 1);
begin
  foreach t in array array['areas','projects','entries','tags','agent_actions']
  loop
    if owner is not null then
      execute format('update %I set user_id = $1 where user_id is null;', t) using owner;
    end if;
    begin
      execute format('alter table %I alter column user_id set not null;', t);
    exception when not_null_violation then
      raise notice '% に user_id 未設定の行が残っています(ユーザー未作成)。ログイン後に手動で割り当ててください。', t;
    end;
  end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 3. slug の一意制約をユーザー単位に
-- ---------------------------------------------------------------------------
alter table areas drop constraint if exists areas_slug_key;
alter table areas add constraint areas_user_slug_key unique (user_id, slug);
alter table tags  drop constraint if exists tags_slug_key;
alter table tags  add constraint tags_user_slug_key unique (user_id, slug);

-- ---------------------------------------------------------------------------
-- 4. ポリシー差し替え
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['entries','projects','areas','tags','entry_tags',
                           'triage_decisions','entry_relations','attachments','agent_actions']
  loop
    execute format('drop policy if exists %I on %I;', t || '_authenticated', t);
  end loop;

  -- user_id を直接持つテーブル
  foreach t in array array['areas','projects','entries','tags','agent_actions']
  loop
    execute format(
      'create policy %I on %I for all to authenticated
         using (user_id = (select auth.uid()))
         with check (user_id = (select auth.uid()));',
      t || '_owner', t);
  end loop;

  -- entries 経由で所有者を判定する子テーブル
  foreach t in array array['triage_decisions','attachments']
  loop
    execute format(
      'create policy %I on %I for all to authenticated
         using (exists (select 1 from entries e
                        where e.id = entry_id and e.user_id = (select auth.uid())))
         with check (exists (select 1 from entries e
                             where e.id = entry_id and e.user_id = (select auth.uid())));',
      t || '_owner', t);
  end loop;
end $$;

create policy entry_tags_owner on entry_tags for all to authenticated
  using (
    exists (select 1 from entries e where e.id = entry_id and e.user_id = (select auth.uid()))
    and exists (select 1 from tags g where g.id = tag_id and g.user_id = (select auth.uid()))
  )
  with check (
    exists (select 1 from entries e where e.id = entry_id and e.user_id = (select auth.uid()))
    and exists (select 1 from tags g where g.id = tag_id and g.user_id = (select auth.uid()))
  );

create policy entry_relations_owner on entry_relations for all to authenticated
  using (
    exists (select 1 from entries e where e.id = from_entry_id and e.user_id = (select auth.uid()))
    and exists (select 1 from entries e where e.id = to_entry_id and e.user_id = (select auth.uid()))
  )
  with check (
    exists (select 1 from entries e where e.id = from_entry_id and e.user_id = (select auth.uid()))
    and exists (select 1 from entries e where e.id = to_entry_id and e.user_id = (select auth.uid()))
  );

-- ---------------------------------------------------------------------------
-- 5. ビューを呼び出し元の権限(=RLS 適用)で実行する
-- ---------------------------------------------------------------------------
alter view inbox_view  set (security_invoker = true);
alter view active_view set (security_invoker = true);
alter view today_view  set (security_invoker = true);
