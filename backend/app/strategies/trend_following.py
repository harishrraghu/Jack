"""Trend-following strategy modules (long and short)."""
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

_TRENDING_UP = {"trend_up", "weak_trend_up"}
_TRENDING_DOWN = {"trend_down", "weak_trend_down"}


class EMAPullbackLong(BaseStrategy):
    """EMA Pullback Entry (Long) — price retests EMA21 during an uptrend."""

    name = "ema_pullback_long"

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
        ema21 = self._get(indicators, "ema21")
        ema50 = self._get(indicators, "ema50")
        rsi = self._get(indicators, "rsi14", default=50.0)
        macd_slope = self._get(indicators, "macd_hist_slope")
        stoch_k = self._get(indicators, "stoch_rsi_k", default=0.5)
        stoch_k_prev = (
            float(indicators["stoch_rsi_k"][-2])
            if len(indicators.get("stoch_rsi_k", [])) > 1
            else stoch_k
        )

        up_regime = regime.type in _TRENDING_UP
        layer2_ok = trend_health is not None and trend_health.status == "healthy"
        layer4_ok = volume.volume_supports_move
        prereqs_met = up_regime and layer2_ok and layer4_ok

        near_ema21 = abs(close - ema21) <= 0.2 * atr
        rsi_reset = 40 <= rsi <= 60
        macd_turning_up = macd_slope > 0
        stoch_cross_up = stoch_k_prev <= 0.3 and stoch_k > 0.3
        matched = prereqs_met and near_ema21 and rsi_reset and macd_turning_up and stoch_cross_up

        reasons: list[str] = []
        if not up_regime:
            reasons.append(f"Regime {regime.type} not trending up")
        if not layer2_ok:
            reasons.append("Trend health not healthy" if trend_health else "Trend health not assessed")
        if not layer4_ok:
            reasons.append("Volume not supporting move")
        if prereqs_met:
            if near_ema21:
                reasons.append(f"Price near EMA21 ({ema21:.0f})")
            if rsi_reset:
                reasons.append(f"RSI reset to {rsi:.0f}")
            if macd_turning_up:
                reasons.append("MACD histogram turning up")
            if stoch_cross_up:
                reasons.append("Stoch RSI crossing up from <0.3")

        entry = round(close, 2) if matched else None
        stop = round(min(close - 1.5 * atr, ema50 - 0.2 * atr), 2) if matched else None
        tgt = round(structure.nearest_resistance, 2) if matched else None
        rr = (
            abs(tgt - entry) / abs(entry - stop)
            if matched and stop and entry != stop
            else None
        )

        return self._make(
            "EMA Pullback Entry (Long)", "trend",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry, stop, tgt, rr,
        )


class SupertrendContinuationLong(BaseStrategy):
    """Supertrend Continuation (Long) — pullback to supertrend in uptrend."""

    name = "supertrend_continuation_long"

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
        ema21 = self._get(indicators, "ema21")
        ema50 = self._get(indicators, "ema50")
        supertrend = self._get(indicators, "supertrend")
        st_dir_val = indicators.get("supertrend_direction", [1.0])[-1]
        st_up = float(st_dir_val) >= 0.5
        vol_sma20 = self._get(indicators, "volume_sma20")

        prereqs_met = regime.type in _TRENDING_UP and (
            trend_health is None or trend_health.status != "exhausted"
        )
        near_st = abs(close - supertrend) <= 0.3 * atr
        vol_below = candles[-1].volume < vol_sma20
        ema_ok = ema21 > ema50
        matched = prereqs_met and st_up and near_st and vol_below and ema_ok

        reasons: list[str] = []
        if not prereqs_met:
            reasons.append(f"Prerequisite not met: regime={regime.type} or trend exhausted")
        if prereqs_met:
            if st_up:
                reasons.append("Supertrend direction is up")
            if near_st:
                reasons.append(f"Price near Supertrend ({supertrend:.0f})")
            if vol_below:
                reasons.append("Volume below average (healthy pullback)")
            if ema_ok:
                reasons.append("EMA21 above EMA50")

        entry = round(close, 2) if matched else None
        stop = round(supertrend - 0.3 * atr, 2) if matched else None
        tgt = round(close + 2 * atr, 2) if matched else None
        rr = abs(tgt - entry) / abs(entry - stop) if matched and stop and entry != stop else None

        return self._make(
            "Supertrend Continuation (Long)", "trend",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry, stop, tgt, rr,
        )


class TrendBreakoutLong(BaseStrategy):
    """Trend Breakout (Long) — BB expansion through resistance with volume."""

    name = "trend_breakout_long"

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
        bb_upper = self._get(indicators, "bb_upper")
        bb_width = self._get(indicators, "bb_width")
        bb_width_prev = (
            float(indicators["bb_width"][-2])
            if len(indicators.get("bb_width", [])) > 1
            else bb_width
        )
        kc_upper = self._get(indicators, "kc_upper")
        vol_sma20 = self._get(indicators, "volume_sma20")

        prereqs_met = regime.type in _TRENDING_UP and volume.candle_vs_avg in ("spike", "elevated")
        bb_expanding = bb_width > bb_width_prev
        breaks_res = close > structure.nearest_resistance - 0.1 * atr
        vol_elevated = candles[-1].volume >= 1.5 * vol_sma20
        kc_broken = bb_upper > kc_upper
        matched = prereqs_met and bb_expanding and breaks_res and vol_elevated and kc_broken

        reasons: list[str] = []
        if not prereqs_met:
            reasons.append(f"Prerequisite not met: volume={volume.candle_vs_avg}")
        if prereqs_met:
            if breaks_res:
                reasons.append(f"Price breaking resistance ({structure.nearest_resistance:.0f})")
            if bb_expanding:
                reasons.append("BB width expanding")
            if vol_elevated:
                reasons.append("Volume 1.5x+ average on breakout")
            if kc_broken:
                reasons.append("BB outside Keltner (real expansion)")

        entry = round(close, 2) if matched else None
        stop = round(structure.nearest_resistance - 0.3 * atr, 2) if matched else None
        tgt = round(close + 2.5 * atr, 2) if matched else None
        rr = abs(tgt - entry) / abs(entry - stop) if matched and stop and entry != stop else None

        return self._make(
            "Trend Breakout (Long)", "trend",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry, stop, tgt, rr,
        )


class EMAPullbackShort(BaseStrategy):
    """EMA Pullback Entry (Short) — mirror of long strategy for downtrends."""

    name = "ema_pullback_short"

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
        ema21 = self._get(indicators, "ema21")
        ema50 = self._get(indicators, "ema50")
        rsi = self._get(indicators, "rsi14", default=50.0)
        macd_slope = self._get(indicators, "macd_hist_slope")
        stoch_k = self._get(indicators, "stoch_rsi_k", default=0.5)
        stoch_k_prev = (
            float(indicators["stoch_rsi_k"][-2])
            if len(indicators.get("stoch_rsi_k", [])) > 1
            else stoch_k
        )

        dn_regime = regime.type in _TRENDING_DOWN
        layer2_ok = trend_health is not None and trend_health.status == "healthy"
        layer4_ok = volume.volume_supports_move
        prereqs_met = dn_regime and layer2_ok and layer4_ok

        near_ema21 = abs(close - ema21) <= 0.2 * atr
        rsi_reset = 40 <= rsi <= 60
        macd_turning_dn = macd_slope < 0
        stoch_cross_dn = stoch_k_prev >= 0.7 and stoch_k < 0.7
        matched = prereqs_met and near_ema21 and rsi_reset and macd_turning_dn and stoch_cross_dn

        reasons: list[str] = []
        if not dn_regime:
            reasons.append(f"Regime {regime.type} not trending down")
        if prereqs_met:
            if near_ema21:
                reasons.append(f"Price near EMA21 ({ema21:.0f})")
            if rsi_reset:
                reasons.append(f"RSI reset to {rsi:.0f}")
            if macd_turning_dn:
                reasons.append("MACD histogram turning down")
            if stoch_cross_dn:
                reasons.append("Stoch RSI crossing down from >0.7")

        entry = round(close, 2) if matched else None
        stop = round(max(close + 1.5 * atr, ema50 + 0.2 * atr), 2) if matched else None
        tgt = round(structure.nearest_support, 2) if matched else None
        rr = abs(tgt - entry) / abs(entry - stop) if matched and stop and entry != stop else None

        return self._make(
            "EMA Pullback Entry (Short)", "trend",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry, stop, tgt, rr,
        )


class SupertrendContinuationShort(BaseStrategy):
    """Supertrend Continuation (Short)."""

    name = "supertrend_continuation_short"

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
        ema21 = self._get(indicators, "ema21")
        ema50 = self._get(indicators, "ema50")
        supertrend = self._get(indicators, "supertrend")
        st_dir_val = indicators.get("supertrend_direction", [0.0])[-1]
        st_down = float(st_dir_val) < 0.5
        vol_sma20 = self._get(indicators, "volume_sma20")

        prereqs_met = regime.type in _TRENDING_DOWN and (
            trend_health is None or trend_health.status != "exhausted"
        )
        near_st = abs(close - supertrend) <= 0.3 * atr
        vol_below = candles[-1].volume < vol_sma20
        ema_ok = ema21 < ema50
        matched = prereqs_met and st_down and near_st and vol_below and ema_ok

        reasons: list[str] = []
        if not prereqs_met:
            reasons.append(f"Prerequisite not met: regime={regime.type}")
        if prereqs_met:
            if st_down:
                reasons.append("Supertrend direction is down")
            if near_st:
                reasons.append(f"Price near Supertrend resistance ({supertrend:.0f})")

        return self._make(
            "Supertrend Continuation (Short)", "trend",
            matched, prereqs_met,
            reasons or ["All conditions checked"],
            round(close, 2) if matched else None,
            round(supertrend + 0.3 * atr, 2) if matched else None,
            round(close - 2 * atr, 2) if matched else None,
        )


class TrendBreakoutShort(BaseStrategy):
    """Trend Breakout (Short) — BB expansion through support with volume."""

    name = "trend_breakout_short"

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
        bb_lower = self._get(indicators, "bb_lower")
        bb_width = self._get(indicators, "bb_width")
        bb_width_prev = (
            float(indicators["bb_width"][-2])
            if len(indicators.get("bb_width", [])) > 1
            else bb_width
        )
        kc_lower = self._get(indicators, "kc_lower")
        vol_sma20 = self._get(indicators, "volume_sma20")

        prereqs_met = regime.type in _TRENDING_DOWN and volume.candle_vs_avg in ("spike", "elevated")
        bb_expanding = bb_width > bb_width_prev
        breaks_sup = close < structure.nearest_support + 0.1 * atr
        vol_elevated = candles[-1].volume >= 1.5 * vol_sma20
        kc_broken_dn = bb_lower < kc_lower
        matched = prereqs_met and bb_expanding and breaks_sup and vol_elevated and kc_broken_dn

        return self._make(
            "Trend Breakout (Short)", "trend",
            matched, prereqs_met,
            [f"Price breaking support ({structure.nearest_support:.0f})", "Volume confirms"]
            if matched
            else [f"Prerequisite: regime={regime.type}, volume={volume.candle_vs_avg}"],
            round(close, 2) if matched else None,
            round(structure.nearest_support + 0.3 * atr, 2) if matched else None,
            round(close - 2.5 * atr, 2) if matched else None,
        )
