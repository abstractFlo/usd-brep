#!/usr/bin/env bash
# Build cadler's usd-brep wheel for macOS (Apple Silicon), as NVIDIA's README describes it:
# Packman has neither OpenUSD, Python nor the premake package for macOS, so OpenUSD 25.11 (no
# imaging) and premake are built from source first, then this checkout against them, packed by
# cadler/macos-wheel.py into a wheel laid out like the Linux and Windows ones, with the version in
# cadler/version.
#
#   cadler/build-macos.sh [out dir]     the wheel goes to dist/ by default; its path is the last line
#
# OpenUSD is built without Python: usd-brep uses only its C++ API, and nothing in the wheel may
# link libpython (see use_python() in premake5-libraries.lua).
#
# Needs the Xcode command line tools, cmake and uv. OpenUSD and premake land in _deps/ and are
# reused by later runs (about 10 minutes the first time on an M1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$ROOT/cadler/version")"
PY_VERSION="3.12.10"          # python-build-standalone, the Python cadler bundles
OPENUSD_TAG="v25.11"          # the OpenUSD in deps/target-deps.packman.xml (Linux, Windows)
PREMAKE_TAG="v5.0.0-beta2"    # what usd-brep uses on Linux and Windows
DEPS="$ROOT/_deps"
OUT="$(mkdir -p "${1:-$ROOT/dist}" && cd "${1:-$ROOT/dist}" && pwd)"
export MACOSX_DEPLOYMENT_TARGET=12.0

[ "$(uname -s)-$(uname -m)" = "Darwin-arm64" ] || { echo "this builds on Apple Silicon Macs only"; exit 1; }
for tool in cmake uv git; do
  command -v "$tool" >/dev/null || { echo "missing '$tool' - see the top of this script"; exit 1; }
done
mkdir -p "$DEPS" "$ROOT/_build"

# python-build-standalone through uv: relocatable, with libpython next to the binary
UV_PYTHON_INSTALL_DIR="$DEPS/python" uv python install "$PY_VERSION" --quiet
PY_HOME="$(dirname "$(dirname "$(readlink -f "$(UV_PYTHON_INSTALL_DIR="$DEPS/python" uv python find --managed-python "$PY_VERSION")")")")"

usd_src="$DEPS/OpenUSD-${OPENUSD_TAG#v}"
if [ ! -f "$DEPS/usd/lib/libusd_usd.dylib" ]; then
  echo "==> building OpenUSD $OPENUSD_TAG"
  [ -d "$usd_src" ] || curl -fsSL "https://github.com/PixarAnimationStudios/OpenUSD/archive/refs/tags/$OPENUSD_TAG.tar.gz" | tar -xz -C "$DEPS"
  # build_usd.py signs its output through xcodebuild, which only a full Xcode has;
  # macos-wheel.py signs every library it ships instead
  perl -0pi -e 's/(def Codesign\(install_path, verbose_output=False\):\n)(?!    return\n)/$1    return\n/' "$usd_src/build_scripts/apple_utils.py"
  "$PY_HOME/bin/python3" "$usd_src/build_scripts/build_usd.py" "$DEPS/usd" \
    --build-target arm64 --build-variant release --ignore-homebrew --no-python \
    --no-imaging --no-usdview --no-materialx --no-usdValidation \
    --no-examples --no-tutorials --no-tools --no-tests --no-docs --no-python-docs \
    --src "$DEPS/usd-deps-src" --build "$DEPS/usd-build" -j "$(sysctl -n hw.ncpu)" > "$ROOT/_build/openusd.log" 2>&1 \
    || { tail -60 "$ROOT/_build/openusd.log"; echo "OpenUSD build failed, see _build/openusd.log"; exit 1; }
  # the wheel ships OpenUSD's license; the sources are not needed any more
  cp "$usd_src/LICENSE.txt" "$DEPS/usd/LICENSE.txt"
  rm -rf "$DEPS/usd-build" "$DEPS/usd-deps-src" "$usd_src"
fi

premake="$DEPS/premake/bin/release/premake5"
if [ ! -x "$premake" ]; then
  echo "==> building premake $PREMAKE_TAG"
  rm -rf "$DEPS/premake"
  git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$PREMAKE_TAG" https://github.com/premake/premake-core.git "$DEPS/premake"
  # its bundled zlib predates the current macOS SDK
  sed -i '' 's/^#      ifndef fdopen$/#      if 0/' "$DEPS/premake/contrib/zlib/zutil.h"
  (cd "$DEPS/premake" && CFLAGS="-Wno-error=implicit-function-declaration" make -f Bootstrap.mak osx > "$ROOT/_build/premake.log" 2>&1) \
    || { tail -60 "$ROOT/_build/premake.log"; echo "premake build failed, see _build/premake.log"; exit 1; }
fi

echo "==> building usd-brep $VERSION for macOS arm64"
# Packman has neither Python nor OpenUSD for macOS: fetch only pybind11, both are staged below.
# Changed for this build only and put back afterwards.
cp "$ROOT/repo.toml" "$ROOT/_build/repo.toml.orig"
trap 'mv "$ROOT/_build/repo.toml.orig" "$ROOT/repo.toml"' EXIT
perl -0pi -e 's#fetch\.packman_target_files_to_pull = \[\n.*?\]#fetch.packman_target_files_to_pull = [\n    "\${root}/deps/target-deps-python-macos.packman.xml",\n]#s' "$ROOT/repo.toml"

# the premake package Packman looks for, in Packman's cache
packman="${PM_PACKAGES_ROOT:-$DEPS/packman}"
pm="$packman/chk/premake/5.0.0-beta1+nv1-macos-universal"
mkdir -p "$pm/bin" && cp "$premake" "$pm/bin/" && touch "$pm/.packman.sha1"
mkdir -p "$ROOT/_build/target-deps/usd" "$ROOT/_build/schema/omniSolid"
ln -sfn "$PY_HOME" "$ROOT/_build/target-deps/python"
ln -sfn "$DEPS/usd" "$ROOT/_build/target-deps/usd/release"
ln -sfn "$DEPS/usd" "$ROOT/_build/target-deps/usd/debug"

(cd "$ROOT" && PM_PACKAGES_ROOT="$packman" SMLIB_MACOS_ARM64_ONLY=1 \
  ./repo.sh build -p macos-universal -r -j "$(sysctl -n hw.ncpu)" > "$ROOT/_build/cadler-build.log" 2>&1) \
  || { tail -60 "$ROOT/_build/cadler-build.log"; echo "usd-brep build failed, see _build/cadler-build.log"; exit 1; }

built="$("$PY_HOME/bin/python3" "$ROOT/cadler/macos-wheel.py" "$ROOT" "$DEPS/usd" "$ROOT/_build/wheels" \
  2> >(grep -v "invalidate the code signature" >&2))"
wheel="$("$PY_HOME/bin/python3" "$ROOT/cadler/wheel-version.py" "$built" "$VERSION")"
mv "$wheel" "$OUT/"
echo "    $(du -sh "$OUT/$(basename "$wheel")" | cut -f1)"
echo "$OUT/$(basename "$wheel")"
