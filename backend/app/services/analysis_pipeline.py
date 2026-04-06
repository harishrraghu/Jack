from app.schemas import AnalysisResponse
from app.services.confluence_engine import ConfluenceEngine
from app.services.context_engine import ContextEngine
from app.services.data_service import DataService
from app.services.drawing_engine import DrawingEngine
from app.services.exit_planner import ExitPlanner
from app.services.forecast_confirmer import ForecastConfirmer
from app.services.forecast_service import ForecastService
from app.services.indicator_engine import IndicatorEngine
from app.services.liquidity_engine import LiquidityEngine
from app.services.narrative_engine import NarrativeEngine
from app.services.regime_engine import RegimeEngine
from app.services.signal_engine import SignalEngine
from app.services.strategy_engine import StrategyEngine
from app.services.structure_levels_engine import StructureLevelsEngine
from app.services.trend_health_engine import TrendHealthEngine
from app.services.volume_engine import VolumeEngine


class AnalysisPipeline:
    def __init__(self) -> None:
        self.data_service = DataService()
        self.indicator_engine = IndicatorEngine()
        self.regime_engine = RegimeEngine()
        self.trend_health_engine = TrendHealthEngine()
        self.structure_levels_engine = StructureLevelsEngine()
        self.volume_engine = VolumeEngine()
        self.strategy_engine = StrategyEngine()
        self.exit_planner = ExitPlanner()
        self.forecast_service = ForecastService()
        self.forecast_confirmer = ForecastConfirmer()
        self.confluence_engine = ConfluenceEngine()
        self.signal_engine = SignalEngine()
        self.drawing_engine = DrawingEngine()
        self.narrative_engine = NarrativeEngine()
        self.context_engine = ContextEngine()
        self.liquidity_engine = LiquidityEngine()

    async def analyze(self, timeframe: str) -> AnalysisResponse:
        candles = await self.data_service.get_candles(timeframe)
        external = await self.data_service.get_global_context()

        # Layer 1: Regime Detection (base indicators only)
        base_indicators = self.indicator_engine.calculate_base(candles)
        regime = self.regime_engine.derive(candles, base_indicators)

        # Full indicators based on detected regime
        indicators = self.indicator_engine.calculate_full(candles, regime)

        # Layer 2: Trend Health (skipped if non-trending)
        trend_health = self.trend_health_engine.assess(candles, indicators, regime)

        # Layer 3: Structure & Levels
        structure_levels = self.structure_levels_engine.analyze(candles, indicators)

        # Layer 4: Volume Verification
        volume = self.volume_engine.analyze(candles, indicators, regime)

        # Context + Liquidity (for strategy evaluation and narrative)
        context = self.context_engine.derive(candles, indicators, external)
        liquidity = self.liquidity_engine.derive(candles)

        # Layer 5: Strategy Selection
        strategies = self.strategy_engine.evaluate(
            candles, indicators, context, regime,
            trend_health, structure_levels, volume, liquidity,
        )

        # Confluence scoring (without Jill yet)
        score = self.confluence_engine.score(
            context, regime, structure_levels, liquidity, indicators,
            strategies, volume, trend_health, forecast_confirmation=None,
        )

        # Signal generation
        signal = self.signal_engine.generate(
            candles, indicators, context, regime, liquidity, strategies, score,
            structure_levels, volume, trend_health,
        )

        # Layer 6: Exit Planning (only if we have a signal)
        exit_plan = None
        if signal.type != "NONE":
            exit_plan = self.exit_planner.plan(
                signal.entry, signal.type, candles, indicators, structure_levels, regime,
            )
            signal.stopLoss = exit_plan.stop_loss
            signal.target = exit_plan.target

        # Layer 7: Jill — TimesFM confirmation (only if Jack produced a signal)
        forecast = None
        forecast_confirmation = None
        if signal.type != "NONE":
            forecast = await self.forecast_service.forecast(candles)
            if forecast:
                forecast_confirmation = self.forecast_confirmer.confirm(
                    signal.type, forecast, indicators["atr"][-1],
                )

        # Re-score with Jill's input
        if forecast_confirmation:
            final_score = self.confluence_engine.score(
                context, regime, structure_levels, liquidity, indicators,
                strategies, volume, trend_health,
                forecast_confirmation=forecast_confirmation,
            )
            signal.confidence = final_score.value
            if forecast_confirmation.available:
                if forecast_confirmation.confirmed:
                    signal.reasons.append(
                        "Jill (TimesFM) confirms: direction agrees, high confidence, no reversal risk"
                    )
                else:
                    flags = []
                    if not forecast_confirmation.agrees:
                        flags.append("direction disagrees")
                    if not forecast_confirmation.confident:
                        flags.append("wide confidence band")
                    if not forecast_confirmation.no_reversal:
                        flags.append("short-term reversal risk")
                    signal.reasons.append(f"Jill (TimesFM) flags: {', '.join(flags)}")
        else:
            final_score = score

        drawings = self.drawing_engine.build(
            candles, indicators, context, liquidity, signal, structure_levels, forecast,
        )
        narrative = self.narrative_engine.build(
            regime, context, signal, volume, trend_health, forecast_confirmation, structure_levels,
        )

        return AnalysisResponse(
            symbol="BANKNIFTY",
            timeframe=timeframe,
            candles=candles,
            context=context,
            regime=regime,
            liquidity=liquidity,
            score=final_score,
            signal=signal,
            narrative=narrative,
            drawings=drawings,
            indicators=indicators,
            volume_analysis=volume,
            trend_health=trend_health,
            structure_levels=structure_levels,
            forecast=forecast,
            forecast_confirmation=forecast_confirmation,
            exit_plan=exit_plan,
            strategies=strategies,
        )
