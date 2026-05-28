# Software Engineering Team Guidance

This reference is loaded when a Team task involves code changes. It provides code-specific
verification strategy, plan patterns, and YAML examples.

## Code preflight

Expands SKILL.md's readiness questions for code. Skip if context is already sufficient.

- **Read key files** — understand structure at a high level, not every line
- **Identify change boundary** — files, interfaces, downstream callers at risk
- **Verify scope** — if it fits in one file under 200 lines, do it yourself
- **Note constraints** — exact paths, naming conventions, invariants for worker prompts

Preflight output:

- **Default (silent)**: bake constraints directly into the implementation task's `prompt` field — no separate doc.
- **Shared design doc**: when 2+ implementation tasks depend on the same API contract / data schema / migration strategy, write `docs/<task>/design.md` and have impl tasks reference it via `depends_on`.

Stop here. Touching code is Team work, not preflight.

## Task splitting for code

Do **not** split codebase exploration from implementation — workers can read code and discover
context themselves. Only split when the deliverables are genuinely independent (e.g. data layer
vs API vs UI in different packages).

## Code-specific verification

Beyond the general verification policy in the main skill, code verifiers must:

- **Run the code** — build, test, lint. Never review by reading the diff alone.
- **Check behavior** — verify the change does what it claims, not just that it compiles.
- **Test edge cases** — empty inputs, concurrent access, error paths, boundary values.
- **Review design** — naming, abstraction boundaries, consistency with existing patterns.
- **Security check** — no exposed secrets, no new injection vectors, proper auth enforcement.
- **Check migrations** — reversibility, data preservation, backward compatibility.

The verifier should NOT:

- Rubber-stamp by re-reading the producer's description
- Only check formatting or style
- Skip running tests because "the code looks right"

## Plan patterns for code

### Pattern: implementation with review + test verification

For large or risky software subtasks, attach separate review and test verifiers to the same
implementation deliverable. This is heavier than a single verifier, so reserve it for migrations,
prompt/agent/skill behavior, API/CLI behavior, persisted data/config, permissions/routing/memory/
cron, or cases where baseline failures need independent attribution.

```yaml
tasks:
  - id: agent-config-prompt-migration
    title: 'migrate agent config prompt loading and datadir compatibility'
    prompt: '<implement the prompt/config migration, compatibility cleanup, tests, docs, and changelog>'
    assigned_to: coder
    verified_by:
      - code-reviewer
      - tester
    verify_prompt:
      code-reviewer: |
        Review the diff for correctness, architecture fit, API/CLI contracts, docs impact,
        backward compatibility, security, and test coverage. PASS only if no blocker/major
        issue remains.
      tester: |
        Independently verify runtime behavior. Do not rely only on the coder's output.
        Run relevant automated tests plus black-box/manual checks. Cover fresh install,
        existing datadir migration, marker/idempotency behavior, API/CLI behavior, and
        baseline failure attribution.
```

`code-reviewer` and `tester` are examples; replace them with exact available agent names. Map keys
in `verify_prompt` must match `verified_by`, or that verifier falls back to the task's `prompt`
field. If only built-in `verifier` is available, use one short split-view prompt instead; it may use
in-process subagents, but must not launch a nested Team plan. Do not split testing into a downstream
task when it verifies the same implementation deliverable.

### Pattern: parallel component tracks + integration gate

When the feature spans independent components (data layer, API, UI), assign each to a separate
worker and add a final integration/e2e task that depends on all of them.

```
[data-layer] --\
[api-layer]  ---+-> [e2e-integration]
[ui-layer]   --/
```

Full example:

```yaml
version: 1
plan:
  name: 'build invoice module from scratch'
  max_concurrency: 10
  max_consecutive_failures: 2
  max_cycles: 20
tasks:
  # -- These three run in parallel (no depends_on) --
  - id: db-models
    title: 'invoice data layer'
    prompt: '<Prisma schema, migration, repository with cursor pagination + optimistic locking, unit tests>'
    assigned_to: coder
    verified_by: verifier
    verify_prompt: '<seed DB, test create -> list -> concurrent update conflict -> soft-delete; check optimistic locking uses version column>'
    timeout_ms: 1800000
  - id: api-routes
    title: 'invoice REST API'
    prompt: '<CRUD endpoints, status transitions via state machine, zod validation, unit tests>'
    assigned_to: coder
    verified_by: verifier
    verify_prompt: '<curl valid + malformed payloads, verify 422/409/pagination; verify state machine pattern, PDF/email are async>'
    timeout_ms: 1800000
  - id: fe-dashboard
    title: 'invoice dashboard UI'
    prompt: '<table with infinite scroll, status filter tabs, line-item form with auto-calc, detail page with timeline, component tests>'
    assigned_to: coder
    verified_by: verifier
    verify_prompt: '<render form, add/remove line items, verify auto-calc; check cursor reset on filter change, integer cents not floats>'
    timeout_ms: 1800000
  # -- Gate: runs after all three tracks --
  - id: e2e
    title: 'invoice end-to-end test'
    prompt: '<e2e test: create via UI -> send -> pay -> verify timeline shows all 3 transitions>'
    assigned_to: verifier
    depends_on: [db-models, api-routes, fe-dashboard]
    verified_by: verifier
    verify_prompt: '<run e2e suite, verify PDF generated with non-zero size; confirm real server, no mocked HTTP>'
    timeout_ms: 1800000
```

### Anti-pattern — over-sharding a single-coder task

The example above is correct because each track touches different packages (data layer / API / UI)
that can be developed independently. But if the work fits in one coder's scope, **do not split
it into artificial sub-tasks**:

```yaml
# BAD -- over-sharded, these are all one coder's job
tasks:
  - id: schema
    title: 'define Prisma schema'
    prompt: '<write the Invoice model>'
    assigned_to: coder
  - id: repo
    title: 'implement repository'
    prompt: '<implement InvoiceRepository>'
    assigned_to: coder
    depends_on: [schema]
  - id: tests
    title: 'write unit tests'
    prompt: '<write tests for the repository>'
    assigned_to: coder
    depends_on: [repo]

# GOOD -- one task, one coder, one deliverable
tasks:
  - id: invoice-data-layer
    title: 'invoice data layer'
    prompt: '<Prisma schema + repository + unit tests, report commit hash>'
    assigned_to: coder
    verified_by: verifier
    verify_prompt: '<run migration, seed, test CRUD + optimistic lock conflict; check schema design and test coverage>'
```

### Pattern: migration + compatibility verifier

For migrations (schema, API, dependency), have one worker do the migration and another
independently verify backward compatibility, data integrity, or rollback safety.

```
[migration-impl] --> [compatibility-check]
```

### Pattern: security-sensitive change + adversarial review

When the change touches auth, permissions, payments, or data access, have the verifier
specifically attempt to break the security boundary.

```
[impl] --> [adversarial-security-review]
```

### Pattern: broad mechanical sweep

For cross-codebase renames, env prefix changes, or API migrations across many files, split
by package/module boundary so workers can proceed in parallel without merge conflicts.

```
[package-A-sweep] --\
[package-B-sweep] ---+-> [verify-no-missed-spots]
[package-C-sweep] --/
```

## Report and documentation deliverables

When a code task includes producing a report (architecture review, audit findings, migration
assessment), reference `references/report.md` in the task prompt for writing principles,
quality signals, and format guidance.
