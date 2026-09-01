# vibration_gateway_rpi4_bleak

Raspberry Pi Bluetooth vibration gateway 專案。

主要部署程式放在 `sourcecode/ework`，預期部署到 Raspberry Pi 的 `/home/pi/ework`。

## 重要文件

- [Raspberry Pi 離線佈建方式](docs/DEPLOYMENT.md)
- [程式結構說明](docs/PROGRAM_OVERVIEW.md)
- [Codex/維運規則](AGENTS.md)

## 離線部署重點

本案的 Raspberry Pi 可能沒有網路，因此 `sourcecode/ework/Bluetooth/bt_frontend/node_modules/` 必須保留在 Git。這份目錄是從 RPi/ARM 環境產生的前端依賴快照，用來支援 clone 後直接執行。
