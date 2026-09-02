# Repository Operating Rules

- The Git repository is the only Source of Truth for this project.
- Before every modification, confirm `git status`, run `git pull`, and verify the current branch.
- Use a `codex/*` branch for new features and fixes.
- If a new `codex/*` branch has no upstream, record the `git pull` result and verify `origin` with `git ls-remote --heads origin` before continuing.
- Do not directly modify existing `v1.0`, `v2.0`, or `v3.0` tags.
- After changes are complete, run tests and inspect `git diff`.
- Do not commit `.env`, API keys, tokens, passwords, credentials, logs, archives, or generated dependency folders.
- Do not merge `main` directly without confirmation.
- Do not use old Codex conversation attachments or legacy folders as the latest source.
- If the current working directory is not this repository, stop and report it.
- Never commit or push directly from `main`; create a `codex/*` branch first for code changes.
- Before any push, confirm the target branch and show the planned changes.

## Command Boundaries

Read-only commands are allowed when they inspect repository state, examples: `git status`, `git log`, `git diff`, `git show`, `git branch`, `git remote`, `git ls-files`, `rg`, and file reads.

Ask for explicit confirmation before commands that change Git or GitHub state, including `git commit`, `git push`, `git tag`, `git merge`, branch deletion, release creation, or pull request creation. Never force push, rewrite history, delete tags, delete releases, or delete remote branches unless the user explicitly requests that exact action.

## Release Workflow

- When creating a new tag, follow the existing repository tag naming pattern and increment the version from the previous tag.
- Before creating a tag, confirm the proposed tag name/version with the user and ask whether to use it or revise it.
- After the user confirms that a change has been merged and confirms tag creation, create a GitHub Release directly from that tag.
- Do not create a release tag for a local test artifact unless the user explicitly approves the final version and release.
- If the user asks to keep AGENTS.md updates local, do not push those updates until the next approved `codex/*` branch push.

## Python Runtime

On Windows, use the Python launcher instead of `python`.

Use:
```bash
py -3.13
```

Examples:
```bash
py -3.13 -m py_compile script.py
py -3.13 -m pytest
py -3.13 -m pip install -r requirements.txt
```

Do not assume that python is available on PATH.

## Validation Workflow

- After completing code changes, run the necessary validation before reporting completion.
- Prefer the smallest relevant Python or Docker validation for the changed behavior. Do not perform a full rebuild solely for validation when a narrower check is sufficient.
- When validation succeeds, report only a concise result summary; do not analyze or reproduce the complete log.
- When validation fails, inspect and analyze the most relevant error output first. Do not read or dump large complete logs unless the focused output is insufficient to diagnose the failure.
- Do not repeatedly run a full Docker build unless it is necessary to verify a material build or dependency change.

## Project Layout

- `sourcecode/ework` is the Raspberry Pi deployment source tree for this project.
- Preserve Python source files, shell scripts, systemd service files, `.ini`/`.conf` configuration files, frontend HTML/CSS/JS/images/libs, firmware `.bin` files, package manifests, and lockfiles needed to rebuild dependencies after clone.
- Keep `sourcecode/ework/Bluetooth/bt_frontend/package.json` and `sourcecode/ework/Bluetooth/bt_frontend/package-lock.json`; they are the source of truth for rebuilding frontend Node dependencies.
- Do not commit `node_modules/`, Python virtual environments, downloaded wheels, caches, logs, local IDE folders, nested `.git` directories copied from deployed source trees, credentials, or machine-local runtime state.
- The Raspberry Pi offline requirement is handled by release artifacts. A release artifact may include generated ARM64/aarch64 dependencies under its package `dependencies/` directory, but those generated dependencies must not be committed to Git.
- Release artifacts target Debian/Raspberry Pi OS 11 Bullseye on ARM64, Python 3.9, Node.js 12+, and glibc 2.31. Build native dependencies on the Bullseye baseline; do not substitute a Bookworm/Python 3.11 builder.
- Raspberry Pi installation must not require network access, pip, npm, venv, or ensurepip. Prepare Python `site-packages` and Node `node_modules` in the release artifact.
- Keep required runtime directories with `.gitkeep` when code expects the directory to exist after clone.
- When service files reference an entrypoint that is missing from `sourcecode/ework`, report the mismatch before changing startup behavior.
- Runtime processes are managed only by `frontend.service`, `backend.service`, and `bt_gateway.service`. Do not add PM2, ecosystem configuration, or additional runtime services unless the user explicitly changes this architecture.

## Search and Review Hygiene

- Do not recursively scan generated dependency or artifact directories unless the task is specifically about them.
- Exclude at least these paths from normal searches: `**/node_modules/**`, `**/.venv/**`, `**/venv/**`, `**/__pycache__/**`, `dist/**`, `offline_bundle/**`, `offline_bundles/**`, `release-artifacts/**`, and `release_artifacts/**`.
- Prefer `rg --glob '!**/node_modules/**' --glob '!dist/**' --glob '!offline_bundle/**'` for broad searches.
