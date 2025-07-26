"""Database initialization utilities."""

import logging
from pathlib import Path
from typing import Dict

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.infrastructure.database.session import get_session_maker
from app.core.domain.entities import Build, Task
from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
from app.core.services.configuration_service import ConfigurationService
from app.settings import get_settings


async def init_database() -> None:
    """Initialize database with Alembic migrations and load data from YAML files."""
    logger = logging.getLogger("app")

    try:
        logger.info("Running database migrations...")
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_alembic_migrations)
        logger.info("Database migrations completed successfully")

        await load_yaml_data()
        logger.info("YAML data loaded successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def run_alembic_migrations() -> None:
    """Run all pending Alembic migrations."""
    project_root = Path(__file__).parent.parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini_path))

    command.upgrade(alembic_cfg, "head")


async def load_yaml_data() -> None:
    """Load tasks and builds from YAML files if they don't exist in the database."""
    logger = logging.getLogger("app")
    settings = get_settings()

    # Initialize configuration service
    config_service = ConfigurationService()

    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            build_repo = SqlBuildRepository(session)
            task_repo = SqlTaskRepository(session)

            # Check if we already have data
            existing_tasks = await task_repo.get_all_tasks()
            existing_builds = await build_repo.get_all_builds()

            if existing_tasks and existing_builds:
                logger.info("Database already contains tasks and builds, skipping YAML import")
                return

            # Load tasks from YAML
            yaml_tasks_path = Path(settings.config_dir) / settings.tasks_config_file
            yaml_builds_path = Path(settings.config_dir) / settings.builds_config_file

            if not yaml_tasks_path.exists():
                logger.warning(f"Tasks YAML file not found: {yaml_tasks_path}")
                # Create sample tasks if YAML doesn't exist
                await create_sample_tasks(task_repo)
            else:
                logger.info(f"Loading tasks from {yaml_tasks_path}")
                tasks = await config_service.load_tasks_config(str(yaml_tasks_path))
                await load_tasks_to_db(task_repo, tasks)
                logger.info(f"Loaded {len(tasks)} tasks from YAML")

            if not yaml_builds_path.exists():
                logger.warning(f"Builds YAML file not found: {yaml_builds_path}")
                # Create sample builds if YAML doesn't exist
                await create_sample_builds(build_repo)
            else:
                logger.info(f"Loading builds from {yaml_builds_path}")
                builds = await config_service.load_builds_config(str(yaml_builds_path))
                await load_builds_to_db(build_repo, builds)
                logger.info(f"Loaded {len(builds)} builds from YAML")

            await session.commit()
            logger.info("YAML data imported successfully")

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to load YAML data: {e}")
            raise


async def load_tasks_to_db(task_repo: SqlTaskRepository, tasks: Dict[str, Task]) -> None:
    """Load tasks from configuration to database."""
    for task_name, task in tasks.items():
        existing = await task_repo.get_task(task_name)
        if not existing:
            await task_repo.save_task(task)


async def load_builds_to_db(build_repo: SqlBuildRepository, builds: Dict[str, Build]) -> None:
    """Load builds from configuration to database."""
    for build_name, build in builds.items():
        existing = await build_repo.get_build(build_name)
        if not existing:
            await build_repo.save_build(build)


async def create_sample_tasks(task_repo) -> None:
    """Create sample tasks for demonstration (fallback when YAML not found)."""
    from app.core.domain.enums import TaskStatus

    sample_tasks = [
        Task(name="compile_core", dependencies=set(), status=TaskStatus.PENDING),
        Task(name="compile_utils", dependencies={"compile_core"}, status=TaskStatus.PENDING),
        Task(name="compile_ui", dependencies={"compile_core"}, status=TaskStatus.PENDING),
        Task(name="run_tests", dependencies={"compile_utils", "compile_ui"}, status=TaskStatus.PENDING),
        Task(name="package", dependencies={"run_tests"}, status=TaskStatus.PENDING),
        Task(name="deploy", dependencies={"package"}, status=TaskStatus.PENDING),
    ]

    for task in sample_tasks:
        existing = await task_repo.get_task(task.name)
        if not existing:
            await task_repo.save_task(task)


async def create_sample_builds(build_repo) -> None:
    """Create sample builds for demonstration (fallback when YAML not found)."""
    from app.core.domain.enums import BuildStatus

    sample_builds = [
        Build(
            name="frontend_build",
            tasks=["compile_core", "compile_utils", "compile_ui", "run_tests", "package"],
            status=BuildStatus.PENDING,
        ),
        Build(
            name="backend_build",
            tasks=["compile_core", "compile_utils", "run_tests", "package"],
            status=BuildStatus.PENDING,
        ),
        Build(
            name="full_build",
            tasks=["compile_core", "compile_utils", "compile_ui", "run_tests", "package", "deploy"],
            status=BuildStatus.PENDING,
        ),
    ]

    for build in sample_builds:
        existing = await build_repo.get_build(build.name)
        if not existing:
            await build_repo.save_build(build)


async def check_database_health() -> bool:
    """Check database connectivity and health."""
    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def get_database_info() -> dict:
    """Get database information and statistics."""
    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            user_count = await session.execute(text("SELECT COUNT(*) FROM users"))
            build_count = await session.execute(text("SELECT COUNT(*) FROM builds"))
            task_count = await session.execute(text("SELECT COUNT(*) FROM tasks"))
            token_count = await session.execute(text("SELECT COUNT(*) FROM refresh_tokens"))

            return {
                "healthy": True,
                "tables": {
                    "users": user_count.scalar(),
                    "builds": build_count.scalar(),
                    "tasks": task_count.scalar(),
                    "refresh_tokens": token_count.scalar(),
                },
                "engine_info": str(get_session_maker().kw['bind'].url),
            }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
        }