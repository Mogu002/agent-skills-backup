# Memory

Mavis memory has three durable layers plus task-local artifacts. The core decision is not
"should I save this" but "which scope does this belong to".

## Decision Rule

Pick the narrowest durable scope that still helps future work. Use the same three-question test
that the `<memory-skill-reminder>` system block injects, in this exact order:

1. **Would the conclusion change for a different user?** → **User memory**
   Identity, preferences, communication style, persistent cross-project workflow facts.
2. **Still true on a different project?** → **Agent memory**
   Reusable lessons private to this agent: patterns, gotchas, future-task leverage.
3. **Only true in this repo/project?** → **Project memory**
   `AGENTS.md` / `CLAUDE.md` (every agent, every task) or referenced topic files (on demand).

If none of the above fits — it is **task-local**. Keep it in the current workspace, scratchpad,
plan board, or final report. Do not promote it to durable memory.

Pick exactly one durable layer. Do not duplicate across layers.

Your `agentName` and `sessionId` are available in `<agent-context>`.

## What NOT to Put in Durable Memory

Apply this filter **before** writing. If any of these apply, skip the write or keep it task-local:

- repo structure, file paths, function names, signatures, or architecture notes you can re-read
  from code
- git facts: recent diffs, blame, commit history, who changed what
- debugging recipes or repair steps that belong in code, commit/MR context, or docs
- standing policy already captured in `AGENTS.md` or `CLAUDE.md`
- temporary task state, current branch details, handoff scraps — keep in current task artifacts
  (workspace/scratchpad/plan board/final report)
- raw activity logs, PR lists, or work journals — keep the non-obvious lesson, not the whole stream
- routine status summaries already covered by the daily digest (when enabled)
- **project-level architectural constraints, design patterns, or behavioral rules that apply to all
  agents/developers** — write to project memory (`AGENTS.md` or a referenced topic file), not
  agent memory; agent memory is private to one agent and won't help teammates

If future-you can recover it cheaply from the repo or project tooling, it does **not** belong in
durable memory. When a user asks to save a list, extract the durable bit: the rule, the surprise,
the constraint, or the pointer.

## Layer Commands

### User memory

User identity, preferences, communication style, persistent cross-agent and cross-project facts about the user.

```bash
mavis memory append --user --content '### <topic> (<date>)
Type: <type>
<content>'
```

### Agent memory

Reusable lessons **private to this agent** across sessions. Patterns, gotchas, future-task leverage.

```bash
mavis memory append <agent-name> --content '### <topic> (<date>)
Type: <type>
<content>
WHY: <why this matters later>'
```

Replace `<agent-name>` with your actual `agentName` from `<agent-context>` (e.g. `main`).

### Project memory

Knowledge that **every agent in the current project/workspace** needs. It lives in the repo and is
shared with all agents/developers in this project. Two tiers:

- **`AGENTS.md` / `CLAUDE.md`** — usually the same file (one may symlink to the other). Every
  agent reads it on every task. Put hot rules, mandatory constraints, and architecture decisions here.
- **Topic files** — domain-specific references such as skill guides or docs referenced from
  `AGENTS.md`. Agents read them on demand; reference them from `AGENTS.md` so agents know when to
  read them.

Write directly to the file in the repo. **No CLI command** — edit with Edit/Write, update
`changelogs/`, and commit alongside related code.

Placement rules:

- Mandatory for every task (like "never merge to main directly") → `AGENTS.md`
- Only relevant for a specific domain (like "daemon seal pattern") → topic file, referenced from
  `AGENTS.md`

### Updating Existing Entries

The `append` commands above are for **new** entries only. To **modify, correct, or remove** an
existing entry, edit the memory file directly with Edit/Write:

- User memory → `~/.mavis/memory/user.md`
- Agent memory hot file → `~/.mavis/agents/<agent-name>/memory/MEMORY.md`
- Agent memory topic file → `~/.mavis/agents/<agent-name>/memory/<topic>.md`
- Project memory → `AGENTS.md` / `CLAUDE.md` or referenced topic file in the repo

`append` only adds new lines and does not dedupe. Using it to "update" produces duplicate entries
that only the daily cleanup curator can merge later.

## Choosing Durable Memory: Layer (where) vs Type (what)

The decision rule above answers **where** to write. The Type tag answers **what kind of entry it
is** so cleanup can dedupe and rebalance correctly. The two are **orthogonal** — first pick the
layer, then label the entry with a Type.

For user/agent memory entries, include a `Type:` line as the **first content line under the
`### <topic> (<date>)` header**. It is required for new entries; the cleanup curator relies on it.

```text
### MR notification flow (2026-05-08)
Type: feedback
CI + CR must pass before asking the user to merge...
```

Three Types:

- **user** — how this user thinks and works: role, goals, preferences, workflow, knowledge level
- **feedback** — how Mavis should behave next time. Save both corrections **and** validated
  judgment calls; if you only remember mistakes, you'll become weirdly timid
  - shape: rule → **Why:** → **Apply when:**
- **reference** — where to look outside the repo: docs, dashboards, chats, tickets, boards,
  runbooks

If unsure: "how the agent should act" → **feedback**; "what is going on around the work" →
re-apply the decision rule above to choose agent / project / task-local.

## Topic Files

Agent memory has two storage forms:

- `MEMORY.md`: always injected; use for hot rules, current state, frequently triggered discipline
- `memory/<topic>.md`: on-demand topics with YAML `description`; read when the description matches
  the current task

Commands:

```bash
mavis memory write-topic <agent-name> <kebab-name> --description "When to read this" --content "..."
mavis memory write-topic <agent-name> <kebab-name> --description "..." --file ./topic.md
mavis memory list-topics [agent-name]
mavis memory read-topic <agent-name> <name>
mavis memory delete-topic <agent-name> <name>
```

Placement rules:

- quick status or durable rule -> `MEMORY.md`
- thick domain reference -> topic file
- stale or superseded content -> delete or let cleanup rebalance

Constraints (cleanup curator auto-rebalances; you don't have to count size manually):

- max 10 topic files per agent
- each topic <= 30KB
- `MEMORY.md` soft target <= 15KB, hard limit 20KB
- do not maintain a manual topic index in `MEMORY.md`

If your write would clearly blow past the soft limit, prefer compacting in place or splitting into
a topic file rather than appending more raw lines.

## Cleanup Model

Cleanup is automatic:

- daily at 05:00 UTC+8
- write-hook when `MEMORY.md` crosses the trigger threshold
- manual: `mavis memory cleanup <agent-name>` (`--force` bypasses dedup window)

The curator rebalances `MEMORY.md` and topics, archives prior state under `memory/archive/<date>/`,
and ends. Do not manually curate unless the current task requires it.

## Treat Recalled Memory as a Hint

Memory helps you orient. It does **not** prove what is true right now.

Before leaning on a memory record:

- if it names a file or path, confirm it still exists
- if it names a function, command, flag, or endpoint, search for it first
- if the user asks about "current", "latest", or "recent", prefer code, git, runtime state, and
  current docs over recalled snapshots
- if the user may act on your recommendation, verify first and then recommend
- if memory conflicts with what you see now, trust the current source of truth and update or delete
  the stale memory

`memory says X existed` ≠ `X exists now`. Architecture notes, repo-state snapshots, and daily
digests are time-stamped views, not live facts.

## Daily Digest

The daily-digest pipeline is **optional and disabled by default** for the core memory pipeline.
Enable it via daemon config if you want a timeline/audit view; the source of truth for memory
remains the user/agent/project layers above.

When enabled:

- **Scheduled digest (04:00 UTC+8):** yesterday's sessions, decisions, and learnings written to
  `~/.mavis/agents/{name}/daily/{YYYY-MM-DD}.md`
- **Intra-day updates:** when sessions finish, today's digest is incrementally updated (debounced
  5 min)
- **TTL:** daily digests older than 60 days are automatically moved to `daily/archive/`
- **Manual trigger:** `mavis memory daily-update <agent-name>`
- **Injection:** `<daily_digest>` block in the system prompt — no manual management needed

If daily digest is disabled (the default), do not look for `<daily_digest>` in the prompt and do
not assume it is keeping a record for you. Write durable lessons directly to the right layer.

## Quick Reference

```bash
# Write
mavis memory append --user --content '### <topic> (<date>)\nType: user\n<content>'
mavis memory append <agent-name> --content '### <topic> (<date>)\nType: feedback\n<content>'
mavis memory write-topic <agent-name> <topic-name> --description "..." --content "..."
# To UPDATE an existing entry, edit the memory file directly with Edit/Write — append doesn't dedupe.

# Read
mavis memory show <agent-name>
mavis memory show --user
mavis memory search <keyword> <agent-name>
mavis memory list-topics <agent-name>
mavis memory read-topic <agent-name> <topic-name>

# Maintain
mavis memory cleanup <agent-name>
mavis memory delete-topic <agent-name> <topic-name>
mavis memory daily-update <agent-name>     # only if digest enabled
```

## The Habit

1. **Start of session:** memories are auto-injected. Topics show as descriptions only — read when
   the description matches your task.
2. **During work:** when you learn something, write immediately. Use the three-question test:
   user-first, then agent, then project. If none fits, keep it task-local.
3. **Before reporting completion:** pause. Did you learn anything reusable? Write it now.
4. **Don't curate by hand:** the daily cleanup spawn does it. Focus on writing useful content.
