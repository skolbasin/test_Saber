"""Logging configuration utilities."""

from typing import Dict, Any

from app.settings import get_settings


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Returns:
        Logging configuration for dictConfig
    """
    settings = get_settings()
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s" if settings.log_format == "json" else settings.log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "json" if settings.log_format == "json" else "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "json" if settings.log_format == "json" else "standard",
                "filename": "logs/saber.log",
                "maxBytes": 10485760,
                "backupCount": 10,
            },
            "celery_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "json" if settings.log_format == "json" else "standard",
                "filename": "logs/celery.log",
                "maxBytes": 10485760,
                "backupCount": 10,
            },
        },
        "loggers": {
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "celery": {
                "level": settings.log_level,
                "handlers": ["console", "celery_file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "redis": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
    }


def setup_logging():
    """Setup logging configuration."""
    import logging.config
    from pathlib import Path
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    logger = logging.getLogger("app")
    logger.info("Logging configured successfully")