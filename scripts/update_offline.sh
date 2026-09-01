#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="/opt/vibration_gateway"

usage() {
  echo "Usage: sudo $0 [--install-root PATH] [--service-mode systemd|none]"
  echo "Installs this package as a new release and preserves shared config, logs, and data."
}

find_install_root() {
  local args=("$@")
  local index
  for ((index = 0; index < ${#args[@]}; index++)); do
    if [[ "${args[index]}" == "--install-root" && $((index + 1)) -lt ${#args[@]} ]]; then
      INSTALL_ROOT="${args[index + 1]}"
    fi
  done
}

main() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  find_install_root "$@"
  [[ -L "${INSTALL_ROOT}/current" ]] || {
    echo "ERROR: No current installation found at ${INSTALL_ROOT}/current; use install_offline.sh first" >&2
    exit 1
  }

  local current_version="unknown"
  local new_version="unknown"
  [[ -f "${INSTALL_ROOT}/current/VERSION" ]] && current_version="$(tr -d '\r\n' < "${INSTALL_ROOT}/current/VERSION")"
  [[ -f "${SCRIPT_DIR}/VERSION" ]] && new_version="$(tr -d '\r\n' < "${SCRIPT_DIR}/VERSION")"
  echo "Offline update: ${current_version} -> ${new_version}"

  "${SCRIPT_DIR}/install_offline.sh" "$@"
}

main "$@"
