#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR=""

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}

find_utf8_locales() {
  locale -a | awk 'BEGIN { IGNORECASE=1 } /^(C|en_US|en_GB)\.(UTF-8|utf8)$/ { print }'
}

generate_for_locale() {
  local locale_name="$1"
  local fixture_dir="$2"
  local output_file="$3"

  (
    export LANG="${locale_name}"
    export LC_ALL="${locale_name}"
    canonical_manifest_file_list "${fixture_dir}" > "${output_file}"
  )
}

main() {
  command -v locale >/dev/null 2>&1 || fail "Missing command: locale"
  command -v cmp >/dev/null 2>&1 || fail "Missing command: cmp"

  # shellcheck source=../scripts/lib/manifest.sh
  source "${REPO_ROOT}/scripts/lib/manifest.sh"

  local utf8_locales
  utf8_locales="$(find_utf8_locales)"
  [[ -n "${utf8_locales}" ]] || fail "No C/en_US/en_GB UTF-8 locale is available"

  TMP_DIR="$(mktemp -d)"
  trap cleanup EXIT

  local fixture_dir="${TMP_DIR}/fixture"
  mkdir -p \
    "${fixture_dir}/config/examples/Bluetooth/conf" \
    "${fixture_dir}/dependencies/node/node_modules/@scope/pkg" \
    "${fixture_dir}/dependencies/node/node_modules/pkg"
  touch \
    "${fixture_dir}/VERSION" \
    "${fixture_dir}/config/examples/Bluetooth/conf/config.ini.example" \
    "${fixture_dir}/dependencies/node/node_modules/@scope/pkg/Alpha.js" \
    "${fixture_dir}/dependencies/node/node_modules/pkg/a.js" \
    "${fixture_dir}/dependencies/node/node_modules/pkg/$(printf '\303\244').js" \
    "${fixture_dir}/MANIFEST.txt" \
    "${fixture_dir}/MANIFEST.sha256"

  generate_for_locale "C" "${fixture_dir}" "${TMP_DIR}/manifest.C"

  local utf8_locale
  local tested_locales="C"
  while IFS= read -r utf8_locale; do
    [[ -n "${utf8_locale}" ]] || continue
    generate_for_locale "${utf8_locale}" "${fixture_dir}" "${TMP_DIR}/manifest.${utf8_locale}"
    cmp "${TMP_DIR}/manifest.C" "${TMP_DIR}/manifest.${utf8_locale}" || fail "Canonical manifest differs between C and ${utf8_locale}"
    tested_locales="${tested_locales}, ${utf8_locale}"
  done <<< "${utf8_locales}"

  if grep -Eq '(^|/)MANIFEST\.(txt|sha256)$' "${TMP_DIR}/manifest.C"; then
    fail "Canonical manifest contains a self-reference"
  fi

  echo "Manifest locale regression OK: ${tested_locales}"
}

main "$@"
