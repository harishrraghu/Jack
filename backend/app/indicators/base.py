"""
Base class for all modular indicators.

Design decisions that fix the identified bugs:
- Bug #1: Each subclass defines `name` as an explicit class-level string attribute
  instead of deriving from cls.__name__.lower().  This decouples the human-readable
  registry key from the Python class name and makes VolumeProfile → "volume_profile"
  (with underscore) trivial.
- Bug #6: __init__ accepts both int and float kwargs via the generic **params signature.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.schemas import Candle


class BaseIndicator(ABC):
    """Abstract base for every indicator module.

    Subclasses MUST:
      1. Define ``name: str`` as a class attribute (registry key).
      2. Implement ``compute(candles) -> dict[str, list[float]]``.

    The ``compute`` return dict must contain **only candle-aligned** arrays
    (i.e. len == len(candles)).  If an indicator produces histogram / profile
    data with a different length it must expose that via a separate key
    documented clearly, and that key must NOT be used in any time-series chart.
    """

    # Subclasses override this; leaving it undefined causes AttributeError on
    # registration so misconfigured indicators are caught at import time.
    name: str

    def __init__(self, **kwargs) -> None:
        # Bug #6 fix: store raw params as-is (already parsed to int/float by
        # _parse_value before cls(**params) is called).
        self.params: dict = kwargs

    @abstractmethod
    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        """Return a dict of {series_name: candle_aligned_list}.

        All lists MUST have exactly len(candles) elements so they can be
        safely zip-aligned with candle timestamps on the frontend.
        """

    @classmethod
    def _to_df(cls, candles: list[Candle]) -> pd.DataFrame:
        """Convenience: convert candle list to a DataFrame."""
        return pd.DataFrame([c.model_dump() for c in candles])
