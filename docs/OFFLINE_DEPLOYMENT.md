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
- `dist/SHA256SUMS`

建置腳本會確認 builder 架構為 ARM64/aarch64。若 Docker 或依賴建置失敗，腳本會中止，不會產生假 artifact。
建置版本必須與 repository 的 `VERSION` 一致，而且 working tree 必須沒有未提交的 source 變更，確保 `BUILD_INFO` 的 Git commit 能精確對應 artifact 內容。

## 驗證離線包

```bash
bash scripts/verify_offline_package.sh dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz
```

驗證重點：

- checksum 可通過
- package 有 `VERSION`、`BUILD_INFO`、`MANIFEST.txt`
- `MANIFEST.sha256` 內每個 package 檔案的 checksum 都正確
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
/opt/vibration_gateway/config
/opt/vibration_gateway/logs
/opt/vibration_gateway/data
```

Installer 會先確認 Linux、ARM64/aarch64、Python、Node.js、package metadata 與 manifest，再建立 release。預設 systemd 模式會啟用並驗證所有服務；若新版本服務驗證失敗，會自動把 `current` 切回原本 release。

## 設定檔保護

現場設定獨立保存在 `/opt/vibration_gateway/config/`，不屬於任何單一 release：

- `ework/Bluetooth/conf/config.ini`
- `ework/Bluetooth/conf/config2.ini`
- `ework/water_detection/config/Parameter.conf`

首次安裝時，會使用 package 內 source tree 的設定。乾淨範例放在 `config/examples/`。Logs 與 runtime data 分別保存在 `/opt/vibration_gateway/logs/`、`/opt/vibration_gateway/data/`，update 與 rollback 都會保留。

## 更新

解壓新 package 後執行：

```bash
sudo ./update_offline.sh
```

更新會檢查目前與新 package 版本，建立新 release 目錄、安裝 package 內依賴，最後切換 `current` symlink 並重啟、驗證 services。若驗證失敗，installer 會嘗試自動切回原版本。

## 回復

回復到前一個 release：

```bash
sudo /opt/vibration_gateway/current/scripts/rollback.sh
```

查看可回復版本：

```bash
ls -1dt /opt/vibration_gateway/releases/*
```

指定 release：

```bash
sudo /opt/vibration_gateway/current/scripts/rollback.sh --target 1.0.1-20260901123000
```

Rollback 會先停止服務、切換 `current`、重新啟動並驗證服務。若目標版本驗證失敗，會嘗試恢復 rollback 前的版本。

## 移除

移除 services 與程式 releases，保留 site config、logs 與 data：

```bash
sudo ./uninstall.sh
```

永久清除整個安裝目錄（包含 site config、logs 與 data）：

```bash
sudo ./uninstall.sh --purge
```

## 注意事項

- Raspberry Pi 必須已有可從 `PATH` 執行的 Node.js。
- Python venv 使用 `--system-site-packages`，方便沿用 RPi OS 已安裝的硬體相關系統套件。
- 若硬體套件無法在 Docker ARM64 builder 產生 wheel，請改在相同 Raspberry Pi OS / ARM64 builder 上執行 `scripts/build_offline_package.sh`。
