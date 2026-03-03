# LDR-Scanner

Event-based liquidity scanner implementing strict, non-discretionary **Liquidity -> Displacement -> Retracement (LDR)** logic across MT5 symbols/timeframes.



## LDR Rules Implemented

### Bearish LDR

1. Liquidity sweep: current candle high exceeds previous confirmed swing high
2. Displacement: candle body `> 1.5 * ATR(14)`
3. Displacement close condition: close in bottom 25% of candle range
4. BOS: candle close breaks below previous confirmed swing low
5. Pullback zone: 50-75% retracement of displacement candle body

### Bullish LDR (inverse)

1. Liquidity sweep: current candle low breaks previous confirmed swing low
2. Displacement: candle body `> 1.5 * ATR(14)`
3. Displacement close condition: close in top 25% of candle range
4. BOS: candle close breaks above previous confirmed swing high
5. Pullback zone: 50-75% retracement of displacement candle body

## Install

```bash
cd /Users/nsisong/projects/ldr-scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Edit `ldr-scanner/config/settings.yaml`:

- Fill MT5 credentials if needed (`login`, `password`, `server`)
- Set `telegram.enabled: true` and provide `token` + `chat_id`
- Adjust `scan_interval_sec`, ATR multiplier, and fractal window if needed

Recommended for production: leave credential fields empty in YAML and pass them as environment variables:

```bash
export MT5_LOGIN="12345678"
export MT5_PASSWORD="your_mt5_password"
export MT5_SERVER="YourBroker-Server"
export TELEGRAM_BOT_TOKEN="123456789:ABCDEF..."
export TELEGRAM_CHAT_ID="123456789"
```

Supported env variables:
- `MT5_PATH`
- `MT5_LOGIN`
- `MT5_PASSWORD`
- `MT5_SERVER`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Run

```bash
cd ldr-scanner
source .venv/bin/activate
python main.py
```

## Telegram Setup (Example)

1. Open Telegram and start `@BotFather`
2. Run `/newbot` and create bot name + username
3. Copy bot token into `config/settings.yaml -> telegram.token`
4. Open a chat with your bot and send any message (for example: `start`)
5. Get your `chat_id`:

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```

6. Copy numeric `chat.id` into `config/settings.yaml -> telegram.chat_id`
7. Set `telegram.enabled: true`

## Telegram Alert Format

The scanner sends messages in this format:

```text
🚨 XAUUSD H1 – Bearish LDR Detected

Sweep: 5342.15
Displacement: 1.80 ATR
BOS: Confirmed

Wait for pullback 5285.00-5295.00
```

## Notes

- MT5 terminal must be installed and accessible from the machine running Python.
- Symbol names must match your broker's MT5 symbol names exactly.
- Duplicate alerts are prevented by persisted IDs in `logs/alert_state.json`.


&copy; 2026. All rights reserved.
