# Raspberry Pi 離線佈建

## 原則

Raspberry Pi target 可以完全沒有網路。所有 Python/Node 執行依賴必須先在有網路的 ARM64/aarch64 builder 產生，放進 release artifact，再搬到 Raspberry Pi 安裝。

Git repository 不再追蹤 `node_modules/`。`package.json`、`package-lock.json`、`requirements.txt` 才是重建依賴的依據。

## 建置離線包

Windows 開發機使用 Docker：

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

ARM64 Linux builder 可直接執行：

```bash
bash scripts/build_offline_package.sh v1.0.1
```

成功後會產生：

- `dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz`
- `dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz.sha256`

建置腳本會確認 builder 架構為 ARM64/aarch64。若 Docker 或依賴建置失敗，腳本會中止，不會產生假 artifact。

## 驗證離線包

```bash
bash scripts/verify_offline_package.sh dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz
```

驗證重點：

- checksum 可通過
- package 有 `VERSION`、`BUILD_INFO`、`MANIFEST.txt`
- source tree 沒有夾帶 `node_modules`
- Python wheelhouse 存在
- Node dependency tree 存在
- installer 與 systemd templates 存在

## 搬移到 Raspberry Pi

將 `.tar.gz` 與 `.sha256` 搬到 Raspberry Pi，例如 USB、內網檔案傳輸或其他離線媒介。到 Raspberry Pi 上執行：

```bash
sha256sum -c vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz.sha256
tar -xzf vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz
cd vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64
sudo ./install_offline.sh
```

預設安裝到：

```text
/opt/vibration_gateway/releases/<version>-<timestamp>
/opt/vibration_gateway/current -> /opt/vibration_gateway/releases/<version>-<timestamp>
```

## 設定檔保護

若系統已安裝過，新版本安裝時會保留目前 release 的現場設定：

- `ework/Bluetooth/conf/config.ini`
- `ework/Bluetooth/conf/config2.ini`
- `ework/water_detection/config/Parameter.conf`

首次安裝時，會使用 package 內 source tree 的設定。乾淨範例放在 `config/examples/`。

## 更新

解壓新 package 後執行：

```bash
sudo ./update_offline.sh
```

更新會建立新 release 目錄、安裝 package 內依賴、保留目前設定，最後切換 `current` symlink 並重啟 services。

## 回復

回復到前一個 release：

```bash
sudo /opt/vibration_gateway/current/scripts/rollback.sh
```

指定 release：

```bash
sudo /opt/vibration_gateway/current/scripts/rollback.sh --target 1.0.1-20260901123000
```

## 移除

只移除 services，保留 release 檔案：

```bash
sudo ./uninstall.sh
```

移除 services 並清除安裝目錄：

```bash
sudo ./uninstall.sh --purge
```

## 注意事項

- Raspberry Pi 必須已有 `/usr/bin/node`。
- Python venv 使用 `--system-site-packages`，方便沿用 RPi OS 已安裝的硬體相關系統套件。
- 若硬體套件無法在 Docker ARM64 builder 產生 wheel，請改在相同 Raspberry Pi OS / ARM64 builder 上執行 `scripts/build_offline_package.sh`。
