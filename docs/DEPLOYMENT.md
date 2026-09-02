# Deployment

## Target check

The Raspberry Pi must report Bullseye, ARM64, Python 3.9, Node.js 12+, and the required system tools:

```bash
cat /etc/os-release
uname -m
python3 --version
node --version
ldd --version | head -n 1
command -v bluetoothctl hciconfig ping
```

The installer performs these checks again and stops before writing `/opt` when the host is incompatible.

## Build and verify

Build on Windows with Docker Desktop:

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

Verify the generated archive:

```bash
bash scripts/verify_offline_package.sh dist/vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39.tar.gz
```

The build requires network access. Raspberry Pi installation does not.

## Install or update

Copy the archive to the Raspberry Pi, then run:

```bash
tar -xzf vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39.tar.gz
cd vibration_gateway_rpi4_bleak-v1.0.1-bullseye-arm64-py39
sudo ./install_offline.sh
```

The same command performs initial installation and updates. It verifies package checksums, host compatibility, Python imports, Node imports, and `bluepy-helper` before creating a release. A failed installation removes the incomplete release and keeps the previous `current` target.

Check the three services:

```bash
systemctl status frontend.service backend.service bt_gateway.service
journalctl -u bt_gateway.service -u backend.service -u frontend.service -n 100 --no-pager
```

## Rollback

```bash
sudo ./rollback.sh
```

Choose a specific installed release when needed:

```bash
sudo ./rollback.sh --target RELEASE_DIRECTORY_NAME
```

## Uninstall

Remove services and releases while preserving configuration, logs, and data:

```bash
sudo ./uninstall.sh
```

Permanently remove `/opt/vibration_gateway`, including field data:

```bash
sudo ./uninstall.sh --purge
```

## Troubleshooting

- `requires Debian/Raspberry Pi OS 11 Bullseye`: do not use this artifact on Bookworm or another distribution.
- `requires Python 3.9`: use the Bullseye system Python; do not install Python 3.11 just for this package.
- `Packaged Python dependencies are incompatible`: confirm the artifact name contains `bullseye-arm64-py39` and rerun package verification.
- `bluepy-helper has incompatible system libraries`: the artifact was built from the wrong glibc baseline and must be rebuilt.
- `ensurepip is not available`: this message comes from the obsolete wheelhouse/venv installer. The current installer never creates a venv.

Old failed installers may have left a partial directory under `/opt/vibration_gateway/releases`. The current installer removes its own incomplete release automatically; inspect old directories before deleting them if field data may be present.
