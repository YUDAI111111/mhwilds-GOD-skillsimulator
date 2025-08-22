# WildsSim Web（UI再現MVP）

- GitHub Pages で動く、**Webオンリー**実装（サーバ不要）
- 有志UIの**見た目と動線**を再現（コードは新規実装）
- データはあなたの **Google Sheets 公開CSV** を直読み

## デプロイ（GitHub 上だけでOK）
1. この一式をリポにアップ
2. Settings → Pages → Source: **GitHub Actions**
3. コミットすると `.github/workflows/pages.yml` が自動で実行 → 公開
4. 

## ローカル開発
```bash
npm i
npm run dev
# http://localhost:5173
```

## 現状（MVP）
- 画面タブ：基本条件 / スキル目標 / 護石 / 飾り / 計算 / 結果
- 護石 I/O：**mhwilds互換**
- 最適化：GLPK (WASM) で「装飾品だけで目標を満たす最小個数」
- 次段：防具・シリーズ・妥協検索・理想護石の実装
