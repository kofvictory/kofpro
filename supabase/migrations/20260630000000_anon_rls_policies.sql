-- ============================================================================
-- anon ロール向け RLS ポリシー追加
--
-- 初期スキーマ(20260628000000)は `authenticated` ロールにのみ全許可ポリシーを
-- 付与していた。しかし本アプリはログイン機能を持たず、publishable(anon) キーで
-- 接続するため、INSERT/UPDATE/SELECT が anon ロールでは拒否されていた。
--
-- 個人利用前提で、anon ロールにも同等の全許可ポリシーを付与する。
-- (マルチユーザ化する場合は、ここを auth.uid() ベースの制御に置き換えること)
-- ============================================================================
do $$
declare t text;
begin
  foreach t in array array['entries','projects','areas','tags','entry_tags',
                           'triage_decisions','entry_relations','attachments','agent_actions']
  loop
    execute format(
      'create policy %I_anon on %I for all to anon using (true) with check (true);',
      t, t);
  end loop;
exception when duplicate_object then null;
end $$;
