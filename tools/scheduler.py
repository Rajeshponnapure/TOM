"""
Task Scheduler Module
Manages background scheduling for agent tasks like Instagram feed monitoring.
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    _AP_SCHEDULER_AVAILABLE = True
except Exception:
    BackgroundScheduler = None
    IntervalTrigger = None
    CronTrigger = None
    _AP_SCHEDULER_AVAILABLE = False

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Manages background task scheduling using APScheduler.
    """
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.scheduler = BackgroundScheduler() if _AP_SCHEDULER_AVAILABLE else None
        self.scheduled_jobs: Dict[str, Any] = {}
        self.is_running = False
        self._fallback_threads: Dict[str, threading.Event] = {}
        self._warned_about_fallback = False

    def _use_fallback_scheduler(self) -> bool:
        return not _AP_SCHEDULER_AVAILABLE or self.scheduler is None

    def _warn_fallback_once(self):
        if not self._warned_about_fallback:
            logger.warning("APScheduler is not installed; using a lightweight in-process fallback scheduler.")
            self._warned_about_fallback = True
    
    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            if not self._use_fallback_scheduler():
                self.scheduler.start()
            else:
                self._warn_fallback_once()
            self.is_running = True
            logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler and wait for running jobs to complete."""
        if self.is_running:
            if not self._use_fallback_scheduler():
                self.scheduler.shutdown(wait=True)
            else:
                for event in self._fallback_threads.values():
                    event.set()
                self._fallback_threads.clear()
            self.is_running = False
            logger.info("Task scheduler stopped")
    
    def schedule_interval_task(self, job_id: str, func: Callable, 
                               hours: int = 3, minutes: int = 0, 
                               seconds: int = 0, args: tuple = None,
                               kwargs: dict = None, replace_existing: bool = True) -> str:
        """
        Schedule a task to run at regular intervals.
        
        Args:
            job_id: Unique identifier for this job
            func: Callable function to execute
            hours: Hours interval (default: 3)
            minutes: Minutes interval
            seconds: Seconds interval
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            replace_existing: If True, replace any existing job with same ID
            
        Returns:
            Job ID of the scheduled task
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        
        try:
            # Remove existing job if requested
            if replace_existing and job_id in self.scheduled_jobs:
                if not self._use_fallback_scheduler() and self.scheduler:
                    self.scheduler.remove_job(job_id)
                elif job_id in self._fallback_threads:
                    self._fallback_threads[job_id].set()
                    del self._fallback_threads[job_id]
                del self.scheduled_jobs[job_id]

            if not self._use_fallback_scheduler() and self.scheduler:
                # Schedule the job
                job = self.scheduler.add_job(
                    func,
                    trigger=IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds),
                    id=job_id,
                    name=job_id,
                    args=args,
                    kwargs=kwargs,
                    max_instances=1,  # Only one instance of this job at a time
                )

                self.scheduled_jobs[job_id] = {
                    'id': job_id,
                    'job': job,
                    'callable': func,
                    'function': func.__name__,
                    'interval': f"{hours}h {minutes}m {seconds}s",
                    'next_run': job.next_run_time,
                    'created_at': datetime.now().isoformat(),
                    'backend': 'apscheduler',
                }

                logger.info(f"Scheduled task '{job_id}' to run every {hours}h {minutes}m {seconds}s")
                logger.info(f"Next run: {job.next_run_time}")
                return job_id

            self._warn_fallback_once()
            interval_seconds = max(1, (hours * 3600) + (minutes * 60) + seconds)
            stop_event = threading.Event()

            def _runner():
                next_run = datetime.now() + timedelta(seconds=interval_seconds)
                while not stop_event.wait(interval_seconds):
                    try:
                        func(*args, **kwargs)
                    except Exception as exc:
                        logger.error(f"Fallback scheduled task '{job_id}' failed: {exc}")
                    next_run = datetime.now() + timedelta(seconds=interval_seconds)
                    job_info = self.scheduled_jobs.get(job_id)
                    if job_info is not None:
                        job_info['next_run'] = next_run

            thread = threading.Thread(target=_runner, name=f"task-{job_id}", daemon=True)
            thread.start()
            self._fallback_threads[job_id] = stop_event
            self.scheduled_jobs[job_id] = {
                'id': job_id,
                'job': None,
                'thread': thread,
                'stop_event': stop_event,
                'callable': func,
                'function': func.__name__,
                'interval': f"{hours}h {minutes}m {seconds}s",
                'next_run': datetime.now() + timedelta(seconds=interval_seconds),
                'created_at': datetime.now().isoformat(),
                'backend': 'fallback',
            }
            logger.info(f"Scheduled fallback task '{job_id}' to run every {hours}h {minutes}m {seconds}s")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to schedule task '{job_id}': {e}")
            raise
    
    def schedule_cron_task(self, job_id: str, func: Callable, 
                           cron_expression: str, args: tuple = None,
                           kwargs: dict = None, replace_existing: bool = True) -> str:
        """
        Schedule a task to run at a specific time using cron expression.
        
        Args:
            job_id: Unique identifier for this job
            func: Callable function to execute
            cron_expression: Cron expression (e.g., "0 9,12,15,18 * * *" for 9am, 12pm, 3pm, 6pm)
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            replace_existing: If True, replace any existing job with same ID
            
        Returns:
            Job ID of the scheduled task
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        
        try:
            # Remove existing job if requested
            if replace_existing and job_id in self.scheduled_jobs:
                if not self._use_fallback_scheduler() and self.scheduler:
                    self.scheduler.remove_job(job_id)
                elif job_id in self._fallback_threads:
                    self._fallback_threads[job_id].set()
                    del self._fallback_threads[job_id]
                del self.scheduled_jobs[job_id]

            if not self._use_fallback_scheduler() and self.scheduler:
                # Schedule the job
                job = self.scheduler.add_job(
                    func,
                    trigger=CronTrigger.from_crontab(cron_expression),
                    id=job_id,
                    name=job_id,
                    args=args,
                    kwargs=kwargs,
                    max_instances=1,
                )

                self.scheduled_jobs[job_id] = {
                    'id': job_id,
                    'job': job,
                    'callable': func,
                    'function': func.__name__,
                    'cron': cron_expression,
                    'next_run': job.next_run_time,
                    'created_at': datetime.now().isoformat(),
                    'backend': 'apscheduler',
                }

                logger.info(f"Scheduled cron task '{job_id}': {cron_expression}")
                logger.info(f"Next run: {job.next_run_time}")
                return job_id

            self._warn_fallback_once()
            self.scheduled_jobs[job_id] = {
                'id': job_id,
                'job': None,
                'callable': func,
                'function': func.__name__,
                'cron': cron_expression,
                'next_run': None,
                'created_at': datetime.now().isoformat(),
                'backend': 'fallback',
                'note': 'Cron scheduling requires APScheduler; stored metadata only.',
            }
            logger.warning(f"Cron scheduling unavailable without APScheduler; stored metadata for '{job_id}' only.")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to schedule cron task '{job_id}': {e}")
            raise
    
    def unschedule_task(self, job_id: str) -> bool:
        """
        Remove a scheduled task.
        
        Args:
            job_id: ID of the task to remove
            
        Returns:
            True if task was removed, False if not found
        """
        try:
            if job_id in self.scheduled_jobs:
                if not self._use_fallback_scheduler() and self.scheduler and self.scheduled_jobs[job_id].get('job') is not None:
                    self.scheduler.remove_job(job_id)
                elif job_id in self._fallback_threads:
                    self._fallback_threads[job_id].set()
                    del self._fallback_threads[job_id]
                del self.scheduled_jobs[job_id]
                logger.info(f"Unscheduled task '{job_id}'")
                return True
            else:
                logger.warning(f"Task '{job_id}' not found in scheduler")
                return False
        except Exception as e:
            logger.error(f"Failed to unschedule task '{job_id}': {e}")
            return False
    
    def get_scheduled_jobs(self) -> Dict[str, Any]:
        """
        Get list of all scheduled jobs.
        
        Returns:
            Dictionary of scheduled jobs with their details
        """
        # Update next_run times
        for job_id, job_info in self.scheduled_jobs.items():
            if 'job' in job_info and job_info['job']:
                job_info['next_run'] = job_info['job'].next_run_time
        
        return self.scheduled_jobs
    
    def pause_task(self, job_id: str) -> bool:
        """
        Pause a scheduled task (can be resumed later).

        Args:
            job_id: ID of the task to pause

        Returns:
            True if task was paused, False if not found or unavailable
        """
        try:
            if job_id in self.scheduled_jobs:
                if self._use_fallback_scheduler():
                    logger.warning(f"Pause not supported in fallback scheduler for task '{job_id}'")
                    return False
                self.scheduler.pause_job(job_id)
                logger.info(f"Paused task '{job_id}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to pause task '{job_id}': {e}")
            return False

    def resume_task(self, job_id: str) -> bool:
        """
        Resume a paused task.

        Args:
            job_id: ID of the task to resume

        Returns:
            True if task was resumed, False if not found or unavailable
        """
        try:
            if job_id in self.scheduled_jobs:
                if self._use_fallback_scheduler():
                    logger.warning(f"Resume not supported in fallback scheduler for task '{job_id}'")
                    return False
                self.scheduler.resume_job(job_id)
                logger.info(f"Resumed task '{job_id}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resume task '{job_id}': {e}")
            return False
    
    def trigger_task_now(self, job_id: str) -> bool:
        """
        Manually trigger a scheduled task immediately.
        
        Args:
            job_id: ID of the task to trigger
            
        Returns:
            True if task was triggered, False if not found
        """
        try:
            if job_id in self.scheduled_jobs:
                job_info = self.scheduled_jobs[job_id]
                job = job_info.get('job')
                if job is not None:
                    job.func(*job.args, **job.kwargs)
                else:
                    func = job_info.get('callable')
                    if callable(func):
                        func()
                logger.info(f"Manually triggered task '{job_id}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to trigger task '{job_id}': {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> TaskScheduler:
    """Get or create the global task scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
