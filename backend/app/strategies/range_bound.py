"""Range-bound strategy modules (BB mean reversion, VWAP reversion, pivot bounce)."""
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


class BollingerMeanReversionLong(BaseStrategy):
    """BB Mean Reversion (Long) — price at lower BB with RSI oversold in range."""

    name = "bb_mean_reversion_long"

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
        last = candles[-1]
        close = last.close
        atr = self._get(indicators, "atr")
        bb_lower = self._get(indicators, "bb_lower")
        bb_middle = self._get(indicators, "bb_middle")
        rsi = self._get(indicators, "rsi14", default=50.0)

        range_ok = regime.type == "range"
        prereqs_met = range_ok and volume.price_volume_divergence != "bearish_divergence"

        at_lower_bb = close <= bb_lower + 0.1 * atr
        rsi_oversold = rsi < 35
        near_support = abs(close - structure.nearest_support) <= 0.5 * atr
        wick_rejection = last.low < bb_lower and last.close > bb_lower
        vol_declining = volume.volume_trend == "contracting"
        matched = prereqs_met and at_lower_bb and rsi_oversold and near_support

        reasons: list[str] = []
        if not range_ok:
            reasons.append(f"Regime {regime.type} is not range")
        elif not prereqs_met:
            reasons.append("Bearish divergence present — skip long")
        else:
            if at_lower_bb:
                reasons.append(f"Price at lower BB ({bb_lower:.0f})")
            if rsi_oversold:
                reasons.append(f"RSI oversold at {rsi:.0f}")
            if near_support:
                reasons.append(f"Near support ({structure.nearest_support:.0f})")
            if wick_rejection:
                reasons.append("Wick rejection below lower BB")
            if vol_declining:
                reasons.append("Volume declining (selling exhaustion)")

        entry = round(close, 2) if matched else None
        stop = round(last.low - 0.2 * atr, 2) if matched else None
        tgt = round(bb_middle, 2) if matched else None
        rr = abs(tgt - entry) / abs(entry - stop) if matched and stop and entry != stop else None

        return self._make(
            "Bollinger Mean Reversion (Long)", "range",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry, stop, tgt, rr,
        )


class BollingerMeanReversionShort(BaseStrategy):
    """BB Mean Reversion (Short) — price at upper BB with RSI overbought in range."""

    name = "bb_mean_reversion_short"

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
        last = candles[-1]
        close = last.close
        atr = self._get(indicators, "atr")
        bb_upper = self._get(indicators, "bb_upper")
        bb_middle = self._get(indicators, "bb_middle")
        rsi = self._get(indicators, "rsi14", default=50.0)

        range_ok = regime.type == "range"
        prereqs_met = range_ok and volume.price_volume_divergence != "bullish_divergence"

        at_upper_bb = close >= bb_upper - 0.1 * atr
        rsi_overbought = rsi > 65
        near_resistance = abs(close - structure.nearest_resistance) <= 0.5 * atr
        matched = prereqs_met and at_upper_bb and rsi_overbought and near_resistance

        reasons: list[str] = []
        if not range_ok:
            reasons.append(f"Regime {regime.type} is not range")
        elif not prereqs_met:
            reasons.append("Bullish divergence present — skip short")
        else:
            if at_upper_bb:
                reasons.append(f"Price at upper BB ({bb_upper:.0f})")
            if rsi_overbought:
                reasons.append(f"RSI overbought at {rsi:.0f}")
            if near_resistance:
                reasons.append(f"Near resistance ({structure.nearest_resistance:.0f})")

        entry = round(close, 2) if matched else None
        stop = round(last.high + 0.2 * atr, 2) if matched else None
        tgt = round(bb_middle, 2) if matched else None
        rr = abs(tgt - entry) / abs(entry - stop) if matched and stop and entry != stop else None

        return self._make(
            "Bollinger Mean Reversion (Short)", "range",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry, stop, tgt, rr,
        )


class VWAPReversion(BaseStrategy):
    """VWAP Reversion — price stretched >1.5 ATR from VWAP with RSI extreme."""

    name = "vwap_reversion"

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
        rsi = self._get(indicators, "rsi14", default=50.0)
        vwap_dist = volume.vwap_distance_atr

        vwap_stretched = vwap_dist > 1.5
        rsi_extreme = rsi < 30 or rsi > 70
        vol_exhaustion = volume.volume_trend == "contracting"
        prereqs_met = regime.type == "range" and vwap_stretched
        matched = prereqs_met and rsi_extreme and vol_exhaustion

        return self._make(
            "VWAP Reversion", "range",
            matched, prereqs_met,
            [f"VWAP distance {vwap_dist:.1f}x ATR, RSI {rsi:.0f}"]
            if matched
            else [f"VWAP distance {vwap_dist:.1f}x ATR (need >1.5)"],
        )


class PivotBounce(BaseStrategy):
    """Pivot Bounce — price at S1 or R1 with no adverse volume spike."""

    name = "pivot_bounce"

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
        close = candles[-1].close
        atr = self._get(indicators, "atr")
        pivot_s1 = self._get(indicators, "pivot_s1")
        pivot_r1 = self._get(indicators, "pivot_r1")

        pivot_bounce_regime = regime.type in ("range", "weak_trend_up", "weak_trend_down")
        near_s1 = abs(close - pivot_s1) <= 0.3 * atr if pivot_s1 else False
        near_r1 = abs(close - pivot_r1) <= 0.3 * atr if pivot_r1 else False
        at_pivot = near_s1 or near_r1
        prereqs_met = pivot_bounce_regime and at_pivot
        vol_ok = volume.candle_vs_avg not in ("spike",)
        matched = prereqs_met and vol_ok

        reasons: list[str] = []
        if at_pivot:
            reasons.append(f"Price at Pivot {'S1' if near_s1 else 'R1'}")
        if vol_ok:
            reasons.append("No adverse volume spike")

        return self._make(
            "Pivot Bounce", "range",
            matched, prereqs_met,
            reasons or [
                f"No pivot level near price (S1={pivot_s1:.0f}, R1={pivot_r1:.0f})"
                if pivot_s1
                else "No pivot data"
            ],
        )
