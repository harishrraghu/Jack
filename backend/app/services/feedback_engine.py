from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalEntryModel
from app.schemas import FeedbackMetric, FeedbackMetrics, RegimeFeedbackMetric


class FeedbackEngine:
    async def summarize(self, session: AsyncSession) -> FeedbackMetrics:
        result = await session.execute(select(JournalEntryModel))
        rows = result.scalars().all()

        if not rows:
            return FeedbackMetrics(overallWinRate=0.0, strategyBreakdown=[], regimeBreakdown=[])

        wins = sum(1 for row in rows if row.outcome == "win")
        strategy_data: dict[str, list[str]] = defaultdict(list)
        regime_data: dict[str, list[str]] = defaultdict(list)

        for row in rows:
            strategy_data[row.strategy_name].append(row.outcome)
            regime_data[row.regime].append(row.outcome)

        strategy_breakdown = [
            FeedbackMetric(
                strategy=strategy,
                winRate=(outcomes.count("win") / len(outcomes)) * 100,
                samples=len(outcomes),
            )
            for strategy, outcomes in strategy_data.items()
        ]

        regime_breakdown = [
            RegimeFeedbackMetric(
                regime=regime,
                winRate=(outcomes.count("win") / len(outcomes)) * 100,
                samples=len(outcomes),
            )
            for regime, outcomes in regime_data.items()
        ]

        return FeedbackMetrics(
            overallWinRate=(wins / len(rows)) * 100,
            strategyBreakdown=strategy_breakdown,
            regimeBreakdown=regime_breakdown,
        )

