"""Log management Celery tasks."""

import gzip
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from celery import Task
from celery.schedules import crontab

from .celery_app import celery_app


logger = logging.getLogger("celery")


class LogManagementTask(Task):
    """Base class for log management tasks."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Log management task {task_id} failed: {exc}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Log management task {task_id} completed successfully")


@celery_app.task(base=LogManagementTask, bind=True)
def archive_old_logs(self) -> dict:
    """
    Archive old rotated log files.
    
    Compresses log files older than 1 day and moves them to archive directory.
    
    Returns:
        Dictionary with archiving results
    """
    logger.info("Starting log archiving task")
    
    logs_dir = Path("logs")
    archive_dir = logs_dir / "archives"
    archive_dir.mkdir(exist_ok=True)
    
    archived_files = []
    errors = []
    
    try:
        log_files = list(logs_dir.glob("*.log.*"))
        
        cutoff_time = time.time() - (24 * 60 * 60)
        old_log_files = [
            f for f in log_files 
            if f.stat().st_mtime < cutoff_time and f.suffix.isdigit()
        ]
        
        logger.info(f"Found {len(old_log_files)} old log files to archive")
        
        for log_file in old_log_files:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = f"{log_file.stem}_{timestamp}.gz"
                archive_path = archive_dir / archive_name
                
                with open(log_file, 'rb') as f_in:
                    with gzip.open(archive_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                if archive_path.exists() and archive_path.stat().st_size > 0:
                    log_file.unlink()
                    archived_files.append(str(archive_path))
                    logger.info(f"Archived and removed: {log_file.name}")
                else:
                    errors.append(f"Failed to create archive for {log_file.name}")
                    
            except Exception as e:
                error_msg = f"Error archiving {log_file.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        result = {
            "task": "archive_old_logs",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "archived_count": len(archived_files),
            "archived_files": archived_files,
            "errors_count": len(errors),
            "errors": errors,
            "status": "completed"
        }
        
        logger.info(f"Log archiving completed: {len(archived_files)} files archived")
        return result
        
    except Exception as e:
        error_msg = f"Log archiving task failed: {str(e)}"
        logger.error(error_msg)
        return {
            "task": "archive_old_logs",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": error_msg
        }


@celery_app.task(base=LogManagementTask, bind=True)
def cleanup_old_archives(self, retention_days: int = 7) -> dict:
    """
    Clean up old archived log files.
    
    Simulates sending archives to external storage and then removes them.
    
    Args:
        retention_days: Number of days to keep archives before cleanup
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting archive cleanup task (retention: {retention_days} days)")
    
    logs_dir = Path("logs")
    archive_dir = logs_dir / "archives"
    
    if not archive_dir.exists():
        return {
            "task": "cleanup_old_archives",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
            "message": "No archive directory found"
        }
    
    uploaded_files = []
    deleted_files = []
    errors = []
    
    try:
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        archive_files = list(archive_dir.glob("*.gz"))
        old_archives = [
            f for f in archive_files 
            if f.stat().st_mtime < cutoff_time
        ]
        
        logger.info(f"Found {len(old_archives)} old archives to process")
        
        for archive_file in old_archives:
            try:
                upload_success = _simulate_upload_to_external_storage(archive_file)
                
                if upload_success:
                    uploaded_files.append(str(archive_file))
                    
                    archive_file.unlink()
                    deleted_files.append(str(archive_file))
                    logger.info(f"Uploaded and removed archive: {archive_file.name}")
                else:
                    errors.append(f"Failed to upload {archive_file.name}")
                    
            except Exception as e:
                error_msg = f"Error processing {archive_file.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        result = {
            "task": "cleanup_old_archives",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "retention_days": retention_days,
            "uploaded_count": len(uploaded_files),
            "uploaded_files": uploaded_files,
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "errors_count": len(errors),
            "errors": errors,
            "status": "completed"
        }
        
        logger.info(f"Archive cleanup completed: {len(deleted_files)} files removed")
        return result
        
    except Exception as e:
        error_msg = f"Archive cleanup task failed: {str(e)}"
        logger.error(error_msg)
        return {
            "task": "cleanup_old_archives",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": error_msg
        }


def _simulate_upload_to_external_storage(archive_path: Path) -> bool:
    """
    Simulate uploading archive to external storage (S3, Azure, etc.).
    
    In a real implementation, this would upload to cloud storage.
    For now, just simulates the process with a delay.
    
    Args:
        archive_path: Path to the archive file
        
    Returns:
        True if upload was successful, False otherwise
    """
    try:
        time.sleep(0.1)
        
        file_size = archive_path.stat().st_size
        logger.info(f"[SIMULATION] Uploading {archive_path.name} ({file_size} bytes) to external storage...")
        
        upload_time = min(file_size / 1000000, 2.0)
        time.sleep(upload_time)
        
        import random
        if random.random() < 0.05:
            logger.warning(f"[SIMULATION] Upload failed for {archive_path.name}")
            return False
        
        logger.info(f"[SIMULATION] Successfully uploaded {archive_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"[SIMULATION] Upload error for {archive_path.name}: {str(e)}")
        return False


@celery_app.task(base=LogManagementTask, bind=True)
def get_log_statistics(self) -> dict:
    """
    Collect statistics about log files and archives.
    
    Returns:
        Dictionary with log file statistics
    """
    logger.info("Collecting log statistics")
    
    logs_dir = Path("logs")
    archive_dir = logs_dir / "archives"
    
    try:
        stats = {
            "task": "get_log_statistics",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "logs_directory": str(logs_dir.absolute()),
            "current_logs": {},
            "rotated_logs": {},
            "archives": {},
            "total_size_mb": 0
        }
        
        total_size = 0
        
        current_logs = list(logs_dir.glob("*.log"))
        for log_file in current_logs:
            size = log_file.stat().st_size
            total_size += size
            stats["current_logs"][log_file.name] = {
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            }
        
        rotated_logs = list(logs_dir.glob("*.log.*"))
        rotated_logs = [f for f in rotated_logs if f.suffix.isdigit()]
        for log_file in rotated_logs:
            size = log_file.stat().st_size
            total_size += size
            stats["rotated_logs"][log_file.name] = {
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            }
        
        if archive_dir.exists():
            archive_files = list(archive_dir.glob("*.gz"))
            for archive_file in archive_files:
                size = archive_file.stat().st_size
                total_size += size
                stats["archives"][archive_file.name] = {
                    "size_bytes": size,
                    "size_mb": round(size / 1024 / 1024, 2),
                    "created": datetime.fromtimestamp(archive_file.stat().st_ctime).isoformat()
                }
        
        stats["total_size_mb"] = round(total_size / 1024 / 1024, 2)
        stats["files_count"] = {
            "current_logs": len(current_logs),
            "rotated_logs": len(rotated_logs),
            "archives": len(stats["archives"]),
            "total": len(current_logs) + len(rotated_logs) + len(stats["archives"])
        }
        
        logger.info(f"Log statistics collected: {stats['files_count']['total']} files, {stats['total_size_mb']} MB")
        return stats
        
    except Exception as e:
        error_msg = f"Failed to collect log statistics: {str(e)}"
        logger.error(error_msg)
        return {
            "task": "get_log_statistics",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": error_msg
        }


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic log management tasks."""
    
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        archive_old_logs.s(),
        name='Daily log archiving'
    )
    
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        cleanup_old_archives.s(retention_days=7),
        name='Daily archive cleanup'
    )
    
    sender.add_periodic_task(
        crontab(minute=0, hour='*/6'),
        get_log_statistics.s(),
        name='Log statistics collection'
    )