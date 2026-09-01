#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"
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
  check_file_in_dir "${dir}" "VERSION"
  check_file_in_dir "${dir}" "BUILD_INFO"
  check_file_in_dir "${dir}" "MANIFEST.txt"
  check_file_in_dir "${dir}" "source/ework/Bluetooth/bleak_v2q1.py"
  check_file_in_dir "${dir}" "source/ework/Bluetooth/bt_webapi_v3.py"
  check_file_in_dir "${dir}" "source/ework/Bluetooth/bt_frontend/index.js"
  check_file_in_dir "${dir}" "dependencies/python/requirements.txt"
  check_file_in_dir "${dir}" "dependencies/python/wheelhouse"
  check_file_in_dir "${dir}" "dependencies/node/bt_frontend_node_modules"
  check_file_in_dir "${dir}" "systemd/vibration-gateway-bt.service"
  check_file_in_dir "${dir}" "install_offline.sh"

  if find "${dir}/source" -path '*/node_modules/*' -print -quit | grep -q .; then
    fail "Source tree contains node_modules; dependencies must live under dependencies/"
  fi

  echo "Package directory OK: ${dir}"
}

verify_archive() {
  local archive="$1"
  [[ -f "${archive}" ]] || fail "Package not found: ${archive}"

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
  verify_dir "${package_dir}"
}

main() {
  if [[ -z "${TARGET}" || "${TARGET}" == "-h" || "${TARGET}" == "--help" ]]; then
    usage
    exit 0
  fi

  if [[ -d "${TARGET}" ]]; then
    verify_dir "${TARGET}"
  else
    verify_archive "${TARGET}"
  fi
}

main "$@"
