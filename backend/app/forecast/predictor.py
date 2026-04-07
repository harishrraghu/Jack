"""
Jill — TimesFM probabilistic forecast predictor.

Bug fixes:
  Bug #3  — _load_model returned None silently:
    The class now uses a lazy-load pattern identical to the existing
    ForecastService but with explicit state tracking.  If TimesFM is not
    installed _available is set to False once and all subsequent calls return
    None immediately without raising AttributeError.

  Bug #7  — Per-request model initialisation:
    JillPredictor is a module-level singleton (one instance per process).
    The heavy model load happens only once on the first forecast call
    (or at startup if ``warmup()`` is called explicitly).

Usage
-----
    from app.forecast.predictor import jill
    result = await jill.predict(candles, horizon=8)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.schemas import Candle, ForecastResult

logger = logging.getLogger(__name__)


class JillPredictor:
    """Singleton TimesFM wrapper.

    Thread-safety note: _load() is called via asyncio.to_thread which means
    it runs in a thread-pool worker.  Because ``_available`` and ``_model``
    are set only once (transition from None → bool / model object), and Python
    GIL protects simple attribute assignment, concurrent first calls are safe
    in practice.  A proper Lock can be added if needed.
    """

    def __init__(self) -> None:
        self._model = None
        # None = not yet attempted; True = loaded; False = unavailable
        self._available: bool | None = None

    # ── internal ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load TimesFM model (blocking — call via asyncio.to_thread).

        Bug #3 fix: if TimesFM is not installed OR any exception occurs during
        loading, ``_available`` is set to False and ``_model`` stays None.
        Subsequent calls short-circuit immediately — no AttributeError.
        """
        if self._available is False:
            return  # already known unavailable; skip

        try:
            import timesfm  # type: ignore[import]

            self._model = timesfm.TimesFm(
                hparams=timesfm.TimesFmHparams(
                    backend="torch",
                    per_core_batch_size=32,
                    horizon_len=8,
                    context_len=128,
                ),
                checkpoint=timesfm.TimesFmCheckpoint(
                    huggingface_repo_id="google/timesfm-2.5-500m-pytorch"
                ),
            )
            self._available = True
            logger.info("Jill (TimesFM) loaded successfully.")
        except ImportError:
            self._available = False
            logger.info("TimesFM not installed — Jill forecasts disabled.")
        except Exception as exc:
            self._available = False
            logger.warning("TimesFM failed to load — Jill forecasts disabled: %s", exc)

    async def warmup(self) -> None:
        """Pre-load the model at application startup (optional).

        Call from FastAPI lifespan to avoid cold-start latency on first request.
        """
        await asyncio.to_thread(self._load)

    async def predict(
        self,
        candles: list[Candle],
        horizon: int = 8,
        lookback: int = 128,
    ) -> Optional[ForecastResult]:
        """Run probabilistic forecast.

        Returns ``None`` if TimesFM is unavailable or the model call fails —
        the caller must handle the None case (Jill is always optional).

        Args:
            candles:  Full candle history; last ``lookback`` candles are used.
            horizon:  Number of future steps to forecast.
            lookback: Context window size fed to the model.
        """
        # Bug #7 fix: _load() is idempotent; call ensures model is loaded.
        await asyncio.to_thread(self._load)

        if not self._available or self._model is None:
            # Bug #3 fix: never attempt self._model.predict when model is None.
            return None

        closes = [c.close for c in candles[-lookback:]]
        if len(closes) < 2:
            logger.warning("Not enough candles for Jill forecast (need ≥2, got %d)", len(closes))
            return None

        try:
            point_forecast, quantile_forecast = await asyncio.to_thread(
                self._model.forecast, [closes], freq=[0]
            )
            p10 = quantile_forecast[0, :, 0].tolist()
            p50 = point_forecast[0].tolist()
            p90 = quantile_forecast[0, :, -1].tolist()

            direction = "up" if p50[-1] > closes[-1] else "down"
            magnitude = abs(p50[-1] - closes[-1])

            return ForecastResult(
                direction=direction,
                magnitude=round(magnitude, 2),
                p10=[round(v, 2) for v in p10],
                p50=[round(v, 2) for v in p50],
                p90=[round(v, 2) for v in p90],
                horizon=horizon,
                confidence_band=round(p90[-1] - p10[-1], 2),
            )
        except Exception as exc:
            logger.warning("Jill forecast failed: %s", exc)
            return None


# ── module-level singleton (bug #7 fix) ───────────────────────────────────────
# Import this instance instead of constructing JillPredictor() per-request.
#
#   from app.forecast.predictor import jill
#   result = await jill.predict(candles)
#
jill = JillPredictor()
