"""Bollinger Bands indicator module."""
from __future__ import annotations

import numpy as np
import pandas as pd
from ta.volatility import BollingerBands as _BB

from app.indicators.base import BaseIndicator
from app.schemas import Candle


def _bb_width_percentile(bb_width: pd.Series, window: int = 50) -> pd.Series:
    """Rolling percentile rank of BB width — used for squeeze detection."""
    def rank_last(arr: np.ndarray) -> float:
        last = arr[-1]
        return float(np.sum(arr < last) / len(arr) * 100)

    return bb_width.rolling(window=window, min_periods=1).apply(rank_last, raw=True)


class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands: upper/middle/lower + normalised width + width percentile."""

    name = "bb"

    def __init__(self, period: int = 20, std_dev: float = 2.0, **kwargs) -> None:
        super().__init__(period=period, std_dev=std_dev, **kwargs)
        self._period = period
        self._std_dev = std_dev

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        close = df["close"]

        bb = _BB(close=close, window=self._period, window_dev=self._std_dev)
        upper = bb.bollinger_hband().fillna(close)
        middle = bb.bollinger_mavg().fillna(close)
        lower = bb.bollinger_lband().fillna(close)

        # Normalised width: (upper-lower)/middle.  Replace zero middle to avoid /0.
        width = ((upper - lower) / middle.replace(0, np.nan)).fillna(0.0)
        width_pct = _bb_width_percentile(width)

        return {
            "bb_upper": upper.round(2).tolist(),
            "bb_middle": middle.round(2).tolist(),
            "bb_lower": lower.round(2).tolist(),
            "bb_width": width.round(4).tolist(),
            "bb_width_percentile": width_pct.round(2).tolist(),
        }
