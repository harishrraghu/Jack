"""Squeeze strategy modules (TTM Squeeze Breakout, Opening Range Breakout)."""
from __future__ import annotations

from app.schemas import (
    Candle,
    DayContext,
    Liquidity,
    Regime,
    Strategy,
    StructureLevels,
    TrendHealth,
    VolumeAnalysis,
)
from app.strategies.base import BaseStrategy


class TTMSqueezeBreakout(BaseStrategy):
    """TTM Squeeze Breakout — BB fires outside Keltner with volume confirmation."""

    name = "ttm_squeeze_breakout"

    def analyze(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        regime: Regime,
        trend_health: TrendHealth | None,
        structure: StructureLevels,
        volume: VolumeAnalysis,
        liquidity: Liquidity,
    ) -> Strategy:
        in_squeeze = bool(self._get(indicators, "in_squeeze") > 0.5)
        sq_fired = bool(self._get(indicators, "squeeze_fired") > 0.5)
        macd_hist = self._get(indicators, "macd_histogram")
        macd_slope = self._get(indicators, "macd_hist_slope")

        prereqs_met = regime.type == "squeeze" or in_squeeze
        sq_long = macd_hist > 0 and macd_slope > 0
        sq_short = macd_hist < 0 and macd_slope < 0
        sq_direction = "long" if sq_long else ("short" if sq_short else "none")
        vol_spike = volume.candle_vs_avg in ("spike", "elevated")
        matched = sq_fired and vol_spike and sq_direction != "none"

        reasons: list[str] = []
        if sq_fired:
            reasons.append("Squeeze fired: BB broke outside Keltner")
        if vol_spike:
            reasons.append(f"Volume spike on squeeze release ({volume.volume_ratio:.1f}x avg)")
        if sq_direction == "long":
            reasons.append("MACD histogram positive and rising — long direction")
        elif sq_direction == "short":
            reasons.append("MACD histogram negative and falling — short direction")
        if not sq_fired:
            reasons.append("Squeeze not yet fired")

        return self._make(
            "TTM Squeeze Breakout", "squeeze",
            matched, prereqs_met,
            reasons or ["No squeeze active"],
        )


class OpeningRangeBreakout(BaseStrategy):
    """Opening Range Breakout — breaks first-candle H/L with elevated volume.

    Note: uses the first candle in the dataset as ORB (simplified; a production
    implementation should filter to the first candle of the trading session by time).
    """

    name = "opening_range_breakout"

    def analyze(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        regime: Regime,
        trend_health: TrendHealth | None,
        structure: StructureLevels,
        volume: VolumeAnalysis,
        liquidity: Liquidity,
    ) -> Strategy:
        if not candles:
            return self._make(
                "Opening Range Breakout", "squeeze",
                False, False, ["No candle data"],
            )

        close = candles[-1].close
        vol_sma20 = self._get(indicators, "volume_sma20")
        orb_high = candles[0].high
        orb_low = candles[0].low

        prereqs_met = volume.candle_vs_avg in ("spike", "elevated")
        breaks_high = close > orb_high and candles[-1].volume > vol_sma20
        breaks_low = close < orb_low and candles[-1].volume > vol_sma20
        matched = prereqs_met and (breaks_high or breaks_low)

        return self._make(
            "Opening Range Breakout", "squeeze",
            matched, prereqs_met,
            [f"Breaking ORB {'high' if breaks_high else 'low'} with volume"]
            if matched
            else ["ORB not broken or volume insufficient"],
        )
