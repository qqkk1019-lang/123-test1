# -*- coding: utf-8 -*-
"""
Scheduled stock scan + email push
- Reads tickers from tickers.txt (one per line). For TW tickers, use the .TW suffix (e.g., 0050.TW).
- Fetches daily price data, computes simple technical/fundamental-ish signals (price MA cross + volume spike).
- Exports CSV and HTML to ./output
- Emails results via SMTP (e.g., Gmail) using env vars:
    SMTP_USER, SMTP_PASS, SMTP_TO (comma-separated), SMTP_HOST (default smtp.gmail.com), SMTP_PORT (default 587)
Environment variables are configured as GitHub Actions secrets.
"""

import os
import io
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone, timedelta

import pandas as pd
import numpy as np

# yfinance is convenient for quick starts. For production / low-latency or TWSE specifics, swap to official APIs.
import yfinance as yf

OUTPUT_DIR = "output"
TICKERS_FILE = "tickers.txt"

def load_tickers(path=TICKERS_FILE):
    with open(path, "r", encoding="utf-8") as f:
        tickers = [x.strip() for x in f.readlines() if x.strip() and not x.startswith("#")]
    return tickers

def fetch_prices(tickers, period="6mo"):
    # yfinance can fetch multiple tickers at once
    data = yf.download(tickers, period=period, group_by='ticker', auto_adjust=False, progress=False)
    return data

def compute_signals(data):
    rows = []
    # When multiple tickers, data is a column MultiIndex: (ticker, field). Handle 1 or many.
    is_multi = isinstance(data.columns, pd.MultiIndex)
    universe = [c[0] for c in data.columns if c[1] == 'Close'] if is_multi else ['SINGLE']

    for t in sorted(set(universe)):
        if is_multi:
            close = data[(t, 'Close')].dropna()
            vol   = data[(t, 'Volume')].dropna()
        else:
            close = data['Close'].dropna()
            vol   = data['Volume'].dropna()

        if len(close) < 50:
            continue

        ma5  = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        vol20 = vol.rolling(20).mean()

        last_date = close.index[-1]
        today_px  = float(close.iloc[-1])
        dchg      = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) > 1 else np.nan
        ma_cross  = int(ma5.iloc[-2] < ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1])  # golden cross today
        vol_spike = int(vol.iloc[-1] > 1.5 * vol20.iloc[-1]) if not np.isnan(vol20.iloc[-1]) else 0
        trend60   = float((today_px / ma60.iloc[-1] - 1) * 100) if not np.isnan(ma60.iloc[-1]) else np.nan

        rows.append({
            "ticker": t,
            "date": last_date.date().isoformat(),
            "price": round(today_px, 4),
            "d_change_%": round(dchg, 2) if not np.isnan(dchg) else None,
            "golden_cross_5_20": bool(ma_cross),
            "vol_spike_vs_20d": bool(vol_spike),
            "above_ma60_%": round(trend60, 2) if not np.isnan(trend60) else None,
        })

    df = pd.DataFrame(rows).sort_values(["golden_cross_5_20","vol_spike_vs_20d","above_ma60_%","d_change_%"], ascending=[False, False, False, False])
    return df

def export_reports(df):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M")
    csv_path = os.path.join(OUTPUT_DIR, f"scan_{ts}.csv")
    html_path = os.path.join(OUTPUT_DIR, f"scan_{ts}.html")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Simple HTML with some highlighting
    html = io.StringIO()
    html.write("<html><head><meta charset='utf-8'><title>Daily Scan</title></head><body>")
    html.write("<h2>Daily Stock Scan</h2>")
    html.write(df.to_html(index=False, justify='center'))
    html.write("<p style='color:#666'>Generated at: {}</p>".format(datetime.now().astimezone().isoformat()))
    html.write("</body></html>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html.getvalue())

    return csv_path, html_path

def send_email(subject, body_html, attachments=None):
    user = os.environ.get("SMTP_USER")
    pwd  = os.environ.get("SMTP_PASS")
    to   = os.environ.get("SMTP_TO", "")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))

    if not (user and pwd and to):
        print("[WARN] SMTP env vars missing; skip email. Required: SMTP_USER, SMTP_PASS, SMTP_TO")
        return False

    recipients = [x.strip() for x in to.split(",") if x.strip()]

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html", "utf-8"))

    for path in (attachments or []):
        part = MIMEBase("application", "octet-stream")
        with open(path, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(user, pwd)
        server.sendmail(user, recipients, msg.as_string())

    print("[OK] Email sent to:", recipients)
    return True

def main():
    tz = timezone(timedelta(hours=8))  # Asia/Taipei
    now_local = datetime.now(tz)

    tickers = load_tickers()
    print(f"[INFO] Loaded {len(tickers)} tickers.")

    data = fetch_prices(tickers)
    df = compute_signals(data)
    csv_path, html_path = export_reports(df)

    subject = f"📈 每日選股掃描（台北時間 {now_local.strftime('%Y-%m-%d %H:%M')}）"
    body = f"""
    <p>您好，這是自動化每日選股掃描。</p>
    <p>Top 10：</p>
    {df.head(10).to_html(index=False)}
    <p>完整結果請見附件（CSV/HTML）。</p>
    """
    send_email(subject, body, [csv_path, html_path])

if __name__ == "__main__":
    main()
