from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime
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
    # Note: Using server_default=func.now() is often preferred for DB-level defaults
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
