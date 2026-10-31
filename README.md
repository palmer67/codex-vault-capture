# codex-vault-capture

把 AI 编程会话里产出的结论，自动沉淀成带索引的 Obsidian 笔记。

[![CI](https://github.com/palmer67/codex-vault-capture/actions/workflows/ci.yml/badge.svg)](https://github.com/palmer67/codex-vault-capture/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 这是什么

和 agent（Codex、Claude Code 等）一起工作久了，真正值钱的东西往往散在对话里：某个方案为什么被放弃、某个报错的真实原因、某段流程的固定步骤。下次再遇到同类问题，翻聊天记录比重新做一遍还慢。

这个工具解决的就是这一步：**给 agent 一个固定的命令行接口**，把会话结论按 JSON 交进来，落成一篇结构化的 Obsidian 笔记——带 frontmatter、带摘要、按分区归位、登记进 MOC 和沉淀日志。

它是作者日常在用的工具，公开是因为机制本身比结果更值得复用。

## 特性

- **结构化落盘**：一篇笔记 = YAML frontmatter + 摘要 callout + 正文 + 延伸概念 + 来源
- **按规则归类**：显式 `category` 优先，其次是关键词规则表，最后兜底到「未分类」。不做模型判断，出错能直接改表
- **自动登记**：写入后在所属分区的 MOC 追加链接，并在沉淀日志记一行 `created / updated`
- **幂等**：同一篇笔记再次写入时只追加一个「更新」段落，索引里的链接不会重复登记
- **可预演**：`--dry-run` 打印将要写入的路径与动作，不落盘
- **链接治理**：只为已存在的笔记生成 `[[wikilinks]]`，其余概念保持纯文本，不制造死链
- **零依赖**：只用 Python 标准库

## 为什么不做成 Obsidian 插件

插件只能在 Obsidian 界面内触发。这里的使用场景是 **agent 会话结束时自动落盘**，全程没有界面，也没有人能点按钮。命令行加 JSON 是 agent 能稳定调用、也能被脚本和 CI 复现的唯一接口。

## 快速开始

要求：Python 3.9+，以及一个已经初始化的 Obsidian vault（目录下有 `.obsidian/`）。

```bash
git clone https://github.com/palmer67/codex-vault-capture.git
cd codex-vault-capture

# 先预演，确认路径和分类对不对
python scripts/capture_to_obsidian.py --vault "/path/to/vault" --json examples/input.json --dry-run

# 没有问题了再去掉 --dry-run
python scripts/capture_to_obsidian.py --vault "/path/to/vault" --json examples/input.json
```

Windows PowerShell：

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
python scripts\capture_to_obsidian.py --vault "$env:USERPROFILE\Documents\Obsidian Vault" --json examples\input.json
```

> **Windows 注意**：不要用 `--stdin` 传中文 JSON。PowerShell 会在管道里把中文字符替换成 `?`，请把 payload 存成 UTF-8 的 `.json` 文件后用 `--json` 传入。脚本默认禁用了 `--stdin`。

## 输入

一个 JSON 对象。必填 `title` 和 `summary`，其余可选：

```json
{
  "title": "为什么工具只在会话结束时写入",
  "file_title": "会话结束时写入的取舍",
  "kind": "decision",
  "summary": "把笔记写入点固定在会话结束，而不是每条消息后都写，避免产生大量半成品笔记。",
  "content": "## 背景\n\nagent 会话过程中结论会反复变化，中途写入会留下大量需要合并的残稿。\n\n## 结论\n\n只在会话结束或结论稳定后写入一次。",
  "category": "知识管理",
  "tags": ["Agent", "Obsidian"],
  "concepts": ["写入时机", "幂等性"]
}
```

字段说明见 [`references/input-schema.md`](references/input-schema.md)，完整的示例文件是 [`examples/input.json`](examples/input.json)。

几个容易混的字段：

| 字段 | 作用 |
| --- | --- |
| `title` | 原始标题，用于日志与来源 |
| `file_title` | 落盘用的文件名（更短更干净时用） |
| `related` | 一到三个**已存在**的笔记，生成 `[[wikilinks]]` |
| `concepts` | 值得留作标签但**不要**变成链接的概念 |
| `category` | 目标分区，决定落在 `资料/<category>/` 下 |
| `project` | 配合 `category: "项目"` 时决定 `项目/<project>/` |
| `raw` | 原文摘录，落到 `系统/Codex/原始记录/`，不进主阅读路径 |

## 输出

`examples/input.json` 跑完之后会得到 [`examples/output-note.md`](examples/output-note.md)：

```markdown
---
type: "decision"
status: "evergreen"
category: "知识管理"
created: "2026-10-31"
tags:
  - "codex"
  - "agent"
  - "obsidian"
---

> [!summary] 摘要
> 把笔记写入点固定在会话结束，而不是每条消息后都写，避免产生大量半成品笔记。

## 具体内容

### 背景
...
```

同时会在分区 MOC 里追加一条链接（见 [`examples/output-category-index.md`](examples/output-category-index.md)），并在 `系统/Codex/沉淀日志.md` 里记一行。

## 工作原理

```text
payload.json
   │
   ├─ 1. 规范化字段：校验必填项，tags 统一成小写 kebab-case
   ├─ 2. 判定归属：显式 category / top_category / project → 关键词规则表 → 未分类
   ├─ 3. 生成正文：frontmatter + 摘要 callout + 正文 + 延伸概念 + 来源
   ├─ 4. 写入并登记：笔记落盘 → 分区 MOC 追加链接 → 沉淀日志追加一行
   └─ 5. 幂等检查：写入前扫描目标文件内容标记，命中则改为追加「更新」段落
```

第 5 步是关键。重复调用不会产生两篇笔记、也不会让 MOC 里出现第二条相同链接，只会给原笔记追加一个带时间戳的「更新」段落——所以它可以被安全地放在自动化流程里反复调用。

## Vault 目录约定

```text
vault/
├── 资料库.md              # 总入口 MOC
├── 个人/
├── 学习/
├── 项目/
│   └── <project>/
├── 资料/
│   ├── 资料.md            # 资料区 MOC
│   ├── AI 与自动化/
│   ├── 技术与排错/
│   └── 知识管理/
│       ├── 知识管理.md    # 分区 MOC
│       └── <note>.md
└── 系统/
    └── Codex/
        ├── 原始记录/
        ├── 沉淀日志.md
        └── 沉淀规则.md
```

分类节点即使只有一篇笔记也会保留，这样图谱里的层级是 `资料库 → 大类 → 分区 → 笔记`，而不是所有笔记直接堆在中心。

## 配置

| 方式 | 说明 |
| --- | --- |
| `--vault <path>` | 指定 vault 路径，优先级最高 |
| 环境变量 `OBSIDIAN_VAULT` | 没有传 `--vault` 时使用 |
| 默认值 | `~/Documents/Obsidian Vault` |

其余参数：

```text
--json <file>         JSON payload 文件
--stdin               从标准输入读取（Windows 下不建议）
--dry-run             只预演，不写入
--auto-related        按标题精确匹配已有笔记，自动补 related
--max-related <n>     直接关联链接的上限，默认 3
--category            指定分区
--project             指定项目名（配合 category: "项目"）
--kind                笔记类型，默认 codex-note
--title / --summary / --content / --tags / --links / --concepts / --parent
                      不使用 JSON 时的命令行字段
```

## 作为 Codex Skill 使用

[`SKILL.md`](SKILL.md) 是写给 agent 的操作说明（何时捕获、链接纪律、分类纪律、PowerShell 注意事项）。把它和 `references/`、`scripts/` 一起放到 skills 目录下，agent 就能在会话结束时自己调用：

```text
<skills-dir>/obsidian-knowledge-capture/
├── SKILL.md
├── references/
└── scripts/capture_to_obsidian.py
```

## 测试

```bash
python -m unittest discover -s tests -v
```

覆盖：笔记生成与 frontmatter、分区 MOC 与日志登记、重复写入的幂等性、`--dry-run` 不落盘、非 vault 路径报错。

## 已知限制

- 分类依赖关键词规则表，不做语义判断；遇到新领域要补规则
- 面向个人 vault 设计，不处理多人协作与冲突合并
- 没有 GUI，也没有 Obsidian 插件版本
- 中文文件名在部分第三方同步工具下可能出问题
- 不做向量检索，检索依赖 Obsidian 自带搜索

## 许可

[MIT](LICENSE)
