"""
Purpose:
A thread-safe manager that tracks, starts, pauses, resumes, and cancels
migration execution worker threads.
"""

from __future__ import annotations

import threading
from typing import Dict

from flask import Flask

from app.workers.local_worker import LocalSimulationWorker


class MigrationWorkerManager:
    """Manages active background migration workers."""

    def __init__(self) -> None:
        self._workers: dict[int, LocalSimulationWorker] = {}
        self._lock = threading.Lock()

    def start_worker(self, app: Flask, migration_id: int) -> bool:
        """Start a new worker for the migration job in a background thread."""
        with self._lock:
            # Clean up dead threads
            self._cleanup_inactive()

            if migration_id in self._workers and self._workers[migration_id].is_alive():
                app.logger.warning(f"Worker for migration {migration_id} is already running.")
                return False

            worker = LocalSimulationWorker(app, migration_id)
            self._workers[migration_id] = worker
            worker.start()
            return True

    def pause_worker(self, migration_id: int) -> bool:
        """Signal the active worker to pause."""
        with self._lock:
            worker = self._workers.get(migration_id)
            if worker and worker.is_alive():
                worker.pause()
                return True
            return False

    def resume_worker(self, app: Flask, migration_id: int) -> bool:
        """Resume a migration job by spawning a new active worker thread."""
        return self.start_worker(app, migration_id)

    def cancel_worker(self, migration_id: int) -> bool:
        """Signal the active worker to cancel and stop execution."""
        with self._lock:
            worker = self._workers.get(migration_id)
            if worker and worker.is_alive():
                worker.cancel()
                return True
            return False

    def retry_worker(self, app: Flask, migration_id: int) -> bool:
        """Start a fresh worker for a failed job; checkpoints preserve progress."""
        return self.start_worker(app, migration_id)

    def get_active_worker(self, migration_id: int) -> LocalSimulationWorker | None:
        """Get the active worker instance if it is currently running."""
        with self._lock:
            worker = self._workers.get(migration_id)
            if worker and worker.is_alive():
                return worker
            return None

    def _cleanup_inactive(self) -> None:
        """Remove workers whose threads have finished execution."""
        inactive_ids = [mid for mid, worker in self._workers.items() if not worker.is_alive()]
        for mid in inactive_ids:
            del self._workers[mid]


# Global worker manager instance
worker_manager = MigrationWorkerManager()
