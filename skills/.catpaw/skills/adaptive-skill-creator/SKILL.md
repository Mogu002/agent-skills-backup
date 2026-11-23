---
name: adaptive-skill-creator
description: Use when creating, updating, or organizing local reusable SKILL.md based skills for multiple agents, IDEs, and Codex-like tools on this machine. Helps design concise skill instructions, shared project structure, metadata, validation checks, and installation handoff paths.
metadata:
  short-description: Create shared local skills for agents and IDEs
---

# Adaptive Skill Creator

Use this skill to create or update local skills that should work across multiple agent or IDE tools.

## Workflow

1. Identify the intended users, trigger phrases, and tools that should consume the skill.
2. Create a minimal skill directory:

```text
skill-name/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
├── scripts/
└── assets/
```

3. Keep `SKILL.md` concise:
   - Frontmatter must include `name` and `description`.
   - The description should say when the skill should be used.
   - Put only essential workflow instructions in the body.
   - Move long examples, API details, templates, and schemas into `references/`, `scripts/`, or `assets/`.

4. Prefer shared local paths for source skills:

```text
~/.catpaw/skills/<skill-name>/
```

5. For Codex availability, copy or install the finished skill into:

```text
~/.codex/skills/<skill-name>/
```

Tell the user to restart Codex after installing or updating a skill that Codex should discover.

## Validation

Before calling a skill ready:

- Confirm `SKILL.md` exists and has valid YAML frontmatter.
- Confirm the directory name and frontmatter `name` match.
- Confirm `description` contains clear trigger conditions.
- Confirm `agents/openai.yaml`, if present, matches the skill purpose.
- Avoid extra docs such as README, changelog, or installation guides unless the user explicitly asks for them.
