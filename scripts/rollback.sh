#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="/opt/vibration_gateway"
TARGET_RELEASE=""
SERVICE_MODE="systemd"
SERVICES=(
  vibration-gateway-bt.service
  vibration-gateway-backend.service
  vibration-gateway-frontend.service
  vibration-gateway-water.service
)

usage() {
  echo "Usage: sudo $0 [--install-root PATH] [--target RELEASE_DIR_NAME] [--service-mode systemd|none]"
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
      --target)
        TARGET_RELEASE="${2:-}"
        shift 2
        ;;
      --service-mode)
        SERVICE_MODE="${2:-}"
        shift 2
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

restart_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  command -v systemctl >/dev/null 2>&1 || return 0
  systemctl daemon-reload
  for service in "${SERVICES[@]}"; do
    systemctl restart "${service}" >/dev/null 2>&1 || true
  done
}

select_previous_release() {
  local current_target=""
  if [[ -L "${INSTALL_ROOT}/current" ]]; then
    current_target="$(readlink -f "${INSTALL_ROOT}/current")"
  fi

  find "${INSTALL_ROOT}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | while read -r release; do
    if [[ "${release}" != "${current_target}" ]]; then
      basename "${release}"
      break
    fi
  done
}

main() {
  parse_args "$@"
  [[ "$(id -u)" -eq 0 ]] || fail "Run with sudo/root for rollback"
  [[ -d "${INSTALL_ROOT}/releases" ]] || fail "No releases directory found"

  if [[ -z "${TARGET_RELEASE}" ]]; then
    TARGET_RELEASE="$(select_previous_release)"
  fi
  [[ -n "${TARGET_RELEASE}" ]] || fail "No previous release found"

  local target_path="${INSTALL_ROOT}/releases/${TARGET_RELEASE}"
  [[ -d "${target_path}" ]] || fail "Target release does not exist: ${target_path}"

  echo "Switching current release to ${target_path}"
  ln -sfn "${target_path}" "${INSTALL_ROOT}/current"
  restart_services
  echo "Rollback complete"
}

main "$@"
