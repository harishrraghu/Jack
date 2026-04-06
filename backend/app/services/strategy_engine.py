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

_TRENDING_UP = {"trend_up", "weak_trend_up"}
_TRENDING_DOWN = {"trend_down", "weak_trend_down"}
_ALL_TRENDING = _TRENDING_UP | _TRENDING_DOWN


def _safe_get(d: dict, key: str, idx: int = -1, default: float = 0.0) -> float:
    lst = d.get(key, [])
    if not lst:
        return default
    return float(lst[idx])


def _make(
    name: str,
    category: str,
    matched: bool,
    prereqs_met: bool,
    reasons: list[str],
    entry: float | None = None,
    stop: float | None = None,
    target: float | None = None,
    rr: float | None = None,
) -> Strategy:
    return Strategy(
        name=name,
        category=category,
        matched=matched,
        prerequisites_met=prereqs_met,
        reasons=reasons,
        entry_price=entry,
        stop_loss=stop,
        target_price=target,
        risk_reward=rr,
    )


class StrategyEngine:
    def evaluate(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        regime: Regime,
        trend_health: TrendHealth | None,
        structure: StructureLevels,
        volume: VolumeAnalysis,
        liquidity: Liquidity,
    ) -> list[Strategy]:
        last = candles[-1]
        close = last.close
        atr = _safe_get(indicators, "atr")
        ema21 = _safe_get(indicators, "ema21")
        ema50 = _safe_get(indicators, "ema50")
        rsi = _safe_get(indicators, "rsi14", default=50.0)
        bb_upper = _safe_get(indicators, "bb_upper")
        bb_lower = _safe_get(indicators, "bb_lower")
        bb_middle = _safe_get(indicators, "bb_middle")
        macd_hist = _safe_get(indicators, "macd_histogram")
        macd_hist_slope = _safe_get(indicators, "macd_hist_slope")
        stoch_k = _safe_get(indicators, "stoch_rsi_k", default=0.5)
        stoch_k_prev = float(indicators["stoch_rsi_k"][-2]) if len(indicators.get("stoch_rsi_k", [])) > 1 else stoch_k
        supertrend = _safe_get(indicators, "supertrend")
        _st_dir_val = indicators.get("supertrend_direction", [1.0])[-1]
        st_dir = "up" if float(_st_dir_val) >= 0.5 else "down"
        vol_sma20 = _safe_get(indicators, "volume_sma20")
        in_squeeze = bool(_safe_get(indicators, "in_squeeze") > 0.5)
        sq_fired = bool(_safe_get(indicators, "squeeze_fired") > 0.5)
        donchian_upper = _safe_get(indicators, "donchian_upper")
        donchian_lower = _safe_get(indicators, "donchian_lower")
        kc_upper = _safe_get(indicators, "kc_upper")
        kc_lower = _safe_get(indicators, "kc_lower")
        pivot_r1 = _safe_get(indicators, "pivot_r1")
        pivot_s1 = _safe_get(indicators, "pivot_s1")
        pivot = _safe_get(indicators, "pivot")
        bb_width = _safe_get(indicators, "bb_width")
        bb_width_prev = float(indicators["bb_width"][-2]) if len(indicators.get("bb_width", [])) > 1 else bb_width

        strategies: list[Strategy] = []

        # ========================
        # TREND_UP strategies
        # ========================

        # --- EMA Pullback Entry (long) ---
        up_prereqs = regime.type in _TRENDING_UP
        layer2_ok = trend_health is not None and trend_health.status == "healthy"
        layer4_ok = volume.volume_supports_move

        prereqs_met = up_prereqs and layer2_ok and layer4_ok
        near_ema21 = abs(close - ema21) <= 0.2 * atr
        rsi_reset = 40 <= rsi <= 60
        macd_turning_up = macd_hist_slope > 0
        stoch_cross_up = stoch_k_prev <= 0.3 and stoch_k > 0.3
        ema_pullback_matched = prereqs_met and near_ema21 and rsi_reset and macd_turning_up and stoch_cross_up

        reasons = []
        if not up_prereqs:
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

        entry_p = round(close, 2) if ema_pullback_matched else None
        stop_p = round(min(close - 1.5 * atr, ema50 - 0.2 * atr), 2) if ema_pullback_matched else None
        tgt_p = round(structure.nearest_resistance, 2) if ema_pullback_matched else None
        rr_val = (abs(tgt_p - entry_p) / abs(entry_p - stop_p)) if ema_pullback_matched and stop_p and tgt_p and entry_p != stop_p else None

        strategies.append(_make(
            "EMA Pullback Entry (Long)", "trend",
            ema_pullback_matched, prereqs_met,
            reasons or ["All conditions checked"],
            entry_p, stop_p, tgt_p, rr_val,
        ))

        # --- Supertrend Continuation (long) ---
        st_prereqs = regime.type in _TRENDING_UP and (trend_health is None or trend_health.status != "exhausted")
        st_up = st_dir == "up"
        near_st = abs(close - supertrend) <= 0.3 * atr
        vol_below_avg = last.volume < vol_sma20
        ema21_above_50 = ema21 > ema50
        st_cont_matched = st_prereqs and st_up and near_st and vol_below_avg and ema21_above_50

        st_reasons = []
        if not st_prereqs:
            st_reasons.append(f"Prerequisite not met: regime={regime.type} or trend exhausted")
        if st_prereqs:
            if st_up:
                st_reasons.append("Supertrend direction is up")
            if near_st:
                st_reasons.append(f"Price near Supertrend ({supertrend:.0f})")
            if vol_below_avg:
                st_reasons.append("Volume below average (healthy pullback)")
            if ema21_above_50:
                st_reasons.append("EMA21 above EMA50")

        st_entry = round(close, 2) if st_cont_matched else None
        st_stop = round(supertrend - 0.3 * atr, 2) if st_cont_matched else None
        st_tgt = round(close + 2 * atr, 2) if st_cont_matched else None
        st_rr = (abs(st_tgt - st_entry) / abs(st_entry - st_stop)) if st_cont_matched and st_stop and st_entry != st_stop else None

        strategies.append(_make(
            "Supertrend Continuation (Long)", "trend",
            st_cont_matched, st_prereqs,
            st_reasons or ["All conditions checked"],
            st_entry, st_stop, st_tgt, st_rr,
        ))

        # --- Trend Breakout (long) ---
        bo_prereqs = regime.type in _TRENDING_UP and volume.candle_vs_avg in ("spike", "elevated")
        bb_expanding = bb_width > bb_width_prev
        price_breaks_resistance = close > structure.nearest_resistance - 0.1 * atr
        vol_elevated = last.volume >= 1.5 * vol_sma20
        kc_broken = bb_upper > kc_upper  # BB outside Keltner
        trend_bo_matched = bo_prereqs and bb_expanding and price_breaks_resistance and vol_elevated and kc_broken

        bo_reasons = []
        if not bo_prereqs:
            bo_reasons.append(f"Prerequisite not met: volume={volume.candle_vs_avg}")
        if bo_prereqs:
            if price_breaks_resistance:
                bo_reasons.append(f"Price breaking resistance ({structure.nearest_resistance:.0f})")
            if bb_expanding:
                bo_reasons.append("BB width expanding")
            if vol_elevated:
                bo_reasons.append("Volume 1.5x+ average on breakout")
            if kc_broken:
                bo_reasons.append("BB outside Keltner (real expansion)")

        bo_entry = round(close, 2) if trend_bo_matched else None
        bo_stop = round(structure.nearest_resistance - 0.3 * atr, 2) if trend_bo_matched else None
        bo_tgt = round(close + 2.5 * atr, 2) if trend_bo_matched else None
        bo_rr = (abs(bo_tgt - bo_entry) / abs(bo_entry - bo_stop)) if trend_bo_matched and bo_stop and bo_entry != bo_stop else None

        strategies.append(_make(
            "Trend Breakout (Long)", "trend",
            trend_bo_matched, bo_prereqs,
            bo_reasons or ["All conditions checked"],
            bo_entry, bo_stop, bo_tgt, bo_rr,
        ))

        # ========================
        # TREND_DOWN mirror strategies
        # ========================

        # --- EMA Pullback Entry (short) ---
        dn_prereqs = regime.type in _TRENDING_DOWN
        dn_layer2_ok = trend_health is not None and trend_health.status == "healthy"
        dn_layer4_ok = volume.volume_supports_move
        dn_prereqs_met = dn_prereqs and dn_layer2_ok and dn_layer4_ok

        near_ema21_dn = abs(close - ema21) <= 0.2 * atr
        rsi_reset_dn = 40 <= rsi <= 60
        macd_turning_dn = macd_hist_slope < 0
        stoch_cross_dn = stoch_k_prev >= 0.7 and stoch_k < 0.7
        ema_pb_dn_matched = dn_prereqs_met and near_ema21_dn and rsi_reset_dn and macd_turning_dn and stoch_cross_dn

        dn_reasons = []
        if not dn_prereqs:
            dn_reasons.append(f"Regime {regime.type} not trending down")
        if dn_prereqs_met:
            if near_ema21_dn:
                dn_reasons.append(f"Price near EMA21 ({ema21:.0f})")
            if rsi_reset_dn:
                dn_reasons.append(f"RSI reset to {rsi:.0f}")
            if macd_turning_dn:
                dn_reasons.append("MACD histogram turning down")
            if stoch_cross_dn:
                dn_reasons.append("Stoch RSI crossing down from >0.7")

        dn_pb_entry = round(close, 2) if ema_pb_dn_matched else None
        dn_pb_stop = round(max(close + 1.5 * atr, ema50 + 0.2 * atr), 2) if ema_pb_dn_matched else None
        dn_pb_tgt = round(structure.nearest_support, 2) if ema_pb_dn_matched else None
        dn_pb_rr = (abs(dn_pb_tgt - dn_pb_entry) / abs(dn_pb_entry - dn_pb_stop)) if ema_pb_dn_matched and dn_pb_stop and dn_pb_entry != dn_pb_stop else None

        strategies.append(_make(
            "EMA Pullback Entry (Short)", "trend",
            ema_pb_dn_matched, dn_prereqs_met,
            dn_reasons or ["All conditions checked"],
            dn_pb_entry, dn_pb_stop, dn_pb_tgt, dn_pb_rr,
        ))

        # --- Supertrend Continuation (short) ---
        st_dn_prereqs = regime.type in _TRENDING_DOWN and (trend_health is None or trend_health.status != "exhausted")
        st_down = st_dir == "down"
        near_st_dn = abs(close - supertrend) <= 0.3 * atr
        st_cont_dn = st_dn_prereqs and st_down and near_st_dn and vol_below_avg and ema21 < ema50

        st_dn_reasons = []
        if not st_dn_prereqs:
            st_dn_reasons.append(f"Prerequisite not met: regime={regime.type}")
        if st_dn_prereqs:
            if st_down:
                st_dn_reasons.append("Supertrend direction is down")
            if near_st_dn:
                st_dn_reasons.append(f"Price near Supertrend resistance ({supertrend:.0f})")

        strategies.append(_make(
            "Supertrend Continuation (Short)", "trend",
            st_cont_dn, st_dn_prereqs,
            st_dn_reasons or ["All conditions checked"],
            round(close, 2) if st_cont_dn else None,
            round(supertrend + 0.3 * atr, 2) if st_cont_dn else None,
            round(close - 2 * atr, 2) if st_cont_dn else None,
        ))

        # --- Trend Breakout (short) ---
        bo_dn_prereqs = regime.type in _TRENDING_DOWN and volume.candle_vs_avg in ("spike", "elevated")
        price_breaks_support = close < structure.nearest_support + 0.1 * atr
        kc_broken_dn = bb_lower < kc_lower
        trend_bo_dn = bo_dn_prereqs and bb_expanding and price_breaks_support and vol_elevated and kc_broken_dn

        strategies.append(_make(
            "Trend Breakout (Short)", "trend",
            trend_bo_dn, bo_dn_prereqs,
            [f"Price breaking support ({structure.nearest_support:.0f})", "Volume confirms"] if trend_bo_dn else [f"Prerequisite: regime={regime.type}, volume={volume.candle_vs_avg}"],
            round(close, 2) if trend_bo_dn else None,
            round(structure.nearest_support + 0.3 * atr, 2) if trend_bo_dn else None,
            round(close - 2.5 * atr, 2) if trend_bo_dn else None,
        ))

        # ========================
        # RANGE strategies
        # ========================

        # --- Bollinger Mean Reversion (Long) ---
        range_prereqs = regime.type == "range"
        bmr_l_prereqs = range_prereqs and volume.price_volume_divergence != "bearish_divergence"
        at_lower_bb = close <= bb_lower + 0.1 * atr
        rsi_oversold = rsi < 35
        vol_declining_on_drop = volume.volume_trend == "contracting"
        near_support_zone = abs(close - structure.nearest_support) <= 0.5 * atr
        # Rejection: low below BB but close above it
        wick_rejection = last.low < bb_lower and last.close > bb_lower
        bmr_l_matched = bmr_l_prereqs and at_lower_bb and rsi_oversold and near_support_zone

        bmr_l_reasons = []
        if not range_prereqs:
            bmr_l_reasons.append(f"Regime {regime.type} is not range")
        elif not bmr_l_prereqs:
            bmr_l_reasons.append("Bearish divergence present — skip long")
        else:
            if at_lower_bb:
                bmr_l_reasons.append(f"Price at lower BB ({bb_lower:.0f})")
            if rsi_oversold:
                bmr_l_reasons.append(f"RSI oversold at {rsi:.0f}")
            if near_support_zone:
                bmr_l_reasons.append(f"Near support ({structure.nearest_support:.0f})")
            if wick_rejection:
                bmr_l_reasons.append("Wick rejection below lower BB")
            if vol_declining_on_drop:
                bmr_l_reasons.append("Volume declining (selling exhaustion)")

        bmr_l_entry = round(close, 2) if bmr_l_matched else None
        bmr_l_stop = round(last.low - 0.2 * atr, 2) if bmr_l_matched else None
        bmr_l_tgt = round(bb_middle, 2) if bmr_l_matched else None
        bmr_l_rr = (abs(bmr_l_tgt - bmr_l_entry) / abs(bmr_l_entry - bmr_l_stop)) if bmr_l_matched and bmr_l_stop and bmr_l_entry != bmr_l_stop else None

        strategies.append(_make(
            "Bollinger Mean Reversion (Long)", "range",
            bmr_l_matched, bmr_l_prereqs,
            bmr_l_reasons or ["All conditions checked"],
            bmr_l_entry, bmr_l_stop, bmr_l_tgt, bmr_l_rr,
        ))

        # --- Bollinger Mean Reversion (Short) ---
        bmr_s_prereqs = range_prereqs and volume.price_volume_divergence != "bullish_divergence"
        at_upper_bb = close >= bb_upper - 0.1 * atr
        rsi_overbought = rsi > 65
        near_resistance_zone = abs(close - structure.nearest_resistance) <= 0.5 * atr
        bmr_s_matched = bmr_s_prereqs and at_upper_bb and rsi_overbought and near_resistance_zone

        bmr_s_reasons = []
        if not range_prereqs:
            bmr_s_reasons.append(f"Regime {regime.type} is not range")
        elif not bmr_s_prereqs:
            bmr_s_reasons.append("Bullish divergence present — skip short")
        else:
            if at_upper_bb:
                bmr_s_reasons.append(f"Price at upper BB ({bb_upper:.0f})")
            if rsi_overbought:
                bmr_s_reasons.append(f"RSI overbought at {rsi:.0f}")
            if near_resistance_zone:
                bmr_s_reasons.append(f"Near resistance ({structure.nearest_resistance:.0f})")

        bmr_s_entry = round(close, 2) if bmr_s_matched else None
        bmr_s_stop = round(last.high + 0.2 * atr, 2) if bmr_s_matched else None
        bmr_s_tgt = round(bb_middle, 2) if bmr_s_matched else None
        bmr_s_rr = (abs(bmr_s_tgt - bmr_s_entry) / abs(bmr_s_entry - bmr_s_stop)) if bmr_s_matched and bmr_s_stop and bmr_s_entry != bmr_s_stop else None

        strategies.append(_make(
            "Bollinger Mean Reversion (Short)", "range",
            bmr_s_matched, bmr_s_prereqs,
            bmr_s_reasons or ["All conditions checked"],
            bmr_s_entry, bmr_s_stop, bmr_s_tgt, bmr_s_rr,
        ))

        # --- VWAP Reversion ---
        vwap_dist = volume.vwap_distance_atr
        vwap_stretched = vwap_dist > 1.5
        rsi_extreme = rsi < 30 or rsi > 70
        vol_exhaustion = volume.volume_trend == "contracting"
        vwap_rev_prereqs = range_prereqs and vwap_stretched
        vwap_rev_matched = vwap_rev_prereqs and rsi_extreme and vol_exhaustion

        strategies.append(_make(
            "VWAP Reversion", "range",
            vwap_rev_matched, vwap_rev_prereqs,
            [f"VWAP distance {vwap_dist:.1f}x ATR, RSI {rsi:.0f}"] if vwap_rev_matched else [f"VWAP distance {vwap_dist:.1f}x ATR (need >1.5)"],
        ))

        # --- Pivot Bounce ---
        pivot_bounce_regime = regime.type in ("range", "weak_trend_up", "weak_trend_down")
        near_pivot_s1 = abs(close - pivot_s1) <= 0.3 * atr if pivot_s1 else False
        near_pivot_r1 = abs(close - pivot_r1) <= 0.3 * atr if pivot_r1 else False
        at_pivot = near_pivot_s1 or near_pivot_r1
        pivot_bounce_prereqs = pivot_bounce_regime and at_pivot
        vol_not_against = volume.candle_vs_avg not in ("spike",)
        pivot_bounce_matched = pivot_bounce_prereqs and vol_not_against

        pv_reasons = []
        if at_pivot:
            pv_reasons.append(f"Price at Pivot {'S1' if near_pivot_s1 else 'R1'}")
        if vol_not_against:
            pv_reasons.append("No adverse volume spike")

        strategies.append(_make(
            "Pivot Bounce", "range",
            pivot_bounce_matched, pivot_bounce_prereqs,
            pv_reasons or [f"No pivot level near price (S1={pivot_s1:.0f}, R1={pivot_r1:.0f})" if pivot_s1 else "No pivot data"],
        ))

        # ========================
        # SQUEEZE strategies
        # ========================

        # --- TTM Squeeze Breakout ---
        sq_prereqs = regime.type == "squeeze" or in_squeeze
        sq_fired_now = sq_fired and in_squeeze is False  # Was in squeeze, now fired
        # Use MACD histogram for direction
        sq_long = macd_hist > 0 and macd_hist_slope > 0
        sq_short = macd_hist < 0 and macd_hist_slope < 0
        sq_direction = "long" if sq_long else ("short" if sq_short else "none")
        vol_spike = volume.candle_vs_avg in ("spike", "elevated")
        sq_matched = sq_fired and vol_spike and sq_direction != "none"

        sq_reasons = []
        if sq_fired:
            sq_reasons.append("Squeeze fired: BB broke outside Keltner")
        if vol_spike:
            sq_reasons.append(f"Volume spike on squeeze release ({volume.volume_ratio:.1f}x avg)")
        if sq_direction == "long":
            sq_reasons.append("MACD histogram positive and rising — long direction")
        elif sq_direction == "short":
            sq_reasons.append("MACD histogram negative and falling — short direction")
        if not sq_fired:
            sq_reasons.append("Squeeze not yet fired")

        strategies.append(_make(
            "TTM Squeeze Breakout", "squeeze",
            sq_matched, sq_prereqs,
            sq_reasons or ["No squeeze active"],
        ))

        # --- Opening Range Breakout ---
        # Use first candle's high/low as ORB (simplified without time-of-day check)
        orb_high = candles[0].high if candles else close
        orb_low = candles[0].low if candles else close
        orb_range = orb_high - orb_low
        orb_prereqs = volume.candle_vs_avg in ("spike", "elevated")
        breaks_orb_high = close > orb_high and last.volume > vol_sma20
        breaks_orb_low = close < orb_low and last.volume > vol_sma20
        orb_matched = orb_prereqs and (breaks_orb_high or breaks_orb_low)

        strategies.append(_make(
            "Opening Range Breakout", "squeeze",
            orb_matched, orb_prereqs,
            [f"Breaking ORB {'high' if breaks_orb_high else 'low'} with volume"] if orb_matched else ["ORB not broken or volume insufficient"],
        ))

        # ========================
        # VOLATILE strategies
        # ========================

        atr_elevated = _safe_get(indicators, "atr") > 1.5 * _safe_get(indicators, "atr_sma20")

        # --- Donchian Breakout ---
        don_prereqs = regime.type == "volatile" and atr_elevated and volume.candle_vs_avg in ("spike", "elevated")
        breaks_don_upper = close >= donchian_upper and vol_spike
        breaks_don_lower = close <= donchian_lower and vol_spike
        don_matched = don_prereqs and (breaks_don_upper or breaks_don_lower)

        strategies.append(_make(
            "Donchian Channel Breakout", "volatile",
            don_matched, don_prereqs,
            [f"Breaking Donchian {'upper' if breaks_don_upper else 'lower'} ({donchian_upper:.0f}/{donchian_lower:.0f})"] if don_matched else [f"Donchian breakout not confirmed (regime={regime.type})"],
        ))

        # --- Stand Aside ---
        stand_aside_prereqs = regime.type == "volatile"
        stand_aside_matched = stand_aside_prereqs and not volume.volume_supports_move

        strategies.append(_make(
            "Stand Aside", "volatile",
            stand_aside_matched, stand_aside_prereqs,
            ["Volatile regime with unconvincing volume — no edge"] if stand_aside_matched else [f"Stand aside not triggered (regime={regime.type})"],
        ))

        # ========================
        # CROSS-REGIME: Liquidity Sweep Reversal
        # ========================
        sweep_prereqs = liquidity.event == "sweep" and volume.candle_vs_avg in ("spike", "elevated")
        # Price swept beyond a key level then reclaimed
        swept_above = liquidity.direction == "bearish" and close > (liquidity.level or close)
        swept_below = liquidity.direction == "bullish" and close < (liquidity.level or close)
        reclaimed = swept_above or swept_below
        sweep_matched = sweep_prereqs and reclaimed

        sweep_reasons = []
        if liquidity.event == "sweep":
            sweep_reasons.append(f"Liquidity sweep {liquidity.direction} at {liquidity.level}")
        if volume.candle_vs_avg in ("spike", "elevated"):
            sweep_reasons.append("Volume spike confirms sweep")
        if not liquidity.event:
            sweep_reasons.append("No liquidity sweep detected")

        strategies.append(_make(
            "Liquidity Sweep Reversal", "cross_regime",
            sweep_matched, sweep_prereqs,
            sweep_reasons or ["No sweep event"],
        ))

        return strategies
