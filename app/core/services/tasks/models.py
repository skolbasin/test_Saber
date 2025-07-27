"""Task service database models."""

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class TaskModel(Base):
    """
    Database model for build tasks.
    
    Represents tasks with their dependencies and execution metadata.
    """
    
    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        nullable=False,
        doc="Unique task identifier"
    )
    
    dependencies: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="List of task names this task depends on"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="Current task execution status"
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error details if task failed"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Task creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last task update timestamp"
    )

    def __repr__(self) -> str:
        """String representation of task model."""
        return f"<TaskModel(name='{self.name}', status='{self.status}', dependencies={len(self.dependencies or [])})>"