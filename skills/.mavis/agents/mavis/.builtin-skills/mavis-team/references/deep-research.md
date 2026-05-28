# Deep Research Team Guidance

This reference is loaded when a Team task involves deep research — multi-source investigation,
evidence synthesis, and verified deliverables. It covers source strategy, fact verification,
and plan patterns.

## Research preflight

Expands SKILL.md's readiness questions for research. Skip if context is already sufficient.

- **Pin the unknowns** — turn vague topics into concrete researchable questions
- **Scope 2–4 parallel angles** — independent enough to assign to separate workers
- **Check source availability** — which sources (web, docs, CLI/MCP, databases) apply?
- **Define deliverable shape** — format, depth, audience

Stop here. Comparing sources or writing conclusions is Team work, not preflight.

## Task splitting for research

For high-stakes or multi-source research, keep verified research/synthesis gates before
production deliverables. Don't combine research and production in one task when the research
needs independent verification. For lightweight research that feeds directly into a small
deliverable (e.g. quick lookup then draft an email), combining is fine.

## Source strategy

When writing task prompts, **specify which sources to check** — don't assume the worker will
figure it out. Sources include web, local files, Lark docs/Bitable, chat/email/meeting notes,
CLI/MCP tools, and business systems. Be explicit.

## Research-specific verification

Beyond the general verification policy in the main skill, research verifiers should focus on:

- **Source independence** — go back to original sources, not re-read the producer's summary
- **Currency** — data, prices, features, and regulatory info must be current
- **Attribution** — every factual claim traces to a specific source (URL, doc name, date, section)
- **Cherry-picking** — synthesis must fairly represent full evidence, not just favorable parts
- **Calculations** — re-derive any numbers, percentages, or rankings from source data

## Plan patterns for research

### Pattern: parallel investigation tracks + synthesis gate

The most common research pattern. Each track investigates an independent angle, then a synthesis
task cross-references all findings.

```
[track-A: market analysis]    --\
[track-B: tech evaluation]    ---+-> [synthesis: cross-reference and recommend]
[track-C: regulatory review]  --/
```

Key rules:
- Each track should have its own verifier pass before synthesis
- The synthesis task should explicitly cross-reference, not just concatenate
- The synthesis verifier should check that every conclusion traces to evidence
- When the synthesis task produces a report, follow `references/report.md` for structure,
  citation format, and quality signals

Full example:

```yaml
version: 1
plan:
  name: 'competitive landscape analysis for product X'
  max_concurrency: 10
  max_consecutive_failures: 2
  max_cycles: 10
tasks:
  # -- These run in parallel --
  - id: market-position
    title: 'market positioning and user segments'
    prompt: '<research product X vs top 5 competitors on positioning, pricing, target segments; cite sources>'
    assigned_to: general
    verified_by: verifier
    verify_prompt: '<verify competitor list is current, pricing is from official sources, segments match public data>'
    timeout_ms: 1800000
  - id: tech-capabilities
    title: 'technical capability comparison'
    prompt: '<compare API features, integrations, performance benchmarks, architecture approaches across competitors; cite docs>'
    assigned_to: general
    verified_by: verifier
    verify_prompt: '<verify feature claims against official docs, check benchmark methodology, flag stale data>'
    timeout_ms: 1800000
  - id: ecosystem-trends
    title: 'ecosystem and industry trends'
    prompt: '<research market trends, regulatory changes, technology shifts affecting this space; cite analyst reports>'
    assigned_to: general
    verified_by: verifier
    verify_prompt: '<verify trend claims cite specific reports with dates, not generic assertions>'
    timeout_ms: 1800000
  # -- Synthesis gate --
  - id: report
    title: 'synthesize final competitive analysis report'
    prompt: '<cross-reference all research tracks, identify strategic opportunities and risks, write structured report with recommendations>'
    assigned_to: general
    depends_on: [market-position, tech-capabilities, ecosystem-trends]
    verified_by: verifier
    verify_prompt: '<verify every recommendation traces to evidence from research tracks, no unsupported claims>'
    timeout_ms: 1800000
```

### Pattern: breadth scan + deep dive

First, a broad scan identifies the most promising areas, then targeted deep dives follow.

```
[broad-scan] --> [deep-dive-A] --\
                 [deep-dive-B] ---+-> [synthesis]
                 [deep-dive-C] --/
```

Use this when the research space is too large to investigate everything in parallel. The broad
scan task should explicitly output which areas deserve deep dives.

### Pattern: multi-source fact verification

When accuracy is critical (financial, legal, regulatory, medical, safety), have multiple
workers independently verify the same claims from different sources.

```
[primary-research]  --> [independent-verification] --> [reconciliation]
```

### Pattern: research + action

When research leads directly to system changes, documents, or communications.

```
[research-tracks]  --> [synthesis]  --> [produce-deliverable]
```

The deliverable task (create report, update spreadsheet, draft email, generate deck) should
depend on completed and verified research. Don't combine research and production in one task.
When the deliverable is a report, reference `references/report.md` in the task prompt for
writing principles and format guidance.
