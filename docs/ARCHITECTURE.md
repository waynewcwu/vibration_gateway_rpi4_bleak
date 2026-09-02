# Architecture

## Runtime services

The gateway uses systemd only:

| Service | Entrypoint | Purpose |
| --- | --- | --- |
| `bt_gateway.service` | `Bluetooth/bleak_v2q1.py` | BLE collection, Modbus, MQTT, and REST data flow |
| `backend.service` | `Bluetooth/bt_webapi_v3.py` | Local configuration and firmware API |
| `frontend.service` | `Bluetooth/bt_frontend/index.js` | Web interface and WebSocket frontend |

The Python entrypoints also require `interface.py`, `server.py`, and `Timeout.py`. Firmware under `Bluetooth/Bin`, configuration under `Bluetooth/conf`, frontend HTML/images/libs, `package.json`, and `package-lock.json` are runtime assets.

PM2, water detection, GUI programs, old backend versions, status services, and vendored `psutil` are not part of the supported runtime.

## Platform contract

The offline artifact targets Debian/Raspberry Pi OS 11 Bullseye on ARM64 with Python 3.9, Node.js 12+, and glibc 2.31. Native Python dependencies are built on the same Bullseye baseline.

Python packages are prepared under `dependencies/python/site-packages` during the online build. Node packages are prepared under `dependencies/node/bt_frontend_node_modules`. Installation copies both trees; the Raspberry Pi does not run package managers or create a virtual environment.

## Installed layout

```text
/opt/vibration_gateway/
  current -> releases/<version>-<timestamp>
  releases/
  config/Bluetooth/conf/
  logs/Bluetooth/
  data/
```

Each release contains application source, Python packages, Node packages, metadata, and maintenance scripts. Configuration, logs, and data live outside releases so updates and rollbacks do not overwrite field state.

The `service/` directory contains field backup units for `/home/pi/ework`. Offline artifacts use the templates in `packaging/systemd/`, which point to `/opt/vibration_gateway/current`.
