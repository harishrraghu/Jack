# ── Stage 1: build ────────────────────────────────────────────────────────────
# Install all Python dependencies (some packages like `ta` and `asyncpg`
# require gcc/build-essential to compile C extensions).
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# setuptools/wheel must come first so packages that rely on legacy setup.py
# (e.g. `ta`) can build their wheels.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Copy only the installed site-packages into a clean slim image.
FROM python:3.12-slim AS runner

WORKDIR /app

# libgomp is needed at runtime by numpy/pandas (OpenMP).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the builder stage.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source and sample data.
COPY app/ ./app/
COPY data/ ./data/

# Use SQLite in-memory by default; override DATABASE_URL for PostgreSQL.
ENV USE_SQLITE_FALLBACK=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
