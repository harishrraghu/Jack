from app.schemas import (
    Candle,
    DayContext,
    Drawing,
    ForecastResult,
    Liquidity,
    Signal,
    StructureLevels,
)


class DrawingEngine:
    def build(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        liquidity: Liquidity,
        signal: Signal,
        structure_levels: StructureLevels | None = None,
        forecast: ForecastResult | None = None,
    ) -> list[Drawing]:
        drawings: list[Drawing] = []

        # --- Entry / Stop / Target lines ---
        drawings.append(Drawing(type="line", data={"id": "entry", "label": "Entry", "price": signal.entry, "color": "#0f766e"}))
        drawings.append(Drawing(type="line", data={"id": "stop", "label": "Stop Loss", "price": signal.stopLoss, "color": "#b91c1c"}))
        drawings.append(Drawing(type="line", data={"id": "target", "label": "Target", "price": signal.target, "color": "#1d4ed8"}))

        # --- S/R Zone from context key levels ---
        if len(context.keyLevels) >= 2:
            drawings.append(Drawing(
                type="zone",
                data={
                    "id": "sr-zone",
                    "label": "Active S/R Zone",
                    "top": max(context.keyLevels[:2]),
                    "bottom": min(context.keyLevels[-2:]),
                    "color": "#f08a4b",
                },
            ))

        # --- Liquidity event label ---
        if liquidity.level is not None:
            drawings.append(Drawing(
                type="label",
                data={
                    "id": "liquidity",
                    "label": f"{liquidity.event} {liquidity.direction}",
                    "price": liquidity.level,
                    "color": "#7c3aed",
                },
            ))

        # --- EMA lines ---
        drawings.append(Drawing(type="label", data={"id": "ema21", "label": "EMA 21", "price": indicators["ema21"][-1], "color": "#1f7a8c"}))
        drawings.append(Drawing(type="label", data={"id": "ema50", "label": "EMA 50", "price": indicators["ema50"][-1], "color": "#f08a4b"}))

        # --- VWAP ---
        drawings.append(Drawing(type="label", data={"id": "vwap", "label": "VWAP", "price": indicators["vwap"][-1], "color": "#5c4d7d"}))

        # --- Bollinger Bands (shaded zone) ---
        if "bb_upper" in indicators and "bb_lower" in indicators:
            drawings.append(Drawing(
                type="zone",
                data={
                    "id": "bb-bands",
                    "label": "BB Bands",
                    "top": indicators["bb_upper"][-1],
                    "bottom": indicators["bb_lower"][-1],
                    "color": "#64748b",
                },
            ))

        # --- VWAP Bands (+/-1 sigma) ---
        if "vwap_upper1" in indicators and "vwap_lower1" in indicators:
            drawings.append(Drawing(
                type="zone",
                data={
                    "id": "vwap-band-1",
                    "label": "VWAP ±1σ",
                    "top": indicators["vwap_upper1"][-1],
                    "bottom": indicators["vwap_lower1"][-1],
                    "color": "#818cf8",
                },
            ))

        # --- Supertrend line ---
        if "supertrend" in indicators and "supertrend_direction" in indicators:
            st_price = indicators["supertrend"][-1]
            st_dir = "up" if indicators["supertrend_direction"][-1] >= 0.5 else "down"
            st_color = "#16a34a" if st_dir == "up" else "#dc2626"
            drawings.append(Drawing(
                type="line",
                data={"id": "supertrend", "label": f"Supertrend ({st_dir})", "price": st_price, "color": st_color},
            ))

        # --- Pivot levels ---
        pivot_labels = {
            "pivot": ("P", "#6b7280"),
            "pivot_r1": ("R1", "#dc2626"),
            "pivot_r2": ("R2", "#ef4444"),
            "pivot_s1": ("S1", "#16a34a"),
            "pivot_s2": ("S2", "#22c55e"),
        }
        for key, (label, color) in pivot_labels.items():
            if key in indicators:
                price = indicators[key][-1]
                drawings.append(Drawing(
                    type="label",
                    data={"id": key, "label": label, "price": price, "color": color},
                ))

        # --- Confluence zones (as shaded rectangles) ---
        if structure_levels:
            for i, zone in enumerate(structure_levels.confluence_zones[:3]):  # top 3
                zone_color = "#16a34a" if zone.type == "support" else "#dc2626"
                drawings.append(Drawing(
                    type="zone",
                    data={
                        "id": f"confluence-{i}",
                        "label": f"{zone.type.capitalize()} ({zone.strength} sources)",
                        "top": zone.top,
                        "bottom": zone.bottom,
                        "color": zone_color,
                    },
                ))

        # --- Forecast (p50 line + p10/p90 band as zone) ---
        if forecast and forecast.p50:
            last_close = candles[-1].close
            # Draw a virtual "forecast zone" using p10/p90 range
            if forecast.p10 and forecast.p90:
                drawings.append(Drawing(
                    type="zone",
                    data={
                        "id": "forecast-band",
                        "label": "TimesFM Forecast Band",
                        "top": max(forecast.p90),
                        "bottom": min(forecast.p10),
                        "color": "#0ea5e9",
                    },
                ))
            # p50 target label
            drawings.append(Drawing(
                type="label",
                data={
                    "id": "forecast-p50",
                    "label": f"Jill → {forecast.p50[-1]:.0f} ({forecast.direction})",
                    "price": forecast.p50[-1],
                    "color": "#0284c7",
                },
            ))

        return drawings
