"""
Strategy Engine — orchestrates all strategy evaluation.

Refactored to delegate each strategy to its own class in ``app/strategies/``.
The public interface (``StrategyEngine.evaluate()``) is unchanged so
``AnalysisPipeline`` requires no modifications.

Bug fixes:
  Bug #10 — Strategy Optional fields: every strategy class in app/strategies/
             returns ``entry_price=None``, ``stop_loss=None``, etc. when
             ``matched=False``.  The Pydantic ``Strategy`` schema already
             declares those as ``float | None = None`` so validation passes.

  Bug #8  — Auto-discovery failures are handled in app/strategies/__init__.py;
             a broken module is skipped without crashing the engine.
"""
from __future__ import annotations

import logging

from app.schemas import (
    Candle,
    DayContext,
    Liquidity,
    Regime,
    Strategy,
    StructureLevels,
    TrendHealth,
    VolumeAnalysis,
)
from app.strategies import AVAILABLE_STRATEGIES
from app.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

# Ordered list of strategy registry keys to evaluate on every request.
# Order matters: "Stand Aside" should be evaluated so the signal engine can
# short-circuit, but it does not affect correctness.
_STRATEGY_ORDER: list[str] = [
    # Trend — long
    "ema_pullback_long",
    "supertrend_continuation_long",
    "trend_breakout_long",
    # Trend — short
    "ema_pullback_short",
    "supertrend_continuation_short",
    "trend_breakout_short",
    # Range
    "bb_mean_reversion_long",
    "bb_mean_reversion_short",
    "vwap_reversion",
    "pivot_bounce",
    # Squeeze
    "ttm_squeeze_breakout",
    "opening_range_breakout",
    # Volatile
    "donchian_breakout",
    "stand_aside",
    # Cross-regime
    "liquidity_sweep_reversal",
]


class StrategyEngine:
    """Orchestrates all strategy evaluation.

    On construction the modular strategy instances are built once and reused
    across requests (they are stateless).
    """

    def __init__(self) -> None:
        self._strategies: list[BaseStrategy] = []
        for key in _STRATEGY_ORDER:
            cls = AVAILABLE_STRATEGIES.get(key)
            if cls is None:
                logger.warning(
                    "Strategy '%s' not found in registry — skipping.  "
                    "Available: %s",
                    key,
                    sorted(AVAILABLE_STRATEGIES),
                )
                continue
            self._strategies.append(cls())
            logger.debug("StrategyEngine: loaded strategy '%s'", key)

        if not self._strategies:
            logger.error(
                "StrategyEngine has no strategies loaded!  "
                "Check that app/strategies/ modules are importable."
            )

    def evaluate(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        regime: Regime,
        trend_health: TrendHealth | None,
        structure: StructureLevels,
        volume: VolumeAnalysis,
        liquidity: Liquidity,
    ) -> list[Strategy]:
        """Run every registered strategy and return the full result list."""
        results: list[Strategy] = []
        for strategy in self._strategies:
            try:
                result = strategy.analyze(
                    candles, indicators, context, regime,
                    trend_health, structure, volume, liquidity,
                )
                results.append(result)
            except Exception as exc:
                logger.error(
                    "Strategy '%s' raised an exception — returning unmatched stub: %s",
                    strategy.name,
                    exc,
                )
                # Return a safe unmatched stub so the pipeline never crashes.
                results.append(
                    Strategy(
                        name=getattr(strategy, "name", "unknown"),
                        category="cross_regime",
                        matched=False,
                        prerequisites_met=False,
                        reasons=[f"Error during evaluation: {exc}"],
                    )
                )
        return results
