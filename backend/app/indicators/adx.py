"""ADX indicator module."""
from __future__ import annotations

from ta.trend import ADXIndicator as _ADX

from app.indicators.base import BaseIndicator
from app.schemas import Candle


class ADXIndicatorWrapper(BaseIndicator):
    """Average Directional Index — measures trend strength (0-100)."""

    name = "adx"

    def __init__(self, period: int = 14, **kwargs) -> None:
        super().__init__(period=period, **kwargs)
        self._period = period

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        adx = _ADX(
            high=df["high"], low=df["low"], close=df["close"], window=self._period
        ).adx().fillna(0.0)
        return {"adx": adx.round(2).tolist()}
