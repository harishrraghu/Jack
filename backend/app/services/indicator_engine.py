import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import ADXIndicator, MACD
from ta.volatility import BollingerBands

from app.schemas import Candle, Regime


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=period).mean().bfill().fillna(0.0)


def _compute_supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series, list[str]]:
    atr = _compute_atr(high, low, close, period)
    hl2 = (high + low) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(close)
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(np.nan, index=close.index)
    direction = ["up"] * n

    # Seed first value
    supertrend.iloc[0] = final_lower.iloc[0]

    for i in range(1, n):
        fu_prev = final_upper.iloc[i - 1]
        fl_prev = final_lower.iloc[i - 1]
        c_prev = close.iloc[i - 1]

        final_upper.iloc[i] = (
            min(basic_upper.iloc[i], fu_prev)
            if c_prev > fu_prev
            else basic_upper.iloc[i]
        )
        final_lower.iloc[i] = (
            max(basic_lower.iloc[i], fl_prev)
            if c_prev < fl_prev
            else basic_lower.iloc[i]
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


def _bb_width_percentile(bb_width: pd.Series, window: int = 50) -> pd.Series:
    def rank_last(arr: np.ndarray) -> float:
        last = arr[-1]
        return float(np.sum(arr < last) / len(arr) * 100)

    return bb_width.rolling(window=window, min_periods=1).apply(rank_last, raw=True)


def _compute_pivot_points(candles: list[Candle]) -> dict[str, float]:
    """Standard daily pivot points from previous day H/L/C."""
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


def _compute_vwap_bands(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    vwap: pd.Series,
) -> dict[str, pd.Series]:
    tp = (high + low + close) / 3
    variance = ((tp - vwap) ** 2 * volume).cumsum() / volume.cumsum()
    std = np.sqrt(variance.clip(lower=0))
    return {
        "vwap_upper1": (vwap + std).round(2),
        "vwap_lower1": (vwap - std).round(2),
        "vwap_upper2": (vwap + 2 * std).round(2),
        "vwap_lower2": (vwap - 2 * std).round(2),
    }


def _compute_fibonacci(candles: list[Candle]) -> dict[str, float]:
    """Fib retracement from most recent significant swing."""
    lookback = min(50, len(candles))
    recent = candles[-lookback:]
    high_idx = max(range(len(recent)), key=lambda i: recent[i].high)
    low_idx = min(range(len(recent)), key=lambda i: recent[i].low)
    swing_high = recent[high_idx].high
    swing_low = recent[low_idx].low
    diff = swing_high - swing_low

    if high_idx > low_idx:
        # Most recent move was up — retracements pull back from high
        return {
            "0.382": round(swing_high - 0.382 * diff, 2),
            "0.500": round(swing_high - 0.500 * diff, 2),
            "0.618": round(swing_high - 0.618 * diff, 2),
        }
    else:
        # Most recent move was down — retracements bounce from low
        return {
            "0.382": round(swing_low + 0.382 * diff, 2),
            "0.500": round(swing_low + 0.500 * diff, 2),
            "0.618": round(swing_low + 0.618 * diff, 2),
        }


class IndicatorEngine:
    def calculate_base(self, candles: list[Candle]) -> dict[str, list[float]]:
        """Layer 1 indicators — computed before regime detection."""
        df = pd.DataFrame([c.model_dump() for c in candles])
        close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

        ema21 = close.ewm(span=21, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()

        ema21_slope = ((ema21 - ema21.shift(5)) / 5).fillna(0.0)
        ema50_slope = ((ema50 - ema50.shift(5)) / 5).fillna(0.0)
        ema200_slope = ((ema200 - ema200.shift(5)) / 5).fillna(0.0)

        tp = (high + low + close) / 3
        vwap = (tp * volume).cumsum() / volume.cumsum()

        adx = ADXIndicator(high=high, low=low, close=close, window=14).adx().fillna(0.0)
        atr = _compute_atr(high, low, close, 14)
        atr_sma20 = atr.rolling(window=20).mean().bfill().fillna(0.0)

        bb = BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = bb.bollinger_hband().fillna(close)
        bb_middle = bb.bollinger_mavg().fillna(close)
        bb_lower = bb.bollinger_lband().fillna(close)
        bb_width = ((bb_upper - bb_lower) / bb_middle.replace(0, np.nan)).fillna(0.0)
        bb_width_pct = _bb_width_percentile(bb_width)

        volume_sma20 = volume.rolling(window=20).mean().bfill().fillna(volume.mean())
        obv = _compute_obv(close, volume)
        obv_slope = _lr_slope(obv, 10)

        return {
            "ema21": ema21.round(2).tolist(),
            "ema50": ema50.round(2).tolist(),
            "ema200": ema200.round(2).tolist(),
            "ema21_slope": ema21_slope.round(4).tolist(),
            "ema50_slope": ema50_slope.round(4).tolist(),
            "ema200_slope": ema200_slope.round(4).tolist(),
            "vwap": vwap.round(2).tolist(),
            "adx": adx.round(2).tolist(),
            "atr": atr.round(2).tolist(),
            "atr_sma20": atr_sma20.round(2).tolist(),
            "bb_upper": bb_upper.round(2).tolist(),
            "bb_middle": bb_middle.round(2).tolist(),
            "bb_lower": bb_lower.round(2).tolist(),
            "bb_width": bb_width.round(4).tolist(),
            "bb_width_percentile": bb_width_pct.round(2).tolist(),
            "volume_sma20": volume_sma20.round(2).tolist(),
            "obv": obv.round(2).tolist(),
            "obv_slope": obv_slope.round(4).tolist(),
            "volume": volume.round(2).tolist(),
        }

    def calculate_full(self, candles: list[Candle], regime: Regime) -> dict[str, list[float]]:
        """Base + all regime-specific indicators merged."""
        ind = self.calculate_base(candles)
        df = pd.DataFrame([c.model_dump() for c in candles])
        close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]
        vwap = pd.Series(ind["vwap"])

        # RSI is always needed
        rsi14 = RSIIndicator(close=close, window=14).rsi().fillna(50.0)
        ind["rsi14"] = rsi14.round(2).tolist()

        # MACD — always computed
        macd_obj = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_hist = macd_obj.macd_diff().fillna(0.0)
        ind["macd_line"] = macd_obj.macd().fillna(0.0).round(2).tolist()
        ind["macd_signal"] = macd_obj.macd_signal().fillna(0.0).round(2).tolist()
        ind["macd_histogram"] = macd_hist.round(2).tolist()
        ind["macd_hist_slope"] = macd_hist.diff(3).fillna(0.0).round(4).tolist()

        # Stochastic RSI — always computed
        srsi = StochRSIIndicator(close=close, window=14, smooth1=3, smooth2=3)
        ind["stoch_rsi_k"] = srsi.stochrsi_k().fillna(0.5).round(4).tolist()
        ind["stoch_rsi_d"] = srsi.stochrsi_d().fillna(0.5).round(4).tolist()

        # Supertrend(10, 3) — always computed; direction encoded as 1.0=up, 0.0=down
        st_val, st_dir = _compute_supertrend(high, low, close, period=10, multiplier=3.0)
        ind["supertrend"] = st_val.round(2).tolist()
        ind["supertrend_direction"] = [1.0 if d == "up" else 0.0 for d in st_dir]

        # Keltner Channels (EMA20 ± 1.5 * ATR10) — always computed (used for squeeze detection)
        kc_middle = close.ewm(span=20, adjust=False).mean()
        kc_atr10 = _compute_atr(high, low, close, 10)
        kc_upper = kc_middle + 1.5 * kc_atr10
        kc_lower = kc_middle - 1.5 * kc_atr10
        ind["kc_upper"] = kc_upper.round(2).tolist()
        ind["kc_middle"] = kc_middle.round(2).tolist()
        ind["kc_lower"] = kc_lower.round(2).tolist()

        # Squeeze detection
        bb_upper_s = pd.Series(ind["bb_upper"])
        bb_lower_s = pd.Series(ind["bb_lower"])
        in_sq = (bb_upper_s < kc_upper) & (bb_lower_s > kc_lower)
        sq_fired = in_sq.shift(1).fillna(False) & ~in_sq
        ind["in_squeeze"] = in_sq.astype(float).tolist()
        ind["squeeze_fired"] = sq_fired.astype(float).tolist()

        # VWAP bands — always computed
        vwap_bands = _compute_vwap_bands(high, low, close, volume, vwap)
        for k, v in vwap_bands.items():
            ind[k] = v.tolist()

        # Pivot Points — always computed
        pivots = _compute_pivot_points(candles)
        for k, v in pivots.items():
            ind[k] = [v] * len(candles)

        # Donchian Channels — always computed (used in volatile strategies)
        ind["donchian_upper"] = high.rolling(20).max().bfill().round(2).tolist()
        ind["donchian_lower"] = low.rolling(20).min().bfill().round(2).tolist()

        # Fibonacci retracement
        fib = _compute_fibonacci(candles)
        for k, v in fib.items():
            ind[f"fib_{k.replace('.', '')}"] = [v] * len(candles)

        return ind

    def calculate(self, candles: list[Candle]) -> dict[str, list[float]]:
        """Legacy single-call for backward compatibility."""
        dummy = Regime(type="range", tradable=True)
        return self.calculate_full(candles, dummy)
