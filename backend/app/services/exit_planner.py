from app.schemas import Candle, ExitPlan, Regime, StructureLevels

_MIN_RR = 1.5


class ExitPlanner:
    def plan(
        self,
        entry: float,
        direction: str,
        candles: list[Candle],
        indicators: dict,
        structure: StructureLevels,
        regime: Regime,
    ) -> ExitPlan:
        atr = indicators["atr"][-1]
        is_long = direction == "BUY_CALL"

        # --- Stop Loss Candidates ---
        candidates: list[tuple[float, str]] = []

        # 1. ATR-based stop
        if regime.type in ("trend_up", "trend_down", "weak_trend_up", "weak_trend_down"):
            multiplier = 1.5
        elif regime.type == "volatile":
            multiplier = 2.0
        else:
            multiplier = 1.0

        if is_long:
            candidates.append((round(entry - multiplier * atr, 2), f"ATR {multiplier}x below entry"))
        else:
            candidates.append((round(entry + multiplier * atr, 2), f"ATR {multiplier}x above entry"))

        # 2. Structural stop: swing low/high from recent candles
        lookback = candles[-20:] if len(candles) >= 20 else candles
        if is_long:
            swing_low = min(c.low for c in lookback)
            structural_stop = round(swing_low - 0.2 * atr, 2)
            candidates.append((structural_stop, "below recent swing low"))
        else:
            swing_high = max(c.high for c in lookback)
            structural_stop = round(swing_high + 0.2 * atr, 2)
            candidates.append((structural_stop, "above recent swing high"))

        # 3. Supertrend stop
        if "supertrend" in indicators:
            st = indicators["supertrend"][-1]
            if is_long:
                st_stop = round(st - 0.3 * atr, 2)
                candidates.append((st_stop, "below Supertrend line"))
            else:
                st_stop = round(st + 0.3 * atr, 2)
                candidates.append((st_stop, "above Supertrend line"))

        # 4. VWAP band stop
        if "vwap_lower1" in indicators and is_long:
            vwap_stop = round(indicators["vwap_lower1"][-1] - 0.1 * atr, 2)
            candidates.append((vwap_stop, "below VWAP -1 sigma"))
        elif "vwap_upper1" in indicators and not is_long:
            vwap_stop = round(indicators["vwap_upper1"][-1] + 0.1 * atr, 2)
            candidates.append((vwap_stop, "above VWAP +1 sigma"))

        # Pick the stop that is tightest but still gives room (at least 0.3 ATR from entry)
        min_distance = 0.3 * atr
        if is_long:
            valid = [(s, m) for s, m in candidates if entry - s >= min_distance]
            if valid:
                stop_price, stop_method = max(valid, key=lambda x: x[0])  # tightest = highest below entry
            else:
                stop_price, stop_method = min(candidates, key=lambda x: x[0])
        else:
            valid = [(s, m) for s, m in candidates if s - entry >= min_distance]
            if valid:
                stop_price, stop_method = min(valid, key=lambda x: x[0])  # tightest = lowest above entry
            else:
                stop_price, stop_method = max(candidates, key=lambda x: x[0])

        # --- Target Candidates ---
        target_candidates: list[tuple[float, str]] = []

        # 1. Next structure level
        if is_long and structure.nearest_resistance > entry:
            target_candidates.append((structure.nearest_resistance, "nearest resistance confluence"))
        elif not is_long and structure.nearest_support < entry:
            target_candidates.append((structure.nearest_support, "nearest support confluence"))

        # 2. ATR projection
        if regime.type in ("trend_up", "trend_down", "weak_trend_up", "weak_trend_down"):
            atr_mult = 2.0
        elif regime.type == "squeeze":
            atr_mult = 3.0
        elif regime.type == "volatile":
            atr_mult = 3.0
        else:
            atr_mult = 1.5

        if is_long:
            target_candidates.append((round(entry + atr_mult * atr, 2), f"ATR {atr_mult}x projection"))
        else:
            target_candidates.append((round(entry - atr_mult * atr, 2), f"ATR {atr_mult}x projection"))

        # 3. Opposing BB (range trades)
        if regime.type == "range":
            if is_long and "bb_middle" in indicators:
                target_candidates.append((round(indicators["bb_middle"][-1], 2), "Bollinger middle band"))
            elif not is_long and "bb_middle" in indicators:
                target_candidates.append((round(indicators["bb_middle"][-1], 2), "Bollinger middle band"))

        # 4. VWAP as target (range/reversion)
        if "vwap" in indicators and regime.type in ("range", "volatile"):
            target_candidates.append((round(indicators["vwap"][-1], 2), "VWAP reversion"))

        # Pick target that gives best R:R (at least 1.5:1)
        stop_dist = abs(entry - stop_price)
        if stop_dist == 0:
            stop_dist = atr

        best_target = None
        best_method = "ATR projection"
        best_rr = 0.0

        for t, m in target_candidates:
            if is_long and t <= entry:
                continue
            if not is_long and t >= entry:
                continue
            rr = abs(t - entry) / stop_dist
            if rr > best_rr:
                best_rr = rr
                best_target = t
                best_method = m

        if best_target is None or best_rr < _MIN_RR:
            # Fallback: ensure minimum 1.5 R:R
            if is_long:
                best_target = round(entry + _MIN_RR * stop_dist, 2)
            else:
                best_target = round(entry - _MIN_RR * stop_dist, 2)
            best_method = f"minimum {_MIN_RR}:1 R:R target"
            best_rr = _MIN_RR

        # --- Trailing stop method ---
        if regime.type in ("trend_up", "trend_down", "weak_trend_up", "weak_trend_down"):
            trailing = "Supertrend line"
        elif regime.type == "volatile":
            trailing = "2x ATR trailing"
        else:
            trailing = "VWAP"

        # Break-even trigger: 1x ATR in favor
        if is_long:
            break_even = round(entry + atr, 2)
        else:
            break_even = round(entry - atr, 2)

        return ExitPlan(
            stop_loss=stop_price,
            stop_method=stop_method,
            target=best_target,
            target_method=best_method,
            risk_reward_ratio=round(best_rr, 2),
            trailing_stop_method=trailing,
            break_even_trigger=break_even,
        )
