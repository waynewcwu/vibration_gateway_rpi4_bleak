#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="/opt/vibration_gateway"
PURGE="false"
SERVICES=(
  vibration-gateway-bt.service
  vibration-gateway-backend.service
  vibration-gateway-frontend.service
  vibration-gateway-water.service
)

usage() {
  echo "Usage: sudo $0 [--install-root PATH] [--purge]"
  echo "Default: remove services and releases; preserve config, logs, and data."
  echo "--purge: permanently remove the entire install root, including config, logs, and data."
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-root)
        [[ $# -ge 2 ]] || fail "--install-root requires a path"
        INSTALL_ROOT="$2"
        shift 2
        ;;
      --purge)
        PURGE="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown argument: $1"
        ;;
    esac
  done

  [[ "${INSTALL_ROOT}" == /* && "${INSTALL_ROOT}" != "/" ]] || fail "Install root must be a safe absolute path"
}

remove_services() {
  command -v systemctl >/dev/null 2>&1 || return 0
  local service
  for service in "${SERVICES[@]}"; do
    systemctl stop "${service}" >/dev/null 2>&1 || true
    systemctl disable "${service}" >/dev/null 2>&1 || true
    rm -f "/etc/systemd/system/${service}"
  done
  systemctl daemon-reload
}

main() {
  parse_args "$@"
  [[ "$(id -u)" -eq 0 ]] || fail "Run with sudo/root for uninstall"
  remove_services

  if [[ "${PURGE}" == "true" ]]; then
    echo "WARNING: Permanently removing releases, site config, logs, and runtime data under ${INSTALL_ROOT}" >&2
    rm -rf "${INSTALL_ROOT}"
    echo "Purged ${INSTALL_ROOT}"
    return 0
  fi

  rm -f "${INSTALL_ROOT}/current"
  rm -rf "${INSTALL_ROOT}/releases"
  echo "Program releases removed. Preserved: ${INSTALL_ROOT}/config, ${INSTALL_ROOT}/logs, ${INSTALL_ROOT}/data"
}

main "$@"
