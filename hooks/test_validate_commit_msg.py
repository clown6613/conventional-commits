#!/usr/bin/env python3
"""Tests for validate_commit_msg.py — run with: python3 hooks/test_validate_commit_msg.py"""

import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(__file__), "validate_commit_msg.py")

# (command, expected_exit, label)
CASES = [
    # Conforming subjects -> allowed (exit 0)
    ('git commit -m "feat: add login"', 0, "feat"),
    ('git commit -m "fix(api): handle null"', 0, "scope"),
    ('git add . && git commit -am "docs: update readme"', 0, "chained -am"),
    ('git commit -m "feat!: breaking change"', 0, "breaking"),
    ('git commit --message="chore: bump deps"', 0, "--message="),
    # Cannot validate -> allowed
    ("git commit", 0, "editor"),
    ("git commit -F msg.txt", 0, "file"),
    ('git commit -m "Merge branch main"', 0, "merge bypass"),
    ("ls -la", 0, "not a commit"),
    # Non-conforming subjects -> blocked (exit 2)
    ('git commit -m "add login"', 2, "no type"),
    ('git commit -m "Fixed the bug"', 2, "wrong type"),
    ('git commit -m "feat:nospace"', 2, "no space"),
    ('git commit -m "feat: "', 2, "empty desc"),
]


def run(command: str, env: dict | None = None) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return proc.returncode


def main() -> int:
    failures = 0
    for command, expected, label in CASES:
        got = run(command)
        ok = got == expected
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: exit={got} (want {expected})")
        failures += not ok

    # CC_SKIP disables enforcement
    got = run('git commit -m "nope"', env={"CC_SKIP": "1"})
    ok = got == 0
    print(f"[{'PASS' if ok else 'FAIL'}] CC_SKIP bypass: exit={got} (want 0)")
    failures += not ok

    # CC_TYPES extends the allowed set
    got = run('git commit -m "wip: scratch"', env={"CC_TYPES": "feat,fix,wip"})
    ok = got == 0
    print(f"[{'PASS' if ok else 'FAIL'}] CC_TYPES custom: exit={got} (want 0)")
    failures += not ok

    print(f"\n{'All tests passed' if not failures else f'{failures} test(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
