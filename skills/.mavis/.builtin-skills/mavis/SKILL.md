---
name: mavis
description: "Mavis runtime entry point. Use this skill for any task about Mavis itself. Trigger when: user asks how to configure or use Mavis, list/inspect/create/update agents, inter-session messaging (use `mavis communication`, not `mavis session`; `finished` means idle/routable, not closed), rotate a session, choose between user/agent/project memory (session memory is removed), schedule a self-reminder while waiting on CI/jobs/batch/human reply, manage hooks (inspect/create/test/delete), control how Feishu or Telegram routes to agents, install or inspect skills, or hot-edit a built-in skill. Also trigger on keywords: mavis agent, mavis session, mavis memory, mavis cron, mavis hook, mavis im, mavis skill, rotate session, report back to parent, set a reminder, wait for CI. Sub-references to read for each subproblem: user-guide, agent, session-and-communication, memory, cron, hook, im, skill-management, skill-evolution."
---

# Mavis

Mavis is Mavis itself: the agent runtime, coordination layer, and operating surface behind agents,
sessions, memory, scheduled work, inbound chat routing, and skill maintenance. This skill is the
entry point for operating that system.

## Capability Map

| Area | What it covers | Read when you need |
| --- | --- | --- |
| `user-guide` | User-facing Mavis usage / configuration questions, daemon basics, config entry points, delegation map | answer “怎么配置 Mavis / Mavis 支持什么 / xxx 怎么用” |
| `agent` | Agent inventory, config, identity, logs, status, visible skills | inspect or update an agent; discover what an agent can use |
| `session-and-communication` | Session lifecycle, message history, main-session rotation, inter-session messaging, peer discovery, report-back patterns | inspect sessions; send results to parent/main; track delegated work |
| `memory` | User / agent / project memory, topic files, cleanup model, what belongs where; session memory is removed | write memory correctly; read or structure long-term memory |
| `cron` | Scheduled tasks, self-reminders, active-hours gating, IM delivery, polling slow operations | wait for CI/jobs/human replies without blocking; run recurring checks |
| `hook` | Hook registry inspection, creation, update, deletion, dry-run testing, event payloads, gating semantics | inspect or modify Mavis hooks; test tool/session gates; explain where hook files live |
| `im` | Feishu / Telegram bridge status, route rules, defaults, session strategy selection | control how inbound chats map to agents and sessions |
| `skill-management` | Skill inventory, visibility, installation, file-level create/update/delete/copy, source/runtime locations | list, inspect, install, or manage skill files |
| `skill-evolution` | Built-in skill editing rules, attribution, conservative patching, diff checklist, push-failure handling | update a built-in Mavis skill from runtime signals |

## Read Map

- Need user-facing “怎么用 / 怎么配置 Mavis” questions, daemon basics, or delegation to a more specialized skill -> `references/user-guide.md`
- Need agent inspection, status, logs, identity, or skill discovery -> `references/agent.md`
- Need session lifecycle, inter-session messaging, parent report-back, or peer discovery -> `references/session-and-communication.md`
- Need to decide whether something belongs in session / agent / user memory -> `references/memory.md`
- Need recurring checks, delayed follow-up, or a self-reminder for async work -> `references/cron.md`
- Need hook registry CLI commands, hook file shape, event payloads, matchers, or dry-run testing -> `references/hook.md`
- Need to route Feishu or Telegram inbound traffic to the right agent/session strategy -> `references/im.md`
- Need to list, inspect, install, create/update/delete/copy skill files -> `references/skill-management.md`
- Need to edit a built-in skill from evolution signals without bloating or damaging it -> `references/skill-evolution.md`

## Minimal Examples

```bash
# Inspect an agent and its visible skills
mavis agent info mavis
mavis skill list mavis

# Report back to your parent session after delegated work
mavis communication send --to "$PARENT_SESSION_ID" --command prompt --content "Task complete. Summary: ..."

# Schedule a polling task while waiting on CI (sessionId mode — stays in current session)
mavis cron create "$agentName" check-ci \
  --schedule "*/5 * * * *" \
  --session-mode sessionId --session-id "$CURRENT_SESSION_ID" \
  --prompt "Check CI. If done, report and delete this cron."

# Schedule a user-requested reminder (new mode — default, no session context needed)
mavis cron create "$agentName" morning-alarm \
  --schedule "0 8 * * *" --timezone "Asia/Shanghai" \
  --prompt "Good morning! Time to start the day."

# Inspect and dry-run hook behavior
mavis hook list --agent mavis --human
mavis hook test mavis:tool-guard \
  --input '{"agentName":"mavis","sessionId":"ses_123","toolName":"bash","toolArgs":{"command":"git status"}}' \
  --output '{"toolArgs":{"command":"git status"},"metadata":{}}'

# Store reusable knowledge in agent memory (session memory / --session is removed)
mavis memory append "$agentName" --content '### <topic> (<date>)
<lesson>
WHY: <why this matters later>'
```

## Rule

Do not treat Mavis as an external business system. If the task is about operating or using Mavis
itself, start here, then read only the reference doc matching the current subproblem.

Do not create a second routing skill for Mavis usage/configuration questions. Add or adjust a
`mavis` reference instead, so this skill remains the single routing entry point for Mavis itself.
