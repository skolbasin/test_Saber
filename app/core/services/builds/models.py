"""Build service database models."""

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class BuildModel(Base):
    """
    Database model for build configurations.
    
    Represents builds with their associated tasks and execution metadata.
    """
    
    __tablename__ = "builds"

    name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        nullable=False,
        doc="Unique build identifier"
    )
    
    tasks: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        doc="List of task names included in this build"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="Current build execution status"
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error details if build failed"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Build creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last build update timestamp"
    )

    def __repr__(self) -> str:
        """String representation of build model."""
        return f"<BuildModel(name='{self.name}', status='{self.status}', tasks={len(self.tasks or [])})>"


class SortResultModel(Base):
    """
    Database model for caching topological sort results.
    
    Stores computed sort results to avoid recalculation for unchanged builds.
    """
    
    __tablename__ = "sort_results"

    build_name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        nullable=False,
        doc="Name of the build that was sorted"
    )
    
    sorted_tasks: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        doc="Topologically sorted list of task names"
    )
    
    algorithm_used: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Algorithm used for sorting"
    )
    
    execution_time_ms: Mapped[float] = mapped_column(
        nullable=False,
        doc="Time taken for sorting in milliseconds"
    )
    
    has_cycles: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether circular dependencies were detected"
    )
    
    config_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Hash of build and task configuration for cache invalidation"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Result creation timestamp"
    )

    def __repr__(self) -> str:
        """String representation of sort result model."""
        return f"<SortResultModel(build_name='{self.build_name}', algorithm='{self.algorithm_used}')>"