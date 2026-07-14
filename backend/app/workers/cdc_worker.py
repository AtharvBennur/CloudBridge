"""
Purpose:
Concrete implementation of the CDC worker for PostgreSQL WAL-based change data capture.
Runs in a background thread, continuously reading WAL changes and applying them to the destination.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Any

from flask import Flask

from app.extensions import db
from app.models.cdc_config import CDCConfig, CDCMode, CDCStatus
from app.models.cdc_event import CDCEvent, ChangeOperation, CDCEventStatus
from app.models.migration import MigrationJob, MigrationStatus
from app.services.cdc_service import CDCService, CDCConfigNotFoundError
from app.workers.base_worker import BaseMigrationWorker


class PostgreSQLCDCWorker(threading.Thread, BaseMigrationWorker):
    """Implements CDC using PostgreSQL logical replication (WAL)."""

    def __init__(self, app: Flask, migration_id: int) -> None:
        super().__init__()
        self.app = app
        self.migration_id = migration_id
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._status = CDCStatus.INITIALIZING
        self._progress = 0.0
        self._last_heartbeat = datetime.utcnow()
        self.cdc_service = CDCService()

    def run(self) -> None:
        self._status = CDCStatus.RUNNING
        self.heartbeat()

        with self.app.app_context():
            try:
                job = MigrationJob.query.get(self.migration_id)
                if not job:
                    self.app.logger.error(f"Migration job {self.migration_id} not found in database.")
                    self._status = CDCStatus.ERROR
                    return

                config = self.cdc_service.get_config(self.migration_id)
                self.app.logger.info(f"CDC Worker Started: Job {job.id} ({job.job_name}), Mode: {config.cdc_mode}")

                # Initialize CDC based on mode
                if config.cdc_mode in {CDCMode.FULL_LOAD, CDCMode.FULL_LOAD_AND_CDC}:
                    self._perform_full_load(job, config)

                if config.cdc_mode in {CDCMode.CDC_ONLY, CDCMode.FULL_LOAD_AND_CDC}:
                    self._perform_cdc_replication(job, config)

                # Mark as completed
                config.status = CDCStatus.COMPLETED
                db.session.commit()
                self._status = CDCStatus.COMPLETED
                self.app.logger.info(f"CDC Worker Finished: Job {job.id} completed successfully.")

            except Exception as exc:
                self.app.logger.error(f"CDC Worker Error: Job {self.migration_id} failed with error: {exc}")
                self._status = CDCStatus.ERROR
                config = self.cdc_service.get_config(self.migration_id)
                config.status = CDCStatus.ERROR
                config.error_message = str(exc)
                config.consecutive_errors += 1
                db.session.commit()

    def _perform_full_load(self, job: MigrationJob, config: CDCConfig) -> None:
        """Perform initial full load of data."""
        self.app.logger.info(f"Starting full load for migration {job.id}")
        
        # Simulate full load process
        tables = ["users", "orders", "products", "transactions", "logs"]
        total_tables = len(tables)
        
        for idx, table in enumerate(tables):
            # Check for stop/pause
            if self._should_stop(job, config):
                return

            self.app.logger.info(f"Full loading table: {table}")
            job.current_table = table
            job.progress_percent = ((idx + 1) / total_tables) * 50  # Full load is 50% of progress
            db.session.commit()
            
            # Simulate table load time
            time.sleep(1)
            
            self.heartbeat()

        self.app.logger.info(f"Full load completed for migration {job.id}")

    def _perform_cdc_replication(self, job: MigrationJob, config: CDCConfig) -> None:
        """Perform continuous CDC replication."""
        self.app.logger.info(f"Starting CDC replication for migration {job.id}")
        
        # Initialize replication slot and publication
        self._initialize_replication(config)
        
        # Main CDC loop
        consecutive_errors = 0
        max_errors = config.max_consecutive_errors
        
        while not self._stop_event.is_set():
            # Check for pause
            if self._pause_event.is_set() or job.status == MigrationStatus.PAUSED:
                self.app.logger.info(f"CDC replication paused for migration {job.id}")
                self._status = CDCStatus.PAUSED
                time.sleep(1)
                continue
            
            # Check for cancellation
            if job.status == MigrationStatus.CANCELLED:
                self.app.logger.info(f"CDC replication cancelled for migration {job.id}")
                self._status = CDCStatus.STOPPED
                return
            
            try:
                # Simulate reading WAL changes
                changes = self._read_wal_changes(config)
                
                if changes:
                    self._apply_changes(job, config, changes)
                    consecutive_errors = 0
                else:
                    # No changes, wait for poll interval
                    time.sleep(config.poll_interval_ms / 1000)
                
                # Update progress
                job.progress_percent = min(50 + (job.progress_percent * 0.5), 99.9)
                db.session.commit()
                
                self.heartbeat()
                
            except Exception as exc:
                consecutive_errors += 1
                self.app.logger.error(f"CDC replication error for migration {job.id}: {exc}")
                
                if consecutive_errors >= max_errors:
                    raise Exception(f"Max consecutive errors ({max_errors}) reached") from exc
                
                time.sleep(2)  # Backoff before retry

    def _initialize_replication(self, config: CDCConfig) -> None:
        """Initialize PostgreSQL logical replication."""
        # In production, this would:
        # 1. Create replication slot if not exists
        # 2. Create publication for tables
        # 3. Start from consistent LSN
        
        if not config.replication_slot_name:
            config.replication_slot_name = f"cloudbridge_slot_{self.migration_id}"
        
        if not config.publication_name:
            config.publication_name = f"cloudbridge_pub_{self.migration_id}"
        
        config.last_lsn = "0/0"  # Start from beginning
        config.status = CDCStatus.RUNNING
        db.session.commit()
        
        self.app.logger.info(f"Replication initialized: slot={config.replication_slot_name}, pub={config.publication_name}")

    def _read_wal_changes(self, config: CDCConfig) -> list[dict[str, Any]]:
        """Simulate reading changes from PostgreSQL WAL."""
        # In production, this would use pgoutput or wal2json plugin
        # to read actual WAL changes from the replication slot
        
        # Simulate random changes for demonstration
        import random
        
        if random.random() < 0.3:  # 30% chance of having changes
            return [
                {
                    "operation": random.choice([ChangeOperation.INSERT, ChangeOperation.UPDATE, ChangeOperation.DELETE]),
                    "table_name": random.choice(["users", "orders", "products"]),
                    "lsn": f"{int(time.time())}/{random.randint(0, 99999999)}",
                    "before_data": {"id": random.randint(1, 1000)} if random.random() < 0.5 else None,
                    "after_data": {"id": random.randint(1, 1000), "name": f"user_{random.randint(1, 1000)}"},
                    "transaction_id": f"tx_{random.randint(1, 10000)}",
                }
            ]
        
        return []

    def _apply_changes(self, job: MigrationJob, config: CDCConfig, changes: list[dict[str, Any]]) -> None:
        """Apply CDC changes to destination database."""
        for change in changes:
            try:
                # Record the change event
                event = self.cdc_service.record_change_event(
                    migration_id=self.migration_id,
                    operation=change["operation"],
                    table_name=change["table_name"],
                    lsn=change["lsn"],
                    before_data=change.get("before_data"),
                    after_data=change.get("after_data"),
                    transaction_id=change.get("transaction_id"),
                    change_timestamp=datetime.utcnow(),
                )
                
                # Simulate applying change to destination
                time.sleep(0.1)
                
                # Mark as processed
                self.cdc_service.mark_event_processed(event.id)
                
                # Update LSN
                config.last_lsn = change["lsn"]
                config.last_sync_at = datetime.utcnow()
                db.session.commit()
                
                self.app.logger.info(f"Applied change: {change['operation']} on {change['table_name']}")
                
            except Exception as exc:
                self.app.logger.error(f"Failed to apply change: {exc}")
                raise

    def _should_stop(self, job: MigrationJob, config: CDCConfig) -> bool:
        """Check if worker should stop."""
        if self._stop_event.is_set():
            return True
        if job.status == MigrationStatus.CANCELLED:
            return True
        if job.status == MigrationStatus.PAUSED:
            return True
        return False

    # BaseMigrationWorker implementation
    def start(self) -> None:
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
        self.app.logger.info(f"CDC Worker Heartbeat: Job {self.migration_id} at {self._last_heartbeat}")

    def retry(self) -> None:
        """Retry a failed CDC worker."""
        if not self.is_alive():
            super().start()
