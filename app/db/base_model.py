from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    """
    Base model for all SQLAlchemy models.
    """

    type_annotation_map = {
        datetime: Annotated[datetime, mapped_column(DateTime(timezone=True))]
    }

    # Auto-generate tablename from class name
    # @declared_attr - no longer needed with Base
    # def __tablename__(cls) -> str:
    #     return cls.__name__.lower()

    # Primary key using Mapped and mapped_column
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Timestamps using Mapped and mapped_column
    # Use server_default and server_onupdate with func.now() for DB-level timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),  # Use database function
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),  # Use database function for initial value
        server_onupdate=func.now(),  # Use database function for updates
        nullable=False,
    )
