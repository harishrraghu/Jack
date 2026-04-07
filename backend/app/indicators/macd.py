"""MACD indicator module."""
from __future__ import annotations

from ta.trend import MACD as _MACD

from app.indicators.base import BaseIndicator
from app.schemas import Candle


class MACDIndicator(BaseIndicator):
    """MACD line, signal, histogram, and 3-bar histogram slope."""

    name = "macd"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        **kwargs,
    ) -> None:
        super().__init__(fast=fast, slow=slow, signal=signal, **kwargs)
        self._fast = fast
        self._slow = slow
        self._signal = signal

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        close = df["close"]

        macd = _MACD(
            close=close,
            window_fast=self._fast,
            window_slow=self._slow,
            window_sign=self._signal,
        )
        hist = macd.macd_diff().fillna(0.0)

        return {
            "macd_line": macd.macd().fillna(0.0).round(2).tolist(),
            "macd_signal": macd.macd_signal().fillna(0.0).round(2).tolist(),
            "macd_histogram": hist.round(2).tolist(),
            # 3-bar finite difference of histogram — positive = momentum building
            "macd_hist_slope": hist.diff(3).fillna(0.0).round(4).tolist(),
        }
