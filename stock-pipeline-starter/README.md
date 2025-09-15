# Stock Pipeline Starter (Taiwan-friendly)

這是一個「可直接部署」的自動化每日選股與寄信推播範例：
- **GitHub Actions** 於台北時間 18:00（工作日）自動執行
- 讀取 `tickers.txt` 中的股號（台股請加 `.TW`）
- 使用 `yfinance` 快速抓取價量資料，計算一些簡易訊號（5/20MA 金叉、量能異常、站上 MA60）
- 產出 CSV 與 HTML 報表到 `output/`，並用 SMTP 寄信（支援 Gmail）

> 想更進階（FinLab 指標、TWSE/OTC 正式 API、回測等）可把 `main.py` 的資料來源與邏輯換掉即可。

---

## 一、快速開始

1. **建立新 GitHub Repo**，把本專案檔案上傳。
2. 在 Repo 右上角 ➜ **Settings → Secrets and variables → Actions → New repository secret**，新增：  
   - `SMTP_USER`：寄件者帳號（Gmail 通常是你的信箱）  
   - `SMTP_PASS`：寄件用密碼（Gmail 建議使用「應用程式密碼」）  
   - `SMTP_TO`：收件者（可逗號分隔多個）  
   - `SMTP_HOST`（可選，預設 `smtp.gmail.com`）  
   - `SMTP_PORT`（可選，預設 `587`）
3. 編輯 `tickers.txt`，放入你要追蹤的股號（台股記得加 `.TW`）。
4. 進入 **Actions** 分頁，確認 workflow 已啟用；可用 **Run workflow** 立即測試。

> GitHub Actions 使用 **UTC 時區**：本範例的 cron 設為 `30 0 * * 1-5`（00:30 UTC），相當於 **台北 08:30**。

---

## 二、客製化

- **更改排程時間**：修改 `.github/workflows/daily.yml` 的 `cron`。
- **強化策略**：在 `main.py` 新增/替換技術指標（MACD/RSI/K/D/布林）、或接入基本面資料。
- **改用專屬資料源**：若你有 FinLab/TWSE API，將 `fetch_prices()` 改成你的資料抓取函式。
- **報表美化**：把 HTML 轉成帶圖表版本，或輸出 Excel / PDF。
- **改用外部寄信服務**：如 SendGrid / Mailgun / SES，只需替換 `send_email()`。

---

## 三、常見問題

- **可以用 Colab 嗎？**  
  可以，但 Colab 的排程/長期穩定性較受限。若你要「長期無人值守」建議用 **GitHub Actions** 或 **Google Apps Script**。
- **Gmail 不能用一般密碼？**  
  是的。請在 Google 帳號啟用兩步驟驚驗，並建立「應用程式密碼」，將其填入 `SMTP_PASS`。
- **台股代碼要加 .TW？**  
  yfinance 模式下需要（例如 `2330.TW`）。若改接 TWSE 官方 API 就不需要。

---

## 四、下一步（進階方案）

- **GitHub Actions + Google Drive 同步**：把輸出上傳到雲端供同事存取。
- **LINE Notify / Slack 推播**：在 workflow 中呼叫 Webhook，一次推播到你慣用的 IM。
- **多名單/多策略**：拆分多個 `main_*.py` 與多個排程 job。
- **回測/績效追蹤**：把每日訊號結果寫入 SQLite/BigQuery，持續評估策略有效性。

---

Made with ❤️ for Taiwan markets. 如需幫忙客製 FinLab/TWSE 指標或 ESG 因子，歡迎開 Issue/告知你的需求。
