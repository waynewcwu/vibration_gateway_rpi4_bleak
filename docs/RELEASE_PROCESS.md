# Release 流程

## 分支

所有修改先從 `main` 建立 `codex/*` branch：

```bash
git switch main
git pull
git switch -c codex/offline-release-architecture
```

不要直接從 `main` commit 或 push 程式修改。

## 版本號

`VERSION` 記錄下一個要測試或準備 release 的版本，例如：

```text
1.0.1
```

建置 artifact 時使用 tag 格式：

```bash
v1.0.1
```

本次 `v1.0.1` 僅作為 local artifact build/test 版本，不建立 tag，不建立 GitHub Release。

## 建置候選 artifact

```powershell
.\scripts\build_offline_package.ps1 -Version v1.0.1
```

或在 ARM64 Linux：

```bash
bash scripts/build_offline_package.sh v1.0.1
```

建置完成後驗證：

```bash
bash scripts/verify_offline_package.sh dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz
```

## PR

push branch 後建立 PR，PR 內容至少包含：

- source repo 清理項目
- 離線 build/install/update/rollback/uninstall 流程
- artifact build 結果與限制
- 已知 entrypoint mismatch
- 測試紀錄

## 正式 Release

只有在 PR merge 且使用者明確確認版本後，才可以建立 tag 與 GitHub Release。

建議步驟：

```bash
git switch main
git pull
git tag v1.0.1
git push origin v1.0.1
gh release create v1.0.1 dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz dist/vibration_gateway_rpi4_bleak-v1.0.1-linux-arm64.tar.gz.sha256 --title "v1.0.1" --notes-file RELEASE_NOTES.md
```

若 artifact 是在另一台 ARM64 builder 產生，請先確認 checksum、`BUILD_INFO`、`MANIFEST.txt`，再上傳 release asset。

## 禁止事項

- 不要 force push。
- 不要改寫已發布 tag。
- 不要刪除既有 release。
- 不要把 `node_modules/`、wheelhouse、`dist/` commit 進 Git。
- 不要把 local test artifact 當正式 release 上傳。
