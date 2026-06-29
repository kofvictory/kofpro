# KofPro 開発ログ (DEVLOG)

> このファイルは KofPro（ライフログ管理アプリ + デスクトップ常駐AIエージェント「コフ」）の
> 制作経緯・設計判断・変更履歴をまとめたものです。
> **別の Claude チャット等に文脈を渡す目的で参照できるように**作成・更新します。
>
> 運用ルール: 機能追加・修正のたびに、末尾の「変更履歴」へ1エントリ追記する。

---

## 1. プロジェクト概要

- **名前**: KofPro LifeLog
- **目的**: 仕事〜生活を一元管理するライフログアプリ + デスクトップ常駐AIエージェント「コフ」
- **リポジトリ**: `kofvictory/kofpro`
- **作業ブランチ**: `claude/desktop-ai-agent-avatar-pb07zz`
- **想定環境**: Windows (Qualcomm Snapdragon X) デスクトップアプリ

## 2. 技術スタック

| 層 | 技術 |
|----|------|
| フロント | Next.js 14 (App Router) / React 18 / TailwindCSS |
| デスクトップ | Electron (本番は Next standalone を子プロセス起動) |
| DB | Supabase (Postgres) — 単一 `entries` テーブル中心の設計 |
| AI (ローカル) | Ollama (OpenAI/Ollama互換API, 既定 qwen2.5, CPU推論) |
| AI (クラウド) | Anthropic API (claude-haiku-4-5) ＝「賢いモード」/フォールバック |
| エージェント | Function Calling (Anthropic / OpenAI 両形式に変換するツール層) |

## 3. アーキテクチャ要点

### AIバックエンド (ハイブリッド)
```
チャットUI (DesktopAgent.tsx)
   │  { messages, prefer }
   ▼
/api/agent (route.ts)
   ├─ prefer==='anthropic' (🧠賢いモード) → Claude へ直行 (強化プロンプト)
   ├─ それ以外 → Ollama (localhost:11434) を ping → 生きていれば使用
   └─ Ollama が落ちている → Anthropic にフォールバック
```
- 接続先は `OLLAMA_HOST` 環境変数で差し替え可能（npurun 等のNPUランタイムへ切替用）。
- ツール使用後に操作系(create/update)が走ると `mutated:true` を返し、UI がタスク一覧を再取得。

### コフの人格 = システムプロンプト + ツール
- 人格はファインチューニングではなく `systemPrompt()` による指示。
- ローカルでも Claude でも**同じ役・同じ道具**。頭脳(モデル)だけ入れ替わる。
- `smart=true`（Claude時）は高度推論・能動提案を解禁する強化プロンプトを適用。

### データモデル (Supabase)
- 中核は単一 `entries` テーブル（task/idea/log/note/decision/event を集約）。
- `triage_status`(inbox/adopted/declined/someday/done/archived), `effort`(quick/short/deep) 等を ENUM 化。
- トリガーで `triage_decisions`(判断履歴) と `updated_at`/`decided_at` を自動記録。
- ビュー: `inbox_view` / `active_view` / `today_view`。
- ログインなし運用のため anon ロールにも RLS 全許可ポリシーを付与（別マイグレーション）。

### コフのツール (Function Calling)
| ツール | 用途 |
|--------|------|
| `list_entries` | 状態/種別/稼働量で一覧 |
| `list_today` | 今日やること (today_view) |
| `search_entries` | キーワード検索 |
| `create_entry` | 作成 (effort/優先度/期限/領域 指定可) |
| `update_entry` | 状態・next_action・優先度・稼働量・期限の更新 |
| `list_areas` | 領域一覧 |
| `list_projects` / `set_entry_project` | プロジェクト一覧 / 紐付け |
| `list_tags` / `tag_entry` / `find_entries_by_tag` | タグ一覧 / 付与 / 横断検索 |

## 4. 主要な設計判断・ハマりどころ

- **Claude Code と DB は非共有**: 私(Claude Code)は git 上のコードのみ扱い、DBに接続しない。`.env.local` は gitignore。
- **NPU は未使用（重要）**: Snapdragon X で Ollama(llama.cpp) は CPU 推論。Hexagon NPU は ONNX 専用で、使うには npurun/AnythingLLM/Foundry Local 等の別スタックが必要。当初「Vulkan/NPUで動く」と説明したが誤りだったため訂正済み。
- **Next.js 14 は `next.config.ts` 非対応** → `.mjs` に変換。
- **Supabase v2 の型不整合** → `Database` 型に `Relationships` 追加 + `ignoreBuildErrors`。
- **Ollama コールドロード**: 7Bモデルの初回読込は数十秒。短いタイムアウトで誤フォールバックしたため、ping(2.5s)+生成(120s)の二段構えに。
- **RLS**: 初期スキーマは authenticated のみ許可。publishable(anon)キー接続では INSERT が拒否され Inbox が空のままだった → anon ポリシー追加で解消。
- **小型モデルの日本語崩れ**: temperature=0.3 + プロンプトで造語禁止を明記して軽減。根本対策は賢いモード or 大型/日本語特化モデル。

## 5. 起動・ビルド

```bash
# 開発 (Next + Electron)
npm run electron:dev
# Windows ARM64 インストーラー
npm run electron:build:win-arm64
```
`.env.local` に `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` /
`OLLAMA_MODEL` /（任意）`ANTHROPIC_API_KEY` / `OLLAMA_HOST` を設定。

## 6. 拡張ロードマップ

- **フェーズ1（実装済）**: 「今日やること」/ effort 稼働量フィルタ
- **フェーズ2（実装済）**: タグ操作・プロジェクト連携（トリアージ補助は賢いモードのプロンプトで対応）
- **フェーズ3**: 判断理由の振り返り(triage_decisions読取)、週次レビュー、agent_actions監査
- **フェーズ4**: 音声入力、画像添付、能動的リマインド
- **NPU化（実験）**: npurun へ `OLLAMA_HOST=http://localhost:11435` で接続

---

## 7. 変更履歴

> 形式: `YYYY-MM-DD｜種別｜要約`（種別: feat=機能 / fix=修正 / chore=雑務 / docs=文書）

- 2026-06-28｜feat｜ライフログ管理機能の初期実装（Supabaseスキーマ・3画面・クイックキャプチャ）※前段のClaudeセッション由来
- 2026-06-28｜feat｜デスクトップ常駐AIアバター「コフ」を追加（SVGアバター + チャットパネル + Anthropic連携）
- 2026-06-28｜chore｜.gitignore 追加
- 2026-06-28｜feat｜Electron デスクトップアプリ化 + Ollama ローカル推論対応（当初NPU表記、後に訂正）
- 2026-06-28｜fix｜ビルドエラー修正・next.config.ts → mjs 変換
- 2026-06-28｜fix｜electron:dev でメインプロセスを起動前にコンパイル
- 2026-06-29｜feat｜コフをタスク連動エージェント化（Function Calling: 5ツール + tool-useループ）
- 2026-06-29｜fix｜Ollama コールドロード待ちのフォールバック誤判定を解消（ping+生成の二段構え）
- 2026-06-29｜fix｜小型ローカルモデルの日本語崩れ軽減（temperature 0.3 + プロンプト強化）
- 2026-06-29｜fix｜anon ロールの RLS ポリシー追加でタスク保存不可を解消
- 2026-06-29｜feat｜フェーズ1: 「今日やること」(list_today) と effort 稼働量対応
- 2026-06-29｜feat｜🧠賢いモード(Claude)トグル追加 + NPU非対応の正確な記述に訂正
- 2026-06-29｜feat｜OLLAMA_HOST を環境変数化（npurun 等のNPUランタイム接続用）
- 2026-06-30｜feat｜賢いモード専用の強化プロンプト（高度推論・能動提案）+ Claude時 max_tokens 2048 + DEVLOG.md 新設
- 2026-06-30｜feat｜フェーズ2: タグ操作(tag_entry/find_entries_by_tag/list_tags)とプロジェクト連携(list_projects/set_entry_project)を追加
