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
  check_file_in_dir "${dir}" "dependencies/python/wheelhouse"
  check_file_in_dir "${dir}" "dependencies/node/bt_frontend_node_modules"
  check_file_in_dir "${dir}" "systemd/vibration-gateway-bt.service"
  check_file_in_dir "${dir}" "install_offline.sh"
  check_file_in_dir "${dir}" "update_offline.sh"
  check_file_in_dir "${dir}" "rollback.sh"
  check_file_in_dir "${dir}" "uninstall.sh"
  check_file_in_dir "${dir}" "verify_offline_package.sh"

  grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' "${dir}/VERSION" || fail "Invalid VERSION"
  version="$(tr -d '\r\n' < "${dir}/VERSION")"
  grep -Fxq "package_version=v${version}" "${dir}/BUILD_INFO" || fail "BUILD_INFO package version does not match VERSION"
  grep -Fxq "source_version=${version}" "${dir}/BUILD_INFO" || fail "BUILD_INFO source version does not match VERSION"
  grep -Eq '^target_arch=(aarch64|arm64)$' "${dir}/BUILD_INFO" || fail "BUILD_INFO is not ARM64"
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

  find "${dir}/dependencies/python/wheelhouse" -type f -name '*.whl' -print -quit | grep -q . || fail "Python wheelhouse is empty"
  find "${dir}/dependencies/node/bt_frontend_node_modules" -type f -print -quit | grep -q . || fail "Node dependency tree is empty"

  if find "${dir}/dependencies/python/wheelhouse" -type f \( -name '*x86_64*' -o -name '*win32*' -o -name '*win_amd64*' \) -print -quit | grep -q .; then
    fail "Python wheelhouse contains non-ARM64 platform packages"
  fi

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
