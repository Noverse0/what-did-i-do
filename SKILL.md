---
name: what-did-i-do
description: Summarize code changes briefly and accurately from Git evidence. Use after an agent edits code when the user asks what changed, requests a concise change summary, prepares a commit or handoff, or asks to push/publish changes and needs a short explanation of what was actually pushed.
---

# What Did I Do

Explain completed code changes in plain language without inventing intent. Keep the final summary short enough to scan immediately.

## Build the evidence

1. Respect repository instructions and finish the requested edit and validation first.
2. Choose exactly one summary scope:
   - For a general change-summary request, use `auto`.
   - Before or after a push, use `outgoing` so the summary covers only commits ahead of the upstream branch.
   - For uncommitted work only, use `working`.
   - For the most recent commit only, use `last`.
3. Run:

   ```bash
   python3 <skill-directory>/scripts/collect_change_context.py --mode <auto|outgoing|working|last>
   ```

4. Read the actual relevant diff before summarizing:
   - Working tree: `git diff --cached` and `git diff`
   - Outgoing commits: `git diff <upstream>...HEAD`
   - Last commit: `git show --format=fuller HEAD`
5. Inspect important new files reported as untracked because ordinary `git diff` does not include their content.

Do not use commit subjects or filenames as the sole evidence for behavioral claims.

## Handle push requests

Perform the repository's normal commit, validation, and push workflow when the user explicitly requests a push. Immediately before pushing, collect `outgoing` evidence. After the push succeeds, report the destination branch and summarize that same outgoing range.

Never describe staged, unstaged, or untracked files as pushed. Mention them separately only when they materially affect the user's understanding. Never push merely because the user requested a summary.

## Write the summary

Default to the user's language. Describe outcomes rather than a file-by-file diary.

Use this shape unless the user asks for another format:

```text
변경 요약
- [사용자 또는 시스템 관점의 핵심 변화]
- [필요할 때만 두 번째 변화]
- 검증: [실제로 실행한 검사와 결과]
```

Apply these limits:

- Use one to three bullets.
- Keep each bullet to one sentence.
- Mention filenames only when they make the explanation clearer.
- Include validation only when it actually ran; otherwise state that it was not run.
- Separate pushed changes from remaining local changes.
- Avoid vague phrases such as "개선했습니다" without naming the observable improvement.

## Resolve edge cases

- If `outgoing` has no upstream branch, state that the push range cannot be established and use the explicit push target if available.
- If the tree is clean and there are no outgoing commits, summarize `last` only when the user clearly wants recent history; otherwise say there are no current changes.
- If generated files dominate the diff, summarize the source change first and mention generated artifacts collectively.
- If the diff contains unrelated user changes, exclude them unless the requested scope explicitly includes them.

Read [references/compatibility.md](references/compatibility.md) only when installing or adapting this skill for Codex, Claude Code, or Gemini CLI.
