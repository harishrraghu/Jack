"""
Indicators package — auto-discovery registry.

Bug fixes:
  Bug #1  — Key mismatch: registry uses ``cls.name`` (explicit string attribute)
             NOT ``cls.__name__.lower()``.  So ``VolumeProfile.name == "volume_profile"``
             and ``EMA.name == "ema"`` — human-readable, underscore-safe.
  Bug #8  — Silent import failures: each module import is wrapped in try/except.
             A broken indicator file logs a warning and is skipped; it does NOT
             crash the whole application startup.
"""
from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path

from app.indicators.base import BaseIndicator

logger = logging.getLogger(__name__)


def load_all_indicators() -> dict[str, type[BaseIndicator]]:
    """Auto-discover every ``BaseIndicator`` subclass in this package.

    Returns a dict keyed by ``cls.name`` (e.g. ``"ema"``, ``"volume_profile"``).
    Modules that fail to import are logged and skipped (bug #8 fix).
    Classes without a ``name`` string attribute are also skipped with a warning.
    Duplicate names log a warning; the first registration wins.
    """
    registry: dict[str, type[BaseIndicator]] = {}
    indicator_dir = Path(__file__).parent

    for file in sorted(indicator_dir.glob("*.py")):
        if file.name.startswith("_"):
            continue  # skip __init__.py, __pycache__, private helpers

        module_name = file.stem
        try:
            module = importlib.import_module(f".{module_name}", package="app.indicators")
        except Exception as exc:
            # Bug #8 fix: log and continue rather than crash.
            logger.warning(
                "Skipping indicator module '%s': failed to import — %s",
                module_name,
                exc,
            )
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not (issubclass(obj, BaseIndicator) and obj is not BaseIndicator):
                continue

            indicator_name = getattr(obj, "name", None)
            if not isinstance(indicator_name, str):
                logger.warning(
                    "Class '%s' in module '%s' has no string 'name' attribute — skipping",
                    obj.__name__,
                    module_name,
                )
                continue

            if indicator_name in registry:
                logger.warning(
                    "Duplicate indicator name '%s' from '%s' — keeping first registration",
                    indicator_name,
                    module_name,
                )
                continue

            registry[indicator_name] = obj
            logger.debug("Registered indicator '%s' ← %s", indicator_name, obj.__name__)

    return registry


# Loaded once at process startup.
AVAILABLE_INDICATORS: dict[str, type[BaseIndicator]] = load_all_indicators()
