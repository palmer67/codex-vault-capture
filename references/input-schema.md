# Input Schema

`capture_to_obsidian.py` accepts one JSON object.

Required:

```json
{
  "title": "Human-readable note title",
  "file_title": "Optional cleaner Obsidian note title",
  "summary": "One or two sentence durable summary"
}
```

Recommended:

```json
{
  "kind": "workflow | decision | concept | project-log | troubleshooting | source-note | template",
  "status": "evergreen | draft | active | done",
  "content": "Markdown body for the durable note",
  "context": "Why this was captured",
  "key_points": ["Point 1", "Point 2"],
  "category": "AI 与自动化 | 知识管理 | 项目管理 | 技术与排错 | 项目 | 学习 | 个人 | custom category",
  "top_category": "Optional explicit top-level area: 个人 | 学习 | 项目 | 资料 | 收件箱 | 归档",
  "tags": ["codex", "obsidian"],
  "parent": "资料库",
  "related": ["Existing user-facing note"],
  "concepts": ["Important concept that should stay plain text"],
  "aliases": ["Alternate title"],
  "source": "Codex session or URL",
  "raw": "Raw source excerpt to store under 系统/Codex/原始记录",
  "project": "Optional project or area"
}
```

Notes:

- `title` is the source idea title; `file_title` can be a cleaner note title for Obsidian.
- `content` should already be distilled by Codex.
- `raw` may be longer, but should not include secrets.
- `parent` is the structural entry note, usually `资料库`.
- `related` must contain only existing user-facing notes with direct reading value.
- `concepts` are plain-text ideas, not `[[wikilinks]]`.
- `category` controls the destination area or resource subfolder. Reusable reference material goes under `资料/<category>`; `category: "项目"` with `project` goes under `项目/<project>`.
- `top_category` can force a top-level area when `category` is a finer-grained label.
- `tags` are normalized to lowercase kebab-case.
