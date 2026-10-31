---
name: obsidian-knowledge-capture
description: Capture durable knowledge from Codex sessions into an Obsidian vault. Use when the user asks to save, record, remember, sync, or automatically organize Codex work into Obsidian; when a session produces reusable decisions, workflows, lessons, project context, research summaries, or troubleshooting knowledge worth preserving; or when maintaining Codex + Obsidian knowledge automation.
---

# Obsidian Knowledge Capture

## Purpose

Turn valuable Codex session output into readable Obsidian knowledge notes, with raw material and logs kept out of the main reading path.

Default vault: `~/Documents/Obsidian Vault` (Windows: `%USERPROFILE%\Documents\Obsidian Vault`). Override with `--vault` or the `OBSIDIAN_VAULT` environment variable.

## Capture Decision

Capture only durable knowledge:

- Stable decisions, designs, workflows, and operating procedures
- Troubleshooting causes and fixes
- Project background the user will need again
- Research summaries with source links
- Reusable prompts, templates, checklists, or commands
- User preferences only when the user explicitly says to remember them

Do not capture secrets, credentials, noisy logs, incidental chat, unverified guesses, or sensitive personal data unless the user explicitly asks.

## Vault Architecture

User-facing notes:

```text
资料库.md
收件箱/
个人/
学习/
项目/
资料/
  资料.md
  AI 与自动化/
  技术与排错/
  知识管理/
  项目管理/
归档/
```

Machine/system material:

```text
系统/
  Codex/
    原始记录/
    沉淀日志.md
    沉淀规则.md
```

## Link Governance

Do not treat every concept as a link. Use three levels:

1. `parent`: one structural entry note, usually `资料库`; it is used for indexing, not written into the note body as a wikilink.
2. `related`: one to three existing, user-facing notes with direct reading value.
3. `concepts`: plain-text concepts that are useful labels but should not become `[[wikilinks]]`.

Only create `[[wikilinks]]` to notes that already exist and are part of the user-facing content layer. Do not link to raw files, logs, rules, system notes, category nodes, or `资料库` from the body of knowledge notes. Do not create unresolved links unless the user explicitly asks to seed future notes.

Graph structure is intentionally hierarchical:

```text
资料库
  ├─ 个人
  ├─ 学习
  ├─ 项目
  ├─ 资料
  │   ├─ AI 与自动化
  │   ├─ 技术与排错
  │   └─ 知识管理
  └─ 系统
```

Keep category nodes even when a category has only one content note. The visible graph should preserve the layer `资料库 -> 大类 -> 分区/项目 -> note` instead of flattening notes directly under the center.

## Category Governance

Use `category`, `domain`, `area`, `top_category`, or `project` in the payload when the destination is clear. Otherwise the script classifies from title, kind, summary, tags, and concepts.

Default categories include:

- `AI 与自动化`
- `知识管理`
- `项目管理`
- `技术与排错`
- `项目`
- `学习`
- `个人`
- `未分类`

Default captures for reusable reference material go under `资料/<分区>`. Explicit `category: "项目"` with `project` goes under `项目/<project>`; `category: "学习"` and `category: "个人"` go to their top-level folders.

Do not create empty subfolders preemptively. A category appears only after it has a note.

## Workflow

1. Distill the session into one or more atomic notes.
2. Build a JSON payload following `references/input-schema.md`.
3. Put only real note relationships in `related`; put broad concepts in `concepts`.
4. On Windows/PowerShell, set UTF-8 before invoking Python: `$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8';`.
5. Do not pipe Chinese JSON through PowerShell stdin. Save the payload as a UTF-8 `.json` file and pass it with `--json`.
6. Run `scripts/capture_to_obsidian.py` with `--dry-run` for first-time or risky captures.
7. Run without `--dry-run` when the paths and links look right.
8. Tell the user which note was created and what links were added.

## Script Usage

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; python scripts\capture_to_obsidian.py --json payload.json
```

Dry run:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; python scripts\capture_to_obsidian.py --json payload.json --dry-run
```

Windows guardrail: `--stdin` is disabled by default because Windows PowerShell can replace Chinese characters with `?` before Python receives the data. Use `--json` with a UTF-8 file.

## Payload Example

```json
{
  "title": "Codex + Obsidian 自动知识沉淀",
  "file_title": "Codex 与 Obsidian 的自动知识沉淀",
  "kind": "workflow",
  "summary": "Codex 将会话中的可复用知识整理成 Obsidian 知识笔记。",
  "content": "## 核心机制\n\n- 判断是否值得记录。\n- 生成结构化笔记。\n- 写入 Obsidian vault。",
  "parent": "资料库",
  "related": ["Obsidian精通路线"],
  "concepts": ["LLM Wiki", "知识管理", "双向链接"],
  "category": "AI 与自动化",
  "tags": ["codex", "obsidian", "knowledge-management"]
}
```

## References

- `references/capture-protocol.md`: capture policy and examples
- `references/input-schema.md`: accepted JSON fields
- `scripts/capture_to_obsidian.py`: deterministic vault writer
