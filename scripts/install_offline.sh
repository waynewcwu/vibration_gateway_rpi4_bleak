#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="/opt/vibration_gateway"
SERVICE_MODE="systemd"
SERVICES=(
  vibration-gateway-bt.service
  vibration-gateway-backend.service
  vibration-gateway-frontend.service
  vibration-gateway-water.service
)

usage() {
  echo "Usage: sudo $0 [--install-root PATH] [--service-mode systemd|none]"
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

as_root_required() {
  [[ "$(id -u)" -eq 0 ]] || fail "Run with sudo/root for installation"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-root)
        INSTALL_ROOT="${2:-}"
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
  [[ -n "${INSTALL_ROOT}" ]] || fail "Install root cannot be empty"
  [[ "${SERVICE_MODE}" == "systemd" || "${SERVICE_MODE}" == "none" ]] || fail "Invalid service mode"
}

stop_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  command -v systemctl >/dev/null 2>&1 || return 0
  for service in "${SERVICES[@]}"; do
    systemctl stop "${service}" >/dev/null 2>&1 || true
  done
}

preserve_runtime_config() {
  local current_dir="$1"
  local release_dir="$2"
  local pairs=(
    "ework/Bluetooth/conf/config.ini"
    "ework/Bluetooth/conf/config2.ini"
    "ework/water_detection/config/Parameter.conf"
  )

  [[ -d "${current_dir}" ]] || return 0
  for rel_path in "${pairs[@]}"; do
    if [[ -f "${current_dir}/${rel_path}" ]]; then
      mkdir -p "$(dirname "${release_dir}/${rel_path}")"
      cp -a "${current_dir}/${rel_path}" "${release_dir}/${rel_path}"
    fi
  done
}

install_python_deps() {
  local release_dir="$1"
  local requirements="${PACKAGE_DIR}/dependencies/python/requirements.txt"
  local wheelhouse="${PACKAGE_DIR}/dependencies/python/wheelhouse"

  [[ -f "${requirements}" ]] || fail "Missing package Python requirements"
  [[ -d "${wheelhouse}" ]] || fail "Missing package Python wheelhouse"

  python3 -m venv --system-site-packages "${release_dir}/venv"
  "${release_dir}/venv/bin/python" -m pip install --no-index --find-links "${wheelhouse}" -r "${requirements}"
}

install_node_deps() {
  local release_dir="$1"
  local node_src="${PACKAGE_DIR}/dependencies/node/bt_frontend_node_modules"
  local frontend_dir="${release_dir}/ework/Bluetooth/bt_frontend"

  [[ -d "${node_src}" ]] || fail "Missing package Node dependencies"
  rm -rf "${frontend_dir}/node_modules"
  cp -a "${node_src}" "${frontend_dir}/node_modules"
}

install_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  need_cmd systemctl

  for service in "${SERVICES[@]}"; do
    local template="${PACKAGE_DIR}/systemd/${service}"
    [[ -f "${template}" ]] || fail "Missing systemd template: ${service}"
    sed "s#@INSTALL_ROOT@#${INSTALL_ROOT}#g" "${template}" > "/etc/systemd/system/${service}"
  done

  systemctl daemon-reload
  for service in "${SERVICES[@]}"; do
    systemctl enable "${service}"
    systemctl restart "${service}"
  done
}

main() {
  parse_args "$@"
  as_root_required
  need_cmd python3
  need_cmd tar
  need_cmd sed

  [[ -d "${PACKAGE_DIR}/source/ework" ]] || fail "Missing package source/ework"
  [[ -f "${PACKAGE_DIR}/VERSION" ]] || fail "Missing package VERSION"

  local version
  version="$(tr -d '\r\n' < "${PACKAGE_DIR}/VERSION")"
  local stamp
  stamp="$(date +%Y%m%d%H%M%S)"
  local release_dir="${INSTALL_ROOT}/releases/${version}-${stamp}"
  local current_link="${INSTALL_ROOT}/current"

  echo "[1/6] Creating release directory ${release_dir}"
  mkdir -p "${release_dir}"
  cp -a "${PACKAGE_DIR}/source/ework" "${release_dir}/ework"
  mkdir -p "${release_dir}/scripts"
  cp -a "${PACKAGE_DIR}/install_offline.sh" "${release_dir}/scripts/install_offline.sh"
  cp -a "${PACKAGE_DIR}/update_offline.sh" "${release_dir}/scripts/update_offline.sh"
  cp -a "${PACKAGE_DIR}/rollback.sh" "${release_dir}/scripts/rollback.sh"
  cp -a "${PACKAGE_DIR}/uninstall.sh" "${release_dir}/scripts/uninstall.sh"
  cp -a "${PACKAGE_DIR}/verify_offline_package.sh" "${release_dir}/scripts/verify_offline_package.sh"
  mkdir -p "${release_dir}/ework/log" "${release_dir}/ework/Bluetooth/log" "${release_dir}/ework/water_detection/log"

  echo "[2/6] Preserving runtime config when upgrading"
  preserve_runtime_config "${current_link}" "${release_dir}"

  echo "[3/6] Installing offline Python dependencies"
  install_python_deps "${release_dir}"

  echo "[4/6] Installing offline Node dependencies"
  install_node_deps "${release_dir}"

  echo "[5/6] Switching current release"
  stop_services
  ln -sfn "${release_dir}" "${current_link}"

  echo "[6/6] Installing services"
  install_services

  echo "Installed version ${version} at ${release_dir}"
}

main "$@"
