from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    """
    Base model for all SQLAlchemy models.
    """

    # Primary key using Mapped and mapped_column
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Timestamps using Mapped and mapped_column
    # Explicitly specify DateTime type in mapped_column
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Explicit type
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Explicit type
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )
