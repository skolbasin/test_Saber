"""Command line interface for Saber Build System."""

import asyncio
import click
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.infrastructure.database.init_db import (
    init_database,
    check_database_health,
    get_database_info,
    load_yaml_data,
)
from app.infrastructure.cache.redis_client import get_redis_client
from app.utils.logging import setup_logging
from app.settings import get_settings


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    project_root = Path(__file__).parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    return Config(str(alembic_ini_path))


@click.group()
def cli():
    """Saber Build System CLI."""
    setup_logging()


@cli.command()
def init_db():
    """Initialize database with migrations and load data from YAML files."""
    click.echo("Initializing database...")
    asyncio.run(init_database())
    click.echo("Database initialized successfully!")


@cli.command()
def migrate():
    """Run database migrations to the latest version."""
    click.echo("Running database migrations...")
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, "head")
    click.echo("Migrations completed successfully!")


@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def create_migration(message: str):
    """Create a new migration file."""
    click.echo(f"Creating migration: {message}")
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)
    click.echo("Migration created successfully!")


@cli.command()
def current():
    """Show current migration version."""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg, verbose=True)


@cli.command()
def history():
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg, verbose=True)


@cli.command()
@click.option('--revision', '-r', default="-1", help='Revision to downgrade to')
@click.confirmation_option(prompt="Are you sure you want to downgrade the database?")
def downgrade(revision: str):
    """Downgrade database to a previous migration."""
    click.echo(f"Downgrading to revision: {revision}")
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    click.echo("Downgrade completed successfully!")


@cli.command()
def load_yaml():
    """Load or reload data from YAML files into the database."""
    click.echo("Loading data from YAML files...")
    asyncio.run(load_yaml_data())
    click.echo("YAML data loaded successfully!")


@cli.command()
def check_db():
    """Check database connectivity and health."""
    click.echo("Checking database health...")

    async def check():
        is_healthy = await check_database_health()
        if is_healthy:
            click.echo("✓ Database connection is healthy")

            info = await get_database_info()
            click.echo(f"\nDatabase statistics:")
            for table, count in info["tables"].items():
                click.echo(f"  - {table}: {count} records")
        else:
            click.echo("✗ Database connection failed")
            return 1
        return 0

    exit_code = asyncio.run(check())
    exit(exit_code)


@cli.command()
def test_redis():
    """Test Redis connectivity."""
    click.echo("Testing Redis connection...")

    async def test():
        try:
            redis_client = get_redis_client()
            await redis_client.connect()
            is_healthy = await redis_client.ping()

            if is_healthy:
                click.echo("✓ Redis connection is healthy")

                test_key = "cli_test_key"
                test_value = "test_value"
                await redis_client.set(test_key, test_value)
                retrieved = await redis_client.get(test_key)

                if retrieved == test_value:
                    click.echo("✓ Redis set/get operations work correctly")
                else:
                    click.echo("✗ Redis set/get operations failed")

                await redis_client.delete(test_key)
            else:
                click.echo("✗ Redis ping failed")
                return 1

            await redis_client.disconnect()
        except Exception as e:
            click.echo(f"✗ Redis connection failed: {e}")
            return 1

        return 0

    exit_code = asyncio.run(test())
    exit(exit_code)


@cli.command()
def show_config():
    """Display current configuration settings."""
    settings = get_settings()

    click.echo("Current configuration:")
    click.echo(f"  Environment: {settings.environment}")
    click.echo(f"  Debug: {settings.debug}")
    click.echo(f"  Database URL: {settings.database_url}")
    click.echo(f"  Redis URL: {settings.redis_url}")
    click.echo(f"  Tasks config: {settings.tasks_config_path}")
    click.echo(f"  Builds config: {settings.builds_config_path}")
    click.echo(f"  JWT Algorithm: {settings.jwt_algorithm}")
    click.echo(f"  Access token expire: {settings.access_token_expire_minutes} minutes")
    click.echo(f"  Refresh token expire: {settings.refresh_token_expire_days} days")


if __name__ == "__main__":
    cli()