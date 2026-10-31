import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capture_to_obsidian.py"

PAYLOAD = {
    "title": "写入时机",
    "file_title": "会话结束时写入的取舍",
    "kind": "decision",
    "summary": "把笔记写入点固定在会话结束，避免产生大量半成品笔记。",
    "content": "## 结论\n\n只在结论稳定后写入一次。",
    "category": "知识管理",
    "tags": ["Agent", "Obsidian"],
    "concepts": ["写入时机"],
}


class CaptureTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.vault = self.tmp / "Vault"
        (self.vault / ".obsidian").mkdir(parents=True)
        self.note = self.vault / "资料" / "知识管理" / "会话结束时写入的取舍.md"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_script(self, vault: Path, payload: dict, *extra: str) -> subprocess.CompletedProcess:
        payload_path = self.tmp / "payload.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--vault", str(vault), "--json", str(payload_path), *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )

    def capture(self, vault: Path, payload: dict = PAYLOAD, *extra: str) -> dict:
        result = self.run_script(vault, payload, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_creates_note_with_frontmatter(self) -> None:
        result = self.capture(self.vault)

        self.assertEqual(result["note"]["action"], "created")
        self.assertTrue(self.note.exists())
        text = self.note.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn('type: "decision"', text)
        self.assertIn('category: "知识管理"', text)
        self.assertIn("> [!summary]", text)
        for tag in ("codex", "agent", "obsidian"):
            self.assertIn(f'  - "{tag}"', text)

    def test_updates_category_index_and_log(self) -> None:
        self.capture(self.vault)

        category_index = self.vault / "资料" / "知识管理" / "知识管理.md"
        self.assertTrue(category_index.exists())
        self.assertIn("[[会话结束时写入的取舍]]", category_index.read_text(encoding="utf-8"))

        log = self.vault / "系统" / "Codex" / "沉淀日志.md"
        self.assertIn("created: 会话结束时写入的取舍", log.read_text(encoding="utf-8"))

    def test_second_capture_appends_update_without_duplicating_index(self) -> None:
        self.capture(self.vault)
        result = self.capture(self.vault)

        self.assertEqual(result["note"]["action"], "updated")
        text = self.note.read_text(encoding="utf-8")
        self.assertEqual(text.count("## 更新 -"), 1)

        category_index = (self.vault / "资料" / "知识管理" / "知识管理.md").read_text(encoding="utf-8")
        self.assertEqual(category_index.count("[[会话结束时写入的取舍]]"), 1)

    def test_dry_run_writes_nothing(self) -> None:
        result = self.capture(self.vault, PAYLOAD, "--dry-run")

        self.assertTrue(result["dry_run"])
        self.assertFalse(self.note.exists())
        self.assertFalse((self.vault / "资料").exists())

    def test_rejects_plain_directory(self) -> None:
        plain = self.tmp / "not-a-vault"
        plain.mkdir()

        result = self.run_script(plain, PAYLOAD)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not look like an Obsidian vault", result.stderr)


if __name__ == "__main__":
    unittest.main()
