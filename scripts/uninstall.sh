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
  echo "--purge also removes installed release files."
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-root)
        INSTALL_ROOT="${2:-}"
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
}

main() {
  parse_args "$@"
  [[ "$(id -u)" -eq 0 ]] || fail "Run with sudo/root for uninstall"

  if command -v systemctl >/dev/null 2>&1; then
    for service in "${SERVICES[@]}"; do
      systemctl stop "${service}" >/dev/null 2>&1 || true
      systemctl disable "${service}" >/dev/null 2>&1 || true
      rm -f "/etc/systemd/system/${service}"
    done
    systemctl daemon-reload
  fi

  if [[ "${PURGE}" == "true" ]]; then
    if [[ "${INSTALL_ROOT}" == "/" || -z "${INSTALL_ROOT}" ]]; then
      fail "Refusing to purge unsafe install root"
    fi
    rm -rf "${INSTALL_ROOT}"
    echo "Removed ${INSTALL_ROOT}"
  else
    echo "Services removed. Installed files remain at ${INSTALL_ROOT}"
  fi
}

main "$@"
