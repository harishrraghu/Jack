from app.schemas import Candle, Liquidity


class LiquidityEngine:
    def derive(self, candles: list[Candle]) -> Liquidity:
        recent = candles[-4:]
        latest = recent[-1]
        prior_high = max(c.high for c in recent[:-1])
        prior_low = min(c.low for c in recent[:-1])

        bullish_sweep = latest.low < prior_low and latest.close > prior_low
        bearish_sweep = latest.high > prior_high and latest.close < prior_high

        if bullish_sweep:
            return Liquidity(event="sweep", direction="bullish", level=round(prior_low, 2))
        if bearish_sweep:
            return Liquidity(event="sweep", direction="bearish", level=round(prior_high, 2))

        gap_up = recent[-1].low > recent[-3].high
        gap_down = recent[-1].high < recent[-3].low
        if gap_up:
            return Liquidity(event="fvg", direction="bullish", level=round(recent[-3].high, 2))
        if gap_down:
            return Liquidity(event="fvg", direction="bearish", level=round(recent[-3].low, 2))

        return Liquidity(event=None, direction=None, level=None)

