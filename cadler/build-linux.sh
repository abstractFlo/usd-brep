#!/usr/bin/env bash
# Build cadler's usd-brep wheel for Linux (x86_64 or aarch64, whichever machine this runs on):
# this checkout, built and packed by NVIDIA's own tooling (prebuild, repo build, repo py_package,
# which also tags it manylinux), then given the version in cadler/version.
#
#   cadler/build-linux.sh [out dir]     the wheel goes to dist/ by default; its path is the last line
#
# Runs on Ubuntu 22.04 (glibc 2.35, usd-brep's Linux ABI) with git, build-essential, binutils,
# patchelf, curl and python3; OpenUSD, Python and premake come from NVIDIA's Packman. Like the
# PyPI wheel it keeps its debug symbols (cadler strips them when it bundles the wheel).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$ROOT/cadler/version")"
OUT="$(mkdir -p "${1:-$ROOT/dist}" && cd "${1:-$ROOT/dist}" && pwd)"
LOG="$ROOT/_build/cadler-build.log"

echo "==> building usd-brep $VERSION for $(uname -m)"
mkdir -p "$ROOT/_build"
rm -rf "$ROOT/_build/py_package"
(cd "$ROOT" && ./prebuild.sh && ./repo.sh build -r -j "$(nproc)" && ./repo.sh py_package -c release) > "$LOG" 2>&1 \
  || { tail -60 "$LOG"; echo "usd-brep build failed, see _build/cadler-build.log"; exit 1; }

built="$(ls "$ROOT"/_build/py_package/wheels/usd_brep-*-manylinux*.whl)"
wheel="$(python3 "$ROOT/cadler/wheel-version.py" "$built" "$VERSION")"
mv "$wheel" "$OUT/"
echo "    $(du -sh "$OUT/$(basename "$wheel")" | cut -f1)"
echo "$OUT/$(basename "$wheel")"
