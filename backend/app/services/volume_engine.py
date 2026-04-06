import numpy as np

from app.schemas import Candle, Regime, VolumeAnalysis


def _obv_trend(obv_list: list[float], n: int = 10) -> str:
    if len(obv_list) < n:
        return "flat"
    slope = obv_list[-1] - obv_list[-n]
    if slope > 0:
        return "rising"
    if slope < 0:
        return "falling"
    return "flat"


def _volume_trend(volumes: list[float], n: int = 10) -> str:
    if len(volumes) < n:
        return "flat"
    y = np.array(volumes[-n:], dtype=float)
    x = np.arange(n, dtype=float)
    slope = np.polyfit(x, y, 1)[0]
    mean_vol = np.mean(y)
    if mean_vol == 0:
        return "flat"
    normalized = slope / mean_vol
    if normalized > 0.01:
        return "expanding"
    if normalized < -0.01:
        return "contracting"
    return "flat"


def _price_volume_divergence(candles: list[Candle], n: int = 5) -> str:
    """Detect divergence between price highs/lows and volume over last n candles."""
    if len(candles) < n + 1:
        return "none"
    recent = candles[-(n + 1):]
    prices = [c.close for c in recent]
    volumes = [c.volume for c in recent]

    # Higher highs but declining volume = bearish divergence
    price_rising = prices[-1] > prices[0]
    vol_declining = volumes[-1] < volumes[0]
    price_falling = prices[-1] < prices[0]
    vol_declining_on_fall = volumes[-1] < volumes[0]

    if price_rising and vol_declining:
        return "bearish_divergence"
    if price_falling and vol_declining_on_fall:
        return "bullish_divergence"
    return "none"


class VolumeEngine:
    def analyze(
        self, candles: list[Candle], indicators: dict, regime: Regime
    ) -> VolumeAnalysis:
        last = candles[-1]
        current_vol = last.volume
        vol_sma20 = indicators["volume_sma20"][-1]
        atr = indicators["atr"][-1]
        vwap = indicators["vwap"][-1]
        close = last.close

        # Volume ratio
        vol_ratio = current_vol / vol_sma20 if vol_sma20 > 0 else 1.0

        # Candle vs average classification
        if vol_ratio >= 2.0:
            candle_vs_avg = "spike"
        elif vol_ratio >= 1.5:
            candle_vs_avg = "elevated"
        elif vol_ratio >= 0.5:
            candle_vs_avg = "normal"
        else:
            candle_vs_avg = "dry"

        # OBV trend
        obv_list = indicators["obv"]
        obv_trend = _obv_trend(obv_list)

        # OBV divergence: OBV direction disagrees with price direction
        price_slope = close - candles[-5].close if len(candles) >= 5 else 0
        obv_slope_val = indicators["obv_slope"][-1]
        obv_divergence = (price_slope > 0 and obv_slope_val < 0) or (price_slope < 0 and obv_slope_val > 0)

        # VWAP position
        vwap_position = "above" if close > vwap else "below"

        # VWAP distance in ATR units
        vwap_distance_atr = abs(close - vwap) / atr if atr > 0 else 0.0

        # Price-volume divergence
        pv_div = _price_volume_divergence(candles)

        # Volume trend (10-period)
        vol_trend = _volume_trend(indicators["volume"])

        # Overall: does volume support the move?
        is_uptrend = regime.type in ("trend_up", "weak_trend_up")
        is_downtrend = regime.type in ("trend_down", "weak_trend_down")

        volume_supports = True
        if candle_vs_avg == "dry":
            volume_supports = False
        if obv_divergence:
            volume_supports = False
        if is_uptrend and pv_div == "bearish_divergence":
            volume_supports = False
        if is_downtrend and pv_div == "bullish_divergence":
            volume_supports = False
        if vol_trend == "contracting" and candle_vs_avg in ("dry", "normal"):
            volume_supports = False

        return VolumeAnalysis(
            candle_vs_avg=candle_vs_avg,
            volume_ratio=round(vol_ratio, 2),
            obv_trend=obv_trend,
            obv_divergence=obv_divergence,
            vwap_position=vwap_position,
            vwap_distance_atr=round(vwap_distance_atr, 2),
            price_volume_divergence=pv_div,
            volume_trend=vol_trend,
            volume_supports_move=volume_supports,
        )
