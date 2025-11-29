## Repository custom instructions for Copilot

Summary
-------
This repository holds a small collection of Python utilities for working with YNAB data.  The project is intentionally minimal and maintained by a single developer.

Environment & Tooling
---------------------
- Target Python: confirm with the maintainer (suggested default: 3.11).
- Dependency management: this repo uses a `project.toml` at the repo root and `uv` to manage environments and dependencies. Ask before assuming a specific `uv` implementation.
- Linting: use `ruff` with a repo-level config when scaffolding or linting changes.

Standard workflow for coding agents
----------------------------------
- **DO NOT make assumptions or guess what features to add.** Only implement features that are explicitly requested in the current conversation. Do not infer requirements from prior projects, file names, or directory structures.
- **DO NOT create files, directories, or code based on what you think the project might need.** Wait for explicit direction about what to build.
- Wait for an explicit approval phrase before making any code changes. The maintainer uses: "make it so".
- Before any file edits or multi-step changes, provide a one-sentence preamble describing what you will do and why.
- Use the repository's `manage_todo_list` pattern to plan multi-step tasks; update the todo list before and after changes when relevant.
- Use `apply_patch` (or create PRs) to make edits. Keep changes small, focused, and consistent with existing style.

Build, test, and validation guidance
-----------------------------------
- Prefer lightweight, reproducible steps and validate commands locally before relying on them in automation.
- When adding CI/workflow steps, document the exact commands required to bootstrap, install, lint, run tests, and validate builds.
- When uncertain about the environment or tool versions, ask the maintainer rather than guessing.

Testing requirements
--------------------
- Generate unit tests with coverage for new features and permutations of behavior as they are added.
- When possible, create integration tests that exercise subcommands with sample data fixtures.
- Use randomized data in fixtures that matches expected input and output formats for realistic testing.
- Tests should be comprehensive but focused on actual behavior rather than implementation details.

Project layout hints
--------------------
- Intended code locations: `src/` or top-level module agreed during design.
- Tests should live in `tests/` and should be runnable with a single command once the environment is provisioned.
- **Only create directories and files that are explicitly requested.** Do not pre-create structures based on assumptions.

Agent constraints and priorities
-------------------------------
Personal instructions (the user's own Copilot settings) take precedence over repository instructions. If multiple instruction sources apply, merge them but avoid conflicts.

Quick checklist before proposing code changes
--------------------------------------------
1. Confirm the exact `uv` tool and Python version with the user.
2. Produce a short design and todo plan (use the `manage_todo_list` tool).
3. Provide a one-line preamble describing intended edits.
4. Make minimal edits with `apply_patch` and run tests/lint locally when possible.
5. Report back with what changed and recommended next steps.

Git commit messages
-------------------
- Use Conventional Commits for repository commits. Examples:
	- `fix(subcommand): mark provider rows matched in-memory`
	- `feat(cli): add --start-date option`
	- `test: add matching memory-flag tests`

	Keep messages concise, use present-tense verbs, and include scope when helpful.

Notes
-----
This file is intended for repository-wide guidance for Copilot and similar coding agents. For additional, session-specific guidance see `SESSION_GUIDANCE.md` at the repo root.
