# vibration_gateway_rpi4_bleak

Raspberry Pi BLE vibration gateway with a Python collector/API and Node.js frontend.

## Supported target

- Debian/Raspberry Pi OS 11 Bullseye, 64-bit ARM (`aarch64`)
- Python 3.9 from `/usr/bin/python3`
- Node.js 12 or newer
- glibc 2.31 or newer on Bullseye
- systemd, BlueZ (`bluetoothctl`, `hciconfig`), and `ping`

Runtime is managed only by `frontend.service`, `backend.service`, and `bt_gateway.service`. PM2 is not used.

## Repository layout

- `sourcecode/ework/Bluetooth/`: application source, frontend assets, config, and firmware.
- `service/`: field backup units for the `/home/pi/ework` layout.
- `packaging/systemd/`: `/opt/vibration_gateway` unit templates used by the offline package.
- `scripts/`: build, install, rollback, uninstall, and verification scripts.
- `docs/`: architecture, deployment, and release maintenance.

Git keeps source, manifests, lockfiles, scripts, docs, service templates, and firmware. Generated dependencies, logs, caches, and release archives are not committed.

## Build

From Windows with Docker Desktop and ARM64 emulation:

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

Output:

```text
dist/vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39.tar.gz
```

The artifact contains ready-to-run Python `site-packages` and Node `node_modules`. The Raspberry Pi does not run pip, npm, venv, or access the network during installation.

## Install or update

```bash
tar -xzf vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39.tar.gz
cd vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39
sudo ./install_offline.sh
```

Use the same command for initial installation and updates. Configuration, logs, and data remain under `/opt/vibration_gateway`.

## Operate

```bash
systemctl status frontend.service backend.service bt_gateway.service
sudo ./rollback.sh
sudo ./uninstall.sh
sudo ./uninstall.sh --purge
```

Normal uninstall preserves configuration, logs, and data. `--purge` permanently removes everything under `/opt/vibration_gateway`.

## Documentation

- `docs/ARCHITECTURE.md`: program and runtime structure.
- `docs/DEPLOYMENT.md`: build, install, update, rollback, removal, and troubleshooting.
- `docs/RELEASE_PROCESS.md`: maintainer verification and release steps.
