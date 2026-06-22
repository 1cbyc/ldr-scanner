# LDR-Scanner

Real-time event-driven liquidity scanner implementing strict mechanical LDR logic using OANDA v20 REST + Streaming APIs.

## Legacy Snapshot

The previous MT5-based implementation has been moved to:

- `/ldr-scanner/v2026.1`

## Strategy Logic

Primary timeframe: `H1`
Bias confirmation timeframe: `H4`

Bearish LDR requires all of the following on a closed H1 candle:

1. Liquidity sweep: `high > most recent confirmed swing high`
2. Displacement:
1. `body > 1.5 * ATR(14)`
2. close in bottom 25% of range
3. candle range > average of last 10 ranges
3. BOS: close below most recent confirmed swing low
4. Pullback zone: 50% to 75% retracement of displacement body

Bullish logic is the exact inverse.

## Environment Setup

```bash
cd ldr-scanner
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## OANDA Setup

1. Create a demo account at [OANDA](https://www.oanda.com/).
2. Log in to the OANDA dashboard and create a personal access token.
3. Copy your account ID from the account details page.
4. Put credentials in environment variables:

```bash
export OANDA_API_KEY="your_oanda_api_token"
export OANDA_ACCOUNT_ID="your_account_id"
export OANDA_ENVIRONMENT="practice"
```

You can also place values in `/config/settings.yaml`, but environment variables are recommended for production.

## Telegram Setup

1. In Telegram, message `@BotFather`.
2. Run `/newbot` and create your bot.
3. Copy the bot token.
4. Send any message to your new bot.
5. Fetch chat updates:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getUpdates"
```

6. Copy your numeric `chat.id`.
7. Export credentials:

```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## Configure Scanner

Edit `ldr-scanner/config/settings.yaml` for:

- `scanner.instruments`
- `strategy.atr_multiplier`
- `strategy.history_bars`
- `logging.level`
- `logging.file`

## Run

```bash
cd ldr-scanner
source .venv/bin/activate
python main.py
```

## Run In Background

```bash
cd ldr-scanner
source .venv/bin/activate
nohup python main.py > logs/nohup.out 2>&1 &
```

## systemd Service (24/7)

Create `/etc/systemd/system/ldr-scanner.service`:

```ini
[Unit]
Description=LDR Scanner OANDA Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ldr-scanner
Environment="OANDA_API_KEY=your_oanda_api_token"
Environment="OANDA_ACCOUNT_ID=your_account_id"
Environment="OANDA_ENVIRONMENT=practice"
Environment="TELEGRAM_BOT_TOKEN=your_telegram_bot_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/opt/ldr-scanner/.venv/bin/python /opt/ldr-scanner/main.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/ldr-scanner/logs/systemd.out
StandardError=append:/opt/ldr-scanner/logs/systemd.err

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ldr-scanner
sudo systemctl start ldr-scanner
sudo systemctl status ldr-scanner
```

## Alert Message Format

```text
🚨 XAU_USD H1 Bearish LDR Detected
Sweep: 5421.35
Displacement: 1.8 ATR
BOS: Confirmed
Pullback Zone: 5285 – 5295
```

## Please understand that...

- Scanner evaluates only closed candles.
- Streaming connection auto-reconnects with exponential backoff.
- Telegram and OANDA API errors are logged and handled with retries where relevant.
- Use `SIGTERM` or `SIGINT` for graceful shutdown.
