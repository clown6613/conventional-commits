# conventional-commits

A Claude Code plugin that **enforces [Conventional Commits](https://www.conventionalcommits.org/)** at the agent layer.

A `PreToolUse(Bash)` hook inspects every `git commit` command *before it runs*. If the commit subject doesn't match `<type>[optional scope][!]: <description>`, the hook blocks the command and feeds the reason back to Claude, which then rewrites the message and retries — automatically.

## Why a PreToolUse hook (and not a git `commit-msg` hook)?

Traditional git hooks (`commit-msg`, `pre-commit`) and skill-based reminders both have a gap when an AI agent is driving:

| Approach | Bypassable by `--no-verify`? | Self-correcting? |
|---|---|---|
| Skill / prompt reminder | n/a (agent can ignore it) | no |
| git `commit-msg` hook | **yes** | no |
| **This plugin (PreToolUse)** | **no** | **yes** |

Because the check runs at the Claude Code tool layer, it intercepts the `git commit` invocation itself — `git commit --no-verify` cannot get around it. And because a blocked call returns guidance to Claude (exit code 2), Claude fixes the message instead of just failing.

## Install

This is a standard Claude Code plugin distributed via a marketplace.

```bash
# In Claude Code:
/plugin marketplace add clown6613/conventional-commits
/plugin install conventional-commits
```

Or point `--plugin-dir` at a local clone for development:

```bash
git clone https://github.com/clown6613/conventional-commits
claude --plugin-dir /path/to/conventional-commits
```

Requires `python3` on `PATH`.

## What gets checked

The **subject line** (first line) of the commit message must be:

```
<type>[optional scope][!]: <description>
```

- **type** — one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert` (customizable, see below)
- **scope** — optional, e.g. `(api)`, `(parser)`
- **!** — optional, marks a breaking change
- **description** — required, non-empty, follows `: ` (note the space)

Examples that pass: `feat: add login`, `fix(api): handle null`, `feat!: drop Node 16`.

### What is intentionally *not* blocked

- Commits with no inline message (`git commit` opening an editor) — cannot be inspected reliably.
- File-based messages (`-F` / `--file`).
- Auto-generated subjects: `Merge …`, `Revert …`, `fixup! …`, `squash! …`, `amend! …`.

## Configuration

Both are environment variables, read at hook execution time:

| Variable | Effect |
|---|---|
| `CC_TYPES` | Comma-separated list of allowed types, replacing the default set. E.g. `CC_TYPES="feat,fix,chore,wip"`. |
| `CC_SKIP` | Set to `1`/`true`/`yes` to disable enforcement entirely. |

## Development

```bash
python3 hooks/test_validate_commit_msg.py
```

The hook reads a Claude Code hook JSON payload on stdin and exits `0` (allow) or `2` (block, with guidance on stderr).

## License

MIT — see [LICENSE](./LICENSE).
