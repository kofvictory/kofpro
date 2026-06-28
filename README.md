# KofPro LifeLog

仕事〜生活を一元管理するライフログ管理アプリ。

## 画面構成

| 画面 | パス | 説明 |
|------|------|------|
| Inbox (トリアージ) | `/triage` | `inbox_view` 一覧。着手 / 見送り / 保留 ボタンで処理 |
| 着手中 | `/active` | `active_view` (status = adopted) |
| 今日 | `/today` | `today_view` (adopted かつ due_at ≦ 今日) |

クイックキャプチャは全画面の上部に常時表示（タイトルだけで inbox 登録）。

## セットアップ

### 1. Supabase プロジェクト作成

[https://supabase.com](https://supabase.com) でプロジェクトを作成し、以下の値を控える。

- **Project URL** (`https://xxxx.supabase.co`)
- **anon public key**

### 2. マイグレーション適用

#### 方法 A — SQL Editor（推奨・最速）

1. Supabase Dashboard → **SQL Editor** を開く
2. `supabase/migrations/20260628000000_lifelog_schema.sql` の全内容を貼り付けて **RUN**

#### 方法 B — Supabase CLI

```bash
npm install -g supabase
supabase login
supabase link --project-ref <your-project-ref>
supabase db push
```

> **注意**: スキーマ (`lifelog_schema.sql`) は変更しないこと。  
> 拡張が必要な場合は `entries.metadata` (jsonb) を使うか、  
> `supabase/migrations/` に新しいファイルを追加してください。

### 3. 環境変数

```bash
cp .env.local.example .env.local
# .env.local を編集して URL と anon key を設定
```

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### 4. 起動

```bash
npm install
npm run dev
# http://localhost:3000 → /triage へリダイレクト
```

## 型の再生成（スキーマ変更後）

```bash
supabase gen types typescript --project-id <your-project-ref> \
  > src/types/supabase-generated.ts
```

`src/types/database.ts` の手動定義型を最新のスキーマに合わせて更新してください。
