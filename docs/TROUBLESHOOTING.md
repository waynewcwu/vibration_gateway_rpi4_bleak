# Troubleshooting

## 建置失敗：Docker 不是 ARM64

`scripts/build_offline_package.sh` 會檢查 `uname -m`，必須是 `aarch64` 或 `arm64`。Windows 開發機請使用：

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

PowerShell wrapper 會用 Docker buildx 建立 `linux/arm64` builder image，再在 ARM64 container 中建置 artifact。

## 建置失敗：Python wheel 建不起來

硬體相關套件如 `RPi.GPIO`、`bluepy` 可能依賴 Raspberry Pi OS 或系統 header。若 Docker builder 無法產生 wheel，請改在相同 Raspberry Pi OS 64-bit / ARM64、有網路的 builder 上執行：

```bash
bash scripts/build_offline_package.sh v1.0.1
```

不要用 x86_64 或 Windows 產生的 dependency tree 冒充 ARM64 artifact。

## 安裝失敗：缺少 Node.js

離線 package 會包含 `node_modules`，但不包含 Node.js runtime。請在 Raspberry Pi image 內預先安裝 Node.js，並確認：

```bash
/usr/bin/node --version
```

## 安裝失敗：服務啟動錯誤

查看 systemd 狀態：

```bash
systemctl status vibration-gateway-bt.service
systemctl status vibration-gateway-backend.service
systemctl status vibration-gateway-frontend.service
systemctl status vibration-gateway-water.service
```

查看 log：

```bash
journalctl -u vibration-gateway-bt.service -n 100 --no-pager
```

## 已知入口不一致

- `sourcecode/ework/ecosystem.config.js` 指向不存在的 `Bluetooth/bleak_v2.py`。新版 service template 使用 `Bluetooth/bleak_v2q1.py`。
- `sourcecode/ework/status.service` 指向不存在的 `monitor.py`。新版 installer 不預設安裝 status service。

若要使用舊 PM2 或 status service，請先補齊缺少的 entrypoint。

## 回復失敗

確認 releases 目錄：

```bash
ls -lah /opt/vibration_gateway/releases
readlink -f /opt/vibration_gateway/current
```

指定要回復的 release：

```bash
sudo /opt/vibration_gateway/current/scripts/rollback.sh --target 1.0.1-20260901123000
```

## Source Repo 出現大型依賴

確認 Git 沒有追蹤 `node_modules`：

```bash
git ls-files "sourcecode/ework/Bluetooth/bt_frontend/node_modules/**"
```

若有輸出，代表 dependency tree 被加入 Git，需要從 index 移除：

```bash
git rm -r --cached sourcecode/ework/Bluetooth/bt_frontend/node_modules
```

本機資料夾可以留下給現場比對，但不應進版控。
