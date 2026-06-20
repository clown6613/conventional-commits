#!/usr/bin/env python3
"""
Conventional Commits enforcement hook for Claude Code.

Runs as a PreToolUse(Bash) hook. When the Bash command is a `git commit` with
an inline message (-m / --message / -F is skipped), the subject line is
validated against the Conventional Commits 1.0.0 spec:

    <type>[optional scope][!]: <description>

If the subject does not conform, the hook exits with code 2, which blocks the
commit and returns the guidance below to Claude so it can rewrite the message.
Because this intercepts the Bash tool call *before* git runs, it cannot be
bypassed with `git commit --no-verify`.

Configuration (optional, via environment variables):
  CC_TYPES   Comma-separated allowed types (default: the Angular/CC set below).
  CC_SKIP    If set to "1"/"true", the hook is disabled (exits 0 immediately).

Read more about hooks: https://docs.claude.com/en/docs/claude-code/hooks
"""

import json
import os
import re
import shlex
import sys

DEFAULT_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]

# Subject lines that git generates or that tooling relies on — allowed as-is.
_BYPASS_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ", "amend! ")


def _allowed_types() -> list[str]:
    raw = os.environ.get("CC_TYPES", "").strip()
    if not raw:
        return DEFAULT_TYPES
    types = [t.strip() for t in raw.split(",") if t.strip()]
    return types or DEFAULT_TYPES


def _subject_pattern(types: list[str]) -> "re.Pattern[str]":
    joined = "|".join(re.escape(t) for t in types)
    # <type>(optional scope)(optional !): <description with at least one char>
    return re.compile(rf"^(?:{joined})(?:\([^)]+\))?(?:!)?: .+")


def _is_git_commit(tokens: list[str]) -> int:
    """Return the index of the `commit` subcommand, or -1 if not a git commit."""
    for i, tok in enumerate(tokens):
        if tok == "commit" and "git" in tokens[:i]:
            return i
    return -1


def _extract_messages(tokens: list[str], commit_idx: int) -> tuple[list[str], bool]:
    """Return (-m/--message values, uses_file_or_editor).

    uses_file_or_editor is True when the message comes from a file (-F/--file)
    or an editor (no inline message), in which case we cannot validate.
    """
    msgs: list[str] = []
    uses_file = False
    i = commit_idx + 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "--":
            break
        if tok in ("-m", "--message"):
            if i + 1 < n:
                msgs.append(tokens[i + 1])
                i += 2
                continue
        elif tok.startswith("--message="):
            msgs.append(tok[len("--message="):])
        elif tok in ("-F", "--file") or tok.startswith("--file="):
            uses_file = True
        elif tok.startswith("-m") and len(tok) > 2:
            # -m"msg" collapses under shlex; -mMSG handled here too
            msgs.append(tok[2:])
        elif tok.startswith("-") and not tok.startswith("--") and tok.endswith("m"):
            # combined short flags where -m is last, e.g. `-am "msg"`
            if i + 1 < n:
                msgs.append(tokens[i + 1])
                i += 2
                continue
        i += 1
    return msgs, uses_file


def _guidance(subject: str, types: list[str]) -> str:
    return (
        f"Commit message does not follow Conventional Commits.\n"
        f"  Got:      {subject!r}\n"
        f"  Expected: <type>[optional scope][!]: <description>\n"
        f"  Example:  feat(parser): add ability to parse arrays\n"
        f"  Allowed types: {', '.join(types)}\n"
        f"Rewrite the commit message to match, then retry. "
        f"(Set CC_SKIP=1 to disable this check.)"
    )


def main() -> None:
    if os.environ.get("CC_SKIP", "").lower() in ("1", "true", "yes"):
        sys.exit(0)

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Don't block on malformed hook input; let other tooling handle it.
        sys.exit(0)

    if input_data.get("tool_name") != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command or "commit" not in command:
        sys.exit(0)

    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. — not our job to block on shell parse errors.
        sys.exit(0)

    commit_idx = _is_git_commit(tokens)
    if commit_idx == -1:
        sys.exit(0)

    messages, uses_file = _extract_messages(tokens, commit_idx)
    if uses_file or not messages:
        # Editor- or file-based message: cannot validate reliably. Allow.
        sys.exit(0)

    types = _allowed_types()
    subject = messages[0].splitlines()[0].strip() if messages[0].strip() else ""

    if subject.startswith(_BYPASS_PREFIXES):
        sys.exit(0)

    if not _subject_pattern(types).match(subject):
        print(_guidance(subject, types), file=sys.stderr)
        # Exit code 2 blocks the tool call and shows stderr to Claude.
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
