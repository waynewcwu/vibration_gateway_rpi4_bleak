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

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-root)
        [[ $# -ge 2 ]] || fail "--install-root requires a path"
        INSTALL_ROOT="$2"
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
}

check_platform() {
  [[ "$(uname -s)" == "Linux" ]] || fail "Offline install supports Linux only"
  local arch
  arch="$(uname -m)"
  [[ "${arch}" == "aarch64" || "${arch}" == "arm64" ]] || fail "Offline install requires ARM64/aarch64, got ${arch}"
}

check_package() {
  [[ -x "${PACKAGE_DIR}/verify_offline_package.sh" ]] || fail "Missing executable package verifier"
  "${PACKAGE_DIR}/verify_offline_package.sh" "${PACKAGE_DIR}"

  local service
  for service in "${SERVICES[@]}"; do
    [[ -f "${PACKAGE_DIR}/systemd/${service}" ]] || fail "Missing systemd template: ${service}"
  done
}

stop_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  local service
  for service in "${SERVICES[@]}"; do
    systemctl stop "${service}" >/dev/null 2>&1 || true
  done
}

verify_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  local deadline=$((SECONDS + 30))
  local service
  local all_active

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

  for service in "${SERVICES[@]}"; do
    systemctl is-active "${service}" >&2 || true
  done
  return 1
}

install_and_start_services() {
  [[ "${SERVICE_MODE}" == "systemd" ]] || return 0
  local service

  for service in "${SERVICES[@]}"; do
    sed "s#@INSTALL_ROOT@#${INSTALL_ROOT}#g" "${PACKAGE_DIR}/systemd/${service}" > "/etc/systemd/system/${service}" || return 1
  done

  systemctl daemon-reload || return 1
  for service in "${SERVICES[@]}"; do
    systemctl enable "${service}" || return 1
    systemctl restart "${service}" || return 1
  done
  verify_services
}

copy_config_if_missing() {
  local destination="$1"
  shift
  [[ -f "${destination}" ]] && return 0

  local candidate
  for candidate in "$@"; do
    if [[ -f "${candidate}" ]]; then
      cp -a "${candidate}" "${destination}"
      return 0
    fi
  done
  fail "No initial configuration available for ${destination}"
}

initialize_shared_state() {
  local old_release="$1"
  local bt_config="${INSTALL_ROOT}/config/Bluetooth/conf"
  local water_config="${INSTALL_ROOT}/config/water_detection"

  mkdir -p "${bt_config}" "${water_config}" "${INSTALL_ROOT}/logs/Bluetooth" "${INSTALL_ROOT}/logs/water_detection" "${INSTALL_ROOT}/data"

  copy_config_if_missing "${bt_config}/config.ini" \
    "${old_release}/ework/Bluetooth/conf/config.ini" \
    "${PACKAGE_DIR}/source/ework/Bluetooth/conf/config.ini"
  copy_config_if_missing "${bt_config}/config2.ini" \
    "${old_release}/ework/Bluetooth/conf/config2.ini" \
    "${PACKAGE_DIR}/source/ework/Bluetooth/conf/config2.ini"
  copy_config_if_missing "${water_config}/Parameter.conf" \
    "${old_release}/ework/water_detection/config/Parameter.conf" \
    "${PACKAGE_DIR}/source/ework/water_detection/config/Parameter.conf"

  if [[ ! -f "${bt_config}/backup.ini" ]]; then
    if [[ -f "${old_release}/ework/Bluetooth/conf/backup.ini" ]]; then
      cp -a "${old_release}/ework/Bluetooth/conf/backup.ini" "${bt_config}/backup.ini"
    elif [[ -f "${PACKAGE_DIR}/source/ework/Bluetooth/conf/backup.ini" ]]; then
      cp -a "${PACKAGE_DIR}/source/ework/Bluetooth/conf/backup.ini" "${bt_config}/backup.ini"
    fi
  fi
}

link_shared_state() {
  local release_dir="$1"

  rm -rf "${release_dir}/ework/Bluetooth/conf" "${release_dir}/ework/Bluetooth/log"
  rm -rf "${release_dir}/ework/water_detection/config" "${release_dir}/ework/water_detection/log"
  ln -s "${INSTALL_ROOT}/config/Bluetooth/conf" "${release_dir}/ework/Bluetooth/conf"
  ln -s "${INSTALL_ROOT}/logs/Bluetooth" "${release_dir}/ework/Bluetooth/log"
  ln -s "${INSTALL_ROOT}/config/water_detection" "${release_dir}/ework/water_detection/config"
  ln -s "${INSTALL_ROOT}/logs/water_detection" "${release_dir}/ework/water_detection/log"
  ln -s "${INSTALL_ROOT}/data" "${release_dir}/data"
}

install_python_deps() {
  local release_dir="$1"
  local requirements="${PACKAGE_DIR}/dependencies/python/requirements.txt"
  local wheelhouse="${PACKAGE_DIR}/dependencies/python/wheelhouse"

  python3 -m venv --system-site-packages "${release_dir}/venv"
  "${release_dir}/venv/bin/python" -m pip install --no-index --find-links "${wheelhouse}" -r "${requirements}"
}

install_node_deps() {
  local release_dir="$1"
  local node_src="${PACKAGE_DIR}/dependencies/node/bt_frontend_node_modules"
  local frontend_dir="${release_dir}/ework/Bluetooth/bt_frontend"

  rm -rf "${frontend_dir}/node_modules"
  cp -a "${node_src}" "${frontend_dir}/node_modules"
}

restore_previous_release() {
  local previous_release="$1"

  echo "Service activation failed; restoring previous release" >&2
  stop_services
  if [[ -n "${previous_release}" && -d "${previous_release}" ]]; then
    ln -sfn "${previous_release}" "${INSTALL_ROOT}/current"
    install_and_start_services || echo "WARNING: Previous release services also failed; inspect systemctl status" >&2
  else
    rm -f "${INSTALL_ROOT}/current"
  fi
}

main() {
  parse_args "$@"
  [[ "$(id -u)" -eq 0 ]] || fail "Run with sudo/root for installation"
  check_platform
  need_cmd python3
  need_cmd node
  need_cmd sed
  need_cmd sha256sum
  need_cmd diff
  [[ "${SERVICE_MODE}" == "none" ]] || need_cmd systemctl
  check_package

  local version
  version="$(tr -d '\r\n' < "${PACKAGE_DIR}/VERSION")"
  local previous_release=""
  local previous_version="none"
  if [[ -L "${INSTALL_ROOT}/current" ]]; then
    previous_release="$(readlink -f "${INSTALL_ROOT}/current")"
    if [[ -f "${previous_release}/VERSION" ]]; then
      previous_version="$(tr -d '\r\n' < "${previous_release}/VERSION")"
    fi
  fi

  local stamp
  stamp="$(date +%Y%m%d%H%M%S)"
  local release_dir="${INSTALL_ROOT}/releases/${version}-${stamp}"
  [[ ! -e "${release_dir}" ]] || fail "Release directory already exists: ${release_dir}"

  echo "Installing ${version}; current version: ${previous_version}"
  mkdir -p "${release_dir}/scripts"
  cp -a "${PACKAGE_DIR}/source/ework" "${release_dir}/ework"
  cp -a "${PACKAGE_DIR}/VERSION" "${PACKAGE_DIR}/BUILD_INFO" "${release_dir}/"
  cp -a "${PACKAGE_DIR}/install_offline.sh" "${PACKAGE_DIR}/update_offline.sh" "${PACKAGE_DIR}/rollback.sh" "${PACKAGE_DIR}/uninstall.sh" "${PACKAGE_DIR}/verify_offline_package.sh" "${release_dir}/scripts/"

  initialize_shared_state "${previous_release}"
  link_shared_state "${release_dir}"
  install_python_deps "${release_dir}"
  install_node_deps "${release_dir}"

  stop_services
  ln -sfn "${release_dir}" "${INSTALL_ROOT}/current"
  if ! install_and_start_services; then
    restore_previous_release "${previous_release}"
    fail "Installation rolled back because service verification failed"
  fi

  echo "Installed version ${version} at ${release_dir}"
  echo "Current release: $(readlink -f "${INSTALL_ROOT}/current")"
}

main "$@"
