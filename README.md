# LDR Scanner

I built for traders who use the LDR method to trade and want to be alerted when high quality structural setups form in real time.

This is a detection and alerting tool. I did not build it to place trades.

## Features

- Detects market ranges, liquidity sweeps, displacements, FVGs, order blocks, and mitigation zones.
- Scores setups out of 100 based on structural quality.
- Alerts to Telegram when high-quality setups form — two states: mitigation pending, and price in entry zone.
- Fully asynchronous architecture (FastAPI + PostgreSQL + Redis + arq workers).
- Pure Python 3.12+ — no MT5 or Windows dependencies.
- Integrated backtesting engine over CSV data.
- Live market data via TwelveData API.

---

## Local Development Setup

### Requirements

- Python 3.12+
- Docker and Docker Compose (for local Postgres + Redis)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/1cbyc/ldr-scanner.git
cd ldr-scanner

# 2. Create your environment file from the example
cp .env.example .env
# Fill in your values — especially TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
# TWELVEDATA_API_KEY, and DATABASE_URL.

# 3. Start local infrastructure
docker compose up -d

# 4. Create and activate a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 5. Install the package
pip install -e .

# 6. Run database migrations
alembic upgrade head

# 7. Start the API server
uvicorn app.main:app --reload

# 8. (Separate terminal) Start the background market scanner
arq app.workers.scanner_worker.WorkerSettings
```

### Send sample Telegram alerts

To preview every alert template without waiting for live setups:

```bash
source .venv/bin/activate
python send_sample_alerts.py
```

---

## VPS Deployment

The project is deployed to a remote server using `rsync` over SSH.  
No credentials or secrets are ever committed to Git.

### One-time setup on the VPS

SSH into the server and run the following once:

```bash
# 1. Create the app directory
mkdir -p ~/apps/ldr-scanner

# 2. Create the .env file manually on the server with your real credentials
nano ~/apps/ldr-scanner/.env
# Paste the contents of .env.example and fill in your real values.

# 3. Install Docker Compose v2 plugin (if not already present)
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
  -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose

# 4. Install the systemd API service
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/ldr-scanner.service << 'EOF'
[Unit]
Description=LDR Scanner API
After=network.target

[Service]
WorkingDirectory=/home/<your-user>/apps/ldr-scanner
EnvironmentFile=/home/<your-user>/apps/ldr-scanner/.env
ExecStart=/home/<your-user>/apps/ldr-scanner/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# 5. Install the systemd background worker service
cat > ~/.config/systemd/user/ldr-scanner-worker.service << 'EOF'
[Unit]
Description=LDR Scanner Background Worker
After=network.target ldr-scanner.service

[Service]
WorkingDirectory=/home/<your-user>/apps/ldr-scanner
EnvironmentFile=/home/<your-user>/apps/ldr-scanner/.env
ExecStart=/home/<your-user>/apps/ldr-scanner/.venv/bin/arq app.workers.scanner_worker.WorkerSettings
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# 6. Enable both services to survive reboots
systemctl --user daemon-reload
systemctl --user enable ldr-scanner ldr-scanner-worker

# 7. Allow the user services to run without an active SSH session
sudo loginctl enable-linger <your-user>
```

### Deploying code updates

After making changes locally, sync the code to the VPS and restart the services:

```bash
# Sync code — secrets in .env are excluded automatically
rsync -az --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'v2026-1' \
  --exclude '*.md' \
  -e "ssh -i ~/.ssh/id_ed25519" \
  ./ <your-user>@<your-vps-ip>:~/apps/ldr-scanner/

# Run migrations if the schema changed
ssh -i ~/.ssh/id_ed25519 <your-user>@<your-vps-ip> \
  "cd ~/apps/ldr-scanner && .venv/bin/alembic upgrade head"

# Restart both services
ssh -i ~/.ssh/id_ed25519 <your-user>@<your-vps-ip> \
  "systemctl --user restart ldr-scanner ldr-scanner-worker"
```

> No IP addresses, usernames, or SSH keys belong in this file.  
> Fill in `<your-user>` and `<your-vps-ip>` from your own records.

### Checking logs on the VPS

```bash
# API logs
journalctl --user -u ldr-scanner -f

# Background worker / scanner logs
journalctl --user -u ldr-scanner-worker -f
```

---

## Environment Variables Reference

All configuration is driven by `.env`. See `.env.example` for the full list with comments. Key variables:

| Variable | Description |
|---|---|
| `DATA_PROVIDER` | `twelvedata`, `csv`, or `mock` |
| `TWELVEDATA_API_KEY` | Your TwelveData API key |
| `SYMBOLS` | Comma-separated symbols, e.g. `XAU/USD,NDX` |
| `DEFAULT_TIMEFRAMES` | Comma-separated, e.g. `H1,M15` |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat or group ID |
| `ALERT_SCORE_THRESHOLD` | Minimum score (0–100) to trigger an alert |
| `MIN_RR` | Minimum risk/reward ratio to qualify a setup |
| `SCAN_INTERVAL_SECONDS` | How often the worker scans (default: 60) |

---

## Alert Types

The scanner sends two types of Telegram messages per setup:

1. **Mitigation Pending** — displacement has occurred and an entry zone exists. Price has not yet retraced. The message says to wait.
2. **Entry Zone Touched** — price has retraced into the mitigation zone. The message prompts for a lower-timeframe execution trigger.

Run `python send_sample_alerts.py` to see both types for both instruments sent to your Telegram chat.
