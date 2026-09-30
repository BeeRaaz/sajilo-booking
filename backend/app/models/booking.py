import enum
import uuid
from datetime import datetime, time

from sqlalchemy import DateTime, ForeignKey, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        index=True,
        default=uuid.uuid4,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "services.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    client_first_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    client_last_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    client_email: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    client_phone: Mapped[str] = mapped_column(
        String,
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
    status: Mapped[BookingStatus] = mapped_column(
        default=BookingStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
