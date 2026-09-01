# 系統與程式結構

## 目標

本專案維護 Raspberry Pi 4 上的 BLE vibration gateway。Git repository 保留可維護的 source、設定範例、manifest、lockfile、佈建腳本與文件；實際離線執行需要的 ARM64 依賴，放在每次 GitHub Release 的離線 artifact。

## 主要目錄

- `sourcecode/ework/Bluetooth/`: BLE 收集、Modbus/MQTT 整合、後端 API、前端 Node.js 服務與 firmware `.bin`。
- `sourcecode/ework/Bluetooth/bt_frontend/`: Node.js frontend/API bridge。`package.json` 與 `package-lock.json` 是重建 `node_modules` 的依據。
- `sourcecode/ework/water_detection/`: 水位偵測程式與 `Parameter.conf`。
- `sourcecode/ework/psutil/`: 既有 vendored psutil source。除非要維護 psutil 本身，日常搜尋與審查應避開此目錄。
- `packaging/systemd/`: 新版離線 installer 使用的 systemd service template。
- `scripts/`: 建置、安裝、更新、回復、移除、驗證離線 package 的腳本。

## 預設服務

新版離線 installer 預設安裝以下 systemd services：

- `vibration-gateway-bt.service`: 執行 `Bluetooth/bleak_v2q1.py`。
- `vibration-gateway-backend.service`: 執行 `Bluetooth/bt_webapi_v3.py`。
- `vibration-gateway-frontend.service`: 執行 `Bluetooth/bt_frontend/index.js`。
- `vibration-gateway-water.service`: 執行 `water_detection/water_detect_v2.1.py`。

## 已知歷史不一致

- `sourcecode/ework/ecosystem.config.js` 仍指向 `Bluetooth/bleak_v2.py`，但目前 source tree 沒有此檔。新版 systemd template 改使用已存在的 `bleak_v2q1.py`。
- `sourcecode/ework/status.service` 指向 `monitor.py`，但目前 source tree 沒有此檔。新版 installer 不預設安裝 status service，避免安裝後啟動失敗。

如需恢復這兩個舊入口，請先補齊 entrypoint，再更新 service template 與文件。

## Source Repo 與 Release Artifact 分工

Git source repo 應保持乾淨：

- 保留 source、設定範例、firmware、service template、manifest、lockfile、文件與 scripts。
- 不追蹤 `node_modules/`、`.venv/`、wheelhouse、build artifact、logs、cache、local backup。

離線 artifact 才包含可執行依賴：

- `dependencies/python/wheelhouse/`
- `dependencies/node/bt_frontend_node_modules/`
- `source/ework/`
- `install_offline.sh`、`update_offline.sh`、`rollback.sh`、`uninstall.sh`

這樣 Git 歷史可以長期維護，RPi 無網路時仍可由 release package 完整安裝。

## Raspberry Pi 安裝配置

預設安裝位置：

```text
/opt/vibration_gateway/
├── releases/<version>-<timestamp>/
├── current -> releases/<version>-<timestamp>
├── config/
├── logs/
└── data/
```

每個 release 內的 Bluetooth／water detection 設定與 log 目錄會連到共用目錄。因此切換版本或 rollback 不會覆蓋現場設定，也不會把 log 與 runtime data 綁死在某一版 release。
