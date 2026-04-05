from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalEntryModel
from app.schemas import JournalEntry, Regime, Signal


class JournalService:
    async def list_entries(self, session: AsyncSession) -> list[JournalEntry]:
        result = await session.execute(
            select(JournalEntryModel).order_by(JournalEntryModel.timestamp.desc()).limit(25)
        )
        rows = result.scalars().all()
        return [
            JournalEntry(
                id=row.id,
                timestamp=row.timestamp,
                signal=Signal(**row.signal),
                outcome=row.outcome,
                notes=row.notes,
                strategyName=row.strategy_name,
            )
            for row in rows
        ]

    async def record_signal(
        self,
        session: AsyncSession,
        signal: Signal,
        strategy_name: str,
        regime: Regime,
    ) -> JournalEntry:
        entry = JournalEntryModel(
            timestamp=datetime.now(timezone.utc),
            signal=signal.model_dump(),
            outcome="neutral",
            notes=["Auto-logged by deterministic analysis pipeline"],
            strategy_name=strategy_name,
            regime=regime.type,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return JournalEntry(
            id=entry.id,
            timestamp=entry.timestamp,
            signal=signal,
            outcome="neutral",
            notes=entry.notes,
            strategyName=entry.strategy_name,
        )

