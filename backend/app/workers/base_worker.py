"""
Purpose:
Defines the abstract interface for all migration workers.
Future targets (e.g. ECS Fargate task executor) will inherit from this base class.
"""

from abc import ABC, abstractmethod


class BaseMigrationWorker(ABC):
    """Abstract interface defining required migration lifecycle operations."""

    @abstractmethod
    def start(self) -> None:
        """Start or resume the migration process."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Temporarily suspend migration execution."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume execution from the last successful checkpoint."""
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Permanently stop and discard the migration job."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Return the current execution status (e.g. RUNNING, PAUSED)."""
        pass

    @abstractmethod
    def get_progress(self) -> float:
        """Return the progress percentage of the migration."""
        pass

    @abstractmethod
    def heartbeat(self) -> None:
        """Trigger a heartbeat update to indicate liveness."""
        pass

    @abstractmethod
    def retry(self) -> None:
        """Retry a failed migration from its most recent checkpoint."""
        pass
