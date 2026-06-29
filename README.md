# KofPro LifeLog

仕事〜生活を一元管理するライフログ管理アプリ。

## 画面構成

| 画面 | パス | 説明 |
|------|------|------|
| Inbox (トリアージ) | `/triage` | `inbox_view` 一覧。着手 / 見送り / 保留 ボタンで処理 |
| 着手中 | `/active` | `active_view` (status = adopted) |
| 今日 | `/today` | `today_view` (adopted かつ due_at ≦ 今日) |

クイックキャプチャは全画面の上部に常時表示（タイトルだけで inbox 登録）。

## AIアシスタント「コフ」

右下に常駐するアバター。クリックでチャットが開き、タスクの読み書きを代行する。

### バックエンド (自動切替)

1. **Ollama** (`localhost:11434`) — ローカル推論。起動していれば優先使用
2. **Anthropic API** — Ollama 未起動時のフォールバック (`ANTHROPIC_API_KEY` 必要)

### タスク連動 (Function Calling)

コフは以下のツールで `entries` を直接操作できる:

| ツール | 用途 |
|--------|------|
| `list_entries` | 状態/種別/稼働量(effort)で一覧 (inbox/adopted/done…) |
| `list_today` | 今日やること (adopted かつ期限が今日以前) |
| `search_entries` | キーワード検索 |
| `create_entry` | タスク/アイデア/予定の作成 (effort 指定可) |
| `update_entry` | 状態変更・next_action・優先度・稼働量・期限の設定 |
| `list_areas` | 領域一覧 (分類用) |

> effort: `quick`=15分 / `short`=1時間 / `deep`=じっくり

作成・更新が走ると画面のタスク一覧は自動でリフレッシュされる。

> **モデル選定**: ツール使用には対応モデルが必要。`.env.local` の `OLLAMA_MODEL` で指定。
> - `qwen2.5` … ツール使用◎ だが小型(7B)のため日本語がやや崩れることがある
> - `qwen2.5:14b` … 日本語の質が向上(要メモリ・低速)
> - ELYZA系 (例 `hf.co/elyza/Llama-3-ELYZA-JP-8B-GGUF`) … 日本語特化で自然
> - `phi4-mini` はツール呼び出しが不安定なので非推奨

## デスクトップアプリ (Electron)

```bash
npm run electron:dev          # 開発起動 (Next.js + Electron)
npm run electron:build:win-arm64   # Windows ARM64 インストーラー生成
```

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
