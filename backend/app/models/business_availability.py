import enum
import uuid
from datetime import time

from sqlalchemy import ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WeekDays(enum.Enum):
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
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "businesses.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    day_of_week: Mapped[WeekDays] = mapped_column(
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
