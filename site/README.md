# 触れる現像講座(仮) — 静的サイト

副業ロードマップ Phase 0-2 の成果物。ビルド不要の静的サイト(依存ライブラリゼロ)。

## 構成

| ファイル | 内容 |
|----------|------|
| `index.html` | ランディング。章一覧(第0章のみ公開、1〜2章は準備中表示) |
| `tone-curve.html` | 第0章 トーンカーブ実験台(公開版) |
| `portfolio.html` | 受託営業ページ(MVP開発 / 教材制作) |
| `assets/site.css` | 共通スタイル |

## デプロイ (Vercel)

```bash
npm i -g vercel
cd site
vercel --prod
```

または Vercel ダッシュボードで新規プロジェクト作成 → このリポジトリを接続 →
**Root Directory を `site`**、Framework Preset を **Other** に設定。

## 公開前の TODO(人間の作業)

各 HTML 内の `TODO(人間)` コメントが目印:

- [ ] ドメイン取得 → Vercel に接続 → 各ページの `og:url` / `og:image` 差し替え
- [ ] サイト名の確定(現在は「触れる現像講座(仮)」)
- [ ] X アカウント作成 → `index.html` / `portfolio.html` のリンク差し替え
- [ ] 連絡用メールアドレス確定 → `portfolio.html` の `mailto:` 差し替え
- [ ] アナリティクス(GA4 等)のスニペット挿入
- [ ] `portfolio.html` の KofPro にデモ URL かスクリーンショットを追加
- [ ] 受託価格(¥300,000〜 / ¥200,000〜)の最終判断
