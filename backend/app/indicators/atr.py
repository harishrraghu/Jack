"""ATR indicator module."""
from __future__ import annotations

import pandas as pd

from app.indicators.base import BaseIndicator
from app.schemas import Candle


def _true_range(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> pd.Series:
    return pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)


class ATR(BaseIndicator):
    """Average True Range + 20-bar SMA of ATR (used as volatility baseline)."""

    name = "atr"

    def __init__(self, period: int = 14, **kwargs) -> None:
        super().__init__(period=period, **kwargs)
        self._period = period

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        high, low, close = df["high"], df["low"], df["close"]

        tr = _true_range(high, low, close)
        atr = tr.rolling(window=self._period).mean().bfill().fillna(0.0)
        atr_sma20 = atr.rolling(window=20).mean().bfill().fillna(0.0)

        return {
            "atr": atr.round(2).tolist(),
            "atr_sma20": atr_sma20.round(2).tolist(),
        }
