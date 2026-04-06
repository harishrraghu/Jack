from app.schemas import (
    Candle,
    ConfluenceZone,
    PriceLevel,
    StructureLevels,
)

_CONFLUENCE_THRESHOLD = 0.003  # 0.3% of price


def _level_strength(n_sources: int) -> str:
    if n_sources >= 3:
        return "strong"
    if n_sources == 2:
        return "moderate"
    return "weak"


def _find_confluence_zones(
    levels: list[PriceLevel], reference_price: float
) -> list[ConfluenceZone]:
    """Group levels within 0.3% of each other into confluence zones."""
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda lv: lv.price)
    zones: list[ConfluenceZone] = []
    used = [False] * len(sorted_levels)

    threshold = reference_price * _CONFLUENCE_THRESHOLD

    for i, lv in enumerate(sorted_levels):
        if used[i]:
            continue
        group = [lv]
        used[i] = True
        for j in range(i + 1, len(sorted_levels)):
            if not used[j] and abs(sorted_levels[j].price - lv.price) <= threshold:
                group.append(sorted_levels[j])
                used[j] = True

        if len(group) < 2:
            continue

        prices = [g.price for g in group]
        sources = [g.source for g in group]
        # Determine zone type by majority
        n_support = sum(1 for g in group if g.type == "support")
        zone_type = "support" if n_support >= len(group) / 2 else "resistance"

        zones.append(
            ConfluenceZone(
                top=round(max(prices), 2),
                bottom=round(min(prices), 2),
                type=zone_type,
                sources=sources,
                strength=len(group),
            )
        )

    return sorted(zones, key=lambda z: z.strength, reverse=True)


class StructureLevelsEngine:
    def analyze(self, candles: list[Candle], indicators: dict) -> StructureLevels:
        current = candles[-1]
        close = current.close
        atr = indicators["atr"][-1]

        levels: list[PriceLevel] = []

        # --- Pivot Points ---
        for key, label, level_type in [
            ("pivot_r1", "pivot_r1", "resistance"),
            ("pivot_r2", "pivot_r2", "resistance"),
            ("pivot_r3", "pivot_r3", "resistance"),
            ("pivot_s1", "pivot_s1", "support"),
            ("pivot_s2", "pivot_s2", "support"),
            ("pivot_s3", "pivot_s3", "support"),
        ]:
            if key in indicators:
                price = indicators[key][-1]
                levels.append(
                    PriceLevel(
                        price=round(price, 2),
                        type=level_type,
                        source=label,
                        strength="moderate",
                    )
                )

        # Pivot center
        if "pivot" in indicators:
            p = indicators["pivot"][-1]
            p_type: str = "support" if close > p else "resistance"
            levels.append(PriceLevel(price=round(p, 2), type=p_type, source="pivot", strength="moderate"))

        # --- Bollinger Bands ---
        if "bb_upper" in indicators:
            bb_upper = indicators["bb_upper"][-1]
            bb_lower = indicators["bb_lower"][-1]
            bb_middle = indicators["bb_middle"][-1]
            levels.append(PriceLevel(price=round(bb_upper, 2), type="resistance", source="bb_upper", strength="moderate"))
            levels.append(PriceLevel(price=round(bb_lower, 2), type="support", source="bb_lower", strength="moderate"))
            bb_mid_type = "support" if close > bb_middle else "resistance"
            levels.append(PriceLevel(price=round(bb_middle, 2), type=bb_mid_type, source="bb_middle", strength="weak"))

        # --- VWAP Bands ---
        for key, label, level_type in [
            ("vwap_upper1", "vwap_plus_1sd", "resistance"),
            ("vwap_upper2", "vwap_plus_2sd", "resistance"),
            ("vwap_lower1", "vwap_minus_1sd", "support"),
            ("vwap_lower2", "vwap_minus_2sd", "support"),
        ]:
            if key in indicators:
                price = indicators[key][-1]
                levels.append(PriceLevel(price=round(price, 2), type=level_type, source=label, strength="moderate"))

        # VWAP itself
        if "vwap" in indicators:
            vwap = indicators["vwap"][-1]
            v_type = "support" if close > vwap else "resistance"
            levels.append(PriceLevel(price=round(vwap, 2), type=v_type, source="vwap", strength="strong"))

        # --- Supertrend ---
        if "supertrend" in indicators:
            st = indicators["supertrend"][-1]
            st_dir = "up" if indicators.get("supertrend_direction", [1.0])[-1] >= 0.5 else "down"
            st_type = "support" if st_dir == "up" else "resistance"
            levels.append(PriceLevel(price=round(st, 2), type=st_type, source="supertrend", strength="strong"))

        # --- Fibonacci Levels ---
        fib_map = {
            "fib_0382": "fib_382",
            "fib_0500": "fib_500",
            "fib_0618": "fib_618",
        }
        fib_levels_out: dict[str, float] = {}
        for key, label in fib_map.items():
            if key in indicators:
                price = indicators[key][-1]
                fib_levels_out[label.replace("fib_", "0.")] = price
                # Determine if fib level is support or resistance
                fib_type = "support" if close > price else "resistance"
                levels.append(PriceLevel(price=round(price, 2), type=fib_type, source=label, strength="moderate"))

        # --- Squeeze detection ---
        in_squeeze = False
        squeeze_fired = False
        if "in_squeeze" in indicators:
            in_squeeze = bool(indicators["in_squeeze"][-1] > 0.5)
        if "squeeze_fired" in indicators:
            squeeze_fired = bool(indicators["squeeze_fired"][-1] > 0.5)

        # --- Supertrend direction ---
        supertrend_value = indicators["supertrend"][-1] if "supertrend" in indicators else close
        supertrend_direction: str = "up"
        if "supertrend_direction" in indicators:
            supertrend_direction = "up" if indicators["supertrend_direction"][-1] >= 0.5 else "down"

        # --- Confluence zones ---
        confluence_zones = _find_confluence_zones(levels, close)

        # --- Nearest support / resistance ---
        supports = sorted([lv for lv in levels if lv.type == "support" and lv.price < close], key=lambda lv: lv.price, reverse=True)
        resistances = sorted([lv for lv in levels if lv.type == "resistance" and lv.price > close], key=lambda lv: lv.price)

        nearest_support = supports[0].price if supports else round(close - atr, 2)
        nearest_resistance = resistances[0].price if resistances else round(close + atr, 2)

        # --- Price position description ---
        position_parts = []
        if "pivot" in indicators:
            p = indicators["pivot"][-1]
            r1 = indicators.get("pivot_r1", [close + atr])[-1]
            s1 = indicators.get("pivot_s1", [close - atr])[-1]
            if s1 < close < p:
                position_parts.append("between S1 and Pivot")
            elif p < close < r1:
                position_parts.append("between Pivot and R1")
            elif close >= r1:
                position_parts.append("above R1")
            else:
                position_parts.append("below S1")

        if "vwap" in indicators:
            vwap = indicators["vwap"][-1]
            position_parts.append("above VWAP" if close > vwap else "below VWAP")

        if "bb_upper" in indicators:
            bb_upper = indicators["bb_upper"][-1]
            bb_lower = indicators["bb_lower"][-1]
            if close >= bb_upper:
                position_parts.append("at upper BB")
            elif close <= bb_lower:
                position_parts.append("at lower BB")
            else:
                position_parts.append("inside BB bands")

        if in_squeeze:
            position_parts.append("inside squeeze")
        if squeeze_fired:
            position_parts.append("squeeze just fired")

        price_position = ", ".join(position_parts) if position_parts else "no level context available"

        return StructureLevels(
            levels=levels,
            confluence_zones=confluence_zones,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            price_position=price_position,
            supertrend_value=round(supertrend_value, 2),
            supertrend_direction=supertrend_direction,
            in_squeeze=in_squeeze,
            squeeze_fired=squeeze_fired,
            fib_levels=fib_levels_out,
        )
