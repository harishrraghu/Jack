from app.schemas import Candle, Structure


class StructureEngine:
    def derive(self, candles: list[Candle]) -> Structure:
        recent = candles[-6:]
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]

        higher_highs = highs[-1] > highs[-3] > highs[-5]
        higher_lows = lows[-1] > lows[-3] > lows[-5]
        lower_highs = highs[-1] < highs[-3] < highs[-5]
        lower_lows = lows[-1] < lows[-3] < lows[-5]

        if higher_highs and higher_lows:
            trend = "bullish"
        elif lower_highs and lower_lows:
            trend = "bearish"
        else:
            trend = "neutral"

        phase = (
            "pullback"
            if (recent[-1].close < recent[-2].close and trend == "bullish")
            or (recent[-1].close > recent[-2].close and trend == "bearish")
            else "impulse"
        )
        return Structure(trend=trend, phase=phase)

