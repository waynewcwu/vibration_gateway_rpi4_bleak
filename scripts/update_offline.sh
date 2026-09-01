#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: sudo $0 [--install-root PATH] [--service-mode systemd|none]"
  echo "Updates are installed as a new release and keep existing runtime config."
}

main() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  "${SCRIPT_DIR}/install_offline.sh" "$@"
}

main "$@"
