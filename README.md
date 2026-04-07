# BANKNIFTY AI Charting + Narrative Analyst

Deterministic decision-support system for BANKNIFTY using a Next.js 15 frontend and FastAPI backend.

## Architecture

- `frontend/`: Next.js 15 App Router dashboard with Lightweight Charts and custom SVG overlays
- `backend/`: FastAPI analysis engine, journal API, WebSocket stream, SQLAlchemy persistence

## Principles

- No trade execution
- No LLM-driven signal generation
- Modular rule-based engines
- Explainable signals and drawings

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Data Setup

The app runs with sample data out of the box. For real BANKNIFTY data:

1. Download 15-min data from [Kaggle](https://www.kaggle.com/datasets/sandeepkapri/banknifty-data-upto-2024)
2. Run the data fetcher:
   ```bash
   cd backend
   pip install Bharat-sm-data-avinash yfinance
   python scripts/fetch_data.py --kaggle /path/to/downloaded_file.csv
   python scripts/fetch_data.py --recent
   python scripts/fetch_data.py --daily
   python scripts/fetch_data.py --merge
   ```
3. The app will automatically use the merged data on next startup.
