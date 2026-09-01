# Raspberry Pi 離線佈建方式

本專案把可部署到 Raspberry Pi 的程式樹放在 `sourcecode/ework`。
目前程式與 service 檔使用的目標路徑是 `/home/pi/ework`。

## 離線依賴原則

此案的 Raspberry Pi 可能沒有網路，因此 repo 需要保留前端服務的 RPi/ARM 依賴快照：

- `sourcecode/ework/Bluetooth/bt_frontend/node_modules/`
- `sourcecode/ework/Bluetooth/bt_frontend/package.json`
- `sourcecode/ework/Bluetooth/bt_frontend/package-lock.json`

在這個專案中，`node_modules/` 不是一般可丟棄的快取，而是 RPi 無網路時 clone 後可直接執行的必要內容。維運時不要刪除它，也不要在 Windows 重新產生後覆蓋。如果要更新 Node 依賴，請在 Raspberry Pi 或相同 ARM/Linux 環境更新，並一起提交 `package.json`、`package-lock.json`、`node_modules/`。

## 從 fresh clone 佈建

在 Raspberry Pi 上執行：

```bash
git clone <repo-url> vibration_gateway_rpi4_bleak
cd vibration_gateway_rpi4_bleak
sudo mkdir -p /home/pi/ework
sudo cp -a sourcecode/ework/. /home/pi/ework/
sudo cp service/bt_gateway.service /etc/systemd/system/
sudo cp service/frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bt_gateway.service frontend.service
sudo systemctl restart bt_gateway.service frontend.service
```

`frontend.service` 啟動後，前端服務預設監聽 `8081` port。

## Service 注意事項

- `service/bt_gateway.service` 啟動 `/home/pi/ework/Bluetooth/bleak_v2q1.py`，此檔目前存在。
- `service/frontend.service` 啟動 `/home/pi/ework/Bluetooth/bt_frontend/index.js`，並依賴已保留的 RPi/ARM `node_modules/`。
- `service/backend.service` 目前指向 `/home/pi/ework/Bluetooth/bt_webapi_v3.py`，但目前程式樹內沒有這個檔案。啟用前需要先確認或補回正確 backend entrypoint。
- `sourcecode/ework/ecosystem.config.js` 目前指向 `bleak_v2.py` 與 `bt_webapi_v3.py`，但這兩個檔案目前不存在。請先視為舊版/待確認 PM2 設定，不要未確認就直接套用。

## Runtime 目錄

repo 以 `.gitkeep` 保留必要 runtime 目錄，確保 clone 後目錄存在：

- `/home/pi/ework/log`
- `/home/pi/ework/Bluetooth/log`
- `/home/pi/ework/water_detection/log`

log 檔是執行時輸出，不應提交進 Git。

## 基本驗證

部署後檢查 service：

```bash
sudo systemctl status bt_gateway.service
sudo systemctl status frontend.service
```

檢查離線前端依賴是否存在：

```bash
test -d /home/pi/ework/Bluetooth/bt_frontend/node_modules/express
test -d /home/pi/ework/Bluetooth/bt_frontend/node_modules/ws
test -d /home/pi/ework/Bluetooth/bt_frontend/node_modules/ping
```

如果這些目錄在無網路 RPi 上不存在，前端服務無法靠 `npm install` 補回，必須恢復 RPi/ARM 產生的 `node_modules/` 快照。
