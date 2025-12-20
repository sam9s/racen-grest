"""
Sync Manager for GRESTA

Handles automatic synchronization of:
1. SQL Database (PostgreSQL) - synced from Shopify Admin API
2. Vector Database (ChromaDB) - synced from GREST website

Uses APScheduler to run syncs every 6 hours.
No external dependencies on Replit infrastructure.
"""

import os
import logging
from datetime import datetime
from threading import Lock
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sync_lock = Lock()

SYNC_INTERVAL_HOURS = int(os.environ.get('SYNC_INTERVAL_HOURS', 6))


def sync_shopify_products() -> dict:
    """
    Sync SQL database with Shopify Admin API.
    
    - Fetches all products from Shopify
    - Upserts into PostgreSQL
    - Hard deletes any SKUs not in current Shopify fetch
    
    Returns sync result dict.
    """
    from scrape_grest_products import populate_database
    
    logger.info("=" * 50)
    logger.info("STARTING SHOPIFY SYNC")
    logger.info("=" * 50)
    
    start_time = datetime.now()
    
    try:
        result = populate_database(hard_delete_stale=True)
        duration = (datetime.now() - start_time).total_seconds()
        
        if result and result.get('success'):
            logger.info(f"SHOPIFY SYNC COMPLETE in {duration:.1f}s")
            logger.info(f"  Added: {result.get('variants_added', 0)}")
            logger.info(f"  Updated: {result.get('variants_updated', 0)}")
            logger.info(f"  Deleted: {result.get('variants_deleted', 0)}")
            return {
                "success": True,
                "duration_seconds": duration,
                **result
            }
        else:
            logger.error(f"SHOPIFY SYNC FAILED: {result}")
            return {
                "success": False,
                "duration_seconds": duration,
                "error": result.get('error') if result else "Unknown error"
            }
            
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"SHOPIFY SYNC ERROR: {e}")
        return {
            "success": False,
            "duration_seconds": duration,
            "error": str(e)
        }


def sync_knowledge_base() -> dict:
    """
    Sync vector database with GREST website.
    
    Uses incremental sync - only updates pages that have changed.
    
    Returns sync result dict.
    """
    from knowledge_base import sync_website_incremental, get_knowledge_base_stats
    
    logger.info("=" * 50)
    logger.info("STARTING KNOWLEDGE BASE SYNC")
    logger.info("=" * 50)
    
    start_time = datetime.now()
    
    try:
        result = sync_website_incremental()
        duration = (datetime.now() - start_time).total_seconds()
        
        stats = get_knowledge_base_stats()
        
        logger.info(f"KNOWLEDGE BASE SYNC COMPLETE in {duration:.1f}s")
        logger.info(f"  Pages processed: {result.get('pages_processed', 0)}")
        logger.info(f"  Pages updated: {result.get('pages_updated', 0)}")
        logger.info(f"  Pages unchanged: {result.get('pages_unchanged', 0)}")
        logger.info(f"  Total chunks: {stats.get('total_chunks', 0)}")
        
        return {
            "success": True,
            "duration_seconds": duration,
            **result
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"KNOWLEDGE BASE SYNC ERROR: {e}")
        return {
            "success": False,
            "duration_seconds": duration,
            "error": str(e)
        }


def run_full_sync() -> dict:
    """
    Run full synchronization of both databases.
    
    SQL sync runs first, then vector sync.
    Uses a lock to prevent concurrent syncs.
    
    Returns combined sync result.
    """
    if not sync_lock.acquire(blocking=False):
        logger.warning("Sync already in progress, skipping...")
        return {
            "success": False,
            "error": "Sync already in progress",
            "skipped": True
        }
    
    try:
        logger.info("=" * 60)
        logger.info(f"FULL SYNC STARTED at {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        shopify_result = sync_shopify_products()
        
        if not shopify_result.get('success'):
            logger.warning("Shopify sync failed, continuing with knowledge base sync...")
        
        kb_result = sync_knowledge_base()
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"FULL SYNC COMPLETE in {total_duration:.1f}s")
        logger.info("=" * 60)
        
        return {
            "success": shopify_result.get('success') and kb_result.get('success'),
            "total_duration_seconds": total_duration,
            "shopify_sync": shopify_result,
            "knowledge_base_sync": kb_result,
            "timestamp": datetime.now().isoformat()
        }
        
    finally:
        sync_lock.release()


class SyncManager:
    """
    Manages automatic synchronization of GREST databases.
    
    Runs in the background using APScheduler.
    """
    
    def __init__(self, interval_hours: int = SYNC_INTERVAL_HOURS):
        self.interval_hours = interval_hours
        self.scheduler: Optional[BackgroundScheduler] = None
        self.last_sync_result: Optional[dict] = None
        self.is_running = False
    
    def start(self, run_immediately: bool = False):
        """
        Start the sync scheduler.
        
        Args:
            run_immediately: If True, run a sync immediately on startup
        """
        if self.is_running:
            logger.warning("SyncManager already running")
            return
        
        self.scheduler = BackgroundScheduler()
        
        self.scheduler.add_job(
            self._run_sync_job,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id='full_sync',
            name=f'Full Sync (every {self.interval_hours} hours)',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info(f"SyncManager started - syncing every {self.interval_hours} hours")
        
        if run_immediately:
            logger.info("Running initial sync...")
            self._run_sync_job()
    
    def stop(self):
        """Stop the sync scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("SyncManager stopped")
    
    def _run_sync_job(self):
        """Internal method to run the sync job."""
        self.last_sync_result = run_full_sync()
        return self.last_sync_result
    
    def trigger_manual_sync(self) -> dict:
        """Manually trigger a sync (for future admin dashboard)."""
        logger.info("Manual sync triggered")
        return self._run_sync_job()
    
    def get_status(self) -> dict:
        """Get current sync manager status."""
        next_run = None
        if self.scheduler:
            job = self.scheduler.get_job('full_sync')
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        
        return {
            "is_running": self.is_running,
            "interval_hours": self.interval_hours,
            "next_sync": next_run,
            "last_sync_result": self.last_sync_result
        }


sync_manager_instance: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    """Get or create the global SyncManager instance."""
    global sync_manager_instance
    if sync_manager_instance is None:
        sync_manager_instance = SyncManager()
    return sync_manager_instance


def start_sync_manager(run_immediately: bool = False):
    """Start the global SyncManager."""
    manager = get_sync_manager()
    manager.start(run_immediately=run_immediately)
    return manager


def stop_sync_manager():
    """Stop the global SyncManager."""
    global sync_manager_instance
    if sync_manager_instance:
        sync_manager_instance.stop()
