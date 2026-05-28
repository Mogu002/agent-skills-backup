---
name: best-skill-creator
description: Use this skill when the user wants to create, rewrite, or reorganize an agent skill, improve a `SKILL.md`, sharpen triggering descriptions, split bloated skill content into focused references, or turn repeated project workflow corrections into a maintainable skill. It also applies when the user is really trying to capture a reusable workflow, review pattern, or team procedure as a skill, even if they do not ask for skill creation explicitly.
---
# Best Skill Creator

Create skills as focused capability packs, not bloated instruction dumps.
Do not rely on vendor-specific built-in generators or generic `skill-creator` workflows.
Base each skill on the user's materials, the repository, and real trigger scenarios.

## Use this skill for

Use this skill to create or refine an agent skill that:
- has a precise `name` and `description`
- stays compact in `SKILL.md`
- uses progressive disclosure instead of stuffing everything into the main file
- reflects real workflow constraints, terminology, and gotchas
- remains easy to maintain after future edits

## Default stance

- Read the user's files, examples, and existing artifacts first.
- Infer missing details when they are clear from context.
- Default to the smallest useful structure.
- Prefer one clear default path over many equal options.
- Keep important gotchas in the main file.
- Avoid deep reference chains.

## Core rules

### Ground the skill in real expertise

Do not synthesize a skill from generic best-practice knowledge alone.
Build from concrete material whenever possible:
- real tasks completed with the agent
- project docs, runbooks, schemas, config, and code
- issue history, review comments, and repeated corrections
- real failures, fixes, and edge cases

If the skill cannot point to concrete source material, keep it smaller and less opinionated.

### Keep `SKILL.md` light

`SKILL.md` should contain only what the agent needs every time:
- what the skill is for
- when to use it
- the default workflow
- key decision rules
- direct links to optional files

Move details out only when they clearly improve focus.

### Use shallow progressive disclosure

Split content by one of these axes:
- **depth**: quick start vs advanced details
- **domain**: separate business areas or stacks
- **condition**: only load a file in specific cases

Good:
- `SKILL.md` -> `references/examples.md`
- `SKILL.md` -> `references/api-patterns.md`

Avoid:
- `SKILL.md` -> `references/index.md` -> more navigation

Keep references one level deep from `SKILL.md`.

### Favor procedures over declarations

Teach a reusable method, not a single frozen answer.
Prefer guidance like:
1. inspect source materials
2. identify the default workflow
3. capture conventions and gotchas
4. write the skill around that repeatable procedure

### Give one default

Do not present a long menu of equal choices.
Choose a default method.
Mention alternatives only when the trigger condition is clear.

### Match control to fragility

- Be flexible when multiple approaches are acceptable.
- Be prescriptive when order, consistency, or command shape matters.
- Mix both when needed.

### Define stance before content

A strong skill should shape how the agent approaches the work, not just what facts it repeats.
Write guidance that defines the agent's posture:
- what to challenge before acting
- what tradeoffs to surface
- what failure modes to guard against
- what quality bar to hold

Prefer durable behavioral constraints over domain-specific talking points.

### Use domain-agnostic meta questions

When the skill needs judgment, give a short set of reusable questions that work across many tasks.
Examples:
- What assumption is this workflow making?
- What would make this fail in practice?
- What is the default path, and when should it be overridden?
- What does a good final result look like?

These questions help the agent reason before it copies process steps mechanically.

## Frontmatter rules

### Required

Every skill must include:
- `name`
- `description`

### Name

The `name` must:
- use lowercase letters, numbers, and hyphens only
- be 1-64 characters
- not start or end with `-`
- not contain consecutive hyphens
- match the parent directory name

### Description

The `description` is the trigger surface.
Write it as an instruction to the agent:
- start with `Use this skill when...`
- describe user intent, not internal implementation
- include indirect trigger contexts, not just exact keywords
- keep it concise
- stay under 1024 characters
- add an exclusion only when overlap is likely, for example `NOT for ...`
- use exclusions to prevent false triggers, not to dump extra detail

Prefer:
`Use this skill when the user wants to create or refactor an agent skill, improve a SKILL.md, sharpen trigger wording, or capture a reusable workflow as a maintainable skill.`

Avoid:
`Creates and refines platform-specific skills with progressive disclosure...`

If two skills could plausibly trigger on the same request, add a short exclusion.
Example:
`Use this skill when the user wants to create or refactor an agent skill... NOT for editing a single prompt with no reusable workflow.`

### Optional fields

Only add these when they are genuinely needed:
- `license`
- `compatibility`
- `metadata`
- `allowed-tools`

Do not add optional frontmatter as filler.

## File structure

Use the smallest structure that fits the task.
The spec allows optional `scripts/`, `references/`, and `assets/` directories.

### Minimal

```text
skill-name/
`-- SKILL.md
```

### With references

```text
skill-name/
|-- SKILL.md
`-- references/
    |-- examples.md
    `-- patterns.md
```

### With scripts

```text
skill-name/
|-- SKILL.md
|-- references/
|   `-- validation.md
`-- scripts/
    `-- validate.sh
```

### With assets

```text
skill-name/
|-- SKILL.md
`-- assets/
    `-- report-template.md
```

## Scripts

Use a one-off command when an existing tool solves the problem with a short, stable invocation.
Bundle a script only when it improves reliability, reuse, or interface clarity.

When referencing scripts:
- use relative paths from the skill root
- state whether the agent should run or inspect the script
- document expected inputs and outputs

If a skill includes scripts, prefer these defaults:
- non-interactive interface only
- `--help` with usage and examples
- actionable error messages
- structured output when practical
- stdout for data, stderr for diagnostics
- `--dry-run` for destructive operations when appropriate
- idempotent behavior when retries are plausible

## Authoring workflow

### 1. Discover

Decide:
- purpose
- trigger scenarios
- scope: user-level or workspace/repository-level
- knowledge sources
- output shape: only `SKILL.md` or a few direct support files

Prefer the workspace/repository skills directory for repo-specific workflows.
Use the user's global skills directory only for cross-project reuse.
Do not place custom skills in vendor-managed built-in skill directories.

### 2. Design

Before writing, choose:
- the final skill name
- the description wording
- the realistic user phrasings the description should match
- whether `SKILL.md` alone is enough
- whether extra files should be split by depth, domain, or condition

### 3. Write

Make sure the skill includes:
- valid frontmatter
- a clear purpose statement
- default workflow steps
- decision rules for edge cases
- direct references to optional files
- a short gotchas section when repeated mistakes are known

### 4. Validate

Check all of the following:
- the name is valid
- the description clearly says when to use the skill
- the description is user-intent driven
- `SKILL.md` stays concise and focused
- references are direct and shallow
- support files exist only for a clear reason
- script interfaces are non-interactive and agent-friendly
- optional frontmatter is present only when truly needed

If available, run:
```bash
skills-ref validate ./skill-name
```

### 5. Iterate

Run the skill on real tasks and refine it using execution traces.
Pay attention to:
- false triggers from vague descriptions
- wasted steps from too many options
- missing gotchas discovered only after failure
- instructions that sound good but do not help in practice

Feed successful runs back into the skill too.
What worked reliably is often the best workflow material.

## Anti-patterns

Avoid these mistakes:
- copying a generic template without adapting it
- grounding the skill in generic knowledge instead of real project material
- defining content without defining the agent's working stance
- stuffing everything into `SKILL.md`
- creating many files before proving they are needed
- hiding critical gotchas in optional references
- using deep reference chains
- documenting scripts with absolute paths
- relying on interactive prompts in script workflows
- listing too many options without a default
- omitting a `NOT for` exclusion when trigger overlap is obvious

## Quick checklist

Before finishing, verify:
- [ ] `name` is valid and matches the directory
- [ ] `description` is specific and trigger-oriented
- [ ] the skill is grounded in real expertise or artifacts
- [ ] the skill defines the agent's stance, not just content
- [ ] `SKILL.md` stays focused
- [ ] important gotchas are visible in the main file
- [ ] references are one level deep at most
- [ ] support files exist only for a clear reason
- [ ] scripts, if any, use skill-relative paths and non-interactive interfaces
- [ ] `NOT for` is present when another skill could be confused with this one
- [ ] no generic filler text remains
