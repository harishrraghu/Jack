from app.schemas import AnalysisResponse
from app.services.confluence_engine import ConfluenceEngine
from app.services.context_engine import ContextEngine
from app.services.data_service import DataService
from app.services.drawing_engine import DrawingEngine
from app.services.indicator_engine import IndicatorEngine
from app.services.liquidity_engine import LiquidityEngine
from app.services.narrative_engine import NarrativeEngine
from app.services.regime_engine import RegimeEngine
from app.services.signal_engine import SignalEngine
from app.services.strategy_engine import StrategyEngine
from app.services.structure_engine import StructureEngine


class AnalysisPipeline:
    def __init__(self) -> None:
        self.data_service = DataService()
        self.indicator_engine = IndicatorEngine()
        self.context_engine = ContextEngine()
        self.structure_engine = StructureEngine()
        self.regime_engine = RegimeEngine()
        self.liquidity_engine = LiquidityEngine()
        self.strategy_engine = StrategyEngine()
        self.confluence_engine = ConfluenceEngine()
        self.signal_engine = SignalEngine()
        self.drawing_engine = DrawingEngine()
        self.narrative_engine = NarrativeEngine()

    async def analyze(self, timeframe: str) -> AnalysisResponse:
        candles = await self.data_service.get_candles(timeframe)
        external = await self.data_service.get_global_context()
        indicators = self.indicator_engine.calculate(candles)
        context = self.context_engine.derive(candles, indicators, external)
        structure = self.structure_engine.derive(candles)
        regime = self.regime_engine.derive(candles, indicators)
        liquidity = self.liquidity_engine.derive(candles)
        strategies = self.strategy_engine.evaluate(candles, indicators, context, structure, regime, liquidity)
        score = self.confluence_engine.score(context, structure, regime, liquidity, indicators, strategies)
        signal = self.signal_engine.generate(candles, indicators, context, structure, regime, liquidity, strategies, score)
        drawings = self.drawing_engine.build(candles, indicators, context, liquidity, signal)
        narrative = self.narrative_engine.build(regime, context, structure, signal)

        return AnalysisResponse(
            symbol="BANKNIFTY",
            timeframe=timeframe,
            candles=candles,
            context=context,
            structure=structure,
            regime=regime,
            liquidity=liquidity,
            score=score,
            signal=signal,
            narrative=narrative,
            drawings=drawings,
            indicators=indicators,
        )

