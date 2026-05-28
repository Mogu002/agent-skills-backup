---
name: mavis-team
description: >
  Run a parallel team plan AND/OR create the agents you need to do it. Two intertwined entry points:
  (1) Execute a complex task with the existing roster — splits into parallel tracks, verifier
  judges each deliverable, you decide accept/retry. Use when the task has genuine parallel value
  (3+ independent tracks), needs independent verification, spans multiple sources/tools, or has
  high error cost. (2) Routing for "build me a team for X" / "add an agent for Y" / "组个团队搞 Z" /
  "拉一个 verifier 帮忙审 W" — if the existing roster can't cover the task, this skill decides
  whether to create new agents (with user consent for implicit needs, direct creation for
  explicit asks) and calls `create-agent` to do the writing. Per-domain deep dives live in
  references/software-engineering.md (code changes) and references/deep-research.md (multi-source
  investigation). Skip for single-step low-complexity tasks you can finish yourself.
---

# Mavis Team

Your entry point for two things that actually go together:

1. **Run a parallel plan** with the existing agents (`developer` / `tester` / `code-reviewer` / your project's experts), verifier judges each deliverable.
2. **Decide whether to create new agents** if the roster is missing what you need — call `create-agent` to do the writing.

## Triggers

Run a plan when ANY:
- Genuine parallel value (3+ independent tracks).
- Adversarial verification matters (security / data-flow / permission code, factual claims, calculations, external delivery).
- Multi-stage delivery chain (research → analyze → write).
- User said "team" / "组个团队" / "build me an agent" / explicitly named you.

First-class scenarios — MUST read the reference BEFORE writing the plan:
- **Software engineering** (cross-component code, refactor / migration, gated delivery) → `references/software-engineering.md`
- **Deep research** (multi-source, 3+ angles, formal synthesis) → `references/deep-research.md`

## Step 1 · Get ready

Five questions — answer in your head from current context. If any is unclear, do a tiny preflight (read a file, check a schema, query a system) yourself before writing the plan. This is NOT a team task.

1. What is the real objective and concrete deliverable?
2. Why does this need a team instead of you doing it directly?
3. What are the natural, non-overlapping work packages?
4. Which sources / tools / agents does each package need?
5. What should the verifier independently re-derive (not re-read producer's work)?

## Step 2 · Pick agents — or create the ones you need

Check `<agent-context>` first (it may carry `availableAgents` and active peer sessions). Otherwise:

```bash
mavis agent list --project "$PWD"     # available agents
mavis communication peers              # active peer sessions
```

If the existing roster fits:
- Prefer a project-specific agent over a generic one with the same role.
- Use `general` for one-off work when no specialist exists.
- Use the **exact agent name** from output, not a display name.
- Multiple tasks can share the same agent (engine spawns separate sessions).

### If no existing agent fits

Two paths — pick by **how the user phrased the request**:

**Implicit need** (user gave a task, you discovered mid-planning the roster is missing a role).

Creating an agent is sticky — registry space, routing weight, awkward to clean up. A plan is throwaway. So **stop and ask**:

1. Pause planning.
2. Report: which task is blocked, which existing agent comes closest, the 1–2 new agents you'd recommend (each: `name`, one-line `description`, scope, stop condition).
3. Wait for explicit user OK. Do NOT call `create-agent` until they say yes.
4. After consent → load `create-agent` and follow it for each new agent.
5. Resume planning with the new names in `assigned_to`.

**Explicit ask** (user said "build me a team for X" / "add an agent for Y" / "组个团队搞 X").

Consent already given. But still review names before writing files:

1. Draft the agent list (each: `name`, one-line `description`, scope, stop condition).
2. Show the list to the user — names + descriptions only — and ask for any edits.
3. Once names are settled → load `create-agent` for each one.
4. Continue with the plan that uses them.

### Team-design checklist (when proposing new agents)

| Choice | Default |
|---|---|
| Total team size | 3–7 max. Beyond → overlap and routing confusion. |
| Coding project always has | `developer` + `tester`. Add `code-reviewer` for high quality bar. |
| Domain specialists | 1–4, named by **responsibility** (`payments-expert`, `db-expert`), NEVER by seniority (`senior-dev`). |
| Stop condition style | Concrete + measurable ("tests pass, MR opened"), NEVER vibe ("user is happy"). |
| Don't | Add a "PM" rein (orchestrator already coordinates) · Clone roles (`developer-1`/`-2`) · Pad "in case" |

## Step 3 · Write the plan

`plan.name` and task `title` are shown to the user — write them in the user's language (e.g. Chinese for Chinese-speaking users).

Software engineering plan examples → `references/software-engineering.md`. Deep research → `references/deep-research.md`. General example:

```yaml
version: 1
plan:
  name: 'quarterly operations review package'
  max_concurrency: 10
  max_consecutive_failures: 2
  max_cycles: 10
tasks:
  - id: data-collection
    title: 'collect metrics from multiple sources'
    prompt: '<extract KPIs from spreadsheets, pull meeting summaries from Lark, gather project status>'
    assigned_to: general
    verified_by: verifier
    verify_prompt: '<verify numbers match source documents, no stale data>'
    timeout_ms: 1800000
  - id: analysis
    title: 'analyze trends and anomalies'
    prompt: '<compare metrics QoQ, identify changes, correlate across sources>'
    assigned_to: general
    depends_on: [data-collection]
    verified_by: verifier
    verify_prompt: '<verify calculations, check trend claims match the underlying data>'
    timeout_ms: 1800000
  - id: deliverable
    title: 'produce final review deck and summary'
    prompt: '<create executive summary doc and supporting deck>'
    assigned_to: general
    depends_on: [data-collection, analysis]
    verified_by: verifier
    verify_prompt: '<verify all charts match source data, recommendations supported by analysis>'
    timeout_ms: 1800000
```

### Field cheatsheet (only the ones you actually need)

| Field | When |
|---|---|
| `depends_on` | Task truly needs another's output. Don't add ceremony. |
| `timeout_ms` | Large tasks: 25–30 min (10+ files / 300+ lines). Hard cap 30 min. |
| `max_retries` | Risky/flaky task. |
| `auto_reject_retries` (plan) | How many verifier FAILs the engine auto-retries (same session, verifier feedback injected) before escalating to you. Default 1. |
| `verified_by` | Single agent, or array of distinct verifier agents (e.g. code-review + runtime-test). All must PASS. |
| `verify_prompt` | String for one verifier; map keyed by verifier agent name when responsibilities differ. Don't list the same verifier twice. |
| `output` / `gates` | Explicit file expectations or objective command checks. |

### Task rules

- One task = one verifiable deliverable. Split by **deliverable boundary**, not by keystroke.
- Every task needs `assigned_to` AND `verified_by`.
- Workers must NOT wait for CI / code review / merge / sleep loops — those are owner work.

### Anti-pattern: over-sharding

If the work fits in one worker's scope, don't artificially split it. Wastes session setup, makes the plan harder to track. Ritual splits ("first research, then implement" when you already know what to implement) are the same trap.

## When the verifier must re-derive (not rubber-stamp)

The team's value isn't parallelism — it's **independent verification**. The verifier must independently re-derive, not re-read the producer's work.

Force re-derive — write `verify_prompt` to make the verifier re-run commands, go back to original sources, or apply adversarial reasoning — when ANY applies:

- Code changes behavior, data flow, permissions, or security boundaries
- Deliverable contains external facts, numbers, dates, quotes, or citations
- Calculations / formulas / financial or statistical models
- Legal / regulatory / policy interpretations
- Business recommendations, risk assessments, strategic conclusions
- Material will be sent externally (users / customers / partners / executives / regulators)
- Multiple sources synthesized — contradictions may exist
- Cross-tool execution had side effects (wrote to systems, sent messages, updated records)

Bad `verify_prompt`: `Check the deliverable.`
Good `verify_prompt`: `Re-run the validator unit test on the staged change. Independently confirm fail-fast behavior on malformed plan-schema.ts. Do not re-read producer's diff.`

## Step 4 · Write good prompts

Each `prompt` and `verify_prompt` is a self-contained spec — a fresh session must be able to act on it. Retry context and file paths are auto-injected.

Bad: `Based on your findings, implement the fix.`
Good: `Update src/validators/plan-schema.ts so tasks with verified_by also require a non-empty verify_prompt. Add validation + unit test. Report the commit hash.`

When a task maps to a known skill, name it: `use the <skill-name> skill to ...`. Pick the skill at plan time — you have more context than the worker. Verify the name exists in `<available_skills>`; a typo gives "skill not found".

Don't name a skill that waits on CI / review / human reply — that's owner work.

## Step 5 · Launch

```bash
mavis team plan run $WORKSPACE/.mavis/plans/plan.yaml
```

Blocks until plan leaves `pending` and prints status. Use `--no-wait` for fire-and-forget.

## Step 6 · Watch and intervene

Heartbeat is every 5 minutes. For faster inspection:

```bash
mavis session messages <session_id> --limit 3
```

| Signal | Action |
|---|---|
| Worker polling CI/CR | Send: `Stop polling. Write deliverable.md and exit.` |
| Worker progressing but near timeout | `mavis team plan extend-timeout <plan_id> <task_id> --minutes 15` (≤60 min/request, only `producing` status) |
| Worker stuck >5 min | Hint, extend, or pause |
| Direction is wrong NOW | `mavis team plan steer <plan_id> --message "<correction>"` |
| Dependency graph wrong (depends_on should be parallel) | `mavis team plan unblock <plan_id> <task_id>` (only `blocked` status; doesn't modify plan.yaml) |
| Plan beyond salvage | `mavis team plan cancel <plan_id>` and take over |

`pause` / `resume` exist for manual debugging — not the normal path.

## Step 7 · Submit a decision

```bash
mavis team plan decision <plan_id> --file decision.json
```

```json
{
  "last_cycle": [
    { "task_id": "task-1", "verdict": "manual_retry", "reason": "Fix the schema edge case the verifier found." }
  ],
  "next_cycle": [
    {
      "task_id": "task-1",
      "title": "fix schema edge case",
      "prompt": "Update the validator so ...",
      "assigned_to": "<agent-name>",
      "verified_by": "verifier",
      "verify_prompt": "Re-run the validator unit test ...",
      "timeout_ms": 1800000
    }
  ],
  "plan_complete": false,
  "message_to_user": "Round 2: retrying with tighter scope."
}
```

Verdicts:
- `accept` — done.
- `reject` — retry because the task failed review.
- `override_accept` — accept anyway because the verifier is wrong.
- `manual_retry` — retry with your explicit correction in `reason`.

### Pick the verdict (and decide same-session vs new-session)

| Scenario | Verdict | Same session retry? |
|---|---|---|
| Minor fix (changelog, formatting, naming) | `reject` original task_id | ✓ Yes — keeps worktree, code context, history |
| Right direction, wrong implementation | `manual_retry` original task_id (correction in `reason`) | ✓ Yes — correction injected |
| Fundamentally wrong approach | `reject` + new task_id in `next_cycle` | ✗ New session, fresh start |
| Independent follow-up | New task_id in `next_cycle` only | ✗ New session, separate deliverable |

Same task_id retries reuse the existing session — worker keeps worktree + context. New task_id = cold start (3–5 min wasted on setup). Don't burn it on a "missing changelog" fix.

**Never mix retry + new task in one decision.** Engine runs the retry first, the new task waits, the retried worker may redo finished work. Either retry only, OR accept and put remaining work in a new task next round.

## Recovery rules

| Situation | Action |
|---|---|
| Worker killed by timeout | Check for `deliverable.md` / branch push / MR first. Timeout ≠ failure. If real, take over; else split or raise `timeout_ms` (≤30 min cap). |
| Worker polling CI/CR | Tell it to stop and exit after writing `deliverable.md`. |
| Agent not found | Re-check exact names from `<peers_update>` or `mavis agent list --project "$PWD"`. |
| Direction wrong mid-cycle | `steer`, don't open detached side sessions. |

## Worker vs owner scope

| Responsibility | Owner |
|---|---|
| Code, test, push, create MR, write `deliverable.md` | **Worker** |
| Research, analyze, draft, write `deliverable.md` | **Worker** |
| Wait for CI / CR, merge MR, clean up worktree | **You (owner)** |
| Any sleep / polling waiting for external systems | **Forbidden in worker prompts** |

Workers have a 30-minute hard cap. Design prompts to produce and exit.

## Mid-plan scope changes

| Situation | Action |
|---|---|
| Current work is now wrong | `steer` immediately to abort + redirect. |
| Current work is fine, next steps need to change | Wait for CycleReport, adjust `next_cycle` in your decision. |
| Both | `steer` to fix running work, then update `next_cycle`. |

Only create a separate plan if the user explicitly says "this is out of scope".

## Quick reference

| Command | Purpose |
|---|---|
| `mavis team plan run <yaml>` | Launch a new plan |
| `mavis team plan status <plan_id>` | Inspect current state |
| `mavis team plan steer <plan_id> --message <text>` | Redirect running work |
| `mavis team plan unblock <plan_id> <task_id>` | Force `blocked` task → `ready` |
| `mavis team plan extend-timeout <plan_id> <task_id> --minutes <n>` | Add runtime to active producer |
| `mavis team plan decision <plan_id> --file <path>` | Submit next-cycle decision |
| `mavis team plan cancel <plan_id>` | Stop the plan |
