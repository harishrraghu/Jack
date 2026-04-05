from app.schemas import Candle, DayContext


class ContextEngine:
    def derive(self, candles: list[Candle], indicators: dict[str, list[float]], external: dict) -> DayContext:
        prev_close = candles[-2].close if len(candles) > 1 else candles[-1].close
        current = candles[-1].close
        atr = indicators["atr"][-1]
        price_delta = current - prev_close

        if price_delta > atr * 0.2 and external["gift_nifty_delta"] >= 0:
            bias = "bullish"
        elif price_delta < -atr * 0.2 and external["gift_nifty_delta"] < 0:
            bias = "bearish"
        else:
            bias = "neutral"

        volatility = "high" if atr > 220 else "medium" if atr > 120 else "low"
        day_type = "event" if external["event_risk"] else "trend" if abs(price_delta) > atr * 0.5 else "range"
        key_levels = [
            round(prev_close, 2),
            round(external["oi_wall_above"], 2),
            round(external["oi_wall_below"], 2),
            round(max(c.high for c in candles[-20:]), 2),
            round(min(c.low for c in candles[-20:]), 2),
        ]

        return DayContext(bias=bias, dayType=day_type, volatility=volatility, keyLevels=key_levels)
