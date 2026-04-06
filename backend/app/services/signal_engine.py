from app.schemas import (
    Candle,
    DayContext,
    Liquidity,
    Regime,
    Score,
    Signal,
    Strategy,
    StructureLevels,
    TrendHealth,
    VolumeAnalysis,
)

_TRENDING_UP = {"trend_up", "weak_trend_up"}
_TRENDING_DOWN = {"trend_down", "weak_trend_down"}


class SignalEngine:
    def generate(
        self,
        candles: list[Candle],
        indicators: dict,
        context: DayContext,
        regime: Regime,
        liquidity: Liquidity,
        strategies: list[Strategy],
        score: Score,
        structure_levels: StructureLevels | None = None,
        volume: VolumeAnalysis | None = None,
        trend_health: TrendHealth | None = None,
    ) -> Signal:
        last = candles[-1]
        atr = indicators["atr"][-1]
        matched = [s for s in strategies if s.matched and s.prerequisites_met]

        reasons = [
            f"Context bias is {context.bias}",
            f"Regime classified as {regime.type} (strength {regime.strength:.0f})",
        ]
        if trend_health:
            reasons.append(f"Trend health: {trend_health.status}, momentum {trend_health.momentum}")
        if volume:
            vol_desc = "supports" if volume.volume_supports_move else "does not support"
            reasons.append(f"Volume {vol_desc} move (ratio {volume.volume_ratio:.1f}x avg)")
        if liquidity.event:
            reasons.append(f"Liquidity event: {liquidity.event} {liquidity.direction}")
        for s in matched:
            reasons.append(f"Strategy: {s.name}")

        # Stand aside takes priority
        stand_aside = next((s for s in strategies if s.name == "Stand Aside" and s.matched), None)
        if stand_aside:
            return Signal(
                type="NONE",
                entry=round(last.close, 2),
                stopLoss=round(last.close - atr, 2),
                target=round(last.close + atr, 2),
                confidence=round(score.value, 2),
                reasons=reasons + ["Volatile regime with unconvincing volume — standing aside"],
            )

        if score.value < 55 or not regime.tradable:
            return Signal(
                type="NONE",
                entry=round(last.close, 2),
                stopLoss=round(last.close - atr, 2),
                target=round(last.close + atr, 2),
                confidence=round(score.value, 2),
                reasons=reasons + [f"Score {score.value:.0f} below execution threshold (55)"],
            )

        # Determine direction from best matched strategy
        long_strategies = [s for s in matched if "(Long)" in s.name or "Reversion (Long)" in s.name or "Call" in s.name]
        short_strategies = [s for s in matched if "(Short)" in s.name or "Reversion (Short)" in s.name or "Put" in s.name]
        neutral_strategies = [s for s in matched if s not in long_strategies and s not in short_strategies]

        # Regime-based direction determination
        is_bullish_regime = regime.type in _TRENDING_UP
        is_bearish_regime = regime.type in _TRENDING_DOWN
        is_range = regime.type in ("range", "squeeze", "volatile")

        direction: str | None = None

        if is_bullish_regime and context.bias != "bearish":
            direction = "BUY_CALL"
        elif is_bearish_regime and context.bias != "bullish":
            direction = "BUY_PUT"
        elif long_strategies and not short_strategies:
            direction = "BUY_CALL"
        elif short_strategies and not long_strategies:
            direction = "BUY_PUT"
        elif is_range and matched:
            # For range/squeeze strategies, determine from the matched strategy name
            first = matched[0]
            if "Long" in first.name or "Reversion (Long)" in first.name:
                direction = "BUY_CALL"
            elif "Short" in first.name or "Reversion (Short)" in first.name:
                direction = "BUY_PUT"
            else:
                # Liquidity sweep or squeeze — use MACD
                macd_hist = indicators.get("macd_histogram", [0])[-1]
                direction = "BUY_CALL" if macd_hist > 0 else "BUY_PUT"

        if direction is None:
            return Signal(
                type="NONE",
                entry=round(last.close, 2),
                stopLoss=round(last.close - atr, 2),
                target=round(last.close + atr, 2),
                confidence=round(score.value, 2),
                reasons=reasons + ["Conditions conflict across modules — no clear direction"],
            )

        # Use entry from best matched strategy if available
        best_strategy = matched[0] if matched else None
        if best_strategy and best_strategy.entry_price:
            entry = best_strategy.entry_price
        else:
            entry = round(last.close, 2)

        if direction == "BUY_CALL":
            stop_loss = round(last.close - atr * 0.9, 2)
            target = round(last.close + atr * 1.8, 2)
            if best_strategy and best_strategy.stop_loss:
                stop_loss = best_strategy.stop_loss
            if best_strategy and best_strategy.target_price:
                target = best_strategy.target_price
        else:
            stop_loss = round(last.close + atr * 0.9, 2)
            target = round(last.close - atr * 1.8, 2)
            if best_strategy and best_strategy.stop_loss:
                stop_loss = best_strategy.stop_loss
            if best_strategy and best_strategy.target_price:
                target = best_strategy.target_price

        return Signal(
            type=direction,
            entry=entry,
            stopLoss=stop_loss,
            target=target,
            confidence=round(score.value, 2),
            reasons=reasons + [f"Bullish/bearish confluence cleared threshold ({score.value:.0f})"],
        )
