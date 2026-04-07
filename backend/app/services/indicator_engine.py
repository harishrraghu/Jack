"""
Indicator Engine — orchestrates all indicator computation.

Refactored to use the modular ``app/indicators/`` package internally while
keeping the existing ``calculate_base()`` / ``calculate_full()`` interface so
that ``AnalysisPipeline`` requires no changes.

Bug fixes applied here:
  Bug #1  — Key mismatch: ``AVAILABLE_INDICATORS`` is keyed by ``cls.name``
             (explicit string).  ``_parse_spec()`` strips trailing digits before
             the registry lookup so "ema21" resolves to cls "ema" correctly.
  Bug #5  — Period parsing: uses ``re.match`` to extract trailing digits safely.
             "rsi14" → ("rsi", 14); "volume_profile" → ("volume_profile", None).
  Bug #6  — Float params: ``_parse_value()`` tries int → float → str, so
             params like "std_dev=2.5" round-trip correctly.
  Bug #8  — Import failures: handled inside ``app/indicators/__init__.py``
             (module-level); IndicatorEngine sees a clean registry dict.
"""
from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd
from ta.momentum import StochRSIIndicator
from ta.trend import ADXIndicator

from app.indicators import AVAILABLE_INDICATORS
from app.indicators.atr import _true_range
from app.schemas import Candle, Regime

logger = logging.getLogger(__name__)


# ── value parser (bug #6 fix) ─────────────────────────────────────────────────

def _parse_value(raw: str):
    """Parse a param string value to int, float, bool, or str."""
    v = raw.strip()
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


# ── spec parser (bug #5 fix) ──────────────────────────────────────────────────

# Bug #5 fix: base name = letters + underscores only (no digits); trailing
# digits are extracted as the period.  "ema21" → ("ema", "21").
# [a-z_]* excludes digits so the second group captures them cleanly.
_SPEC_RE = re.compile(r"^([a-z][a-z_]*)(\d+)?$")


def _parse_spec(spec: str) -> tuple[str, dict]:
    """Parse an indicator spec string into (registry_key, kwargs).

    Examples
    --------
    "ema21"                 → ("ema",            {"period": 21})
    "rsi14"                 → ("rsi",            {"period": 14})
    "bb"                    → ("bb",             {})
    "volume_profile:bins=30"→ ("volume_profile", {"bins": 30})
    "bb:std_dev=2.5"        → ("bb",             {"std_dev": 2.5})
    "vwap"                  → ("vwap",           {})
    """
    if ":" in spec:
        base, params_str = spec.split(":", 1)
        params: dict = {}
        for part in params_str.split(","):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            params[k.strip()] = _parse_value(v)
        return base.strip(), params

    # Bug #5 fix: use regex to cleanly separate alphabetic name from trailing
    # digits.  "ema21" → base="ema", digits="21".  "vwap" → base="vwap", None.
    m = _SPEC_RE.match(spec)
    if m:
        base = m.group(1)
        digits = m.group(2)
        params = {"period": int(digits)} if digits else {}
        return base, params

    # Fallback: treat the whole spec as a name with no params.
    return spec, {}


# ── low-level helpers (kept for indicators not yet in the modular package) ────

def _compute_supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series, list[str]]:
    tr = _true_range(high, low, close)
    atr = tr.rolling(window=period).mean().bfill().fillna(0.0)
    hl2 = (high + low) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(close)
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(np.nan, index=close.index)
    direction = ["up"] * n
    supertrend.iloc[0] = final_lower.iloc[0]

    for i in range(1, n):
        fu_prev = final_upper.iloc[i - 1]
        fl_prev = final_lower.iloc[i - 1]
        c_prev = close.iloc[i - 1]
        final_upper.iloc[i] = (
            min(basic_upper.iloc[i], fu_prev) if c_prev > fu_prev else basic_upper.iloc[i]
        )
        final_lower.iloc[i] = (
            max(basic_lower.iloc[i], fl_prev) if c_prev < fl_prev else basic_lower.iloc[i]
        )
        dir_prev = direction[i - 1]
        if dir_prev == "up":
            if close.iloc[i] < final_lower.iloc[i]:
                direction[i] = "down"
                supertrend.iloc[i] = final_upper.iloc[i]
            else:
                direction[i] = "up"
                supertrend.iloc[i] = final_lower.iloc[i]
        else:
            if close.iloc[i] > final_upper.iloc[i]:
                direction[i] = "up"
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                direction[i] = "down"
                supertrend.iloc[i] = final_upper.iloc[i]

    return supertrend.bfill(), direction


def _compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff().fillna(0))
    return (sign * volume).cumsum()


def _lr_slope(series: pd.Series, n: int) -> pd.Series:
    result = pd.Series(0.0, index=series.index)
    x = np.arange(n, dtype=float)
    for i in range(n - 1, len(series)):
        y = series.iloc[i - n + 1 : i + 1].values.astype(float)
        if not np.any(np.isnan(y)):
            result.iloc[i] = np.polyfit(x, y, 1)[0]
    return result


def _compute_pivot_points(candles: list[Candle]) -> dict[str, float]:
    if len(candles) < 2:
        c = candles[-1].close
        return {k: c for k in ("pivot", "pivot_r1", "pivot_r2", "pivot_r3", "pivot_s1", "pivot_s2", "pivot_s3")}

    times = pd.to_datetime([c.time for c in candles], unit="s")
    df = pd.DataFrame([c.model_dump() for c in candles])
    df["date"] = times.date.tolist()
    unique_dates = sorted(df["date"].unique())
    if len(unique_dates) < 2:
        prev_h = df["high"].max()
        prev_l = df["low"].min()
        prev_c = df["close"].iloc[-1]
    else:
        prev_date = unique_dates[-2]
        prev_day = df[df["date"] == prev_date]
        prev_h = prev_day["high"].max()
        prev_l = prev_day["low"].min()
        prev_c = prev_day["close"].iloc[-1]

    p = (prev_h + prev_l + prev_c) / 3
    return {
        "pivot": round(p, 2),
        "pivot_r1": round(2 * p - prev_l, 2),
        "pivot_r2": round(p + (prev_h - prev_l), 2),
        "pivot_r3": round(prev_h + 2 * (p - prev_l), 2),
        "pivot_s1": round(2 * p - prev_h, 2),
        "pivot_s2": round(p - (prev_h - prev_l), 2),
        "pivot_s3": round(prev_l - 2 * (prev_h - p), 2),
    }


def _compute_fibonacci(candles: list[Candle]) -> dict[str, float]:
    lookback = min(50, len(candles))
    recent = candles[-lookback:]
    high_idx = max(range(len(recent)), key=lambda i: recent[i].high)
    low_idx = min(range(len(recent)), key=lambda i: recent[i].low)
    swing_high = recent[high_idx].high
    swing_low = recent[low_idx].low
    diff = swing_high - swing_low
    if high_idx > low_idx:
        return {
            "0.382": round(swing_high - 0.382 * diff, 2),
            "0.500": round(swing_high - 0.500 * diff, 2),
            "0.618": round(swing_high - 0.618 * diff, 2),
        }
    return {
        "0.382": round(swing_low + 0.382 * diff, 2),
        "0.500": round(swing_low + 0.500 * diff, 2),
        "0.618": round(swing_low + 0.618 * diff, 2),
    }


# ── IndicatorOrchestrator (new modular API) ───────────────────────────────────

class IndicatorOrchestrator:
    """Compute a user-selected set of indicators using the modular registry.

    This is the new public API for ad-hoc indicator selection.  The legacy
    ``AnalysisPipeline`` uses ``IndicatorEngine`` below.

    Example
    -------
        orchestrator = IndicatorOrchestrator(["ema21", "ema50", "rsi14",
                                              "bb", "volume_profile:bins=30"])
        data = orchestrator.compute(candles)   # dict[str, list[float]]

    Bug #1 fix: spec "ema21" → base "ema" → AVAILABLE_INDICATORS["ema"]
    Bug #2 fix: IndicatorOrchestrator lives in this file (services/), not in
                app/indicators/__init__.py, so the import path is correct.
    """

    DEFAULT = ["ema21", "ema50", "ema200", "vwap", "rsi14", "macd", "bb", "atr"]

    def __init__(self, selected: list[str] | None = None) -> None:
        self.selected = selected or self.DEFAULT

    def compute(self, candles: list[Candle]) -> dict[str, list[float]]:
        result: dict[str, list[float]] = {}
        for spec in self.selected:
            base_name, params = _parse_spec(spec)
            # Bug #1 fix: look up by base_name, not full spec.
            cls = AVAILABLE_INDICATORS.get(base_name)
            if cls is None:
                logger.warning(
                    "Unknown indicator '%s' (parsed base='%s') — skipping.  "
                    "Available: %s",
                    spec, base_name, sorted(AVAILABLE_INDICATORS),
                )
                continue
            try:
                instance = cls(**params)
                data = instance.compute(candles)
                result.update(data)
            except Exception as exc:
                logger.error("Indicator '%s' failed: %s", spec, exc)
        return result


# ── IndicatorEngine (pipeline-compatible orchestrator) ────────────────────────

class IndicatorEngine:
    """Pipeline-compatible orchestrator.

    Delegates to modular indicator classes for EMA, VWAP, RSI, MACD, BB, ATR,
    ADX.  Keeps direct computation for complex derived indicators that don't
    yet have standalone modules (Supertrend, Keltner, Stoch RSI, OBV, etc.).

    The public interface (``calculate_base``, ``calculate_full``, ``calculate``)
    is unchanged so ``AnalysisPipeline`` requires zero modification.
    """

    def calculate_base(self, candles: list[Candle]) -> dict[str, list[float]]:
        """Layer-1 indicators — computed before regime detection."""
        df = pd.DataFrame([c.model_dump() for c in candles])
        close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

        # ── modular indicators ────────────────────────────────────────────────
        ind: dict = {}

        # EMA 21 / 50 / 200 (each call returns ema{N} + ema{N}_slope)
        for period in (21, 50, 200):
            cls = AVAILABLE_INDICATORS.get("ema")
            if cls:
                ind.update(cls(period=period).compute(candles))

        # VWAP
        vwap_cls = AVAILABLE_INDICATORS.get("vwap")
        if vwap_cls:
            ind.update(vwap_cls().compute(candles))

        # ATR + ATR SMA20
        atr_cls = AVAILABLE_INDICATORS.get("atr")
        if atr_cls:
            ind.update(atr_cls(period=14).compute(candles))

        # Bollinger Bands + width percentile
        bb_cls = AVAILABLE_INDICATORS.get("bb")
        if bb_cls:
            ind.update(bb_cls(period=20, std_dev=2.0).compute(candles))

        # ADX
        adx_cls = AVAILABLE_INDICATORS.get("adx")
        if adx_cls:
            ind.update(adx_cls(period=14).compute(candles))

        # ── non-modular helpers ───────────────────────────────────────────────
        # Volume SMA20
        vol_sma20 = volume.rolling(window=20).mean().bfill().fillna(volume.mean())
        ind["volume_sma20"] = vol_sma20.round(2).tolist()
        ind["volume"] = volume.round(2).tolist()

        # OBV + slope
        obv = _compute_obv(close, volume)
        ind["obv"] = obv.round(2).tolist()
        ind["obv_slope"] = _lr_slope(obv, 10).round(4).tolist()

        return ind

    def calculate_full(self, candles: list[Candle], regime: Regime) -> dict[str, list[float]]:
        """Layer-1 base + all regime-specific indicators merged."""
        ind = self.calculate_base(candles)
        df = pd.DataFrame([c.model_dump() for c in candles])
        close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]
        vwap = pd.Series(ind["vwap"])

        # ── modular: RSI ──────────────────────────────────────────────────────
        rsi_cls = AVAILABLE_INDICATORS.get("rsi")
        if rsi_cls:
            ind.update(rsi_cls(period=14).compute(candles))
        else:
            from ta.momentum import RSIIndicator as _RSI
            ind["rsi14"] = _RSI(close=close, window=14).rsi().fillna(50.0).round(2).tolist()

        # ── modular: MACD ─────────────────────────────────────────────────────
        macd_cls = AVAILABLE_INDICATORS.get("macd")
        if macd_cls:
            ind.update(macd_cls(fast=12, slow=26, signal=9).compute(candles))
        else:
            from ta.trend import MACD as _MACD
            m = _MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
            hist = m.macd_diff().fillna(0.0)
            ind["macd_line"] = m.macd().fillna(0.0).round(2).tolist()
            ind["macd_signal"] = m.macd_signal().fillna(0.0).round(2).tolist()
            ind["macd_histogram"] = hist.round(2).tolist()
            ind["macd_hist_slope"] = hist.diff(3).fillna(0.0).round(4).tolist()

        # ── non-modular: Stochastic RSI ───────────────────────────────────────
        srsi = StochRSIIndicator(close=close, window=14, smooth1=3, smooth2=3)
        ind["stoch_rsi_k"] = srsi.stochrsi_k().fillna(0.5).round(4).tolist()
        ind["stoch_rsi_d"] = srsi.stochrsi_d().fillna(0.5).round(4).tolist()

        # ── non-modular: Supertrend ───────────────────────────────────────────
        st_val, st_dir = _compute_supertrend(high, low, close, period=10, multiplier=3.0)
        ind["supertrend"] = st_val.round(2).tolist()
        ind["supertrend_direction"] = [1.0 if d == "up" else 0.0 for d in st_dir]

        # ── non-modular: Keltner Channels (EMA20 ± 1.5 ATR10) ────────────────
        kc_middle = close.ewm(span=20, adjust=False).mean()
        tr = _true_range(high, low, close)
        kc_atr10 = tr.rolling(window=10).mean().bfill().fillna(0.0)
        ind["kc_upper"] = (kc_middle + 1.5 * kc_atr10).round(2).tolist()
        ind["kc_middle"] = kc_middle.round(2).tolist()
        ind["kc_lower"] = (kc_middle - 1.5 * kc_atr10).round(2).tolist()

        # ── Squeeze detection ─────────────────────────────────────────────────
        bb_upper_s = pd.Series(ind["bb_upper"])
        bb_lower_s = pd.Series(ind["bb_lower"])
        kc_upper_s = pd.Series(ind["kc_upper"])
        kc_lower_s = pd.Series(ind["kc_lower"])
        in_sq = (bb_upper_s < kc_upper_s) & (bb_lower_s > kc_lower_s)
        sq_fired = in_sq.shift(1).fillna(False) & ~in_sq
        ind["in_squeeze"] = in_sq.astype(float).tolist()
        ind["squeeze_fired"] = sq_fired.astype(float).tolist()

        # ── modular: VWAP bands ───────────────────────────────────────────────
        vwap_bands_cls = AVAILABLE_INDICATORS.get("vwap_bands")
        if vwap_bands_cls:
            ind.update(vwap_bands_cls().compute(candles))
        else:
            variance = ((((high + low + close) / 3) - vwap) ** 2 * volume).cumsum() / volume.cumsum()
            std = np.sqrt(variance.clip(lower=0))
            ind["vwap_upper1"] = (vwap + std).round(2).tolist()
            ind["vwap_lower1"] = (vwap - std).round(2).tolist()
            ind["vwap_upper2"] = (vwap + 2 * std).round(2).tolist()
            ind["vwap_lower2"] = (vwap - 2 * std).round(2).tolist()

        # ── non-modular: Pivot Points ─────────────────────────────────────────
        pivots = _compute_pivot_points(candles)
        for k, v in pivots.items():
            ind[k] = [v] * len(candles)

        # ── non-modular: Donchian Channels ────────────────────────────────────
        ind["donchian_upper"] = high.rolling(20).max().bfill().round(2).tolist()
        ind["donchian_lower"] = low.rolling(20).min().bfill().round(2).tolist()

        # ── non-modular: Fibonacci ─────────────────────────────────────────────
        fib = _compute_fibonacci(candles)
        for k, v in fib.items():
            ind[f"fib_{k.replace('.', '')}"] = [v] * len(candles)

        return ind

    def calculate(self, candles: list[Candle]) -> dict[str, list[float]]:
        """Legacy single-call for backward compatibility."""
        dummy = Regime(type="range", tradable=True)
        return self.calculate_full(candles, dummy)
