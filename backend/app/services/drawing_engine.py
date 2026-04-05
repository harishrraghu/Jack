from app.schemas import Candle, DayContext, Drawing, Liquidity, Signal


class DrawingEngine:
    def build(
        self,
        candles: list[Candle],
        indicators: dict[str, list[float]],
        context: DayContext,
        liquidity: Liquidity,
        signal: Signal,
    ) -> list[Drawing]:
        drawings: list[Drawing] = [
            Drawing(type="line", data={"id": "entry", "label": "Entry", "price": signal.entry, "color": "#0f766e"}),
            Drawing(type="line", data={"id": "stop", "label": "Stop Loss", "price": signal.stopLoss, "color": "#b91c1c"}),
            Drawing(type="line", data={"id": "target", "label": "Target", "price": signal.target, "color": "#1d4ed8"}),
            Drawing(
                type="zone",
                data={
                    "id": "sr-zone",
                    "label": "Active S/R Zone",
                    "top": max(context.keyLevels[:2]),
                    "bottom": min(context.keyLevels[-2:]),
                    "color": "#f08a4b",
                },
            ),
        ]

        if liquidity.level is not None:
            drawings.append(
                Drawing(
                    type="label",
                    data={
                        "id": "liquidity",
                        "label": f"{liquidity.event} {liquidity.direction}",
                        "price": liquidity.level,
                        "color": "#7c3aed",
                    },
                )
            )

        for line_id, label, price, color in (
            ("ema21", "EMA 21", indicators["ema21"][-1], "#1f7a8c"),
            ("ema50", "EMA 50", indicators["ema50"][-1], "#f08a4b"),
            ("vwap", "VWAP", indicators["vwap"][-1], "#5c4d7d"),
        ):
            drawings.append(Drawing(type="label", data={"id": line_id, "label": label, "price": price, "color": color}))

        return drawings

