# LDR Scanner

I bult a broker independent scanner for Liquidity Displacement Reversal (LDR) setups. I trade financial markets with LDR, so I decided to build a means to get setups.

## Features
- Detects market ranges, sweeps, displacements, FVGs, order blocks, and mitigation zones.
- Scores setups out of 100 based on structural quality.
- Alerts to Telegram when high-quality setups form.
- Fully asynchronous architecture with FastAPI, Postgres, and background workers.
- Pure Python 3.12+ (no MT5 or Windows dependencies).
- Integrated backtesting engine over CSV data.

## Setup Instructions

### Requirements
- Python 3.12+
- Docker and Docker Compose
- Poetry / Pip (via pyproject.toml)

### Installation
1. Clone the repository and navigate to the project root.
2. Copy `.env.example` to `.env` and fill in the required variables (especially `TELEGRAM_BOT_TOKEN`).
3. Run `docker compose up -d` to start PostgreSQL and Redis.
4. Install dependencies:
   ```bash
   pip install -e .
   ```
5. Run database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```
7. (Optional) Run the background worker for scanning:
   ```bash
   arq run app.workers.scanner_worker.WorkerSettings
   ```
