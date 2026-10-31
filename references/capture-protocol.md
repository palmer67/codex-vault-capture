# Capture Protocol

## What Gets Captured

Capture notes that future Codex or the user can reuse:

- Decisions: why one approach was chosen over another
- Workflows: repeatable steps, scripts, prompts, or procedures
- Concepts: reusable explanations and mental models
- Troubleshooting: symptom, cause, fix, verification
- Project logs: durable status, context, next steps
- Research: source-backed summary and implications

## What Stays Out

Do not record credentials, tokens, raw private data, or incidental chat. Do not write uncertain claims as facts. If a claim is useful but uncertain, mark it as an inference.

## Distillation Pattern

Use this structure before calling the script:

```markdown
## Why This Matters

## Key Points

## Procedure or Details

## Links

## Open Questions
```

## Link Discipline

Use `[[wikilinks]]` only for existing notes that the reader should actually open next. Put broad labels and future ideas in `concepts` as plain text.

Avoid linking:

- Raw capture files
- Logs and rules
- Broad nouns such as "知识管理" unless a real note exists and is directly useful
- Demo concepts from examples

Prefer:

- One `parent` entry note for hierarchy, used by the script and indexes, not as a body wikilink
- One to three `related` notes for direct continuation
- Plain `concepts` for loose context

## Category Discipline

Put each durable note into one primary category. Use `category` when obvious; otherwise let the script classify from metadata.

Use these defaults:

- `AI 与自动化`: Codex, AI agents, MCP, automation, workflows
- `知识管理`: Obsidian, Notion, note-taking, MOC, knowledge management
- `项目管理`: reusable project templates, checklists, sync rules
- `技术与排错`: scripts, CLI, API, bugs, troubleshooting
- `项目`: concrete project notes when paired with `project`
- `学习`: courses, learning routes, reading, exercises, stage summaries
- `个人`: personal affairs and privacy indexes

Avoid keeping ordinary notes in the vault root. The root should stay quiet.

## Graph Discipline

Treat `资料库.md`, top-level MOCs, and resource/project MOCs as deliberate navigation skeleton nodes. They should appear in the graph to show the layer `资料库 -> 大类 -> 分区/项目 -> content note`, but they are not ordinary knowledge entities.

Keep category nodes even when a category has only one content note. This prevents the graph from flattening unrelated notes directly under the center.

Do not write body links to:

- `资料库`
- Category nodes such as `AI 与自动化`
- System notes under `系统`

## Capture Timing

- At the end of a completed task, capture the durable lesson.
- During long work, capture only after a stable decision or result.
- When the user says "记下来", "存到 Obsidian", "以后自动记录", or "沉淀一下", capture immediately.

## Quality Bar

A good note answers:

- What reusable idea should I remember?
- When would I use it again?
- What does it connect to?
- What evidence or context supports it?
