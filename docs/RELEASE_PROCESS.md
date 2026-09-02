# Release Process

## Prepare

1. Work on a `codex/*` branch and confirm `git status` is clean before building.
2. Keep `VERSION` and the requested `vX.Y.Z` build argument aligned.
3. Keep Python dependencies fully pinned in `requirements.txt` and Node dependencies locked in `package-lock.json`.
4. Do not commit `dist/`, dependency folders, logs, credentials, or generated archives.

## Validate source

```bash
bash -n scripts/*.sh tests/*.sh
bash tests/test_manifest_locale.sh
```

Run Python syntax checks and `node --check` for the retained service entrypoints before the full build.

## Build

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

The builder must be Bullseye ARM64 with Python 3.9, Node.js 12, and glibc 2.31. It prepares Python `site-packages` and Node `node_modules`, then writes `BUILD_INFO`, `MANIFEST.txt`, `MANIFEST.sha256`, and the archive checksum.

## Offline lifecycle

Verify the archive, extract it in a Bullseye ARM64 container, and run with networking disabled:

```bash
bash scripts/verify_offline_package.sh dist/vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39.tar.gz
bash tests/test_offline_lifecycle.sh EXTRACTED_PACKAGE_DIRECTORY
```

The lifecycle test installs with `--service-mode none`, verifies Python and Node imports, confirms no venv exists, tests normal uninstall, and tests purge.

## Publish

Review `git diff`, commit and push the approved branch, and update the pull request. Create tags or GitHub Releases only after explicit confirmation and merge approval.
