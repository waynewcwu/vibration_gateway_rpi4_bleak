# vibration_gateway_rpi4_bleak

Raspberry Pi 4 BLE vibration gateway project. The repository keeps maintainable source code, configuration templates, manifests, deployment scripts, and release documentation. Raspberry Pi offline runtime dependencies are built into release artifacts, not committed to Git.

## Project Overview

This project collects BLE vibration data on Raspberry Pi, exposes local web/API functions, serves a Node.js frontend, and includes water detection utilities. The deployment source tree is `sourcecode/ework`; release packages install it under `/opt/vibration_gateway/current/ework` by default.

## Repository Structure

- `sourcecode/ework/`: Raspberry Pi application source tree.
- `sourcecode/ework/Bluetooth/`: BLE collector, backend API, frontend, firmware files, and BLE configuration.
- `sourcecode/ework/water_detection/`: water detection scripts and configuration.
- `scripts/`: offline build, install, update, rollback, uninstall, and package verification scripts.
- `packaging/systemd/`: systemd service templates used by the offline installer.
- `config/examples/`: sanitized configuration examples.
- `docs/`: deployment, release, troubleshooting, and architecture notes.
- `VERSION`: next package test version for local artifact builds.

## Requirements

Development/build machine:

- Git
- Docker with `buildx` and ARM64 emulation enabled
- PowerShell on Windows when using `scripts/build_offline_package.ps1`

Raspberry Pi target:

- Raspberry Pi OS 64-bit / ARM64
- Python 3.11 compatible environment
- Node.js available at `/usr/bin/node`
- systemd
- Bluetooth, GPIO, and required hardware permissions configured by the device image

## Development

Use a `codex/*` branch for changes. Keep source files, manifests, lockfiles, docs, firmware, scripts, and templates in Git. Do not commit `node_modules/`, virtual environments, wheelhouses, logs, generated archives, or local runtime state.

Frontend dependencies are defined by:

- `sourcecode/ework/Bluetooth/bt_frontend/package.json`
- `sourcecode/ework/Bluetooth/bt_frontend/package-lock.json`

Python runtime dependencies are listed in `requirements.txt`.

## Offline Deployment Overview

The source repository is intentionally clean. Offline Raspberry Pi operation is handled by a release artifact that contains:

- application source under `source/ework`
- Python wheels under `dependencies/python/wheelhouse`
- Node dependencies under `dependencies/node/bt_frontend_node_modules`
- systemd templates
- installer/update/rollback/uninstall scripts
- manifest and checksum metadata

## Build Offline Package

From a Windows development machine with Docker:

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

From an ARM64 Linux builder:

```bash
bash scripts/build_offline_package.sh v1.0.1
```

The artifact is written to `dist/` and ignored by Git.

## Install on Raspberry Pi

Copy the `.tar.gz` and `.sha256` files to the Raspberry Pi, then:

```bash
sha256sum -c vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz.sha256
tar -xzf vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz
cd vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64
sudo ./install_offline.sh
```

## Update

Extract the newer offline package and run:

```bash
sudo ./update_offline.sh
```

The installer creates a new release directory and preserves current runtime configuration files when an existing installation is present.

## Rollback

To switch back to the previous installed release:

```bash
sudo /opt/vibration_gateway/current/scripts/rollback.sh
```

When running from an extracted package, use:

```bash
sudo ./rollback.sh
```

## Uninstall

Remove services while keeping installed files:

```bash
sudo ./uninstall.sh
```

Remove services and installed release files:

```bash
sudo ./uninstall.sh --purge
```

## Release Process

Build and validate an offline package before creating a tag. Do not tag or upload a test artifact unless the version has been approved for release.

See `docs/RELEASE_PROCESS.md`.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/OFFLINE_DEPLOYMENT.md`
- `docs/RELEASE_PROCESS.md`
- `docs/TROUBLESHOOTING.md`
- `AGENTS.md`
