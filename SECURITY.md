# Security

REPL.io has a deliberately small surface: zero dependencies and a ~2.5k LOC core of Python standard library.

## Reporting vulnerabilities

Please report security issues privately instead of opening a public issue.

Contact: open an issue on GitHub with the `security` label, or reach out directly to the maintainer (see the GitHub profile at https://github.com/emyasnikov/replio).

## What to include

- Affected version
- Steps to reproduce
- Impact description
- Suggested fix, if any

## Scope

Tool execution (`run_command`) runs with the permissions of the launching user. Read/write/list outside the project worktree escalate to `ask`; `run_command` is `ask` by default. Do not run REPL.io as root or with an API server exposed without authentication.
