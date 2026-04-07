"""
Forecast Service — thin wrapper that delegates to the Jill singleton.

Bug #7 fix: the model is loaded once (module-level singleton in
``app/forecast/predictor.py``) instead of being re-instantiated on every
request.  ForecastService now simply proxies calls to ``jill``.
"""
from __future__ import annotations

from typing import Optional

from app.forecast.predictor import jill
from app.schemas import Candle, ForecastResult


class ForecastService:
    """Layer-7 Jill forecaster — delegates to the module-level singleton."""

    async def forecast(
        self,
        candles: list[Candle],
        horizon: int = 8,
        lookback: int = 128,
    ) -> Optional[ForecastResult]:
        """Return a probabilistic forecast or None if TimesFM is unavailable."""
        return await jill.predict(candles, horizon=horizon, lookback=lookback)
