from app.schemas import (
    DayContext,
    ForecastConfirmation,
    Narrative,
    Regime,
    Signal,
    StructureLevels,
    TrendHealth,
    VolumeAnalysis,
)


def _regime_phrase(regime: Regime) -> str:
    labels = {
        "trend_up": "a strong uptrend",
        "trend_down": "a strong downtrend",
        "weak_trend_up": "a developing uptrend",
        "weak_trend_down": "a developing downtrend",
        "range": "a range-bound market",
        "squeeze": "a volatility squeeze",
        "volatile": "a volatile, directionless market",
    }
    base = labels.get(regime.type, regime.type.replace("_", " "))
    return f"{base} (EMA alignment: {regime.ema_alignment.replace('_', ' ')}, ADX confidence {regime.strength:.0f})"


class NarrativeEngine:
    def build(
        self,
        regime: Regime,
        context: DayContext,
        signal: Signal,
        volume: VolumeAnalysis | None = None,
        trend_health: TrendHealth | None = None,
        forecast_confirmation: ForecastConfirmation | None = None,
        structure_levels: StructureLevels | None = None,
    ) -> Narrative:
        # Layer 1: Regime
        regime_line = f"Market is in {_regime_phrase(regime)} with {context.bias} daily bias."

        # Layer 2: Trend health
        if trend_health:
            health_line = (
                f"Momentum is {trend_health.momentum} — {trend_health.rsi_context}. "
                f"MACD histogram is {trend_health.macd_histogram_slope}. "
                f"VWAP {'supports' if trend_health.vwap_supporting else 'does not support'} the trend."
            )
        else:
            health_line = f"Regime is {regime.type} — trend health layer skipped."

        # Layer 3: Structure
        if structure_levels:
            st_desc = structure_levels.price_position
            zones = structure_levels.confluence_zones
            zone_line = ""
            if zones:
                best = zones[0]
                zone_line = (
                    f" Price is near a {best.strength}-source {best.type} confluence zone "
                    f"({', '.join(best.sources[:3])})."
                )
            squeeze_line = " Squeeze active — coiling for breakout." if structure_levels.in_squeeze else ""
            squeeze_line += " Squeeze just fired!" if structure_levels.squeeze_fired else ""
            structure_line = f"Price is {st_desc}.{zone_line}{squeeze_line}"
        else:
            structure_line = "Structure analysis not available."

        # Layer 4: Volume
        if volume:
            vol_line = (
                f"Volume is {volume.candle_vs_avg} ({volume.volume_ratio:.1f}x avg) — "
                f"OBV {volume.obv_trend}"
            )
            if volume.obv_divergence:
                vol_line += ", OBV divergence detected (warning)"
            if volume.price_volume_divergence != "none":
                vol_line += f", {volume.price_volume_divergence.replace('_', ' ')}"
            vol_line += f". VWAP: price is {volume.vwap_position} ({volume.vwap_distance_atr:.1f}x ATR away)."
        else:
            vol_line = "Volume analysis not available."

        # Layer 5: Signal
        if signal.type != "NONE":
            setup_line = (
                f"Signal: {signal.type} at {signal.entry:.0f}. "
                f"Stop: {signal.stopLoss:.0f}, Target: {signal.target:.0f}. "
                f"Confidence: {signal.confidence:.0f}/100."
            )
        else:
            setup_line = f"No trade signal. Score {signal.confidence:.0f}/100 — {signal.reasons[-1] if signal.reasons else 'conditions not met'}."

        # Layer 7: Jill
        if forecast_confirmation and forecast_confirmation.available:
            if forecast_confirmation.confirmed:
                jill_line = "Jill (TimesFM) confirms: direction agrees, confidence band tight, no reversal risk."
            else:
                flags = []
                if not forecast_confirmation.agrees:
                    flags.append("direction disagrees")
                if not forecast_confirmation.confident:
                    flags.append(f"wide confidence band ({forecast_confirmation.band_width})")
                if not forecast_confirmation.no_reversal:
                    flags.append("short-term reversal risk in forecast")
                jill_line = f"Jill (TimesFM) flags: {', '.join(flags)}."
        elif forecast_confirmation and not forecast_confirmation.available:
            jill_line = "Jill (TimesFM) not loaded — Jack operating solo."
        else:
            jill_line = ""

        summary = f"{regime_line} {health_line}"
        setup = f"{structure_line} {vol_line}"
        risk = "Avoid forcing entries when context and regime diverge or score drops below threshold."
        action_parts = [setup_line]
        if jill_line:
            action_parts.append(jill_line)
        action_parts.append("This engine never executes trades.")

        return Narrative(
            regime=regime.type,
            summary=summary,
            setup=setup,
            risk=risk,
            action=" ".join(action_parts),
        )
