"""CloudWatch Log Streaming Service.

Handles:
- Discovering log streams for ECS tasks
- Reading log events continuously
- Streaming logs to the frontend via WebSocket
- Extracting error/exception lines from logs
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import ClientError

from app.services.migration_errors import MigrationError, log_stream_error

logger = logging.getLogger(__name__)

LOG_GROUP_NAME = "/aws/ecs/cloudbridge-migration-workers"


@dataclass
class LogEvent:
    """A single CloudWatch log event."""

    timestamp: int  # Unix ms
    message: str
    ingestion_time: int = 0

    @property
    def timestamp_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc).isoformat()


class LogStreamingService:
    """Streams CloudWatch logs for ECS migration tasks."""

    def __init__(self, logs_client: Any, region: str) -> None:
        self._logs = logs_client
        self._region = region

    def ensure_log_group(self) -> str:
        """Ensure the log group exists. Idempotent."""
        try:
            response = self._logs.describe_log_groups(logGroupNamePrefix=LOG_GROUP_NAME)
            for g in response.get("logGroups", []):
                if g["logGroupName"] == LOG_GROUP_NAME:
                    return LOG_GROUP_NAME
        except ClientError:
            pass

        try:
            self._logs.create_log_group(
                logGroupName=LOG_GROUP_NAME,
                tags={"ManagedBy": "CloudBridge"},
            )
            logger.info("Created CloudWatch log group: %s", LOG_GROUP_NAME)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "ResourceAlreadyExistsException":
                logger.warning("Failed to create log group: %s", exc)

        return LOG_GROUP_NAME

    def find_log_stream(self, task_arn: str, task_definition_family: str) -> str | None:
        """Find the log stream for a specific ECS task.

        ECS creates log streams with pattern: ecs/<family>/<task-id>
        """
        # Extract task ID from ARN
        task_id = task_arn.split("/")[-1] if "/" in task_arn else task_arn
        stream_prefix = f"ecs/{task_definition_family}/{task_id}"

        try:
            response = self._logs.describe_log_streams(
                logGroupName=LOG_GROUP_NAME,
                logStreamNamePrefix=stream_prefix,
                orderBy="LastEventTime",
                descending=True,
                limit=5,
            )
            streams = response.get("logStreams", [])
            if streams:
                # Find exact match or closest match
                for s in streams:
                    if task_id in s.get("logStreamName", ""):
                        return s["logStreamName"]
                # Fall back to first stream with matching prefix
                return streams[0]["logStreamName"]
        except ClientError as exc:
            logger.warning("Failed to find log stream for task %s: %s", task_arn, exc)

        return None

    def get_log_events(
        self,
        log_stream_name: str,
        start_time: int | None = None,
        limit: int = 100,
    ) -> list[LogEvent]:
        """Get log events from a log stream."""
        try:
            kwargs: dict[str, Any] = {
                "logGroupName": LOG_GROUP_NAME,
                "logStreamName": log_stream_name,
                "limit": limit,
                "startFromHead": True,
            }
            if start_time:
                kwargs["startTime"] = start_time

            response = self._logs.get_log_events(**kwargs)
            events = []
            for e in response.get("events", []):
                events.append(LogEvent(
                    timestamp=e.get("timestamp", 0),
                    message=e.get("message", ""),
                    ingestion_time=e.get("ingestionTime", 0),
                ))
            return events
        except ClientError as exc:
            raise log_stream_error(
                f"Failed to get log events: {exc}",
                log_stream_name,
                retryable=True,
            ) from exc

    def get_recent_errors(self, log_stream_name: str, tail_lines: int = 50) -> list[str]:
        """Get recent error/exception lines from logs."""
        events = self.get_log_events(log_stream_name, limit=tail_lines)
        error_lines = []
        for event in events:
            msg = event.message
            if any(keyword in msg.lower() for keyword in [
                "error", "exception", "traceback", "failed", "fatal",
                "cannotpullcontainer", "refused", "timeout",
            ]):
                error_lines.append(msg)
        return error_lines

    def stream_logs(
        self,
        log_stream_name: str,
        callback: Any,
        poll_interval: int = 3,
        max_duration: int = 3600,
    ) -> None:
        """Continuously stream logs, invoking callback for each new batch.

        Args:
            log_stream_name: The CloudWatch log stream name
            callback: Callable(log_events: list[LogEvent]) for each new batch
            poll_interval: Seconds between polls
            max_duration: Maximum seconds to stream
        """
        next_token = None
        start_time = int(time.time() * 1000)
        deadline = time.time() + max_duration

        while time.time() < deadline:
            try:
                kwargs: dict[str, Any] = {
                    "logGroupName": LOG_GROUP_NAME,
                    "logStreamName": log_stream_name,
                    "startFromHead": True,
                }
                if next_token:
                    kwargs["nextToken"] = next_token
                else:
                    kwargs["startTime"] = start_time

                response = self._logs.get_log_events(**kwargs)
                events = response.get("events", [])

                if events:
                    log_events = [
                        LogEvent(
                            timestamp=e.get("timestamp", 0),
                            message=e.get("message", ""),
                            ingestion_time=e.get("ingestionTime", 0),
                        )
                        for e in events
                    ]
                    callback(log_events)

                next_token = response.get("nextForwardToken")
                # If nextForwardToken == nextBackwardToken, no new events
                if next_token == response.get("nextBackwardToken"):
                    time.sleep(poll_interval)
                    continue

            except ClientError as exc:
                logger.warning("Log streaming error: %s", exc)
                time.sleep(poll_interval)
                continue

            time.sleep(poll_interval)
