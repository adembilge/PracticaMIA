"""Pseudonymous, bounded daily LLM use accounting for preview cases."""
from datetime import date
from sqlalchemy import CheckConstraint, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssistantDailyUsage(Base):
    __tablename__ = "assistant_daily_usage"
    __table_args__ = (
        CheckConstraint("request_count > 0", name="ck_assistant_daily_usage_positive"),
    )

    subject_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    usage_day: Mapped[date] = mapped_column(Date, primary_key=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
