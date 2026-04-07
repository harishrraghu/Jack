"""Volume Profile indicator module.

Bug fixes applied:
  Bug #4 — Array length mismatch:  All returned arrays are candle-aligned
    (len == len(candles)).  The profile histogram has a different conceptual
    length (= bins), so it is NOT placed in the main indicators dict.  Instead
    we return two candle-aligned series:
      - "volume_poc" : the Point-of-Control price repeated across all candles
        (useful for plotting a horizontal POC line on the chart).
      - "candle_bin_volume" : each candle's close mapped to its price-bin volume
        (gives volume context at each price point in time).

  Bug #9 — pd.cut NaN intervals:  We use ``include_lowest=True`` and guard
    against NaN interval ``mid`` values explicitly before accessing them.
"""
from __future__ import annotations

import pandas as pd

from app.indicators.base import BaseIndicator
from app.schemas import Candle


class VolumeProfile(BaseIndicator):
    """Volume aggregated by price level — returns candle-aligned outputs."""

    name = "volume_profile"

    def __init__(self, period: int | None = None, bins: int = 20, **kwargs) -> None:
        # Bug #6 fix: bins is accepted as int OR float (cast to int for safety).
        # period is accepted but ignored (VolumeProfile has no rolling window).
        super().__init__(bins=bins, **kwargs)
        self._bins = int(bins)

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        n = len(candles)
        df = self._to_df(candles)
        close = df["close"]
        volume = df["volume"]

        fallback_poc = float(close.iloc[-1])

        try:
            # include_lowest=True ensures the minimum price value is always
            # captured in a valid bin, avoiding NaN edges (bug #9).
            price_bins = pd.cut(close, bins=self._bins, include_lowest=True)
            profile = volume.groupby(price_bins, observed=False).sum()
        except Exception:
            # Degenerate data (e.g. constant price): return safe fallback.
            return {
                "volume_poc": [fallback_poc] * n,
                "candle_bin_volume": volume.round(2).tolist(),
            }

        # Bug #9 fix: filter out NaN intervals before accessing .mid
        valid_profile: dict = {}
        for interval, vol in profile.items():
            if interval is not None and hasattr(interval, "mid") and not pd.isna(interval.mid):
                valid_profile[interval] = float(vol)

        if not valid_profile:
            return {
                "volume_poc": [fallback_poc] * n,
                "candle_bin_volume": volume.round(2).tolist(),
            }

        poc_interval = max(valid_profile, key=valid_profile.__getitem__)
        poc_price = round(float(poc_interval.mid), 2)

        # Bug #4 fix: candle_bin_volume maps each candle's close to its bin's
        # accumulated volume — same length as candles, fully chart-alignable.
        candle_bin_vol = price_bins.map(
            lambda iv: float(valid_profile.get(iv, 0.0))
            if iv is not None and hasattr(iv, "mid") and not pd.isna(iv.mid)
            else 0.0
        ).fillna(0.0)

        return {
            "volume_poc": [poc_price] * n,
            "candle_bin_volume": candle_bin_vol.round(2).tolist(),
        }
