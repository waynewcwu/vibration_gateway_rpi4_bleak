#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="${1:-}"
TMP_DIR=""

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}

main() {
  [[ -d "${PACKAGE_DIR}" ]] || fail "Usage: $0 EXTRACTED_PACKAGE_DIR"
  [[ "$(id -u)" -eq 0 ]] || fail "Lifecycle test must run as root"

  TMP_DIR="$(mktemp -d)"
  trap cleanup EXIT
  local install_root="${TMP_DIR}/install"

  "${PACKAGE_DIR}/install_offline.sh" --install-root "${install_root}" --service-mode none
  [[ -L "${install_root}/current" ]] || fail "Installer did not create current symlink"
  [[ -d "${install_root}/current/python/site-packages" ]] || fail "Installed Python dependencies are missing"
  [[ ! -e "${install_root}/current/venv" ]] || fail "Installer unexpectedly created a venv"

  PYTHONNOUSERSITE=1 PYTHONPATH="${install_root}/current/python/site-packages" /usr/bin/python3 -c \
    'import bleak, bluepy.btle, flask, flask_cors, modbus_tk, paho.mqtt.client, serial, websocket_server, xmodem'
  NODE_PATH="${install_root}/current/ework/Bluetooth/bt_frontend/node_modules" node -e \
    "['body-parser','express','formidable','ip','ping','ws'].forEach(require)"

  "${PACKAGE_DIR}/uninstall.sh" --install-root "${install_root}"
  [[ ! -e "${install_root}/current" ]] || fail "Uninstall left the current symlink"
  [[ ! -e "${install_root}/releases" ]] || fail "Uninstall left release directories"
  [[ -d "${install_root}/config" ]] || fail "Default uninstall removed preserved config"

  "${PACKAGE_DIR}/uninstall.sh" --install-root "${install_root}" --purge
  [[ ! -e "${install_root}" ]] || fail "Purge left the install root"
  echo "Offline install/uninstall lifecycle OK"
}

main "$@"
