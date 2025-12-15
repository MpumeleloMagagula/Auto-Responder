import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from models import EmailConfig, SchedulerConfig
from email_ingestor import fetch_and_process_emails

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def auto_fetch_emails_job():
    """Background job to automatically fetch emails."""
    logger.info(f"[{datetime.now()}] Auto-fetch job started...")
    
    db = SessionLocal()
    try:
        scheduler_config = db.query(SchedulerConfig).filter(
            SchedulerConfig.is_active == True
        ).first()
        
        if not scheduler_config or not scheduler_config.auto_fetch_enabled:
            logger.info("Auto-fetch is disabled, skipping...")
            return
        
        email_config = db.query(EmailConfig).filter(
            EmailConfig.is_active == True
        ).first()
        
        if not email_config:
            logger.warning("No email configuration found, skipping auto-fetch...")
            return
        
        result = fetch_and_process_emails(db, email_config)
        
        scheduler_config.last_fetch_at = datetime.utcnow()
        scheduler_config.last_fetch_count = result.get("processed", 0)
        db.commit()
        
        logger.info(f"Auto-fetch completed: {result['processed']} emails processed")
        if result.get("errors"):
            for error in result["errors"]:
                logger.error(f"Auto-fetch error: {error}")
                
    except Exception as e:
        logger.error(f"Auto-fetch job failed: {str(e)}")
    finally:
        db.close()


def get_scheduler_config(db: Session) -> dict:
    """Get current scheduler configuration."""
    config = db.query(SchedulerConfig).first()
    if config:
        return {
            "auto_fetch_enabled": config.auto_fetch_enabled,
            "fetch_interval_minutes": config.fetch_interval_minutes,
            "last_fetch_at": config.last_fetch_at,
            "last_fetch_count": config.last_fetch_count
        }
    return {
        "auto_fetch_enabled": False,
        "fetch_interval_minutes": 5,
        "last_fetch_at": None,
        "last_fetch_count": 0
    }


def update_scheduler_job(interval_minutes: int):
    """Update the scheduler job interval."""
    job_id = "auto_fetch_emails"
    
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    scheduler.add_job(
        auto_fetch_emails_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        name="Auto Fetch Emails",
        replace_existing=True
    )
    logger.info(f"Scheduler updated: fetching every {interval_minutes} minutes")


def start_scheduler(db: Session):
    """Start the scheduler with current configuration."""
    config = db.query(SchedulerConfig).first()
    
    if not config:
        config = SchedulerConfig(
            auto_fetch_enabled=False,
            fetch_interval_minutes=5
        )
        db.add(config)
        db.commit()
    
    if config.auto_fetch_enabled:
        update_scheduler_job(config.fetch_interval_minutes)
        logger.info("Scheduler started with auto-fetch enabled")
    else:
        logger.info("Scheduler initialized but auto-fetch is disabled")
    
    if not scheduler.running:
        scheduler.start()


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
