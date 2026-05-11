"""Scheduler lease behavior tests."""

import asyncio

from req_tracker.scheduler.models import ScheduleConfig
from req_tracker.scheduler.service import RunScheduler


class FakeLeaseManager:
    def __init__(self, acquired: bool) -> None:
        self.acquired = acquired
        self.acquire_calls = 0
        self.release_calls = 0

    def acquire_scheduler_lease(
        self,
        *,
        lease_name: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> bool:
        self.acquire_calls += 1
        assert lease_name == "test-lease"
        assert owner_id == "worker-a"
        assert ttl_seconds == 60
        return self.acquired

    def release_scheduler_lease(self, *, lease_name: str, owner_id: str) -> None:
        self.release_calls += 1
        assert lease_name == "test-lease"
        assert owner_id == "worker-a"


def test_periodic_run_uses_lease_and_releases_after_success() -> None:
    lease = FakeLeaseManager(acquired=True)
    scheduler = RunScheduler(
        ScheduleConfig(lease_name="test-lease", lease_ttl_seconds=60),
        lease_manager=lease,
        owner_id="worker-a",
    )
    started: list[tuple[str, str, str]] = []

    result = asyncio.run(
        scheduler._run_now(  # noqa: SLF001
            runner=lambda run_id, project_key, scenario: started.append(
                (run_id, project_key, scenario)
            ),
            new_id=lambda prefix: f"{prefix}_001",
            require_lease=True,
        )
    )

    assert result.error is None
    assert result.run_id == "sched_001"
    assert started == [("sched_001", "RUNE_CAM_ALPHA", "RUNE_MULTI_SOURCE")]
    assert scheduler.status().runs_started == 1
    assert scheduler.status().lease_enabled is True
    assert lease.acquire_calls == 1
    assert lease.release_calls == 1


def test_periodic_run_skips_when_lease_is_held_by_another_worker() -> None:
    lease = FakeLeaseManager(acquired=False)
    scheduler = RunScheduler(
        ScheduleConfig(lease_name="test-lease", lease_ttl_seconds=60),
        lease_manager=lease,
        owner_id="worker-a",
    )
    started: list[str] = []

    result = asyncio.run(
        scheduler._run_now(  # noqa: SLF001
            runner=lambda run_id, _project_key, _scenario: started.append(run_id),
            new_id=lambda prefix: f"{prefix}_skipped",
            require_lease=True,
        )
    )

    assert result.error == "scheduler lease held by another worker"
    assert started == []
    status = scheduler.status()
    assert status.runs_started == 0
    assert status.lease_skips == 1
    assert lease.acquire_calls == 1
    assert lease.release_calls == 0
