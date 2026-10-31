#!/usr/bin/env python3
"""Capture distilled Codex knowledge into an Obsidian vault."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def configure_utf8_stdio() -> None:
    """Keep Chinese paths readable when PowerShell captures Python output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


configure_utf8_stdio()


DEFAULT_VAULT = Path.home() / "Documents" / "Obsidian Vault"
INVALID_FILENAME_CHARS = r'<>:"/\|?*'
WIKI_DIR_NAME = "资料"
SYSTEM_DIR_NAME = "系统"
CODEX_SYSTEM_DIR_NAME = "Codex"
RAW_DIR_NAME = "原始记录"
INDEX_NOTE_NAME = "资料"
LOG_NOTE_NAME = "沉淀日志"
RULES_NOTE_NAME = "沉淀规则"
DEFAULT_PARENT_NOTE = "资料库"
ROOT_INDEX_NOTE_NAME = "资料库"
USER_FACING_DIRS = {"个人", "学习", "项目", "资料", "收件箱", "归档"}
CATEGORY_ALIASES = {
    "笔记与知识管理": "知识管理",
    "项目与复盘": "项目",
}
CATEGORY_TOP_LEVEL = {
    "个人": "个人",
    "学习": "学习",
    "项目": "项目",
    "资料": "资料",
    "收件箱": "收件箱",
    "归档": "归档",
}
CATEGORY_RULES = [
    (
        "AI 与自动化",
        {
            "ai",
            "llm",
            "codex",
            "mcp",
            "automation",
            "agent",
            "workflow",
            "自动化",
            "智能体",
        },
    ),
    (
        "知识管理",
        {
            "obsidian",
            "notion",
            "note",
            "notes",
            "note-taking",
            "knowledge-management",
            "wiki",
            "moc",
            "知识管理",
            "笔记",
            "双向链接",
        },
    ),
    (
        "项目管理",
        {
            "project",
            "project-log",
            "decision",
            "retro",
            "review",
            "iteration",
            "复盘",
            "迭代",
            "决策",
        },
    ),
    (
        "技术与排错",
        {
            "troubleshooting",
            "bug",
            "debug",
            "error",
            "script",
            "cli",
            "api",
            "mcp",
            "排错",
            "脚本",
        },
    ),
]
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "your",
    "you",
    "are",
    "was",
    "were",
    "codex",
    "obsidian",
}


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def read_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.stdin:
        if os.name == "nt" and os.environ.get("OBSIDIAN_CAPTURE_ALLOW_STDIN") != "1":
            raise SystemExit(
                "Refusing --stdin on Windows because PowerShell can corrupt Chinese text in native-command pipes. "
                "Write a UTF-8 JSON payload file and pass it with --json instead. "
                "Set OBSIDIAN_CAPTURE_ALLOW_STDIN=1 only if you have verified the pipe encoding."
            )
        raw = sys.stdin.read()
    elif args.json:
        raw = Path(args.json).read_text(encoding="utf-8")
    else:
        data: dict[str, Any] = {
            "title": args.title,
            "summary": args.summary,
            "kind": args.kind,
            "content": args.content,
            "tags": args.tags or [],
            "links": args.links or [],
            "parent": args.parent,
            "concepts": args.concepts or [],
            "category": args.category,
            "project": args.project,
        }
        return {k: v for k, v in data.items() if v not in (None, "", [])}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Payload must be a JSON object.")
    return payload


def require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Missing required text field: {key}")
    return value.strip()


def as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(value).strip()]


def normalize_tag(tag: str) -> str:
    tag = tag.strip().lstrip("#").lower()
    tag = re.sub(r"\s+", "-", tag)
    tag = re.sub(r"[^0-9a-zA-Z_\-\u4e00-\u9fff]", "-", tag)
    tag = re.sub(r"-{2,}", "-", tag).strip("-")
    return tag


def safe_filename(title: str) -> str:
    clean = title.strip()
    for char in INVALID_FILENAME_CHARS:
        clean = clean.replace(char, "-")
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    return clean[:120] or "Untitled"


def yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(values: list[str]) -> str:
    if not values:
        return " []"
    return "\n" + "\n".join(f"  - {yaml_scalar(value)}" for value in values)


def note_title(payload: dict[str, Any]) -> str:
    return as_text(payload.get("file_title")) or require_text(payload, "title")


def classify_category(payload: dict[str, Any]) -> str:
    explicit = as_text(payload.get("category")) or as_text(payload.get("domain")) or as_text(payload.get("area"))
    if explicit:
        return CATEGORY_ALIASES.get(explicit, safe_filename(explicit))

    text_parts = [
        as_text(payload.get("title")),
        as_text(payload.get("file_title")),
        as_text(payload.get("kind")),
        as_text(payload.get("summary")),
        as_text(payload.get("context")),
        " ".join(as_list(payload.get("tags"))),
        " ".join(as_list(payload.get("concepts"))),
    ]
    haystack = " ".join(text_parts).lower()
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword.lower() in haystack:
                return category
    return "未分类"


def destination_dir(vault: Path, payload: dict[str, Any], category: str) -> Path:
    top_level = as_text(payload.get("top_category")) or as_text(payload.get("section"))
    top_level = CATEGORY_ALIASES.get(top_level, top_level)
    project = as_text(payload.get("project"))

    if top_level in CATEGORY_TOP_LEVEL:
        if top_level == "项目" and project:
            return vault / "项目" / safe_filename(project)
        return vault / CATEGORY_TOP_LEVEL[top_level]

    if category in CATEGORY_TOP_LEVEL:
        if category == "项目" and project:
            return vault / "项目" / safe_filename(project)
        return vault / CATEGORY_TOP_LEVEL[category]

    return vault / WIKI_DIR_NAME / category


def index_path_for_category(vault: Path, payload: dict[str, Any], category: str) -> Path:
    note_dir = destination_dir(vault, payload, category)
    if note_dir.name in USER_FACING_DIRS:
        return note_dir / f"{note_dir.name}.md"
    return note_dir / f"{category}.md"


def root_index_path(vault: Path) -> Path:
    return vault / f"{ROOT_INDEX_NOTE_NAME}.md"


def frontmatter(payload: dict[str, Any], created: dt.datetime, related: list[str]) -> str:
    kind = as_text(payload.get("kind"), "note") or "note"
    status = as_text(payload.get("status"), "evergreen") or "evergreen"
    tags = [normalize_tag(tag) for tag in as_list(payload.get("tags"))]
    tags = [tag for tag in tags if tag]
    if "codex" not in tags:
        tags.insert(0, "codex")

    aliases = as_list(payload.get("aliases"))
    project = as_text(payload.get("project"))
    category = classify_category(payload)

    lines = [
        "---",
        f"type: {yaml_scalar(kind)}",
        f"status: {yaml_scalar(status)}",
        f"category: {yaml_scalar(category)}",
        f"created: {yaml_scalar(created.date().isoformat())}",
        f"tags:{yaml_list(tags)}",
    ]
    if aliases:
        lines.append(f"aliases:{yaml_list(aliases)}")
    if project:
        lines.append(f"project: {yaml_scalar(project)}")
    lines.append("---")
    return "\n".join(lines)


def vault_markdown_files(vault: Path) -> list[Path]:
    files: list[Path] = []
    for path in vault.rglob("*.md"):
        if ".obsidian" in path.parts:
            continue
        files.append(path)
    return files


def is_system_path(path: Path) -> bool:
    return SYSTEM_DIR_NAME in path.parts or RAW_DIR_NAME in path.parts


def is_user_facing_note(vault: Path, path: Path) -> bool:
    if is_system_path(path):
        return False
    try:
        relative = path.relative_to(vault)
    except ValueError:
        return False
    return len(relative.parts) == 1 or relative.parts[0] in USER_FACING_DIRS


def is_moc_note(path: Path) -> bool:
    category_names = {category for category, _ in CATEGORY_RULES}
    moc_names = {ROOT_INDEX_NOTE_NAME, INDEX_NOTE_NAME, *USER_FACING_DIRS, *category_names}
    return path.stem in moc_names or path.stem.endswith("索引")


def title_for_note(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return path.stem
    match = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    if match:
        return match.group(1).strip()
    return path.stem


def note_catalog(vault: Path) -> dict[str, Path]:
    catalog: dict[str, Path] = {}
    for path in vault_markdown_files(vault):
        if not is_user_facing_note(vault, path):
            continue
        title = title_for_note(path)
        catalog.setdefault(title, path)
        catalog.setdefault(path.stem, path)
    return catalog


def tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text.lower())
    return {word for word in words if word not in STOPWORDS}


def split_link_targets(vault: Path, payload: dict[str, Any], max_related: int, auto_related: bool) -> tuple[str, list[str], list[str]]:
    catalog = note_catalog(vault)
    page_title = note_title(payload)
    parent = as_text(payload.get("parent"), DEFAULT_PARENT_NOTE)
    if parent and parent not in catalog:
        parent = ""

    explicit = as_list(payload.get("related")) or as_list(payload.get("links"))
    concepts = as_list(payload.get("concepts")) or as_list(payload.get("mentions"))
    direct: list[str] = []
    seen: set[str] = set()

    def add_direct(name: str) -> None:
        clean = name.strip().strip("[]")
        if not clean or clean == page_title or clean == parent or clean in seen:
            return
        path = catalog.get(clean)
        if path and not is_moc_note(path):
            direct.append(clean)
            seen.add(clean)
        elif clean not in concepts:
            concepts.append(clean)

    for name in explicit:
        add_direct(name)

    if not auto_related:
        return parent, direct[:max_related], dedupe(concepts)

    seed_text = "\n".join(
        [
            as_text(payload.get("title")),
            page_title,
            as_text(payload.get("summary")),
            as_text(payload.get("context")),
            as_text(payload.get("content")),
            " ".join(as_list(payload.get("tags"))),
        ]
    )
    for name, path in sorted(catalog.items()):
        if len(direct) >= max_related:
            break
        if name == parent or name == page_title or is_moc_note(path):
            continue
        if len(name) >= 4 and name in seed_text:
            add_direct(name)
    return parent, direct[:max_related], dedupe(concepts)


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip().strip("[]")
        if clean and clean not in seen:
            result.append(clean)
            seen.add(clean)
    return result


def wikilink(name: str) -> str:
    return f"[[{name}]]"


def section_list(title: str, items: list[str]) -> str:
    if not items:
        return ""
    return f"\n## {title}\n\n" + "\n".join(f"- {item}" for item in items) + "\n"


def demote_headings(markdown: str) -> str:
    lines = []
    in_fence = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            lines.append(line)
        elif in_fence:
            lines.append(line)
        elif line.startswith("##### "):
            lines.append("###### " + line[6:])
        elif line.startswith("#### "):
            lines.append("##### " + line[5:])
        elif line.startswith("### "):
            lines.append("#### " + line[4:])
        elif line.startswith("## "):
            lines.append("### " + line[3:])
        elif line.startswith("# "):
            lines.append("## " + line[2:])
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def build_note(payload: dict[str, Any], created: dt.datetime, parent: str, direct_related: list[str], concepts: list[str]) -> str:
    summary = require_text(payload, "summary")
    context = as_text(payload.get("context"))
    content = as_text(payload.get("content"))
    key_points = as_list(payload.get("key_points"))
    open_questions = as_list(payload.get("open_questions"))
    source = as_text(payload.get("source"), "Codex session")

    parts = [
        frontmatter(payload, created, direct_related),
        "",
        "> [!summary] 摘要",
        "> " + summary.replace("\n", "\n> "),
    ]
    if key_points:
        parts.append(section_list("关键结论", key_points).strip())
    if context:
        parts.extend(["", "## 背景", "", context])
    if content:
        parts.extend(["", "## 具体内容", "", demote_headings(content)])
    if direct_related:
        parts.extend(["", "## 直接相关", "", "\n".join(f"- {wikilink(name)}" for name in direct_related)])
    if concepts:
        parts.extend(["", "## 延伸概念", "", "\n".join(f"- {name}" for name in concepts)])
    if open_questions:
        parts.append(section_list("待确认", open_questions).strip())
    if source:
        parts.extend(["", "## 来源", "", f"- {source}"])
    return "\n".join(part for part in parts if part is not None).rstrip() + "\n"


def build_raw(payload: dict[str, Any], created: dt.datetime) -> str:
    title = require_text(payload, "title")
    raw = as_text(payload.get("raw")) or as_text(payload.get("content")) or require_text(payload, "summary")
    source = as_text(payload.get("source"), "Codex session")
    return (
        "---\n"
        'type: "raw"\n'
        f"created: {yaml_scalar(created.date().isoformat())}\n"
        f"source: {yaml_scalar(source)}\n"
        "---\n\n"
        "> [!note] 原始材料\n"
        "> 这份文件只用于回溯，平时阅读整理后的知识笔记即可。\n\n"
        f"## 原始内容 - {title}\n\n"
        f"{raw.rstrip()}\n"
    )


def ensure_base_files(vault: Path, dry_run: bool) -> list[tuple[Path, str]]:
    wiki_dir = vault / WIKI_DIR_NAME
    system_dir = vault / SYSTEM_DIR_NAME / CODEX_SYSTEM_DIR_NAME
    files = {
        vault / f"{ROOT_INDEX_NOTE_NAME}.md": (
            "---\n"
            'type: "moc"\n'
            'status: "active"\n'
            "tags:\n"
            '  - "personal-library"\n'
            '  - "moc"\n'
            "---\n\n"
            "> 这里是个人资料库的总入口。\n\n"
            "## 大类入口\n\n"
        ),
        wiki_dir / f"{INDEX_NOTE_NAME}.md": (
            "---\n"
            'type: "moc"\n'
            'status: "active"\n'
            "tags:\n"
            '  - "personal-library"\n'
            "---\n\n"
            "> 这里是资料区入口。\n"
            "> 具体资料由分区节点继续分支；全库总入口是 `资料库.md`。\n\n"
            "## 分区\n\n"
        ),
        system_dir / f"{LOG_NOTE_NAME}.md": (
            "---\n"
            'type: "log"\n'
            'status: "active"\n'
            "tags:\n"
            '  - "codex"\n'
            "---\n\n"
            "## 记录\n"
        ),
        system_dir / f"{RULES_NOTE_NAME}.md": (
            "---\n"
            'type: "rules"\n'
            'status: "active"\n'
            "tags:\n"
            '  - "codex"\n'
            "---\n\n"
            "## 记录什么\n\n"
            "- 稳定决策、可复用流程、排错经验、项目背景、研究摘要。\n"
            "- 用户明确说要记住的偏好。\n\n"
            "## 不记录什么\n\n"
            "- 密码、token、cookie、私钥和 `.env` 内容。\n"
            "- 临时闲聊、噪声日志、未经确认的猜测。\n\n"
            "## 写法\n\n"
            "- 整理后的可复用资料放在 `资料`。\n"
            "- 原始材料放在 `系统/Codex/原始记录`。\n"
            "- 优先使用少量有意义的双向链接，不把普通概念词强行做成链接。\n\n"
            "## 图谱骨架\n\n"
            "- `资料库.md` 是图谱中心节点，只链接大类节点。\n"
            "- `资料.md` 是资料区入口，连接资料分区节点。\n"
            "- 每个有内容的资料分区保留一个同名分区节点，例如 `AI 与自动化.md`。\n"
            "- 具体资料文件正文只链接直接相关的内容笔记，不反向链接 `资料库` 或分类节点。\n"
            "- 系统文件、原始记录、日志和规则不进入主图谱。\n"
        ),
    }

    planned: list[tuple[Path, str]] = []
    for path, content in files.items():
        if not path.exists():
            planned.append((path, content))
            if not dry_run:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    return planned


def append_once(path: Path, text: str, marker: str | None, dry_run: bool) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker and marker in existing:
        return False
    if text.strip() in existing:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    return True


def update_index(vault: Path, title: str, summary: str, created: dt.datetime, dry_run: bool) -> bool:
    return False


def update_root_category_link(vault: Path, category: str, dry_run: bool) -> bool:
    path = root_index_path(vault) if category in CATEGORY_TOP_LEVEL else vault / WIKI_DIR_NAME / f"{INDEX_NOTE_NAME}.md"
    marker = wikilink(category)
    line = f"- {wikilink(category)}\n"
    return append_once(path, line, marker, dry_run)


def update_category_index(vault: Path, payload: dict[str, Any], category: str, title: str, summary: str, dry_run: bool) -> bool:
    path = index_path_for_category(vault, payload, category)
    if not path.exists() and not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            'type: "moc"\n'
            'status: "active"\n'
            f"category: {yaml_scalar(category)}\n"
            "tags:\n"
            '  - "moc"\n'
            "---\n\n"
            f"> 这里收纳“{category}”相关笔记。\n\n"
            "## 笔记\n",
            encoding="utf-8",
        )
    marker = wikilink(title)
    line = f"\n- {wikilink(title)}：{summary}\n"
    return append_once(path, line, marker, dry_run)


def update_log(vault: Path, title: str, created: dt.datetime, action: str, dry_run: bool) -> bool:
    path = vault / SYSTEM_DIR_NAME / CODEX_SYSTEM_DIR_NAME / f"{LOG_NOTE_NAME}.md"
    stamp = created.strftime("%Y-%m-%d %H:%M")
    line = f"\n- {stamp} - {action}: {title}\n"
    return append_once(path, line, None, dry_run)


def write_note(path: Path, content: str, payload: dict[str, Any], created: dt.datetime, dry_run: bool) -> str:
    if path.exists():
        update = [
            "",
            f"## 更新 - {created.strftime('%Y-%m-%d %H:%M')}",
            "",
            "> " + require_text(payload, "summary"),
        ]
        extra = as_text(payload.get("content"))
        if extra:
            update.extend(["", demote_headings(extra)])
        if not dry_run:
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n".join(update).rstrip() + "\n")
        return "updated"

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return "created"


def write_raw(path: Path, content: str, dry_run: bool) -> str:
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return "created"


def run(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_payload(args)
    title = require_text(payload, "title")
    summary = require_text(payload, "summary")
    vault = Path(args.vault or os.environ.get("OBSIDIAN_VAULT", "") or DEFAULT_VAULT).expanduser()
    if not vault.exists():
        raise SystemExit(f"Vault does not exist: {vault}")
    if not (vault / ".obsidian").exists():
        raise SystemExit(f"Path does not look like an Obsidian vault: {vault}")

    created = now_local()
    page_title = note_title(payload)
    safe_title = safe_filename(page_title)
    category = classify_category(payload)
    wiki_dir = destination_dir(vault, payload, category)
    raw_dir = vault / SYSTEM_DIR_NAME / CODEX_SYSTEM_DIR_NAME / RAW_DIR_NAME
    note_path = wiki_dir / f"{safe_title}.md"
    raw_path = raw_dir / f"_raw-{created.strftime('%Y%m%d-%H%M')}-{safe_title}.md"
    parent, direct_related, concepts = split_link_targets(vault, payload, args.max_related, args.auto_related)
    note_content = build_note(payload, created, parent, direct_related, concepts)
    raw_content = build_raw(payload, created)

    planned_base = ensure_base_files(vault, args.dry_run)
    note_action = write_note(note_path, note_content, payload, created, args.dry_run)
    raw_action = write_raw(raw_path, raw_content, args.dry_run)
    index_changed = update_root_category_link(vault, category, args.dry_run)
    category_index_changed = update_category_index(vault, payload, category, page_title, summary, args.dry_run)
    log_changed = update_log(vault, page_title, created, note_action, args.dry_run)

    return {
        "dry_run": args.dry_run,
        "vault": str(vault),
        "note": {"path": str(note_path), "action": note_action},
        "raw": {"path": str(raw_path), "action": raw_action},
        "category": category,
        "parent": parent,
        "direct_related": direct_related,
        "concepts": concepts,
        "base_files_planned": [str(path) for path, _ in planned_base],
        "index_changed": index_changed,
        "category_index_changed": category_index_changed,
        "log_changed": log_changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Codex knowledge into Obsidian.")
    parser.add_argument("--vault", help="Path to Obsidian vault")
    parser.add_argument("--json", help="Path to JSON payload")
    parser.add_argument("--stdin", action="store_true", help="Read JSON payload from stdin")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--title", help="Note title when not using JSON")
    parser.add_argument("--summary", help="Note summary when not using JSON")
    parser.add_argument("--kind", default="codex-note", help="Capture kind")
    parser.add_argument("--content", default="", help="Markdown content")
    parser.add_argument("--tags", nargs="*", help="Tags")
    parser.add_argument("--links", nargs="*", help="Explicit related notes")
    parser.add_argument("--parent", help="Parent MOC or entry note")
    parser.add_argument("--concepts", nargs="*", help="Plain-text concepts that should not become links")
    parser.add_argument("--category", help="Destination category or top-level section")
    parser.add_argument("--project", help="Project name for captures under 项目")
    parser.add_argument("--auto-related", action="store_true", help="Auto-link exact existing note title matches")
    parser.add_argument("--max-related", type=int, default=3, help="Maximum direct related links")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
