# Repository Operating Rules

- The Git repository is the only Source of Truth for this project.
- Before every modification, confirm `git status`, run `git pull`, and verify the current branch.
- Use a `codex/*` branch for new features and fixes.
- If a new `codex/*` branch has no upstream, record the `git pull` result and verify `origin` with `git ls-remote --heads origin` before continuing.
- Do not directly modify existing `v1.0`, `v2.0`, or `v3.0` tags.
- After changes are complete, run tests and inspect `git diff`.
- Do not commit `.env`, API keys, tokens, passwords, credentials, logs, or `offline_bundle/**/*.tar.gz`.
- Do not merge `main` directly without confirmation.
- Do not use old Codex conversation attachments or legacy folders as the latest source.
- If the current working directory is not this repository, stop and report it.
- Never commit or push directly from `main`; create a `codex/*` branch first for code changes.
- Before any push, confirm the target branch and show the planned changes.

## Release workflow

- When creating a new tag, follow the existing repository tag naming pattern and increment the version from the previous tag.
- Before creating a tag, confirm the proposed tag name/version with the user and ask whether to use it or revise it.
- After the user confirms that a change has been merged and confirms tag creation, create a GitHub Release directly from that tag.
- If the user asks to keep AGENTS.md updates local, do not push those updates until the next approved `codex/*` branch push.

## Python runtime

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

## Project layout

- `sourcecode/ework` is the Raspberry Pi deployment source tree for this project.
- Preserve Python source files, shell scripts, systemd service files, PM2 config, `.ini`/`.conf` configuration files, frontend HTML/CSS/JS/images/libs, firmware `.bin` files, package manifests, and lockfiles needed to rebuild dependencies after clone.
- Preserve `sourcecode/ework/Bluetooth/bt_frontend/node_modules/` because this project supports Raspberry Pi offline clone-and-run deployment and that dependency tree was generated on the RPi/ARM environment.
- Do not replace the preserved frontend `node_modules/` from Windows or another non-RPi environment. If dependencies must change, update them on the RPi/ARM target or another matching ARM/Linux environment, then commit `package.json`, `package-lock.json`, and `node_modules/` together.
- Do not commit other generated dependency folders, caches, logs, local IDE folders, nested `.git` directories copied from deployed source trees, credentials, or machine-local runtime state.
- Keep required runtime directories with `.gitkeep` when code expects the directory to exist after clone.
- When service files reference an entrypoint that is missing from `sourcecode/ework`, report the mismatch before changing startup behavior.
