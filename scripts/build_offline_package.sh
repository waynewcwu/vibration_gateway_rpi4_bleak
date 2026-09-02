#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION_ARG="${1:-}"
DIST_DIR="${REPO_ROOT}/dist"
FRONTEND_DIR="${REPO_ROOT}/sourcecode/ework/Bluetooth/bt_frontend"
REQUIREMENTS_FILE="${REPO_ROOT}/requirements.txt"
VERSION_FILE="${REPO_ROOT}/VERSION"
MANIFEST_LIB="${SCRIPT_DIR}/lib/manifest.sh"
TMP_DIR=""

usage() {
  echo "Usage: $0 vX.Y.Z"
  echo "Build an ARM64 offline package under dist/."
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}

validate_version() {
  [[ "${VERSION_ARG}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Version must look like v1.0.1"
}

copy_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "${dst}"
  tar \
    --exclude='Bluetooth/bt_frontend/node_modules' \
    --exclude='*/node_modules' \
    --exclude='*/__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*/log/*' \
    --exclude='*/logs/*' \
    --exclude='.git' \
    --exclude='.git.backup' \
    -C "${src}" -cf - . | tar -C "${dst}" -xf -
}

build_python_wheelhouse() {
  local package_dir="$1"
  local wheelhouse="${package_dir}/dependencies/python/wheelhouse"
  mkdir -p "${wheelhouse}"
  cp "${REQUIREMENTS_FILE}" "${package_dir}/dependencies/python/requirements.txt"
  python3 -m pip install --upgrade pip wheel setuptools
  python3 -m pip wheel --wheel-dir "${wheelhouse}" -r "${REQUIREMENTS_FILE}"
}

build_node_dependencies() {
  local package_dir="$1"
  local tmp_dir="$2"
  local node_build="${tmp_dir}/node-build"
  local node_dest="${package_dir}/dependencies/node/bt_frontend_node_modules"

  mkdir -p "${node_build}" "${package_dir}/dependencies/node"
  cp "${FRONTEND_DIR}/package.json" "${node_build}/package.json"
  cp "${FRONTEND_DIR}/package-lock.json" "${node_build}/package-lock.json"
  cp "${FRONTEND_DIR}/package.json" "${package_dir}/dependencies/node/package.json"
  cp "${FRONTEND_DIR}/package-lock.json" "${package_dir}/dependencies/node/package-lock.json"

  (
    cd "${node_build}"
    npm ci --omit=dev --no-audit --fund=false
  )

  cp -a "${node_build}/node_modules" "${node_dest}"
}

write_manifest() {
  local package_dir="$1"
  local manifest_tmp="${TMP_DIR}/MANIFEST.txt"
  (
    cd "${package_dir}"
    canonical_manifest_file_list "${package_dir}" > "${manifest_tmp}"
    mv "${manifest_tmp}" MANIFEST.txt
    while IFS= read -r file; do
      sha256sum "${file}"
    done < MANIFEST.txt > MANIFEST.sha256
    sha256sum MANIFEST.txt >> MANIFEST.sha256
  )
}

main() {
  if [[ "${VERSION_ARG:-}" == "-h" || "${VERSION_ARG:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  validate_version
  need_cmd git
  need_cmd tar
  need_cmd find
  need_cmd sed
  need_cmd sha256sum
  need_cmd python3
  need_cmd npm
  need_cmd node

  [[ -f "${MANIFEST_LIB}" ]] || fail "Missing ${MANIFEST_LIB}"
  # shellcheck source=lib/manifest.sh
  source "${MANIFEST_LIB}"

  [[ -f "${REQUIREMENTS_FILE}" ]] || fail "Missing ${REQUIREMENTS_FILE}"
  [[ -f "${VERSION_FILE}" ]] || fail "Missing ${VERSION_FILE}"
  [[ -f "${FRONTEND_DIR}/package.json" ]] || fail "Missing frontend package.json"
  [[ -f "${FRONTEND_DIR}/package-lock.json" ]] || fail "Missing frontend package-lock.json"

  local source_version
  source_version="$(tr -d '\r\n' < "${VERSION_FILE}")"
  [[ "${VERSION_ARG}" == "v${source_version}" ]] || fail "Requested ${VERSION_ARG} does not match VERSION (${source_version})"
  git -C "${REPO_ROOT}" diff --cached --quiet || fail "Staged source changes exist; commit them before building an artifact"
  git -C "${REPO_ROOT}" diff --quiet --ignore-cr-at-eol || fail "Tracked source changes exist; commit them before building an artifact"
  [[ -z "$(git -C "${REPO_ROOT}" ls-files --others --exclude-standard)" ]] || fail "Untracked source files exist; commit or ignore them before building an artifact"

  local arch
  arch="$(uname -m)"
  [[ "${arch}" == "aarch64" || "${arch}" == "arm64" ]] || fail "Builder must run on ARM64/aarch64, got ${arch}"

  local clean_version="${VERSION_ARG#v}"
  local package_name="vibration_gateway_rpi4_bleak-${VERSION_ARG}-linux-arm64"
  TMP_DIR="$(mktemp -d)"
  trap cleanup EXIT

  local package_dir="${TMP_DIR}/${package_name}"
  mkdir -p "${package_dir}/source" "${package_dir}/dependencies/python" "${package_dir}/dependencies/node" "${DIST_DIR}"

  echo "[1/7] Copying source tree"
  copy_tree "${REPO_ROOT}/sourcecode/ework" "${package_dir}/source/ework"

  echo "[2/7] Copying deployment scripts and docs"
  mkdir -p "${package_dir}/scripts" "${package_dir}/docs" "${package_dir}/systemd" "${package_dir}/config/examples" "${package_dir}/lib"
  cp "${SCRIPT_DIR}/install_offline.sh" "${package_dir}/install_offline.sh"
  cp "${SCRIPT_DIR}/update_offline.sh" "${package_dir}/update_offline.sh"
  cp "${SCRIPT_DIR}/rollback.sh" "${package_dir}/rollback.sh"
  cp "${SCRIPT_DIR}/uninstall.sh" "${package_dir}/uninstall.sh"
  cp "${SCRIPT_DIR}/verify_offline_package.sh" "${package_dir}/verify_offline_package.sh"
  cp "${MANIFEST_LIB}" "${package_dir}/lib/manifest.sh"
  cp -a "${REPO_ROOT}/packaging/systemd/." "${package_dir}/systemd/"
  cp -a "${REPO_ROOT}/config/examples/." "${package_dir}/config/examples/"
  cp -a "${REPO_ROOT}/docs/." "${package_dir}/docs/" 2>/dev/null || true
  chmod +x "${package_dir}"/*.sh

  echo "[3/7] Building Python wheelhouse"
  build_python_wheelhouse "${package_dir}"

  echo "[4/7] Building Node dependencies"
  build_node_dependencies "${package_dir}" "${TMP_DIR}"

  echo "[5/7] Writing build metadata"
  {
    echo "package_version=${VERSION_ARG}"
    echo "source_version=${clean_version}"
    echo "git_commit=$(git -C "${REPO_ROOT}" rev-parse HEAD)"
    echo "git_branch=$(git -C "${REPO_ROOT}" branch --show-current)"
    echo "git_dirty=false"
    echo "target_arch=${arch}"
    echo "python_version=$(python3 --version)"
    echo "node_version=$(node --version)"
    echo "npm_version=$(npm --version)"
    echo "build_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "${package_dir}/BUILD_INFO"
  echo "${clean_version}" > "${package_dir}/VERSION"

  echo "[6/7] Writing manifest and archive"
  write_manifest "${package_dir}"
  tar -C "${TMP_DIR}" -czf "${DIST_DIR}/${package_name}.tar.gz" "${package_name}"

  echo "[7/7] Writing checksum"
  (
    cd "${DIST_DIR}"
    sha256sum "${package_name}.tar.gz" > "${package_name}.tar.gz.sha256"
    sha256sum "${package_name}.tar.gz" > SHA256SUMS
  )

  echo "Built: ${DIST_DIR}/${package_name}.tar.gz"
  echo "Checksum: ${DIST_DIR}/${package_name}.tar.gz.sha256"
  echo "Checksum index: ${DIST_DIR}/SHA256SUMS"
}

main "$@"
