"""
Base class for all modular strategy modules.

Bug #10 fix: ``Strategy`` schema already defines all optional fields as
``float | None = None``, so strategies that set them to None when unmatched
pass Pydantic validation.  This file documents and enforces that contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

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


class BaseStrategy(ABC):
    """Abstract base for every strategy module.

    Subclasses MUST:
      1. Define ``name: str`` as a class-level string (registry key).
      2. Implement ``analyze(...)`` returning a ``Strategy``.

    ``analyze`` is always called regardless of regime; each strategy is
    responsible for its own prerequisite checks and must return a Strategy
    with ``matched=False`` (and ``prerequisites_met=False``) when conditions
    are not right — never raise an exception for mis-matched regime.
    """

    name: str

    @abstractmethod
    def analyze(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        regime: Regime,
        trend_health: TrendHealth | None,
        structure: StructureLevels,
        volume: VolumeAnalysis,
        liquidity: Liquidity,
    ) -> Strategy:
        """Evaluate conditions and return a Strategy result.

        - ``matched=True`` only when ALL prerequisite AND entry conditions met.
        - ``entry_price``, ``stop_loss``, ``target_price``, ``risk_reward``
          must be ``None`` when ``matched=False`` (schema enforces Optional).
        """

    # ── shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _get(indicators: dict, key: str, idx: int = -1, default: float = 0.0) -> float:
        lst = indicators.get(key, [])
        if not lst:
            return default
        return float(lst[idx])

    @staticmethod
    def _make(
        name: str,
        category: str,
        matched: bool,
        prereqs_met: bool,
        reasons: list[str],
        entry: float | None = None,
        stop: float | None = None,
        target: float | None = None,
        rr: float | None = None,
    ) -> Strategy:
        """Bug #10 fix: all optional numeric fields default to None when not matched."""
        return Strategy(
            name=name,
            category=category,
            matched=matched,
            prerequisites_met=prereqs_met,
            reasons=reasons,
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            risk_reward=rr,
        )
