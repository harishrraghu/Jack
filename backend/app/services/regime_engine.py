from app.schemas import Candle, Regime


class RegimeEngine:
    def derive(self, candles: list[Candle], indicators: dict[str, list[float]]) -> Regime:
        close = candles[-1].close
        ema21 = indicators["ema21"][-1]
        ema50 = indicators["ema50"][-1]
        ema200 = indicators["ema200"][-1]
        vwap = indicators["vwap"][-1]
        adx = indicators["adx"][-1]

        if close > ema21 > ema50 > ema200 and close > vwap and adx >= 20:
            return Regime(type="trend_up", tradable=True)
        if close < ema21 < ema50 < ema200 and close < vwap and adx >= 20:
            return Regime(type="trend_down", tradable=True)
        return Regime(type="range", tradable=adx >= 15)

