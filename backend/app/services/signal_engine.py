from app.schemas import Candle, DayContext, Liquidity, Regime, Score, Signal, Strategy, Structure


class SignalEngine:
    def generate(
        self,
        candles: list[Candle],
        indicators: dict[str, list[float]],
        context: DayContext,
        structure: Structure,
        regime: Regime,
        liquidity: Liquidity,
        strategies: list[Strategy],
        score: Score,
    ) -> Signal:
        last = candles[-1]
        atr = indicators["atr"][-1]
        matched = [strategy for strategy in strategies if strategy.matched]
        reasons = [
            f"Context bias is {context.bias}",
            f"Structure trend is {structure.trend} in {structure.phase}",
            f"Regime classified as {regime.type}",
        ]

        if liquidity.event:
            reasons.append(f"Liquidity event: {liquidity.event} {liquidity.direction}")
        reasons.extend(strategy.name for strategy in matched)

        if score.value < 65 or not regime.tradable:
            return Signal(
                type="NONE",
                entry=round(last.close, 2),
                stopLoss=round(last.close - atr, 2),
                target=round(last.close + atr, 2),
                confidence=round(score.value, 2),
                reasons=reasons + ["Score below execution threshold"],
            )

        if regime.type == "trend_up" and context.bias != "bearish":
            return Signal(
                type="BUY_CALL",
                entry=round(last.close, 2),
                stopLoss=round(last.close - atr * 0.9, 2),
                target=round(last.close + atr * 1.8, 2),
                confidence=round(score.value, 2),
                reasons=reasons + ["Bullish confluence cleared threshold"],
            )

        if regime.type == "trend_down" and context.bias != "bullish":
            return Signal(
                type="BUY_PUT",
                entry=round(last.close, 2),
                stopLoss=round(last.close + atr * 0.9, 2),
                target=round(last.close - atr * 1.8, 2),
                confidence=round(score.value, 2),
                reasons=reasons + ["Bearish confluence cleared threshold"],
            )

        return Signal(
            type="NONE",
            entry=round(last.close, 2),
            stopLoss=round(last.close - atr, 2),
            target=round(last.close + atr, 2),
            confidence=round(score.value, 2),
            reasons=reasons + ["Conditions conflict across modules"],
        )
