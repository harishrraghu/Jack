from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class JournalEntryModel(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    signal: Mapped[dict] = mapped_column(JSON, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    regime: Mapped[str] = mapped_column(String(32), nullable=False)
