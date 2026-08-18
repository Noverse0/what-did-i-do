from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "scripts" / "collect_change_context.py"


def run(
    command: list[str], cwd: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def git(repo: Path, *args: str) -> str:
    return run(["git", *args], repo).stdout.strip()


def init_repository(repo: Path) -> None:
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Skill Test")
    git(repo, "config", "user.email", "skill-test@example.com")


def commit_file(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)


class CollectorIntegrationTests(unittest.TestCase):
    def collect(
        self, repo: Path, mode: str = "auto"
    ) -> subprocess.CompletedProcess[str]:
        return run(
            [sys.executable, str(COLLECTOR), "--repo", str(repo), "--mode", mode],
            ROOT,
            check=False,
        )

    def test_auto_prefers_working_tree_and_lists_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            init_repository(repo)
            commit_file(repo, "app.py", "value = 1\n", "initial")
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            (repo / "test_app.py").write_text("assert True\n", encoding="utf-8")

            result = self.collect(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mode: working", result.stdout)
            self.assertIn("app.py", result.stdout)
            self.assertIn("test_app.py", result.stdout)

    def test_outgoing_reports_commits_ahead_of_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "remote.git"
            repo = base / "work"
            run(["git", "init", "--bare", str(remote)], base)
            run(["git", "clone", str(remote), str(repo)], base)
            git(repo, "checkout", "-b", "main")
            git(repo, "config", "user.name", "Skill Test")
            git(repo, "config", "user.email", "skill-test@example.com")
            commit_file(repo, "app.py", "value = 1\n", "initial")
            git(repo, "push", "-u", "origin", "main")
            commit_file(repo, "app.py", "value = 2\n", "change value")

            result = self.collect(repo, "outgoing")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("upstream: origin/main", result.stdout)
            self.assertIn("mode: outgoing", result.stdout)
            self.assertIn("change value", result.stdout)
            self.assertIn("app.py", result.stdout)

    def test_outgoing_without_upstream_is_explicitly_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            init_repository(repo)
            commit_file(repo, "app.py", "value = 1\n", "initial")

            result = self.collect(repo, "outgoing")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No upstream branch is configured.", result.stdout)
            self.assertIn("unknown without an explicit push target", result.stdout)

    def test_last_handles_repository_without_commits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            init_repository(repo)

            result = self.collect(repo, "last")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mode: last", result.stdout)
            self.assertIn("repository has no commits", result.stdout)

    def test_non_repository_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.collect(Path(directory))

            self.assertEqual(result.returncode, 2)
            self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
