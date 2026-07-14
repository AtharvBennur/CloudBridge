"""
Purpose:
Concrete implementation of the migration worker for local simulation.
Runs in a background thread, simulates multi-table data migration in chunks,
transient failures, retries, checkpointing, and heartbeats.
"""

from __future__ import annotations

import random
import threading
import time
from datetime import datetime
from typing import Any

from flask import Flask

from app.extensions import db
from app.models.migration import MigrationJob, MigrationStatus
from app.models.migration_checkpoint import MigrationCheckpoint
from app.workers.base_worker import BaseMigrationWorker


class LocalSimulationWorker(threading.Thread, BaseMigrationWorker):
    """Simulates a chunk-by-chunk database migration in a background thread."""

    def __init__(self, app: Flask, migration_id: int) -> None:
        super().__init__()
        self.app = app
        self.migration_id = migration_id
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._status = MigrationStatus.PENDING
        self._progress = 0.0
        self._last_heartbeat = datetime.utcnow()

    def run(self) -> None:
        self._status = MigrationStatus.RUNNING
        self.heartbeat()

        with self.app.app_context():
            job = MigrationJob.query.get(self.migration_id)
            if not job:
                self.app.logger.error(f"Migration job {self.migration_id} not found in database.")
                self._status = MigrationStatus.FAILED
                return

            self.app.logger.info(f"Migration Started: Job {job.id} ({job.job_name})")
            
            # Setup migration parameters
            tables = ["users", "orders", "products", "transactions", "logs"]
            total_tables = len(tables)
            total_rows_simulated = 50000
            rows_per_table = total_rows_simulated // total_tables
            job.total_rows = total_rows_simulated
            db.session.commit()

            chunk_size = job.chunk_size or 1000
            rows_migrated = job.rows_migrated or 0

            # 1. Check if resuming from checkpoint
            latest_checkpoint = (
                MigrationCheckpoint.query.filter_by(migration_id=self.migration_id)
                .order_by(MigrationCheckpoint.created_at.desc())
                .first()
            )
            if latest_checkpoint:
                rows_migrated = latest_checkpoint.rows_processed
                self.app.logger.info(
                    f"Resuming job {job.id} from checkpoint '{latest_checkpoint.checkpoint_name}' with {rows_migrated} rows processed."
                )

            current_table_index = (rows_migrated // rows_per_table) if rows_per_table > 0 else 0
            if current_table_index >= total_tables:
                current_table_index = total_tables - 1

            while rows_migrated < total_rows_simulated:
                # 2. Check for thread stops or DB state updates
                db.session.expire(job)
                job = MigrationJob.query.get(self.migration_id)
                if not job:
                    break

                if job.status == MigrationStatus.PAUSED or self._pause_event.is_set():
                    self.app.logger.info(f"Migration job {self.migration_id} paused.")
                    self._status = MigrationStatus.PAUSED
                    break
                if job.status == MigrationStatus.CANCELLED or self._stop_event.is_set():
                    self.app.logger.info(f"Migration job {self.migration_id} cancelled.")
                    self._status = MigrationStatus.CANCELLED
                    break

                current_table = tables[current_table_index]
                job.current_table = current_table
                db.session.commit()

                # 3. Simulate transient connection error (5% probability)
                simulated_error = random.random() < 0.05
                if simulated_error:
                    self.app.logger.warning(f"Retries: Transient network error encountered on table {current_table} for job {job.id}.")
                    retry = 0
                    success = False
                    while retry < job.max_retries:
                        retry += 1
                        job.retry_count = retry
                        db.session.commit()
                        self.app.logger.info(f"Retrying... Attempt {retry}/{job.max_retries} for job {job.id}")
                        time.sleep(0.5)
                        if random.random() > 0.3:  # 70% success chance
                            success = True
                            self.app.logger.info(f"Retry attempt {retry} succeeded for job {job.id}.")
                            break
                    
                    if not success:
                        job.status = MigrationStatus.FAILED
                        job.error_message = f"Failed to migrate table {current_table} after {job.max_retries} attempts."
                        db.session.commit()
                        self.app.logger.error(f"Migration Failed: Job {job.id} failed. {job.error_message}")
                        self._status = MigrationStatus.FAILED
                        return

                # 4. Simulate actual chunk transfer time
                time.sleep(0.3)
                rows_migrated += chunk_size
                if rows_migrated > total_rows_simulated:
                    rows_migrated = total_rows_simulated

                # Update database job
                self._progress = (rows_migrated / total_rows_simulated) * 100.0
                job.rows_migrated = rows_migrated
                job.progress_percent = self._progress
                db.session.commit()

                # Liveness heartbeat
                self.heartbeat()

                # 5. Periodically checkpoint after completing each table
                if (rows_migrated % rows_per_table == 0) or (rows_migrated == total_rows_simulated):
                    checkpoint_name = f"checkpoint_{current_table}_{rows_migrated}"
                    checkpoint = MigrationCheckpoint(
                        migration_id=self.migration_id,
                        checkpoint_name=checkpoint_name,
                        progress_percent=self._progress,
                        rows_processed=rows_migrated,
                        checkpoint_metadata=f'{{"table": "{current_table}", "rows_migrated": {rows_migrated}, "timestamp": {time.time()}}}',
                    )
                    db.session.add(checkpoint)
                    db.session.commit()
                    self.app.logger.info(f"Checkpoint Saved: Checkpoint '{checkpoint_name}' recorded for job {job.id}.")

                    # Move to next table
                    if current_table_index < total_tables - 1:
                        current_table_index += 1

            # 6. Mark completed
            if rows_migrated >= total_rows_simulated:
                job.status = MigrationStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                db.session.commit()
                self._status = MigrationStatus.COMPLETED
                self.app.logger.info(f"Migration Finished: Job {job.id} completed successfully.")

    # BaseMigrationWorker implementation
    def start(self) -> None:
        # Thread.start() must be called explicitly: calling self.start() here
        # would recursively invoke this interface method forever.
        super().start()

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()
        if not self.is_alive():
            super().start()

    def cancel(self) -> None:
        self._stop_event.set()

    def get_status(self) -> str:
        return self._status

    def get_progress(self) -> float:
        return self._progress

    def heartbeat(self) -> None:
        self._last_heartbeat = datetime.utcnow()
        # Log worker status liveness
        self.app.logger.info(f"Worker Status: Heartbeat for job {self.migration_id} updated at {self._last_heartbeat}.")

    def retry(self) -> None:
        """Restart a failed worker from its persisted checkpoint."""
        if not self.is_alive():
            super().start()
