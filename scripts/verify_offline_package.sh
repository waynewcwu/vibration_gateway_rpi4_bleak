#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"
MANIFEST_LIB="${SCRIPT_DIR}/lib/manifest.sh"
TMP_DIR=""

usage() {
  echo "Usage: $0 PACKAGE.tar.gz|EXTRACTED_PACKAGE_DIR"
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}

check_file_in_dir() {
  local dir="$1"
  local path="$2"
  [[ -e "${dir}/${path}" ]] || fail "Missing ${path}"
}

verify_dir() {
  local dir="$1"
  local manifest_output=""
  local version=""

  check_file_in_dir "${dir}" "VERSION"
  check_file_in_dir "${dir}" "BUILD_INFO"
  check_file_in_dir "${dir}" "MANIFEST.txt"
  check_file_in_dir "${dir}" "MANIFEST.sha256"
  check_file_in_dir "${dir}" "lib/manifest.sh"
  check_file_in_dir "${dir}" "source/ework/Bluetooth/bleak_v2q1.py"
  check_file_in_dir "${dir}" "source/ework/Bluetooth/bt_webapi_v3.py"
  check_file_in_dir "${dir}" "source/ework/Bluetooth/bt_frontend/index.js"
  check_file_in_dir "${dir}" "dependencies/python/requirements.txt"
  check_file_in_dir "${dir}" "dependencies/python/site-packages"
  check_file_in_dir "${dir}" "dependencies/python/site-packages/bluepy/bluepy-helper"
  check_file_in_dir "${dir}" "dependencies/node/bt_frontend/package.json"
  check_file_in_dir "${dir}" "dependencies/node/bt_frontend/package-lock.json"
  check_file_in_dir "${dir}" "dependencies/node/bt_frontend/node_modules"
  check_file_in_dir "${dir}" "systemd/frontend.service"
  check_file_in_dir "${dir}" "systemd/backend.service"
  check_file_in_dir "${dir}" "systemd/bt_gateway.service"
  check_file_in_dir "${dir}" "install_offline.sh"
  check_file_in_dir "${dir}" "rollback.sh"
  check_file_in_dir "${dir}" "uninstall.sh"
  check_file_in_dir "${dir}" "verify_offline_package.sh"

  grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' "${dir}/VERSION" || fail "Invalid VERSION"
  version="$(tr -d '\r\n' < "${dir}/VERSION")"
  grep -Fxq "package_version=v${version}" "${dir}/BUILD_INFO" || fail "BUILD_INFO package version does not match VERSION"
  grep -Fxq "source_version=${version}" "${dir}/BUILD_INFO" || fail "BUILD_INFO source version does not match VERSION"
  grep -Eq '^target_arch=(aarch64|arm64)$' "${dir}/BUILD_INFO" || fail "BUILD_INFO is not ARM64"
  grep -Fxq 'target_os=debian-11-bullseye' "${dir}/BUILD_INFO" || fail "BUILD_INFO target OS is not Bullseye"
  grep -Fxq 'target_python=3.9' "${dir}/BUILD_INFO" || fail "BUILD_INFO target Python is not 3.9"
  grep -Fxq 'target_node_min=12' "${dir}/BUILD_INFO" || fail "BUILD_INFO target Node.js is not 12+"
  grep -Fxq 'target_glibc=2.31' "${dir}/BUILD_INFO" || fail "BUILD_INFO target glibc is not 2.31"
  grep -Eq '^git_commit=[0-9a-f]{40}$' "${dir}/BUILD_INFO" || fail "BUILD_INFO has no valid Git commit"
  grep -Fxq 'git_dirty=false' "${dir}/BUILD_INFO" || fail "Artifact was not built from a clean Git worktree"

  if ! manifest_output="$(cd "${dir}" && sha256sum -c MANIFEST.sha256 2>&1)"; then
    echo "${manifest_output}" | tail -n 20 >&2
    fail "Package manifest checksum failed"
  fi

  if ! canonical_manifest_file_list "${dir}" | diff - "${dir}/MANIFEST.txt" >/dev/null; then
    fail "Package file list does not match MANIFEST.txt"
  fi

  if find "${dir}/source" -path '*/node_modules/*' -print -quit | grep -q .; then
    fail "Source tree contains node_modules; dependencies must live under dependencies/"
  fi

  [[ ! -e "${dir}/source/ework/ecosystem.config.js" ]] || fail "Package contains obsolete PM2 ecosystem configuration"
  if find "${dir}/dependencies/node/bt_frontend/node_modules" -iname '*pm2*' -print -quit | grep -q .; then
    fail "Package contains obsolete PM2 dependencies"
  fi
  if find "${dir}/systemd" -maxdepth 1 -type f \
    ! -name 'frontend.service' \
    ! -name 'backend.service' \
    ! -name 'bt_gateway.service' \
    -print -quit | grep -q .; then
    fail "Package contains an unsupported systemd service"
  fi

  find "${dir}/dependencies/python/site-packages" -type f -print -quit | grep -q . || fail "Python runtime dependencies are empty"
  find "${dir}/dependencies/python/site-packages/RPi" -type f -name '_GPIO*.so' -print -quit | grep -q . || fail "RPi.GPIO native extension is missing"
  find "${dir}/dependencies/node/bt_frontend/node_modules" -type f -print -quit | grep -q . || fail "Node dependency tree is empty"

  [[ ! -e "${dir}/dependencies/python/wheelhouse" ]] || fail "Package contains obsolete Python wheelhouse"
  [[ ! -e "${dir}/dependencies/node/bt_frontend_node_modules" ]] || fail "Package contains obsolete Node dependency layout"
  [[ ! -e "${dir}/update_offline.sh" ]] || fail "Package contains obsolete update wrapper"

  echo "Package directory OK: ${dir}"
}

verify_archive() {
  local archive="$1"
  [[ -f "${archive}" ]] || fail "Package not found: ${archive}"

  tar -tzf "${archive}" >/dev/null || fail "Archive integrity check failed"

  if [[ -f "${archive}.sha256" ]]; then
    (
      cd "$(dirname "${archive}")"
      sha256sum -c "$(basename "${archive}.sha256")"
    )
  fi

  TMP_DIR="$(mktemp -d)"
  trap cleanup EXIT
  tar -xzf "${archive}" -C "${TMP_DIR}"

  local package_dir
  package_dir="$(find "${TMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [[ -n "${package_dir}" ]] || fail "Archive did not contain a package directory"
  [[ "$(find "${TMP_DIR}" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 1 ]] || fail "Archive must contain exactly one package directory"
  verify_dir "${package_dir}"
}

main() {
  if [[ -z "${TARGET}" || "${TARGET}" == "-h" || "${TARGET}" == "--help" ]]; then
    usage
    exit 0
  fi

  [[ -f "${MANIFEST_LIB}" ]] || fail "Missing ${MANIFEST_LIB}"
  # shellcheck source=lib/manifest.sh
  source "${MANIFEST_LIB}"

  if [[ -d "${TARGET}" ]]; then
    verify_dir "${TARGET}"
  else
    verify_archive "${TARGET}"
  fi
}

main "$@"
