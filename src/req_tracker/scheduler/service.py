"""Async periodic scheduler for local and server deployments."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from req_tracker.scheduler.models import (
    ScheduleConfig,
    ScheduledRunResult,
    ScheduleStatus,
)

RunCallback = Callable[[str, str, str], object]
IdFactory = Callable[[str], str]


class RunScheduler:
    """Manage periodic analysis runs inside the API process."""

    def __init__(self, config: ScheduleConfig | None = None) -> None:
        self.config = config or ScheduleConfig()
        self.last_run: ScheduledRunResult | None = None
        self.next_run_at: datetime | None = None
        self.runs_started = 0
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
                await self.run_now(runner=runner, new_id=new_id)
                self.next_run_at = datetime.now(UTC) + timedelta(
                    seconds=self.config.interval_seconds
                )
