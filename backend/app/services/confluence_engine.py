from app.schemas import DayContext, Liquidity, Regime, Score, Strategy, Structure


class ConfluenceEngine:
    def score(
        self,
        context: DayContext,
        structure: Structure,
        regime: Regime,
        liquidity: Liquidity,
        indicators: dict[str, list[float]],
        strategies: list[Strategy],
    ) -> Score:
        structure_score = 30 if structure.trend != "neutral" else 10
        regime_score = 20 if regime.tradable else 5
        liquidity_score = 20 if liquidity.event else 8
        indicator_score = 10 if indicators["rsi14"][-1] > 52 or indicators["rsi14"][-1] < 48 else 6
        context_score = 20 if context.bias != "neutral" else 8
        strategy_bonus = 8 if any(strategy.matched for strategy in strategies) else 0

        return Score(
            value=min(
                100.0,
                structure_score + regime_score + liquidity_score + indicator_score + context_score + strategy_bonus,
            )
        )

