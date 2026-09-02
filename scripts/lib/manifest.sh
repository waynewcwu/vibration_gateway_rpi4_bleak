#!/usr/bin/env bash

canonical_manifest_file_list() {
  local package_dir="$1"

  (
    export LC_ALL=C
    cd "${package_dir}"
    find . -type f ! -name 'MANIFEST.txt' ! -name 'MANIFEST.sha256' \
      | sort \
      | sed 's#^\./##'
  )
}
