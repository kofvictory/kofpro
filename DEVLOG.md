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

### フローティング常駐コフ (Electron)
- コフは常時最前面・枠なし・**透過**の別 BrowserWindow（`/floating` ルート）に常駐。
  デスクトップにはコフ本体と吹き出しだけが見える（小窓の白枠なし）。
  メインを最小化/閉じても残る。Electron時はメイン内アバターは非表示（コフは1体）。
- 開閉時は preload 経由の IPC でウィンドウを 112x112⇔360x600 に伸縮（右下アンカー）。
  透過の死角(クリックを吸う不可視領域)を最小化するため閉時は小さく保つ。
  クリックスルーは不採用。`FLOAT_TRANSPARENT=false` で非透過カードに即戻せる。
- **コフ本体がクリック(開閉)とドラッグ(移動)を兼ねる**: renderer は mousedown後
  4px超の移動でドラッグ開始/終了だけを IPC 通知し、移動自体は main process が
  `screen.getCursorScreenPoint()` を16msポーリングしてウィンドウをカーソル追従させる
  (DPI座標系のズレとmousemove取りこぼしを回避)。吹き出しヘッダーは app-region drag。
- 位置決めは常に `clampToWorkArea()`（最寄りディスプレイの作業領域に押し戻し）を通す。
  初回起動時にコフが画面外へ見切れる不具合（DPIスケーリング環境）の対策。
- ウィンドウ間のタスク一覧同期は RefreshProvider 内の BroadcastChannel(`kofpro-refresh`)。

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

## 6.5 EP01 撮影ゲートの現状（BUILD_SPEC_FOR_EP01 の必須4項目）

- ✅ **#1 Markdown生表示を消す** … systemPrompt の禁止 + サーバー側 stripMarkdown の二重防御で実装済み
- ✅ **#2 賢いモードの別人感** … ヘッダー色切替(紫ローカル⇔琥珀Claude)+応答元チップ。実機検証済み
- ✅ **#3 フローティング常駐** … 透過ウィンドウ・本体クリック開閉/ドラッグ・見切れ修正。実機検証済み
- ✅ **#4 実演操作の安定** … キャプチャ/今日/done/オフライン/フォールバック/コールドロードを実機確認済み
- 残: ⑦コールドロードの実測秒数の確定（ナレ台本の【●●秒】埋め）のみ。撮影・編集フェーズ。
- 撮影実務の資料: docs/FILMING_CHECKLIST_EP01.md / EP01_MATERIAL_TASKS.md /
  EP01_NARRATION_CHECKLIST.md / EP01_POST_UPLOAD_MONETIZATION.md

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
- 2026-07-02｜feat｜EP01撮影ゲート#1: systemPromptに話し方ルールを追加し、チャット返答からMarkdown生記法(太字/表/見出し/箇条書き)を排除
- 2026-07-02｜feat｜EP01撮影ゲート#2: 賢いモードの別人感を可視化 — ヘッダーが紫(ローカル)⇔琥珀(賢い/Claude)で切替、各返答に応答元チップ(ローカル/Claude)を表示。フォールバック(⑤)も画で分かる
- 2026-07-02｜feat｜EP01撮影ゲート#3: フローティング常駐コフ(最小構成) — 常時最前面の枠なし別ウィンドウ(/floatingルート)にコフが常駐。顔クリックで開閉(IPCでウィンドウを96x96⇔360x600に伸縮・右下アンカー)、縁とヘッダーはapp-regionドラッグ。Electron時はメイン内アバターを非表示(コフは1体)。RefreshProviderにBroadcastChannelを追加しウィンドウ間でタスク一覧を同期。透過ウィンドウは採用せず(スコープ外)
- 2026-07-02｜docs｜EP01撮影ゲート#4: docs/FILMING_CHECKLIST_EP01.md 新設 — 受け入れ基準の検証手順、オフライン実演の罠(SupabaseはクラウドのためオフラインはLLM会話のみ)、フォールバック/コールドロードの再現手順、inboxキュレーション案
- 2026-07-02｜fix/feat｜フローティングを透過ウィンドウ化(ユーザー指示によりスコープ拡張) — 小窓の白枠なしでコフ本体と吹き出しだけが浮かぶ見た目に。コフ本体でクリック(開閉)/ドラッグ(移動、main processがカーソル追従)。初回起動時の画面外見切れを clampToWorkArea で修正。FLOAT_TRANSPARENT フラグで非透過に即時退避可能
- 2026-07-02｜docs｜docs/EP01_MATERIAL_TASKS.md 新設 — shot_list の撮影素材をコフ(create_entry)に渡せる17タスク×4バッチに再構成。賢いモードでコピペ登録し、着手中にすれば today_view に撮影予定が載る(①B実演の画作りを兼ねる)
- 2026-07-02｜fix｜完了操作が「着手中」「今日」一覧に反映されないバグ修正 — /active・/today が useRefresh 未購読で初回取得のみだった(DBは更新済み・表示だけ古い)。両ページで count を購読。あわせて update_entry を堅牢化(非UUIDはタイトル部分一致で解決・曖昧なら明示エラー)、プロンプトに「ツールerror時は成功と言わない」を追加
- 2026-07-03｜note｜EP01用の実測値を確定(撮影マシン Snapdragon X Elite / RAM 32GB) — `ollama ps`: qwen2.5 5.8GB **100% CPU**。生成中のタスクマネージャー: CPU 69%(3.2GHz)・**NPU 0%**・GPU(Adreno) 12%(描画由来)・RAM 21.7/31.6GB。結論: Ollama推論は純CPU、GPUは非関与。ナレの「CPUで動いている」は実測どおりで正確。「ローカルモードでPCが遅くなる」の体感原因もCPU飽和で確定
- 2026-07-03｜fix｜ローカルモデルの実運用で見つかった2症状に対処 — (1)update_entry のタイトル解決がカギ括弧ごとコピーされた入力(「…」)で失敗 → 前後の括弧/引用符を除去してから照合、候補検索のDBエラーも隠さず返す。(2)ツールを呼ばずに実在しないタスク一覧を捏造 → プロンプトに【捏造の禁止】を明記。なお前回修正の「error時に成功と言わない」は機能していることを実機で確認(コフが失敗を正直に報告するようになった)。捏造クリップは②「小型モデルの弱点」の撮影素材に転用可
- 2026-07-03｜note｜賢いモードのエンドツーエンド動作を実機確認 — ヘッダーが琥珀「賢い (Claude)」に切替(ゲート#2の別人感OK)、着手中3件を実データどおり正確に列挙(捏造なし)、「完了したタスクはまだない」も正答、完了操作が成功し一覧が3件→2件へ即時反映(完了反映fix検証OK)。結論: 同一タスクで ローカル=失敗/捏造 vs Claude=全部正確 の対比が実機で再現 — EP01②⑤の主題「小型ローカルの限界とハイブリッドの意義」がそのまま素材化した
- 2026-07-03｜note｜⑤フォールバック実演の撮影成功 + 撮影ノウハウ確定 — Windows版Ollamaは監視役の "ollama app.exe" が子の ollama.exe を**自動再起動**するため、子だけ殺すと即復活してフォールバックしない(実機で確認)。正解は親→子の順で taskkill(またはトレイからQuit)。死活確認は `ollama list` が接続エラーになること。手順は FILMING_CHECKLIST_EP01.md に反映済み
- 2026-07-03｜feat｜OLLAMA_GEN_TIMEOUT を環境変数化 — .env.local に OLLAMA_GEN_TIMEOUT=8000 を設定すると、修正前の「コールドロード中にタイムアウト→Claude誤フォールバック」をコード編集なしで再現(⑦ビフォー撮影用)。撮影後は行削除で120秒に戻る
- 2026-07-03｜feat｜エージェントの全ツール呼び出しとバックエンド選択をdevターミナルにログ出力 — [agent]受付(prefer/genTimeout)・[agent-tool]名+引数+結果(400字)・応答元/失敗理由。モデルの主張とDB実態が食い違ったときの一次情報
- 2026-07-03｜feat｜チャットに会話クリア(🗑)ボタンを追加 — ×で閉じても会話状態は保持される(フローティングは再読込されない)。長い履歴に小型モデルの過去のハルシネーションが残ると後続応答がツール呼び出しをスキップして不安定化(In-Context Learningによる汚染)。🗑で履歴リセットし確実なツール呼び出しを回復
- 2026-07-03｜feat｜応答からMarkdown記法を機械的に除去 (撮影ゲート#1の安全網) — プロンプト禁止に加え、サーバー側 stripMarkdown で ```code fence```/表/太字/見出し/- [ ]箇条書き/インラインコードを除去。小型モデルが崩しても吹き出しに生記法が出ない二重防御(両バックエンド適用)
- 2026-07-03｜note｜ハルシネーションの根治は7Bでは不可と確認 — お題を「事実確認(今日やること/inbox)」にするとツール呼び出し率が上がり捏造が減る。相談形式は捏造しやすい。撮影は ローカル=事実確認/Claude=相談 の役割分担で回避。将来のサーバー側ガード(ツール未使用なら実データ注入して再生成)はEP02以降の候補(IDEA_BACKLOG級)
- 2026-07-03｜docs｜撮影・収録・後工程の資料を整備 — docs/EP01_NARRATION_CHECKLIST.md(全章VO台本+別テイク)、docs/EP01_POST_UPLOAD_MONETIZATION.md(DaVinci編集/YouTube公開/収益化)。既存の FILMING_CHECKLIST_EP01.md / EP01_MATERIAL_TASKS.md と合わせEP01の実務資料が一式揃った
- 2026-07-03｜docs｜EP01台本レビュー実施(docs/EP01_SCRIPT_REVIEW.md) — 手直し用v2をSCRIPT_REVIEW_GUIDEの評価軸+DEVLOG照合でレビュー。🔴発見: ⑤フォールバックの「ヘッダー色が紫→オレンジに変わる」は実装と不一致(色はトグル連動、フォールバックで変わるのはチップのみ)→台本をチップ基準に修正。🟡: ⑥図解の(Vulkan/GPU)但し書きを純CPUに、②の弱点カットは造語/捏造の実録クリップに。技術記述はDEVLOGとほぼ完全一致で捏造なし。残: ⑦コールドロード実測値の確定
- 2026-07-03｜note｜⑦コールドロード実測値を確定 — `ollama stop qwen2.5` → `Measure-Command { ollama run qwen2.5 }` のクリーン計測で **約20秒**(22.4/19.2/17.5s)。生成タイムアウト120秒に対し十分余裕があり、二段タイムアウトの「解決」は成立(コード変更不要)。⚠️ ただしOBS録画＋多数アプリでメモリ逼迫時はコールドロードが**120秒超→Claudeフォールバック**を観測(POST 129769ms)。⑦のローカル完走ショットは重いアプリを閉じて撮ること(FILMING_CHECKLIST に注意追記)。ナレ台本の【●●秒】は約20秒で確定
- 2026-07-03｜note｜モデルのメモリ保持はOllama管理(KofPro非依存) — Ollamaは最後のリクエストから keep_alive(既定5分)モデルを保持。KofProを閉じても降りない。コールドロードは「アプリ起動時」でなく「モデルがメモリから降りた後の最初のリクエスト」で発生(5分アイドル/`ollama stop`/再起動)。OLLAMA_KEEP_ALIVE を延ばせば常時温存可(5.8GB RAM占有と引き換え)=EP02級ネタ
- 2026-07-03｜docs｜台本レビューに🟡「専門用語のライト層向け言い換え」を追記(EP01_SCRIPT_REVIEW.md) — フォールバック/コールドロード(→コールドスタート寄せも可)/ping/Function Calling/正規化/ルーティング/ONNX等の初出グロス案。主視聴者にNPU気になるライト層を含むため、用語は消さず初出で日常語を1文添える方針
- 2026-07-03｜fix/note｜生成タイムアウトを120s→240sに引き上げ + ⑦の数字を実測で確定 — OBSを閉じてもアプリ初回はフォールバックしていた。原因は「素のモデル読込20秒」ではなく「アプリ初回フル応答=読込+ツール文脈+複数ラウンド生成」が重く、実測 **151.5秒**(dev: POST 151542ms, served by ollama)で旧120秒を超えていたため。240sで 151<240 となりローカル完走を実機確認。⑦ナレの数字を訂正: 「読込だけ約20秒/初回フル応答約150秒(これがタイムアウト発火の主因)/生成タイムアウト240秒」。読込20秒だけでは120秒に引っかからず辻褄が合わない不整合を解消。※起動時ウォームアップで初回コールドを消す案はEP01のⅦ物語を無効化するため採用せず(EP02候補)
- 2026-07-03｜docs｜撮影ショット進捗トラッカー新設(docs/EP01_SHOTLIST_PROGRESS.md) — shot_listを基に✅/🟡/⬜で撮影しながら更新できる進捗表。最優先の証拠系・フォールバック・コールドロードは確保済、残コアはA系(常駐/キャプチャ/done/オフライン/⑤対比/⑥偽りの安心/⑧ダイジェスト)・Bスペック画面・Cコード差分×2、要撮り直しは⑦ビフォー/①⑤別人感
- 2026-07-05｜docs｜IP注意を明記(EP01_SCRIPT_REVIEW / SHOTLIST_PROGRESS) — ①コフ常駐構図の背景に公式ロックマンエグゼのサイト/キービジュアルを小ネタで映す案は不採用。IP_GUIDELINESのNG(キャラデザ/ロゴ/スクショ/ゲーム映像)に該当し、セリフ非言及でも画面表示時点でNG・収益化でContent IDリスク。背景は自分の実物(エディタ/KofPro/ターミナル)、エグゼ愛はコフ+ナレで語る
