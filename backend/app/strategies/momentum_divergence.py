"""Volatile-regime and cross-regime strategy modules."""
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


class DonchianChannelBreakout(BaseStrategy):
    """Donchian Channel Breakout — volatile regime, ATR elevated, breaks 20-period channel."""

    name = "donchian_breakout"

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
        atr_sma20 = self._get(indicators, "atr_sma20")
        donchian_upper = self._get(indicators, "donchian_upper")
        donchian_lower = self._get(indicators, "donchian_lower")
        vol_spike = volume.candle_vs_avg in ("spike", "elevated")

        atr_elevated = atr > 1.5 * atr_sma20
        prereqs_met = (
            regime.type == "volatile"
            and atr_elevated
            and volume.candle_vs_avg in ("spike", "elevated")
        )
        breaks_upper = close >= donchian_upper and vol_spike
        breaks_lower = close <= donchian_lower and vol_spike
        matched = prereqs_met and (breaks_upper or breaks_lower)

        return self._make(
            "Donchian Channel Breakout", "volatile",
            matched, prereqs_met,
            [
                f"Breaking Donchian {'upper' if breaks_upper else 'lower'} "
                f"({donchian_upper:.0f}/{donchian_lower:.0f})"
            ]
            if matched
            else [f"Donchian breakout not confirmed (regime={regime.type})"],
        )


class StandAside(BaseStrategy):
    """Stand Aside — volatile regime with unconvincing volume; no edge."""

    name = "stand_aside"

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
        prereqs_met = regime.type == "volatile"
        matched = prereqs_met and not volume.volume_supports_move

        return self._make(
            "Stand Aside", "volatile",
            matched, prereqs_met,
            ["Volatile regime with unconvincing volume — no edge"]
            if matched
            else [f"Stand aside not triggered (regime={regime.type})"],
        )


class LiquiditySweepReversal(BaseStrategy):
    """Liquidity Sweep Reversal — sweep of key level with reclaim and volume spike."""

    name = "liquidity_sweep_reversal"

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

        prereqs_met = (
            liquidity.event == "sweep"
            and volume.candle_vs_avg in ("spike", "elevated")
        )
        swept_above = liquidity.direction == "bearish" and close > (liquidity.level or close)
        swept_below = liquidity.direction == "bullish" and close < (liquidity.level or close)
        reclaimed = swept_above or swept_below
        matched = prereqs_met and reclaimed

        reasons: list[str] = []
        if liquidity.event == "sweep":
            reasons.append(f"Liquidity sweep {liquidity.direction} at {liquidity.level}")
        if volume.candle_vs_avg in ("spike", "elevated"):
            reasons.append("Volume spike confirms sweep")
        if not liquidity.event:
            reasons.append("No liquidity sweep detected")

        return self._make(
            "Liquidity Sweep Reversal", "cross_regime",
            matched, prereqs_met,
            reasons or ["No sweep event"],
        )
