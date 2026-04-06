from app.schemas import (
    DayContext,
    ForecastConfirmation,
    Liquidity,
    Regime,
    Score,
    Strategy,
    StructureLevels,
    TrendHealth,
    VolumeAnalysis,
)


class ConfluenceEngine:
    def score(
        self,
        context: DayContext,
        regime: Regime,
        structure_levels: StructureLevels,
        liquidity: Liquidity,
        indicators: dict,
        strategies: list[Strategy],
        volume: VolumeAnalysis,
        trend_health: TrendHealth | None,
        forecast_confirmation: ForecastConfirmation | None = None,
    ) -> Score:
        score = 0

        # Layer 1: Regime quality (max 20)
        if regime.type in ("trend_up", "trend_down"):
            score += 20
        elif regime.type in ("weak_trend_up", "weak_trend_down"):
            score += 12
        elif regime.type == "squeeze":
            score += 15 if structure_levels.squeeze_fired else 8
        elif regime.type == "range":
            score += 10
        else:  # volatile
            score += 5

        # Layer 2: Trend health (max 15)
        if trend_health is not None:
            if trend_health.status == "healthy" and trend_health.momentum in ("accelerating", "steady"):
                score += 15
            elif trend_health.status == "healthy":
                score += 10
            elif trend_health.status == "weakening":
                score += 5
            elif trend_health.status == "exhausted":
                score -= 10

        # Layer 3: Structure support (max 20)
        if structure_levels.confluence_zones:
            best_zone = max(structure_levels.confluence_zones, key=lambda z: z.strength)
            score += min(20, best_zone.strength * 5)

        # Layer 4: Volume confirmation (max 20)
        if volume.volume_supports_move:
            score += 12
        if volume.candle_vs_avg in ("spike", "elevated"):
            score += 5
        if volume.price_volume_divergence == "none":
            score += 3
        if volume.obv_divergence:
            score -= 15

        # Layer 5: Strategy match (max 15)
        matched = [s for s in strategies if s.matched and s.prerequisites_met]
        score += min(15, len(matched) * 8)

        # Context bias (max 10)
        if context.bias != "neutral":
            score += 10

        # Liquidity event bonus
        if liquidity.event == "sweep":
            score += 8

        # Layer 7: Jill (max +15 / min -20)
        if forecast_confirmation is not None and forecast_confirmation.available:
            if forecast_confirmation.confirmed:
                score += 15
            else:
                penalty = 0
                if not forecast_confirmation.agrees:
                    penalty += 10
                if not forecast_confirmation.confident:
                    penalty += 5
                if not forecast_confirmation.no_reversal:
                    penalty += 5
                score -= penalty

        return Score(value=float(max(0, min(100, score))))
