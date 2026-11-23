---
name: spec-driven-development
description: 当用户想把粗略产品想法、功能请求、工程需求或重构目标推进为 requirements.md、design.md、tasks.md，并希望 agent/LLM 通过需求审批、架构设计、正确性属性、测试策略和可执行编码任务来驱动实现时，使用这个技能。NOT for 只需要临时回答、一次性代码片段或不需要沉淀 spec 文档的场景。
---

# Spec-Driven Development

Use this skill to turn an ambiguous request into an approved, testable, implementation-ready spec, then execute the resulting coding tasks only after the user approves the task plan.

## Default Path

Work in three gated stages:

1. Create or update `requirements.md`.
2. After explicit user approval, create or update `design.md`.
3. After explicit user approval, create or update `tasks.md`, ask how to handle optional tests, then begin coding only after approval.

Do not skip a stage. Do not enter the next stage based on implied approval, silence, or a vague positive response. Approval must be explicit, such as "approved", "approve", "同意", "批准", "可以进入下一阶段", or an equivalent unambiguous instruction.

## Stage 1: Requirements

Goal: turn the user's rough idea into structured, verifiable requirements.

Create `requirements.md` with exactly these top-level sections:

1. `Introduction`
2. `Glossary`
3. `Requirements`

Each requirement must include:

- A stable requirement ID, such as `REQ-001`.
- One `User Story`.
- One or more `Acceptance Criteria`.

Use this requirement shape:

```markdown
### REQ-001: Short Requirement Name

**User Story:** As a <role>, I want <capability>, so that <benefit>.

**Acceptance Criteria:**

1. WHEN <trigger>, THE <System> SHALL <response>.
2. IF <unwanted condition>, THEN THE <System> SHALL <response>.
```

### EARS Rules

Every acceptance criterion must use exactly one of these EARS patterns:

- Ubiquitous: `THE <System> SHALL <response>.`
- Event-driven: `WHEN <trigger>, THE <System> SHALL <response>.`
- State-driven: `WHILE <state>, THE <System> SHALL <response>.`
- Unwanted event: `IF <unwanted condition>, THEN THE <System> SHALL <response>.`
- Optional feature: `WHERE <feature is included>, THE <System> SHALL <response>.`
- Complex: `WHEN <trigger>, WHILE <state>, THE <System> SHALL <response>.` or `WHEN <trigger>, WHERE <feature is included>, THE <System> SHALL <response>.`

Keep each acceptance criterion as one testable sentence. Use `SHALL` only for required behavior.

### INCOSE Quality Rules

Before asking for approval, revise every requirement so that it is:

- Clear and precise: use active voice, explicit actors, explicit objects, and no ambiguous adjectives.
- Testable: include explicit conditions, observable outputs, and measurable thresholds when thresholds matter.
- Complete: avoid escape clauses such as "as appropriate", "if possible", "etc.", "TBD", or "and so on".
- Bounded: avoid unbounded absolute words such as "all", "every", "never", or "always" unless the scope is explicitly bounded and testable.
- Positive: state what the system shall do, not only what the system shall not do.
- Pronoun-free: replace pronouns such as "it", "they", "this", and "that" with concrete nouns.

If the system includes a parser, serializer, importer, exporter, encoder, decoder, compiler, formatter, or schema converter, explicitly add round-trip requirements. A round-trip criterion must state the input domain, transformation path, equivalence rule, and allowed lossiness.

At the end of Stage 1, ask the user to approve `requirements.md`. Do not create `design.md` until approval is explicit.

## Stage 2: Design

Goal: produce an architecture and correctness plan based only on the approved requirements.

Create `design.md` with exactly these top-level sections:

1. `Overview`
2. `Architecture`
3. `Components and Interfaces`
4. `Data Models`
5. `Correctness Properties`
6. `Error Handling`
7. `Testing Strategy`

Use Mermaid diagrams when they clarify architecture, control flow, state transitions, or data flow.

### Design Sequence

Follow this order:

1. Draft `Overview`, `Architecture`, `Components and Interfaces`, and `Data Models`.
2. Review every acceptance criterion from `requirements.md`.
3. Classify each acceptance criterion as `property`, `example`, `not-testable`, or `boundary`.
4. Perform property reflection: deduplicate overlapping properties, merge logically equivalent properties, and remove redundant assertions.
5. Convert every testable criterion into one or more universally quantified correctness properties.
6. Finish `Error Handling` and `Testing Strategy`.

### Correctness Properties

Each property must:

- Have a stable property ID, such as `PROP-001`.
- Use universal quantification, such as `For all...` or `For any...`.
- Trace back to specific requirement IDs and acceptance criterion numbers.
- State the input domain, preconditions, operation, and expected invariant or relation.
- Be testable by a property-based, model-based, metamorphic, or randomized test when practical.

Prefer these property patterns when they fit:

- Invariants: preserved state or relationships.
- Round Trip: parse-serialize-parse, encode-decode, import-export, or format-read equivalence.
- Idempotence: repeated operation produces the same externally visible result.
- Metamorphic: related inputs produce predictably related outputs.
- Model-based: implementation behavior matches a simpler reference model.
- Confluence: different valid operation orders converge to the same result.
- Error conditions: invalid inputs produce bounded, specified failures without corrupting state.

Use this property shape:

```markdown
#### PROP-001: Property Name

- **Statement:** For all <input domain>, when <operation> is applied under <preconditions>, <expected relation> holds.
- **Traces:** REQ-001 AC-1, REQ-002 AC-3
- **Test Method:** property-based | model-based | metamorphic | randomized
```

### Testing Strategy

Plan both example-based tests and property-based tests:

- Unit tests must cover concrete examples, edge cases, and representative failure paths.
- Property tests must cover universal properties, randomized inputs, generators, shrinking strategy when applicable, and boundary domains.
- Every requirement must be covered by at least one planned test or explicitly marked as not directly testable with a rationale.

At the end of Stage 2, ask the user to approve `design.md`. Do not create `tasks.md` until approval is explicit.

## Stage 3: Tasks

Goal: turn the approved design into an executable coding task list for an AI coding agent.

Before creating `tasks.md`, check whether `design.md` uses pseudocode without a concrete programming language. If the implementation language is not explicit, ask the user to choose a programming language before writing tasks.

Create `tasks.md` with exactly these top-level sections:

1. `Overview`
2. `Tasks`

Tasks must use checkbox format and at most two hierarchy levels: epic to sub-task.

Each task must:

- Be a concrete coding action, such as writing code, editing a file, adding a test, or changing a schema.
- Reference specific requirement IDs.
- Build incrementally on earlier tasks.
- Avoid orphan code that is unused by later tasks.
- Exclude deployment, manual user testing, release management, documentation-only work, stakeholder review, and non-coding process tasks.

Testing tasks must:

- Appear immediately after the related implementation task.
- Mark optional testing sub-tasks with `*`.
- For property tests, reference both property IDs from `design.md` and requirement IDs from `requirements.md`.
- Insert checkpoint tasks at reasonable intervals: `- [ ] Ensure all tests pass.`

Use this task shape:

```markdown
## Tasks

- [ ] 1. Implement <capability> foundation. [REQ-001, REQ-002]
  - [ ] 1.1 Add <file/module/function> for <specific behavior>. [REQ-001]
  - [ ] 1.2 Add unit tests for <examples and boundaries>. [REQ-001]
  - [ ] * 1.3 Add property tests for <property>. [PROP-001; REQ-001]
- [ ] 2. Ensure all tests pass.
```

At the end of Stage 3, ask the user whether optional testing tasks should remain optional for a fast MVP or become mandatory for comprehensive testing. After the user explicitly approves the task list and testing mode, begin coding execution automatically.

## Approval and Revision Loop

After creating or modifying any stage document:

1. Summarize the material changes.
2. Ask for explicit approval.
3. If the user requests changes, update the current stage document only.
4. Repeat the approval request.
5. Proceed to the next stage only after explicit approval.

If the user tries to jump ahead, briefly explain the blocked gate and ask for approval of the current stage.

## Quality Checklist

Before presenting each stage document:

- Requirement IDs, acceptance criteria, property IDs, and task references are stable and traceable.
- No acceptance criterion violates EARS syntax.
- No requirement uses ambiguous pronouns, escape clauses, or unbounded absolutes.
- Parser or serializer work includes round-trip requirements and round-trip properties.
- Design properties trace to requirements and avoid logical duplicates.
- Testing strategy includes both example-based and property-based testing.
- Tasks are coding-only, incremental, and cover every approved requirement.
- Approval is requested before moving forward.
