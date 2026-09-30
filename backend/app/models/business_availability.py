import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WeekDays(str, enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class BusinessAvailability(Base):
    __tablename__ = "business_availability"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        nullable=False,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "businesses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    day_of_week: Mapped[WeekDays] = mapped_column(
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
