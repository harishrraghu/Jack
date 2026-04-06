from app.schemas import Candle, Regime


class RegimeEngine:
    def derive(self, candles: list[Candle], indicators: dict[str, list[float]]) -> Regime:
        close = candles[-1].close
        ema21 = indicators["ema21"][-1]
        ema50 = indicators["ema50"][-1]
        ema200 = indicators["ema200"][-1]
        vwap = indicators["vwap"][-1]
        adx = indicators["adx"][-1]
        atr = indicators["atr"][-1]
        atr_sma20 = indicators["atr_sma20"][-1]
        bb_width_pct = indicators["bb_width_percentile"][-1]

        ema21_slope = indicators["ema21_slope"][-1]
        ema50_slope = indicators["ema50_slope"][-1]
        ema200_slope = indicators["ema200_slope"][-1]

        # EMA alignment classification
        fully_bullish = ema21 > ema50 > ema200
        fully_bearish = ema21 < ema50 < ema200
        partial_bull = (ema21 > ema50 and ema50 <= ema200) or (ema21 <= ema50 and ema50 > ema200)
        partial_bear = (ema21 < ema50 and ema50 >= ema200) or (ema21 >= ema50 and ema50 < ema200)

        if fully_bullish:
            ema_alignment = "fully_bullish"
        elif fully_bearish:
            ema_alignment = "fully_bearish"
        elif partial_bull or partial_bear:
            ema_alignment = "partial"
        else:
            ema_alignment = "mixed"

        # EMA slopes
        slopes_positive = ema21_slope > 0 and ema50_slope > 0 and ema200_slope > 0
        slopes_negative = ema21_slope < 0 and ema50_slope < 0 and ema200_slope < 0

        # Volatility flags
        atr_elevated = atr_sma20 > 0 and atr > 1.5 * atr_sma20
        in_squeeze = bb_width_pct <= 10

        # Compute regime strength (confidence 0-100)
        def _strength(factors: list[bool]) -> float:
            return round(sum(factors) / len(factors) * 100, 1)

        # --- Classification ---

        # Squeeze: BB compressed, ADX < 20
        if in_squeeze and adx < 20:
            strength = _strength([in_squeeze, adx < 20])
            return Regime(
                type="squeeze",
                tradable=True,
                strength=strength,
                ema_alignment=ema_alignment,
                bb_width_percentile=bb_width_pct,
            )

        # Volatile: high ATR, no direction
        if atr_elevated and adx < 20:
            strength = _strength([atr_elevated, adx < 20])
            return Regime(
                type="volatile",
                tradable=True,
                strength=strength,
                ema_alignment=ema_alignment,
                bb_width_percentile=bb_width_pct,
            )

        # Strong uptrend: ADX > 25, fully bullish EMAs, positive slopes, above VWAP
        if adx > 25 and fully_bullish and slopes_positive and close > vwap:
            strength = _strength([adx > 25, fully_bullish, slopes_positive, close > vwap])
            return Regime(
                type="trend_up",
                tradable=True,
                strength=strength,
                ema_alignment="fully_bullish",
                bb_width_percentile=bb_width_pct,
            )

        # Strong downtrend: ADX > 25, fully bearish EMAs, negative slopes, below VWAP
        if adx > 25 and fully_bearish and slopes_negative and close < vwap:
            strength = _strength([adx > 25, fully_bearish, slopes_negative, close < vwap])
            return Regime(
                type="trend_down",
                tradable=True,
                strength=strength,
                ema_alignment="fully_bearish",
                bb_width_percentile=bb_width_pct,
            )

        # Cross-check: ADX says trending but EMAs not aligned → override to range
        if adx > 25 and not (fully_bullish or fully_bearish):
            return Regime(
                type="range",
                tradable=True,
                strength=40.0,
                ema_alignment=ema_alignment,
                bb_width_percentile=bb_width_pct,
            )

        # Weak uptrend: ADX 20-25, partial bullish alignment forming
        if 20 <= adx <= 25 and (fully_bullish or ema_alignment == "partial") and close > vwap:
            strength = _strength([adx >= 20, close > vwap, ema21 > ema50])
            return Regime(
                type="weak_trend_up",
                tradable=True,
                strength=strength,
                ema_alignment=ema_alignment,
                bb_width_percentile=bb_width_pct,
            )

        # Weak downtrend: ADX 20-25, partial bearish alignment forming
        if 20 <= adx <= 25 and (fully_bearish or ema_alignment == "partial") and close < vwap:
            strength = _strength([adx >= 20, close < vwap, ema21 < ema50])
            return Regime(
                type="weak_trend_down",
                tradable=True,
                strength=strength,
                ema_alignment=ema_alignment,
                bb_width_percentile=bb_width_pct,
            )

        # Default: range
        tradable = adx >= 15 and not atr_elevated
        return Regime(
            type="range",
            tradable=tradable,
            strength=max(0, 30 - adx),
            ema_alignment=ema_alignment,
            bb_width_percentile=bb_width_pct,
        )
