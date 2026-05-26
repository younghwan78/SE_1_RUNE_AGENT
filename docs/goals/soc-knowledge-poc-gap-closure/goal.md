# SoC Knowledge PoC Gap Closure

## Objective

Bring the existing implementation closer to `SoC_Knowledge_PoC_Design_v4.0.md` by repeatedly analyzing the current `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md`, selecting the largest safe verified work package, implementing it, and verifying it until a final audit proves the PoC design is satisfied or only external blockers remain.

## Original Request

`기존에 구현된 코드를 SoC_Knowledge_PoC_Design_v4.0.md 문서를 참조해서 수정하는 것을 goal로 진행하고 있어. 현재 정확한 구현 상황과 gap을 참조해서 단계별로 적절한 goal을 세우고 이를 기준으로 실행하게 상세 목표를 잡아줘`

## Intake Summary

- Input shape: `existing_plan`
- Audience: project owner and future `/goal` execution PM
- Authority: `requested`
- Proof type: `test`
- Completion proof: a final Judge or PM audit maps current implementation evidence, verification command output, and remaining external blockers back to every material requirement in `SoC_Knowledge_PoC_Design_v4.0.md` and `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md`, then records `full_outcome_complete: true`.
- Goal oracle: the live state of the repo plus fresh verification commands prove that each selected gap-closing slice is implemented, tested, documented where required, and reflected in the gap report.
- Likely misfire: continuing to add small gates, docs, or scaffolds while leaving the highest-risk remaining gaps, live-evidence gaps, or design-critical behavior unimplemented or unverified.
- Blind spots considered: current worktree may contain many uncommitted changes; prior chat memory may be stale; some gaps require external services, local models, credentials, or live target databases; existing implementation should be reused where it aligns with the production plan instead of replacing it.
- Existing plan facts:
  - `PRODUCTION_EXECUTION_PLAN.md` is the repository source of truth.
  - `SoC_Knowledge_PoC_Design_v4.0.md` is the current PoC design target.
  - `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md` is the working gap report to minimize.
  - Keep approved graph data and pending AI proposals logically separate.
  - LLM calls must go through the model gateway and remain traceable.
  - Claude Code source skills handle source access procedures; MCP tool names must not leak into product code.
  - Follow the existing implementation where practical; do not rewrite from scratch unless the evidence shows reuse is slower or riskier.
  - Use Python 3.12+, uv, Pydantic, FastAPI, type hints, structured logs, idempotency keys for command APIs, and tests matched to blast radius.
  - Do not reintroduce removed PRD files.

## Goal Oracle

The oracle for this goal is:

`A final audit can point to current files, fresh command outputs, and gap-report status proving that every material requirement in SoC_Knowledge_PoC_Design_v4.0.md is implemented or explicitly blocked by named external evidence, with no queued required Worker task left unresolved.`

The PM must keep comparing task receipts to this oracle. Planning, discovery, a passing tiny slice, or a clean-looking board is not enough. The goal finishes only when a final Judge/PM audit maps receipts and verification back to this oracle and records `full_outcome_complete: true`.

## Goal Kind

`existing_plan`

## Current Tranche

This tranche is continuous implementation and verification. The first phase is a read-only evidence pass over the design document, gap report, current diff, repository source of truth, and available verification commands. The PM must then select the largest safe useful Worker slice that closes a material gap without requiring external credentials or production access. After each verified slice, update the gap report and continue to the next safe slice unless a phase boundary, rejected verification, ambiguity, or final completion audit is due.

## Non-Negotiable Constraints

- Do not treat the prior conversation as authoritative; inspect the current worktree and command output before using it as evidence.
- Do not implement outside an active Worker task with explicit `allowed_files`, `verify`, and `stop_if`.
- Preserve user or pre-existing uncommitted changes; do not revert unrelated work.
- Prefer reusing existing modules, tests, fixtures, and gate patterns over parallel implementations.
- Keep model-specific SDK or process calls behind `src/req_tracker/model_gateway/`.
- Keep deterministic logic testable without live LLM calls.
- Keep live external dependency checks skip-safe by default and explicit when `--live`, `--require-live`, or equivalent flags are used.
- Do not hardcode secrets, credentials, tokens, internal endpoints, or unmasked confidential data.
- Update `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md` whenever a gap status materially changes.
- Run fresh verification before claiming a Worker slice is complete.

## Stop Rule

Stop only when a final audit proves the full original outcome is complete.

Do not stop after planning, discovery, or Judge selection if a safe Worker task can be activated.

Do not stop after a single verified Worker package when the broader owner outcome still has safe local follow-up work. Advance the board to the next highest-leverage safe Worker package and continue unless a phase, risk, rejected-verification, ambiguity, or final-completion review is due.

Do not create one Worker/Judge pair per repeated file, table, route, or helper. Put repeated same-shape work into one Worker package and review the package as a whole.

## Slice Sizing

Safe means bounded, explicit, verified, and reversible. It does not mean tiny.

A good task is the largest safe useful slice.

Small is not the goal. Useful is the goal.

A Worker should finish the whole assigned slice. A Judge should judge the whole assigned slice. A PM should reorient the board when tasks are safe but not moving the outcome.

Tiny tasks are allowed when the failure is isolated, the risk is high, the scope is unknown, or the tiny task unlocks a larger slice. Tiny tasks are bad when they keep happening, do not change behavior, only add wrappers/contracts/proof files, or avoid the real milestone.

Do not stop because a slice needs owner input, credentials, production access, destructive operations, or policy decisions. Mark that exact slice blocked with a receipt, create the smallest safe follow-up or workaround task, and continue all local, non-destructive work that can still move the goal toward the full outcome.

## Canonical Board

Machine truth lives at:

`docs/goals/soc-knowledge-poc-gap-closure/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/soc-knowledge-poc-gap-closure/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Run the bundled GoalBuddy update checker when available and mention a newer version without blocking.
4. Re-check the intake: original request, input shape, authority, proof, blind spots, existing plan facts, and likely misfire.
5. Work only on the active board task.
6. Assign Scout, Judge, Worker, or PM according to the task.
7. Write a compact task receipt.
8. Update the board.
9. If safe local work remains, choose the next largest reversible Worker package and continue unless blocked.
10. If a problem, suggestion, or follow-up should become a repo artifact, create an approved issue/PR or ask the operator whether to create one.
11. Review at phase, risk, rejected-verification, ambiguity, or final-completion boundaries; do not review every small Worker by habit.
12. Finish only with a Judge/PM audit receipt that maps receipts and verification back to the original user outcome and records `full_outcome_complete: true`.

Issue and PR handoffs are supporting artifacts. `state.yaml` remains authoritative, and every external artifact decision must be recorded in a task receipt.
