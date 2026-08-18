#!/usr/bin/env python3
"""Collect bounded Git evidence for a concise code-change summary."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

MAX_SECTION_LINES = 200


class GitError(RuntimeError):
    """Raised when required Git evidence cannot be collected."""


@dataclass(frozen=True)
class Repository:
    root: Path
    branch: str
    upstream: str | None
    push_target: str | None


def run_git(
    args: Sequence[str], *, cwd: Path | None = None, required: bool = True
) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        if required:
            detail = result.stderr.strip() or "Git command failed"
            raise GitError(f"git {' '.join(args)}: {detail}")
        return ""
    return result.stdout.rstrip()


def resolve_tracking_ref(root: Path, spec: str) -> str | None:
    """Resolve @{upstream} or @{push} to a ref that actually exists."""
    name = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", spec],
        cwd=root,
        required=False,
    )
    if not name:
        return None
    # @{push} can name a ref that was never fetched or pushed yet.
    if not run_git(
        ["rev-parse", "--verify", "--quiet", f"{name}^{{commit}}"],
        cwd=root,
        required=False,
    ):
        return None
    return name


def discover_repository(start: Path) -> Repository:
    root_text = run_git(["rev-parse", "--show-toplevel"], cwd=start)
    root = Path(root_text).resolve()
    branch = run_git(["branch", "--show-current"], cwd=root, required=False)
    if not branch:
        branch = "(detached HEAD)"
    upstream = resolve_tracking_ref(root, "@{upstream}")
    push_target = resolve_tracking_ref(root, "@{push}")
    return Repository(
        root=root, branch=branch, upstream=upstream, push_target=push_target
    )


def outgoing_target(repo: Repository) -> str | None:
    """Where a push would land: prefer @{push} over @{upstream}."""
    return repo.push_target or repo.upstream


def has_head(repo: Repository) -> bool:
    return bool(
        run_git(["rev-parse", "--verify", "HEAD"], cwd=repo.root, required=False)
    )


def is_merge_commit(repo: Repository) -> bool:
    return bool(
        run_git(
            ["rev-parse", "--verify", "--quiet", "HEAD^2"],
            cwd=repo.root,
            required=False,
        )
    )


def has_working_changes(repo: Repository) -> bool:
    return bool(
        run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=repo.root)
    )


def outgoing_count(repo: Repository) -> int:
    target = outgoing_target(repo)
    if not target or not has_head(repo):
        return 0
    value = run_git(["rev-list", "--count", f"{target}..HEAD"], cwd=repo.root)
    return int(value)


def choose_mode(requested: str, repo: Repository) -> str:
    if requested != "auto":
        return requested
    if has_working_changes(repo):
        return "working"
    if outgoing_count(repo) > 0:
        return "outgoing"
    return "last"


def section(title: str, content: str) -> str:
    body = content.strip() or "(none)"
    lines = body.splitlines()
    if len(lines) > MAX_SECTION_LINES:
        omitted = len(lines) - MAX_SECTION_LINES
        lines = [*lines[:MAX_SECTION_LINES], f"... ({omitted} more lines omitted)"]
    return "\n".join([f"## {title}", *lines])


def collect_working(repo: Repository) -> list[str]:
    return [
        section(
            "Staged files",
            run_git(["diff", "--cached", "--name-status", "-M"], cwd=repo.root),
        ),
        section(
            "Staged stat",
            run_git(["diff", "--cached", "--stat", "-M"], cwd=repo.root),
        ),
        section(
            "Unstaged files",
            run_git(["diff", "--name-status", "-M"], cwd=repo.root),
        ),
        section(
            "Unstaged stat",
            run_git(["diff", "--stat", "-M"], cwd=repo.root),
        ),
        section(
            "Untracked files",
            run_git(["ls-files", "--others", "--exclude-standard"], cwd=repo.root),
        ),
    ]


def collect_outgoing(repo: Repository) -> list[str]:
    target = outgoing_target(repo)
    if not target:
        return [
            section("Warning", "No upstream branch is configured."),
            section("Outgoing commits", "(unknown without an explicit push target)"),
        ]
    revision = f"{target}..HEAD"
    comparison = f"{target}...HEAD"
    return [
        section(
            "Outgoing commits",
            run_git(["log", "--format=%h%x09%s", revision], cwd=repo.root),
        ),
        section(
            "Outgoing files",
            run_git(["diff", "--name-status", "-M", comparison], cwd=repo.root),
        ),
        section(
            "Outgoing stat",
            run_git(["diff", "--stat", "-M", comparison], cwd=repo.root),
        ),
    ]


def collect_last(repo: Repository) -> list[str]:
    if not has_head(repo):
        return [section("Last commit", "(repository has no commits)")]
    details = [
        section(
            "Last commit",
            run_git(["log", "-1", "--format=%h%x09%s"], cwd=repo.root),
        )
    ]
    if is_merge_commit(repo):
        # diff-tree -m reports every parent, so pin the first-parent diff
        # explicitly and say so instead of returning misleading evidence.
        details.append(
            section(
                "Note",
                "HEAD is a merge commit; file lists show the first-parent diff.",
            )
        )
        file_args = [
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-M",
            "HEAD^",
            "HEAD",
        ]
        stat_args = ["diff", "--stat", "-M", "HEAD^", "HEAD"]
    else:
        file_args = [
            "diff-tree",
            "--root",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-M",
            "HEAD",
        ]
        stat_args = ["show", "--stat", "--format=", "-M", "HEAD"]
    details.extend(
        [
            section("Last commit files", run_git(file_args, cwd=repo.root)),
            section("Last commit stat", run_git(stat_args, cwd=repo.root)),
        ]
    )
    return details


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("auto", "working", "outgoing", "last"),
        default="auto",
        help="Git change scope to collect (default: auto)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Path inside the target Git repository (default: current directory)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repo = discover_repository(args.repo.resolve())
        mode = choose_mode(args.mode, repo)
        if mode == "working":
            details = collect_working(repo)
        elif mode == "outgoing":
            details = collect_outgoing(repo)
        else:
            details = collect_last(repo)
    except (GitError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    header = [
        "# Git change context",
        f"repository: {repo.root}",
        f"branch: {repo.branch}",
        f"upstream: {repo.upstream or '(none)'}",
    ]
    if repo.push_target and repo.push_target != repo.upstream:
        header.append(f"push target: {repo.push_target}")
    header.append(f"mode: {mode}")
    print("\n".join([*header, "", *details]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
