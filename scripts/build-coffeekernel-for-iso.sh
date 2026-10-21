#!/usr/bin/env bash
# Build or restore the single CoffeeKernel image for the ISO. The cache key is
# independent of the CoffeeOS UI release number: if Debian's kernel source,
# CoffeeKernel config and compiler are unchanged, a later ISO can reuse the
# verified kernel .debs instead of recompiling Linux from scratch.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE=core
JOBS=${COFFEE_KERNEL_JOBS:-}
CACHE_DIR=${COFFEE_KERNEL_CACHE_DIR:-/var/cache/coffeeos/coffeekernel}
CCACHE_DIR=${CCACHE_DIR:-/var/cache/coffeeos/ccache}
POLICY="$ROOT/optimization/cache-policy.conf"
# shellcheck disable=SC1090
[[ ! -f $POLICY ]] || source "$POLICY"
CACHE_ABI=${COFFEE_KERNEL_CACHE_ABI:-1000}
while (( $# )); do
  case "$1" in
    --mode) MODE=${2:?missing mode}; shift 2 ;;
    --jobs) JOBS=${2:?missing jobs}; shift 2 ;;
    -h|--help) echo 'Usage: build-coffeekernel-for-iso.sh --mode stock|core|deep [--jobs N]'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$MODE" in stock|core|deep) ;; *) echo "Invalid mode: $MODE" >&2; exit 2 ;; esac
PKGDIR="$ROOT/live-build/config/packages.chroot"
AUDITDIR="$ROOT/live-build/config/includes.chroot/usr/share/coffeeos"
mkdir -p "$PKGDIR" "$AUDITDIR" "$CACHE_DIR" "$CCACHE_DIR"
rm -f "$PKGDIR"/linux-image-*-coffee_*.deb "$PKGDIR"/linux-headers-*-coffee_*.deb
if [[ $MODE == stock ]]; then
  printf 'kernel=debian-stock\nmode=stock\n' > "$AUDITDIR/kernel-build-status.txt"
  echo 'CoffeeKernel build skipped in stock mode; Debian fallback kernel only.'
  exit 0
fi

choose_jobs() {
  local cpu mem_kb mem_mb mem_jobs jobs
  cpu=$(nproc 2>/dev/null || echo 2)
  mem_kb=$(awk '/MemAvailable:/ {print $2; exit}' /proc/meminfo 2>/dev/null || echo 2097152)
  mem_mb=$((mem_kb / 1024))
  mem_jobs=$((mem_mb / 1024))
  (( mem_jobs < 2 )) && mem_jobs=2
  jobs=$cpu
  (( jobs > mem_jobs )) && jobs=$mem_jobs
  (( jobs > 24 )) && jobs=24
  (( jobs < 1 )) && jobs=1
  printf '%s\n' "$jobs"
}
[[ -n $JOBS ]] || JOBS=$(choose_jobs)

source_version=$(dpkg-query -W -f='${Version}' linux-source-6.12 2>/dev/null || true)
config_version=$(dpkg-query -W -f='${Version}' linux-config-6.12 2>/dev/null || true)
[[ -n $source_version && $source_version == "$config_version" ]] || {
  echo "CoffeeKernel source/config packages are missing or mismatched: source=$source_version config=$config_version" >&2
  exit 4
}
fragment="$ROOT/kernel/configs/coffee.conf"
[[ -f $fragment ]] || { echo "Missing CoffeeKernel config fragment: $fragment" >&2; exit 4; }
fragment_sha=$(sha256sum "$fragment" | awk '{print $1}')
gccver=$(gcc -dumpfullversion -dumpversion 2>/dev/null || gcc -dumpversion 2>/dev/null || echo unknown)
material="source=$source_version\nconfig=$config_version\nfragment=$fragment_sha\ngcc=$gccver\narch=$(dpkg --print-architecture)\ncache-abi=$CACHE_ABI\n"
key=$(printf '%b' "$material" | sha256sum | awk '{print $1}')
cache="$CACHE_DIR/$key"

restore_cache() {
  [[ -s "$cache/SHA256SUMS" && -s "$cache/build-info.json" ]] || return 1
  (cd "$cache" && sha256sum -c SHA256SUMS >/dev/null 2>&1) || { rm -rf -- "$cache"; return 1; }
  shopt -s nullglob
  local images=("$cache"/linux-image-*-coffee_*.deb)
  local headers=("$cache"/linux-headers-*-coffee_*.deb)
  shopt -u nullglob
  [[ ${#images[@]} == 1 && ${#headers[@]} == 1 ]] || { rm -rf -- "$cache"; return 1; }
  mkdir -p "$ROOT/dist/kernels/coffee"
  rm -f "$ROOT/dist/kernels/coffee"/*.deb "$ROOT/dist/kernels/coffee"/SHA256SUMS "$ROOT/dist/kernels/coffee"/build-info.json
  cp -f -- "${images[0]}" "${headers[0]}" "$ROOT/dist/kernels/coffee/"
  cp -f -- "$cache/build-info.json" "$ROOT/dist/kernels/coffee/"
  (cd "$ROOT/dist/kernels/coffee" && sha256sum ./*.deb > SHA256SUMS)
  cp -f -- "${images[0]}" "${headers[0]}" "$PKGDIR/"
  {
    echo 'kernel=CoffeeKernel'
    echo "mode=$MODE"
    echo 'cache=hit'
    echo "cache_key=$key"
    echo "image=$(basename "${images[0]}")"
    echo "headers=$(basename "${headers[0]}")"
    echo 'fallback=linux-image-amd64'
  } > "$AUDITDIR/kernel-build-status.txt"
  cp -f -- "$cache/build-info.json" "$AUDITDIR/coffeekernel-build-info.json"
  echo "[CoffeeOS kernel] CACHE HIT: reusing $(basename "${images[0]}")"
  return 0
}

if restore_cache; then exit 0; fi

echo "[CoffeeOS kernel] CACHE MISS: compiling CoffeeKernel with $JOBS job(s)."
export COFFEE_KERNEL_WORK="$ROOT/optimized-kernel-build"
export COFFEE_KERNEL_DIST="$ROOT/dist/kernels"
export COFFEE_KERNEL_REVISION="$CACHE_ABI"
export CCACHE_DIR
rm -rf -- "$COFFEE_KERNEL_WORK" "$COFFEE_KERNEL_DIST/coffee"
bash "$ROOT/scripts/build-kernel.sh" --jobs "$JOBS"
shopt -s nullglob
images=("$COFFEE_KERNEL_DIST/coffee"/linux-image-*-coffee_*.deb)
headers=("$COFFEE_KERNEL_DIST/coffee"/linux-headers-*-coffee_*.deb)
shopt -u nullglob
[[ ${#images[@]} == 1 && ${#headers[@]} == 1 ]] || {
  echo "Expected one CoffeeKernel image and one headers package; got ${#images[@]} image(s), ${#headers[@]} headers." >&2
  exit 5
}
cp -f -- "${images[0]}" "${headers[0]}" "$PKGDIR/"
{
  echo 'kernel=CoffeeKernel'
  echo "mode=$MODE"
  echo 'cache=miss-built'
  echo "cache_key=$key"
  echo "image=$(basename "${images[0]}")"
  echo "headers=$(basename "${headers[0]}")"
  echo 'fallback=linux-image-amd64'
} > "$AUDITDIR/kernel-build-status.txt"
cp -f -- "$COFFEE_KERNEL_DIST/coffee/build-info.json" "$AUDITDIR/coffeekernel-build-info.json"

# Publish atomically into the persistent build cache only after the kernel build
# has produced and checksummed both required packages.
tmp="$cache.new.$$"
rm -rf -- "$tmp"; mkdir -p "$tmp"
cp -f -- "${images[0]}" "${headers[0]}" "$COFFEE_KERNEL_DIST/coffee/build-info.json" "$tmp/"
(cd "$tmp" && sha256sum ./*.deb > SHA256SUMS)
rm -rf -- "$cache"; mv -- "$tmp" "$cache"
echo "[CoffeeOS kernel] cached for future builds: $cache"
echo "Staged CoffeeKernel image for ISO: $(basename "${images[0]}")"
echo "Staged CoffeeKernel headers in ISO for DKMS: $(basename "${headers[0]}")"
