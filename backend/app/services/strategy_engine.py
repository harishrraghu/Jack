from app.schemas import Candle, DayContext, Liquidity, Regime, Strategy, Structure


class StrategyEngine:
    def evaluate(
        self,
        candles: list[Candle],
        indicators: dict[str, list[float]],
        context: DayContext,
        structure: Structure,
        regime: Regime,
        liquidity: Liquidity,
    ) -> list[Strategy]:
        last = candles[-1]
        ema21 = indicators["ema21"][-1]
        rsi = indicators["rsi14"][-1]
        atr = indicators["atr"][-1]
        recent_high = max(c.high for c in candles[-10:])
        recent_low = min(c.low for c in candles[-10:])

        return [
            Strategy(
                name="Trend Pullback",
                matched=(
                    regime.type == "trend_up"
                    and structure.phase == "pullback"
                    and last.close > ema21
                    and 45 <= rsi <= 62
                ),
                reasons=[
                    "Uptrend regime with controlled pullback",
                    "Price holding above EMA21",
                    "RSI reset supports continuation",
                ],
            ),
            Strategy(
                name="Breakout",
                matched=(
                    regime.type != "range"
                    and last.close >= recent_high - atr * 0.15
                    and context.volatility != "low"
                ),
                reasons=["Price pressing recent high", "Volatility supports expansion"],
            ),
            Strategy(
                name="Reversal",
                matched=(
                    liquidity.event == "sweep"
                    and liquidity.direction == "bullish"
                    and structure.trend != "bearish"
                ),
                reasons=["Liquidity sweep suggests exhaustion", "Structure is not bearish impulse"],
            ),
            Strategy(
                name="Range",
                matched=(
                    regime.type == "range"
                    and abs(last.close - ((recent_high + recent_low) / 2)) < atr * 0.3
                ),
                reasons=["Regime classified as range", "Price rotating near equilibrium"],
            ),
        ]

