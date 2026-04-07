"""VWAP and VWAP-Band indicator modules."""
from __future__ import annotations

import numpy as np

from app.indicators.base import BaseIndicator
from app.schemas import Candle


class VWAP(BaseIndicator):
    """Session VWAP (cumulative from the first candle in the dataset)."""

    name = "vwap"

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        tp = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
        return {"vwap": vwap.round(2).tolist()}


class VWAPBands(BaseIndicator):
    """VWAP ±1σ and ±2σ bands (volume-weighted standard deviation)."""

    name = "vwap_bands"

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        df = self._to_df(candles)
        high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]

        tp = (high + low + close) / 3
        cum_vol = volume.cumsum()
        vwap = (tp * volume).cumsum() / cum_vol

        variance = ((tp - vwap) ** 2 * volume).cumsum() / cum_vol
        std = np.sqrt(variance.clip(lower=0))

        return {
            "vwap_upper1": (vwap + std).round(2).tolist(),
            "vwap_lower1": (vwap - std).round(2).tolist(),
            "vwap_upper2": (vwap + 2 * std).round(2).tolist(),
            "vwap_lower2": (vwap - 2 * std).round(2).tolist(),
        }
