from app.schemas import DayContext, Narrative, Regime, Signal, Structure


class NarrativeEngine:
    def build(
        self,
        regime: Regime,
        context: DayContext,
        structure: Structure,
        signal: Signal,
    ) -> Narrative:
        return Narrative(
            regime=regime.type,
            summary=(
                f"Market is in {regime.type.replace('_', ' ')} with {context.bias} daily bias "
                f"and {structure.phase} structure."
            ),
            setup=(
                f"Signal state is {signal.type}. The system is prioritizing {structure.trend} structure "
                f"while filtering through volatility={context.volatility} and dayType={context.dayType}."
            ),
            risk="Avoid forcing entries when context and regime diverge or score drops below threshold.",
            action="Monitor only the plotted entry, stop, target, and liquidity areas. This engine never executes trades.",
        )

