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

