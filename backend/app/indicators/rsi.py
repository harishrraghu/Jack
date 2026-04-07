"""RSI indicator module."""
from __future__ import annotations

from ta.momentum import RSIIndicator as _RSI

from app.indicators.base import BaseIndicator
from app.schemas import Candle


class RSI(BaseIndicator):
    """Relative Strength Index."""

    name = "rsi"

    def __init__(self, period: int = 14, **kwargs) -> None:
        super().__init__(period=period, **kwargs)
        self._period = period

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        rsi = _RSI(close=df["close"], window=self._period).rsi().fillna(50.0)
        return {f"rsi{self._period}": rsi.round(2).tolist()}
