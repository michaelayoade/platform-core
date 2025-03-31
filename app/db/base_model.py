from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr


class BaseModel:
    """
    Base model for all SQLAlchemy models.
    """

    # Auto-generate tablename from class name
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
