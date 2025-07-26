"""YAML data loader for database initialization."""

import os
import yaml
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select

from app.core.domain.enums import BuildStatus, TaskStatus
from app.core.services.builds.models import BuildModel
from app.core.services.tasks.models import TaskModel


async def load_initial_data_to_db(engine: AsyncEngine) -> None:
    """
    Load initial data from YAML files to database.

    Args:
        engine: Database engine
    """
    async with AsyncSession(engine) as session:
        try:
            existing_tasks = await session.execute(select(TaskModel))
            if existing_tasks.scalar():
                return

            # Load tasks
            tasks_path = "config/tasks.yaml"
            if os.path.exists(tasks_path):
                with open(tasks_path, "r", encoding="utf-8") as f:
                    tasks_data = yaml.safe_load(f)

                for task_data in tasks_data.get("tasks", []):
                    task_model = TaskModel(
                        name=task_data["name"],
                        dependencies=task_data.get("dependencies", []),
                        status=TaskStatus.PENDING.value,
                        created_at=datetime.now(),
                    )
                    session.add(task_model)

            # Load builds
            builds_path = "config/builds.yaml"
            if os.path.exists(builds_path):
                with open(builds_path, "r", encoding="utf-8") as f:
                    builds_data = yaml.safe_load(f)

                for build_data in builds_data.get("builds", []):
                    build_model = BuildModel(
                        name=build_data["name"],
                        tasks=build_data.get("tasks", []),
                        status=BuildStatus.PENDING.value,
                        created_at=datetime.now(),
                    )
                    session.add(build_model)

            await session.commit()

        except Exception as e:
            await session.rollback()
            print(f"Warning: Could not load initial data: {e}")