# 程式結構說明

本 repo 保存 Raspberry Pi Bluetooth vibration gateway 的部署內容，主要程式位於 `sourcecode/ework`。

## 主要元件

- `sourcecode/ework/Bluetooth/bleak_v2q1.py`：Bluetooth gateway 主程式，使用 BLE、Modbus TCP、MQTT、設定檔與韌體資料。
- `sourcecode/ework/Bluetooth/bt_frontend/index.js`：Node.js 前端服務，提供 HTML 頁面、靜態資源、log/MCU/網路狀態相關 API，預設監聽 `8081`。
- `sourcecode/ework/Bluetooth/bt_webapi_v1.py`：目前程式樹內存在的 Flask Bluetooth API 舊版實作。
- `sourcecode/ework/water_detection/water_detect_v2.1.py`：漏水偵測程式，使用 GPIO、ADS1115 與 Modbus TCP。
- `service/*.service`：建議安裝到 `/etc/systemd/system/` 的 systemd unit 檔。

## 重要目錄

- `sourcecode/ework/Bluetooth/conf/`：Bluetooth gateway 設定檔。
- `sourcecode/ework/Bluetooth/Bin/`：MCU 韌體 `.bin` 檔，供 gateway 與前端上傳/更新流程使用。
- `sourcecode/ework/Bluetooth/bt_frontend/html/`：前端頁面。
- `sourcecode/ework/Bluetooth/bt_frontend/images/`：前端圖片與操作說明圖。
- `sourcecode/ework/Bluetooth/bt_frontend/libs/`：前端瀏覽器端靜態函式庫。
- `sourcecode/ework/Bluetooth/bt_frontend/node_modules/`：為無網路 RPi 部署保留的 RPi/ARM Node.js 依賴快照。
- `sourcecode/ework/psutil/`：隨專案保留的 Python `psutil` source tree。

## Git 必須保留的內容

為了讓 Raspberry Pi 無網路時 clone 後仍可直接部署，以下內容應保留在 Git：

- `sourcecode/ework` 底下的 Python 程式
- shell script，例如 `UI.sh`
- `.service` 檔
- `.ini` 與 `.conf` 設定檔
- MCU 韌體 `.bin` 檔
- 前端 HTML、JS、images、瀏覽器端 libs
- `sourcecode/ework/Bluetooth/bt_frontend/package.json`
- `sourcecode/ework/Bluetooth/bt_frontend/package-lock.json`
- `sourcecode/ework/Bluetooth/bt_frontend/node_modules/`

## Git 不應保留的內容

以下屬於 runtime 或本機產物，不應提交：

- logs，例如 `*.log`、`frontend_logs.txt`、`error_log.txt`
- Python `__pycache__/` 與 `*.pyc`
- 本機 IDE 目錄，例如 `.vscode/`、`.idea/`、`.vs/`
- 從部署資料夾複製進來的內嵌 `.git/`
- credentials、tokens、`.env`、備份檔、本機 runtime state

## 已知啟動設定不一致處

目前 repo 內的 service/PM2 設定有幾個需要維運時先確認的地方：

- `service/backend.service` 指向 `bt_webapi_v3.py`，但目前此檔不存在。
- `sourcecode/ework/ecosystem.config.js` 指向 `bleak_v2.py` 與 `bt_webapi_v3.py`，但目前這兩個檔案不存在。
- `service/bt_gateway.service` 指向 `bleak_v2q1.py`，此檔目前存在。
- `sourcecode/ework/Bluetooth/bt_webapi_v1.py` 目前存在，可能是舊版 backend API。

不要在未確認實際現場啟動方式前，直接把 service 或 PM2 entrypoint 改到其他檔案。
