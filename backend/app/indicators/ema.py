"""EMA indicator module."""
from __future__ import annotations

from app.indicators.base import BaseIndicator
from app.schemas import Candle


class EMA(BaseIndicator):
    """Exponential Moving Average with 5-bar linear slope."""

    name = "ema"

    def __init__(self, period: int = 21, **kwargs) -> None:
        super().__init__(period=period, **kwargs)
        self._period = period

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        close = df["close"]
        period = self._period

        ema = close.ewm(span=period, adjust=False).mean()
        # Slope: absolute price change per bar over a 5-bar window.
        # Kept as absolute value (same unit as price) — consumers that need
        # percentage slope should normalise by price themselves.
        slope = ((ema - ema.shift(5)) / 5).fillna(0.0)

        return {
            f"ema{period}": ema.round(2).tolist(),
            f"ema{period}_slope": slope.round(4).tolist(),
        }
