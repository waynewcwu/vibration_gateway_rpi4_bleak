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
        [[ $# -ge 2 ]] || fail "--install-root requires a path"
        INSTALL_ROOT="$2"
        shift 2
        ;;
      --target)
        [[ $# -ge 2 ]] || fail "--target requires a release directory name"
        TARGET_RELEASE="$2"
        shift 2
        ;;
      --service-mode)
        [[ $# -ge 2 ]] || fail "--service-mode requires systemd or none"
        SERVICE_MODE="$2"
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

  [[ "${INSTALL_ROOT}" == /* && "${INSTALL_ROOT}" != "/" ]] || fail "Install root must be a safe absolute path"
  [[ "${SERVICE_MODE}" == "systemd" || "${SERVICE_MODE}" == "none" ]] || fail "Invalid service mode"
  [[ -z "${TARGET_RELEASE}" || ( "${TARGET_RELEASE}" != */* && "${TARGET_RELEASE}" != "." && "${TARGET_RELEASE}" != ".." ) ]] || fail "Target must be a release directory name"
}

stop_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  local service
  for service in "${SERVICES[@]}"; do
    systemctl stop "${service}" >/dev/null 2>&1 || true
  done
}

start_and_verify_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  local service
  local deadline=$((SECONDS + 30))
  local all_active

  systemctl daemon-reload || return 1
  for service in "${SERVICES[@]}"; do
    systemctl restart "${service}" || return 1
  done

  while (( SECONDS < deadline )); do
    all_active="true"
    for service in "${SERVICES[@]}"; do
      if systemctl is-failed --quiet "${service}"; then
        systemctl status "${service}" --no-pager --lines=20 >&2 || true
        return 1
      fi
      systemctl is-active --quiet "${service}" || all_active="false"
    done
    [[ "${all_active}" == "true" ]] && return 0
    sleep 1
  done
  return 1
}

select_previous_release() {
  local current_target=""
  [[ -L "${INSTALL_ROOT}/current" ]] && current_target="$(readlink -f "${INSTALL_ROOT}/current")"

  find "${INSTALL_ROOT}/releases" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' \
    | sort -nr \
    | cut -d' ' -f2- \
    | while IFS= read -r release; do
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
  [[ "${SERVICE_MODE}" == "none" ]] || command -v systemctl >/dev/null 2>&1 || fail "Missing command: systemctl"

  local previous_target=""
  [[ -L "${INSTALL_ROOT}/current" ]] && previous_target="$(readlink -f "${INSTALL_ROOT}/current")"
  [[ -n "${TARGET_RELEASE}" ]] || TARGET_RELEASE="$(select_previous_release)"
  [[ -n "${TARGET_RELEASE}" ]] || fail "No previous release found"

  local target_path="${INSTALL_ROOT}/releases/${TARGET_RELEASE}"
  [[ -d "${target_path}" ]] || fail "Target release does not exist: ${target_path}"
  [[ "${target_path}" != "${previous_target}" ]] || fail "Target release is already current"

  echo "Rolling back to ${target_path}"
  stop_services
  ln -sfn "${target_path}" "${INSTALL_ROOT}/current"

  if ! start_and_verify_services; then
    echo "Rollback target failed service verification; restoring original release" >&2
    stop_services
    if [[ -n "${previous_target}" && -d "${previous_target}" ]]; then
      ln -sfn "${previous_target}" "${INSTALL_ROOT}/current"
      start_and_verify_services || echo "WARNING: Original release services also failed" >&2
    fi
    fail "Rollback failed"
  fi

  echo "Rollback complete: $(readlink -f "${INSTALL_ROOT}/current")"
}

main "$@"
