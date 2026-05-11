"""Async periodic scheduler for local and server deployments."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from req_tracker.scheduler.models import (
    ScheduleConfig,
    ScheduledRunResult,
    ScheduleStatus,
)

RunCallback = Callable[[str, str, str], object]
IdFactory = Callable[[str], str]


class SchedulerLeaseManager(Protocol):
    """Optional distributed lease backend for multi-worker scheduler deployments."""

    def acquire_scheduler_lease(
        self,
        *,
        lease_name: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> bool:
        """Acquire or renew a scheduler lease."""

    def release_scheduler_lease(self, *, lease_name: str, owner_id: str) -> None:
        """Release a scheduler lease owned by this instance."""


class RunScheduler:
    """Manage periodic analysis runs inside the API process."""

    def __init__(
        self,
        config: ScheduleConfig | None = None,
        *,
        lease_manager: SchedulerLeaseManager | None = None,
        owner_id: str | None = None,
    ) -> None:
        self.config = config or ScheduleConfig()
        self.lease_manager = lease_manager
        self.owner_id = owner_id or f"scheduler_{uuid4().hex[:12]}"
        self.last_run: ScheduledRunResult | None = None
        self.next_run_at: datetime | None = None
        self.runs_started = 0
        self.lease_skips = 0
        self.last_error: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the background loop is active."""
        return self._task is not None and not self._task.done()

    async def configure(
        self,
        config: ScheduleConfig,
        *,
        runner: RunCallback,
        new_id: IdFactory,
    ) -> ScheduleStatus:
        """Apply a schedule configuration."""
        await self.stop()
        self.config = config
        if config.enabled:
            await self.start(runner=runner, new_id=new_id)
        return self.status()

    async def start(self, *, runner: RunCallback, new_id: IdFactory) -> ScheduleStatus:
        """Start the periodic loop if enabled."""
        if self.is_running:
            return self.status()
        self.config.enabled = True
        self._stop_event = asyncio.Event()
        self.next_run_at = datetime.now(UTC) + timedelta(seconds=self.config.interval_seconds)
        self._task = asyncio.create_task(self._loop(runner=runner, new_id=new_id))
        return self.status()

    async def stop(self) -> ScheduleStatus:
        """Stop the periodic loop."""
        self.config.enabled = False
        if self._task is not None and not self._task.done():
            if self._stop_event is not None:
                self._stop_event.set()
            await self._task
        self._task = None
        self._stop_event = None
        self.next_run_at = None
        return self.status()

    async def run_now(self, *, runner: RunCallback, new_id: IdFactory) -> ScheduledRunResult:
        """Run one scheduled analysis immediately."""
        return await self._run_now(runner=runner, new_id=new_id, require_lease=False)

    def _acquire_lease(self) -> bool:
        if self.lease_manager is None:
            return True
        return self.lease_manager.acquire_scheduler_lease(
            lease_name=self.config.lease_name,
            owner_id=self.owner_id,
            ttl_seconds=self.config.lease_ttl_seconds,
        )

    def _release_lease(self) -> None:
        if self.lease_manager is None:
            return
        self.lease_manager.release_scheduler_lease(
            lease_name=self.config.lease_name,
            owner_id=self.owner_id,
        )

    async def _run_now(
        self,
        *,
        runner: RunCallback,
        new_id: IdFactory,
        require_lease: bool,
    ) -> ScheduledRunResult:
        if require_lease and not self._acquire_lease():
            self.lease_skips += 1
            run_id = new_id(self.config.run_id_prefix)
            result = ScheduledRunResult(
                run_id=run_id,
                completed_at=datetime.now(UTC),
                error="scheduler lease held by another worker",
            )
            self.last_run = result
            self.last_error = result.error
            return result
        run_id = new_id(self.config.run_id_prefix)
        result = ScheduledRunResult(run_id=run_id)
        self.last_run = result
        self.runs_started += 1
        try:
            runner(run_id, self.config.project_key, self.config.scenario)
            result = result.model_copy(update={"completed_at": datetime.now(UTC)})
            self.last_error = None
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            result = result.model_copy(
                update={"completed_at": datetime.now(UTC), "error": self.last_error}
            )
        finally:
            if require_lease:
                self._release_lease()
        self.last_run = result
        return result

    def status(self) -> ScheduleStatus:
        """Return current schedule status."""
        return ScheduleStatus(
            enabled=self.config.enabled,
            running=self.is_running,
            interval_seconds=self.config.interval_seconds,
            project_key=self.config.project_key,
            scenario=self.config.scenario,
            last_run_id=self.last_run.run_id if self.last_run else None,
            last_started_at=self.last_run.started_at if self.last_run else None,
            last_completed_at=self.last_run.completed_at if self.last_run else None,
            last_error=self.last_error,
            next_run_at=self.next_run_at,
            runs_started=self.runs_started,
            lease_name=self.config.lease_name,
            lease_owner_id=self.owner_id,
            lease_enabled=self.lease_manager is not None,
            lease_skips=self.lease_skips,
        )

    async def _loop(self, *, runner: RunCallback, new_id: IdFactory) -> None:
        while self._stop_event is not None:
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.interval_seconds,
                )
                break
            except TimeoutError:
                await self._run_now(runner=runner, new_id=new_id, require_lease=True)
                self.next_run_at = datetime.now(UTC) + timedelta(
                    seconds=self.config.interval_seconds
                )
