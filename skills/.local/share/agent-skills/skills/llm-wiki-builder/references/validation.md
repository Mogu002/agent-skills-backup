# Validation

Use this reference to close the loop after wiring or migration work.

## Minimum Checks

1. Run the runtime entry in status mode:

```bash
bash tools/llm-wiki-entry.sh status
```

2. Verify the Codex entry can forward CLI arguments:

```bash
bash tools/llm-wiki-entry.sh codex exec --help
```

3. Confirm the vault still has:
   - `AGENTS.md`
   - `index.md`
   - `todo.md`
   - `log.md`
   - `.agents/skills/llm-wiki/SKILL.md`
   - `.agents/skills/llm-wiki-builder/SKILL.md`

4. Confirm a durable note explains the runtime boundary.
5. Confirm another durable note explains how the three entry points should be used.
6. Append a rollout note to `log.md`.

## Dry-Run Expectations

- A user saying "把这个 vault 落实成可实际使用的 LLM wiki" should trigger this builder skill, not the daily `llm-wiki` skill.
- A user saying "把这篇文章入库" should trigger `llm-wiki`, not this builder skill.
- A user saying "检查这个知识库有没有断链" should also go to `llm-wiki`, not this builder skill.
