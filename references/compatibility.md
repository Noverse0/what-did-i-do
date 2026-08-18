# Agent compatibility

Keep `SKILL.md`, `scripts/`, and this `references/` directory together. The core workflow
intentionally uses only Git and Python 3 so the same package can be reused by coding agents that
support Agent Skills.

The portable subset follows the [Agent Skills specification](https://agentskills.io/specification):
a directory named after the skill, a `SKILL.md` file with `name` and `description`, concise
instructions, and optional bundled resources. Product-specific metadata under `agents/` is
optional and must not change the portable workflow.

## Installation and invocation

| Agent | Project scope | User scope | Invocation notes |
| --- | --- | --- | --- |
| OpenAI Codex | `.agents/skills/what-did-ai-do/` | `$HOME/.agents/skills/what-did-ai-do/` | Invoke explicitly from the skills UI/command surface or let the description trigger it implicitly. `agents/openai.yaml` supplies optional OpenAI UI metadata. OMX installations may instead use their configured `.codex/skills` root. |
| Claude Code | `.claude/skills/what-did-ai-do/` | `$HOME/.claude/skills/what-did-ai-do/` | Invoke as `/what-did-ai-do` or let Claude select it from the description. |
| Gemini CLI | `.gemini/skills/what-did-ai-do/` or `.agents/skills/what-did-ai-do/` | `$HOME/.gemini/skills/what-did-ai-do/` or `$HOME/.agents/skills/what-did-ai-do/` | Gemini discovers metadata, then activates a matching skill with user consent. Use `/skills` or `gemini skills` to manage installed skills. |

Keep platform-only frontmatter out of the shared `SKILL.md`. Claude options such as
`disable-model-invocation`, for example, reduce portability. Prefer a platform wrapper only when
platform-specific permissions or invocation control are required.

## Behavior contract

Regardless of agent, preserve these rules:

1. Trigger after code edits when the user asks for a summary or explicitly requests a push.
2. Derive scope from Git evidence.
3. Inspect the relevant diff before making semantic claims.
4. Keep the explanation to one to three outcome-focused bullets.
5. Distinguish pushed commits from uncommitted local changes.

## Official references

- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Anthropic: Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Gemini CLI: Managing Agent Skills](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/using-agent-skills.md)
- [Gemini CLI: Creating Agent Skills](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/creating-skills.md)
