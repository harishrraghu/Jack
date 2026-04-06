from app.schemas import Candle, Regime, TrendHealth

_TRENDING = {"trend_up", "trend_down", "weak_trend_up", "weak_trend_down"}


class TrendHealthEngine:
    def assess(
        self, candles: list[Candle], indicators: dict, regime: Regime
    ) -> TrendHealth | None:
        """Returns None if regime is not trending (Layer 2 is skipped)."""
        if regime.type not in _TRENDING:
            return None

        close = candles[-1].close
        rsi = indicators["rsi14"][-1]
        vwap = indicators["vwap"][-1]
        ema21 = indicators["ema21"][-1]
        ema50 = indicators["ema50"][-1]
        macd_hist = indicators["macd_histogram"][-1]
        macd_hist_slope = indicators["macd_hist_slope"][-1]
        stoch_k = indicators["stoch_rsi_k"][-1]
        stoch_k_prev = indicators["stoch_rsi_k"][-2] if len(indicators["stoch_rsi_k"]) > 1 else stoch_k
        stoch_d = indicators["stoch_rsi_d"][-1]

        is_uptrend = regime.type in ("trend_up", "weak_trend_up")

        # --- RSI context ---
        if is_uptrend:
            if 60 <= rsi <= 80:
                rsi_context = f"RSI {rsi:.0f} in uptrend — healthy momentum"
                rsi_status = "healthy"
            elif rsi > 80:
                rsi_context = f"RSI {rsi:.0f} in uptrend — overextended"
                rsi_status = "overextended"
            elif rsi < 50:
                rsi_context = f"RSI {rsi:.0f} in uptrend — trend weakening"
                rsi_status = "weakening"
            else:
                rsi_context = f"RSI {rsi:.0f} in uptrend — normal range"
                rsi_status = "healthy"
        else:
            if 20 <= rsi <= 40:
                rsi_context = f"RSI {rsi:.0f} in downtrend — healthy bearish momentum"
                rsi_status = "healthy"
            elif rsi < 20:
                rsi_context = f"RSI {rsi:.0f} in downtrend — overextended"
                rsi_status = "overextended"
            elif rsi > 50:
                rsi_context = f"RSI {rsi:.0f} in downtrend — trend weakening"
                rsi_status = "weakening"
            else:
                rsi_context = f"RSI {rsi:.0f} in downtrend — normal range"
                rsi_status = "healthy"

        # --- MACD histogram slope ---
        if macd_hist_slope > 0:
            macd_slope_label = "rising"
        elif macd_hist_slope < 0:
            macd_slope_label = "falling"
        else:
            macd_slope_label = "flat"

        # --- Momentum ---
        if macd_slope_label == "rising" and rsi_status == "healthy":
            momentum = "accelerating"
        elif macd_slope_label == "falling" and rsi_status in ("weakening", "overextended"):
            momentum = "decelerating"
        elif macd_hist < 0 and is_uptrend:
            momentum = "reversing"
        elif macd_hist > 0 and not is_uptrend:
            momentum = "reversing"
        elif macd_slope_label == "flat":
            momentum = "steady"
        else:
            momentum = "steady"

        # --- Stochastic RSI signal ---
        # Detect cross: k crossed from above/below 0.8/0.2
        if stoch_k_prev >= 0.8 and stoch_k < 0.8:
            stoch_signal = "bearish_cross"
        elif stoch_k_prev <= 0.2 and stoch_k > 0.2:
            stoch_signal = "bullish_cross"
        else:
            stoch_signal = "neutral"

        # --- VWAP supporting ---
        if is_uptrend:
            vwap_supporting = close > vwap
        else:
            vwap_supporting = close < vwap

        # --- EMA 21 relationship ---
        price_vs_ema21 = close - ema21
        ema21_above_ema50 = ema21 > ema50

        # --- Overall status ---
        if rsi_status == "overextended":
            status = "overextended"
        elif momentum == "reversing" or (rsi_status == "weakening" and not vwap_supporting):
            status = "exhausted"
        elif rsi_status == "weakening" or momentum == "decelerating":
            status = "weakening"
        else:
            status = "healthy"

        # Stoch RSI bearish cross in uptrend + MACD flattening = momentum dying
        if is_uptrend and stoch_signal == "bearish_cross" and macd_slope_label in ("flat", "falling"):
            if status == "healthy":
                status = "weakening"
        if not is_uptrend and stoch_signal == "bullish_cross" and macd_slope_label in ("flat", "rising"):
            if status == "healthy":
                status = "weakening"

        return TrendHealth(
            status=status,
            momentum=momentum,
            rsi_context=rsi_context,
            macd_histogram_slope=macd_slope_label,
            stoch_rsi_signal=stoch_signal,
            vwap_supporting=vwap_supporting,
        )
