#!/usr/bin/env bash
#
# Install the DuckDB CLI, the `snowflake` community extension, and the ADBC
# Snowflake driver the extension depends on -- without root, pip, unzip or wget.
#
# Designed for locked-down runtimes (Orchestra agent sandboxes, slim CI images)
# where the only things you can rely on are curl, python3 and a POSIX shell.
#
# Idempotent: re-running it skips work that is already done.
#
# Environment:
#   DUCKDB_VERSION      Tag to install, e.g. v1.5.6. Default: latest release.
#   DUCKDB_INSTALL_DIR  Where the binary goes. Default: $HOME/.local/duckdb
#
set -euo pipefail

DUCKDB_VERSION="${DUCKDB_VERSION:-latest}"
INSTALL_DIR="${DUCKDB_INSTALL_DIR:-$HOME/.local/duckdb}"
BIN="$INSTALL_DIR/duckdb"

log() { printf '[install] %s\n' "$*" >&2; }
die() { printf '[install] ERROR: %s\n' "$*" >&2; exit 1; }

for tool in curl python3; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool is required but not installed."
done

# ---------------------------------------------------------------------------
# 1. Work out which build we need.
#
# Getting this wrong is the single most common failure: the amd64 zip downloads
# and extracts perfectly happily on an arm64 box, then dies with
# "cannot execute binary file: Exec format error".
# ---------------------------------------------------------------------------
raw_os="$(uname -s)"
raw_arch="$(uname -m)"

case "$raw_os" in
  Linux)  os="linux" ;;
  Darwin) os="osx" ;;
  *)      die "Unsupported OS '$raw_os'. This script handles Linux and macOS." ;;
esac

case "$raw_arch" in
  x86_64|amd64)  arch="amd64"; wheel_arch="x86_64" ;;
  aarch64|arm64) arch="arm64"; wheel_arch="aarch64" ;;
  *)             die "Unsupported architecture '$raw_arch'." ;;
esac

if [ "$os" = "osx" ]; then
  asset="duckdb_cli-osx-universal.zip"
  [ "$arch" = "arm64" ] && wheel_arch="arm64"
else
  asset="duckdb_cli-linux-${arch}.zip"
fi

if [ "$DUCKDB_VERSION" = "latest" ]; then
  url="https://github.com/duckdb/duckdb/releases/latest/download/${asset}"
else
  url="https://github.com/duckdb/duckdb/releases/download/${DUCKDB_VERSION}/${asset}"
fi

# ---------------------------------------------------------------------------
# 2. DuckDB CLI.
# ---------------------------------------------------------------------------
mkdir -p "$INSTALL_DIR"

if [ -x "$BIN" ] && "$BIN" -c "select 1" >/dev/null 2>&1; then
  log "DuckDB CLI already present at $BIN"
else
  log "Downloading $asset ($raw_os/$raw_arch)"
  tmpzip="$(mktemp "${TMPDIR:-/tmp}/duckdb.XXXXXX.zip")"
  trap 'rm -f "$tmpzip"' EXIT
  curl -fsSL --retry 3 --max-time 300 -o "$tmpzip" "$url" \
    || die "Download failed: $url"
  # No unzip in these images; the stdlib is always there.
  python3 -c "
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    z.extractall(sys.argv[2])
" "$tmpzip" "$INSTALL_DIR" || die "Could not extract $asset"
  chmod +x "$BIN"
  rm -f "$tmpzip"
  trap - EXIT
  "$BIN" -c "select 1" >/dev/null 2>&1 \
    || die "DuckDB binary will not run -- most likely an OS/arch mismatch."
fi

version="$("$BIN" -noheader -list -c "select version()" | tr -d '[:space:]')"
platform="$("$BIN" -noheader -list -c "pragma platform" | tr -d '[:space:]')"
log "DuckDB $version ($platform)"

# ---------------------------------------------------------------------------
# 3. The `snowflake` community extension.
# ---------------------------------------------------------------------------
if "$BIN" -c "LOAD snowflake" >/dev/null 2>&1; then
  log "snowflake extension already installed"
else
  log "Installing snowflake community extension"
  "$BIN" -c "INSTALL snowflake FROM community; LOAD snowflake;" >/dev/null \
    || die "Could not install the snowflake community extension."
fi

# ---------------------------------------------------------------------------
# 4. The ADBC Snowflake driver.
#
# The extension is a thin wrapper over Apache Arrow ADBC and is useless without
# libadbc_driver_snowflake. There is no standalone tarball, but the PyPI wheel
# is just a zip with the shared library inside -- so we can fetch it with curl
# and open it with python3, no pip required.
#
# The search path DuckDB uses is stamped with the DuckDB version, so this has
# to be redone whenever you move to a new DuckDB release.
# ---------------------------------------------------------------------------
ext_dir="$HOME/.duckdb/extensions/${version}/${platform}"
mkdir -p "$ext_dir"

if [ "$os" = "osx" ]; then
  driver_name="libadbc_driver_snowflake.dylib"
  plat_tag="macosx"
else
  driver_name="libadbc_driver_snowflake.so"
  plat_tag="manylinux"
fi

if [ -f "$ext_dir/$driver_name" ]; then
  log "ADBC Snowflake driver already installed"
else
  log "Resolving ADBC Snowflake driver wheel from PyPI"
  wheel_url="$(python3 -c "
import json, sys, urllib.request
plat_tag, wheel_arch = sys.argv[1], sys.argv[2]
with urllib.request.urlopen('https://pypi.org/pypi/adbc-driver-snowflake/json', timeout=60) as r:
    data = json.load(r)
for f in data['releases'][data['info']['version']]:
    name = f['filename']
    if name.endswith('.whl') and plat_tag in name and wheel_arch in name:
        print(f['url'])
        break
" "$plat_tag" "$wheel_arch")"

  [ -n "$wheel_url" ] || die "No ADBC driver wheel published for ${plat_tag}/${wheel_arch}."

  log "Downloading ADBC driver"
  tmpwhl="$(mktemp "${TMPDIR:-/tmp}/adbc.XXXXXX.whl")"
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/adbc.XXXXXX")"
  trap 'rm -rf "$tmpwhl" "$tmpdir"' EXIT
  curl -fsSL --retry 3 --max-time 300 -o "$tmpwhl" "$wheel_url" \
    || die "Driver download failed."
  python3 -c "
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    z.extractall(sys.argv[2])
" "$tmpwhl" "$tmpdir"

  found="$(find "$tmpdir" -name "$driver_name" -print -quit)"
  [ -n "$found" ] || die "Wheel did not contain $driver_name."
  cp "$found" "$ext_dir/$driver_name"
  rm -rf "$tmpwhl" "$tmpdir"
  trap - EXIT
  log "Installed $driver_name -> $ext_dir"
fi

log "Done. DuckDB CLI: $BIN"
printf '%s\n' "$BIN"
