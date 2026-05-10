"""In-memory trace repository for local and test workflows."""

from datetime import UTC, datetime

from req_tracker.debug.hash import stable_hash
from req_tracker.debug.models import AgentRun, AgentStepTrace, LLMCallTrace, RunType, TriggerSource


class InMemoryTraceRepository:
    """Store runs, steps, and LLM traces in memory."""

    def __init__(self) -> None:
        self.runs: dict[str, AgentRun] = {}
        self.steps: dict[str, AgentStepTrace] = {}
        self.llm_calls: dict[str, LLMCallTrace] = {}

    def create_run(
        self,
        *,
        run_id: str,
        run_type: RunType,
        project_key: str,
        triggered_by: str,
        trigger_source: TriggerSource,
    ) -> AgentRun:
        """Create a queued run."""
        run = AgentRun(
            run_id=run_id,
            run_type=run_type,
            project_key=project_key,
            triggered_by=triggered_by,
            trigger_source=trigger_source,
        )
        self.runs[run_id] = run
        return run

    def mark_run_running(self, run_id: str) -> AgentRun:
        """Mark a run as running."""
        run = self.runs[run_id].model_copy(update={"status": "running"})
        self.runs[run_id] = run
        return run

    def complete_run(self, run_id: str, status: str = "succeeded") -> AgentRun:
        """Complete a run."""
        run = self.runs[run_id].model_copy(
            update={"status": status, "completed_at": datetime.now(UTC)}
        )
        self.runs[run_id] = run
        return run

    def start_step(
        self,
        *,
        step_id: str,
        run_id: str,
        stage_name: str,
        input_payload: object,
        retry_count: int = 0,
    ) -> AgentStepTrace:
        """Start a step trace."""
        step = AgentStepTrace(
            step_id=step_id,
            run_id=run_id,
            stage_name=stage_name,
            status="running",
            input_hash=stable_hash(input_payload),
            retry_count=retry_count,
        )
        self.steps[step_id] = step
        return step

    def finish_step(
        self,
        *,
        step_id: str,
        output_payload: object,
        output_ref: str | None = None,
    ) -> AgentStepTrace:
        """Finish a step successfully."""
        current = self.steps[step_id]
        updated = current.model_copy(
            update={
                "status": "succeeded",
                "output_hash": stable_hash(output_payload),
                "output_ref": output_ref,
                "completed_at": datetime.now(UTC),
            }
        )
        self.steps[step_id] = updated
        return updated

    def fail_step(
        self,
        *,
        step_id: str,
        error_class: str,
        error_message: str,
    ) -> AgentStepTrace:
        """Mark a step as failed."""
        current = self.steps[step_id]
        updated = current.model_copy(
            update={
                "status": "failed",
                "error_class": error_class,
                "error_message": error_message,
                "completed_at": datetime.now(UTC),
            }
        )
        self.steps[step_id] = updated
        return updated

    def record_llm_call(self, trace: LLMCallTrace) -> LLMCallTrace:
        """Record an LLM call trace."""
        self.llm_calls[trace.llm_call_id] = trace
        return trace

    def list_steps(self, run_id: str) -> list[AgentStepTrace]:
        """List steps for a run."""
        return [step for step in self.steps.values() if step.run_id == run_id]

