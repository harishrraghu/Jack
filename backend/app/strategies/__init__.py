"""
Strategies package — auto-discovery registry.

Same design as app/indicators/__init__.py:
  - Registry keyed by ``cls.name`` (explicit string attribute).
  - Import failures are logged and skipped (bug #8 pattern).
  - Duplicate names log a warning; first registration wins.
"""
from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path

from app.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


def load_all_strategies() -> dict[str, type[BaseStrategy]]:
    """Auto-discover every ``BaseStrategy`` subclass in this package."""
    registry: dict[str, type[BaseStrategy]] = {}
    strategy_dir = Path(__file__).parent

    for file in sorted(strategy_dir.glob("*.py")):
        if file.name.startswith("_"):
            continue

        module_name = file.stem
        try:
            module = importlib.import_module(f".{module_name}", package="app.strategies")
        except Exception as exc:
            logger.warning(
                "Skipping strategy module '%s': failed to import — %s",
                module_name,
                exc,
            )
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not (issubclass(obj, BaseStrategy) and obj is not BaseStrategy):
                continue

            strategy_name = getattr(obj, "name", None)
            if not isinstance(strategy_name, str):
                logger.warning(
                    "Class '%s' in module '%s' has no string 'name' attribute — skipping",
                    obj.__name__,
                    module_name,
                )
                continue

            if strategy_name in registry:
                logger.warning(
                    "Duplicate strategy name '%s' from '%s' — keeping first registration",
                    strategy_name,
                    module_name,
                )
                continue

            registry[strategy_name] = obj
            logger.debug("Registered strategy '%s' ← %s", strategy_name, obj.__name__)

    return registry


AVAILABLE_STRATEGIES: dict[str, type[BaseStrategy]] = load_all_strategies()
