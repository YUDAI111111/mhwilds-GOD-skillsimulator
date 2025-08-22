# WildsSim Web-Only (WASM)

完全ブラウザ（GitHub Pages）で動く最適化UI。あなたの公開CSVをそのまま読みます。

## ローカル開発
```bash
npm i
npm run dev
# http://localhost:5173

```

## GitHub Pages 配信（自動デプロイ）
1. GitHub にリポを作成して、このフォルダ一式を push
2. 初回 push 後、Actions を有効化
3. push のたびに `gh-pages` ブランチへ自動デプロイ
4. Settings → Pages → Branch: **gh-pages / root** を選択

> ルーティング対策で `404.html` を同梱（`index.html` のコピー）。
