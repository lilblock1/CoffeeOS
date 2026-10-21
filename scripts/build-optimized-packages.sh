#!/usr/bin/env bash
# Rebuild selected Debian Trixie source packages with conservative CoffeeOS
# compiler optimizations. A persistent binary cache makes repeated Deep builds
# reuse already-optimized .debs when Debian source + policy are unchanged.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/optimization/packages.tsv"
POLICY="$ROOT/optimization/cache-policy.conf"
MODE=core
JOBS=${COFFEE_OPT_JOBS:-}
CACHE_DIR=${COFFEE_OPT_CACHE_DIR:-/var/cache/coffeeos/optimized-packages}
CCACHE_DIR=${CCACHE_DIR:-/var/cache/coffeeos/ccache}
PACKAGE_REVISION=${COFFEE_PACKAGE_REVISION:-}
# shellcheck disable=SC1090
[[ ! -f $POLICY ]] || source "$POLICY"
CACHE_ABI=${COFFEE_OPT_CACHE_ABI:-1000}
[[ -n $PACKAGE_REVISION ]] || PACKAGE_REVISION=$CACHE_ABI

usage() {
  cat <<'USAGE'
Usage: sudo bash scripts/build-optimized-packages.sh [--mode stock|core|deep] [--jobs N]

stock  Use only official Debian binaries.
core   Rebuild curated high-impact compositor/gaming/UI packages.
deep   Include graphics/audio/input packages such as Mesa and PipeWire.

Deep builds use a persistent content-keyed binary cache. Once a package has been
built for the same Debian source version, architecture, compiler and CoffeeOS
optimization policy, later ISO builds copy the verified cached .debs instead of
compiling it again. ccache is also used for cache misses when available.

The distributable packages never use -march=native; broad x86-64 compatibility
is preserved. Failed optimized package builds are logged and skipped so Debian's
stable binary remains the fallback.
USAGE
}
while (( $# )); do
  case "$1" in
    --mode) MODE=${2:?missing mode}; shift 2 ;;
    --jobs) JOBS=${2:?missing jobs}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ $MODE == stock || $MODE == core || $MODE == deep ]] || { echo "Invalid mode: $MODE" >&2; exit 2; }

choose_jobs() {
  local cpu mem_kb mem_mb mem_jobs jobs
  cpu=$(nproc 2>/dev/null || echo 2)
  mem_kb=$(awk '/MemAvailable:/ {print $2; exit}' /proc/meminfo 2>/dev/null || echo 2097152)
  mem_mb=$((mem_kb / 1024))
  # Large C/C++ packages can consume substantial memory. Aim for about 1.25 GiB
  # available RAM per worker. Modern high-core systems may safely use more than
  # the old 12-job ceiling, while the RAM gate still prevents runaway parallelism.
  mem_jobs=$((mem_mb / 1280))
  (( mem_jobs < 2 )) && mem_jobs=2
  jobs=$cpu
  (( jobs > mem_jobs )) && jobs=$mem_jobs
  (( jobs > 24 )) && jobs=24
  (( jobs < 1 )) && jobs=1
  printf '%s\n' "$jobs"
}
if [[ -z $JOBS ]]; then JOBS=$(choose_jobs); fi
[[ $JOBS =~ ^[1-9][0-9]*$ ]] || { echo 'Jobs must be a positive integer.' >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo 'Run as root on the disposable Debian builder.' >&2; exit 2; }
[[ -f $MANIFEST ]] || { echo "Missing optimization manifest: $MANIFEST" >&2; exit 3; }

PKGDIR="$ROOT/live-build/config/packages.chroot"
WORK="$ROOT/optimized-build"
REPORT="$ROOT/dist/optimized"
STATUS="$REPORT/STATUS.tsv"
mkdir -p "$PKGDIR" "$REPORT" "$CACHE_DIR" "$CCACHE_DIR"
# The CoffeeKernel wrapper runs before this script and stages its image .deb in
# packages.chroot. Clean stale optimized application/library packages without
# deleting the already-built CoffeeKernel or CoffeeOS system package.
find "$PKGDIR" -maxdepth 1 -type f -name '*.deb' ! -name 'linux-image-*-coffee_*.deb' ! -name 'coffeeos-system_*.deb' -delete
rm -rf "$WORK"
mkdir -p "$WORK"
printf 'source\ttier\toptimization\tresult\tbinaries\n' > "$STATUS"
STATUS_LOCK="$REPORT/STATUS.lock"
: > "$STATUS_LOCK"
record_status() {
  local src=$1 tier=$2 opt=$3 result=$4 binaries=$5
  {
    flock -x 9
    printf '%s\t%s\t%s\t%s\t%s\n' "$src" "$tier" "$opt" "$result" "$binaries" >> "$STATUS"
  } 9>>"$STATUS_LOCK"
}

if [[ $MODE == stock ]]; then
  record_status none stock debian-default stock '(none)'
  mkdir -p "$ROOT/live-build/config/includes.chroot/usr/share/coffeeos"
  cp "$STATUS" "$ROOT/live-build/config/includes.chroot/usr/share/coffeeos/optimized-packages.tsv"
  echo 'CoffeeOS optimized package rebuild disabled: using stock Debian binaries.'
  exit 0
fi

for exe in apt-get apt-cache dpkg dpkg-buildpackage dpkg-deb dpkg-parsechangelog python3 sha256sum flock; do
  command -v "$exe" >/dev/null || { echo "Missing build tool: $exe" >&2; exit 3; }
done

# apt source/build-dep requires deb-src metadata. This exists only in the build
# builder and never enters the resulting CoffeeOS image. Reuse the exact
# Signed-By keyring configured by the current Debian builder; Debian images may
# use either the .pgp or .gpg archive-keyring filename and APT rejects duplicate
# repository definitions that disagree on Signed-By.
DEBIAN_ARCHIVE_KEYRING="$(
  awk '/^Signed-By:[[:space:]]*/ {print $2; exit}' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
)"
if [[ -z $DEBIAN_ARCHIVE_KEYRING ]]; then
  for candidate in /usr/share/keyrings/debian-archive-keyring.pgp /usr/share/keyrings/debian-archive-keyring.gpg; do
    [[ -r $candidate ]] && { DEBIAN_ARCHIVE_KEYRING=$candidate; break; }
  done
fi
[[ -n $DEBIAN_ARCHIVE_KEYRING && -r $DEBIAN_ARCHIVE_KEYRING ]] || {
  echo 'Cannot locate the Debian archive keyring used by the build environment.' >&2
  exit 3
}
cat > /etc/apt/sources.list.d/coffeeos-build-src.sources <<SRC
Types: deb-src
URIs: http://deb.debian.org/debian
Suites: trixie trixie-updates
Components: main contrib non-free non-free-firmware
Signed-By: $DEBIAN_ARCHIVE_KEYRING

Types: deb-src
URIs: http://security.debian.org/debian-security
Suites: trixie-security
Components: main contrib non-free non-free-firmware
Signed-By: $DEBIAN_ARCHIVE_KEYRING
SRC
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Languages=none update

if command -v ccache >/dev/null 2>&1; then
  export CCACHE_DIR
  export CCACHE_BASEDIR="$WORK"
  export CCACHE_NOHASHDIR=true
  ccache -M "${COFFEE_CCACHE_MAXSIZE:-15G}" >/dev/null 2>&1 || true
  [[ -d /usr/lib/ccache ]] && export PATH="/usr/lib/ccache:$PATH"
  echo "[CoffeeOS optimize] compiler cache enabled: $CCACHE_DIR"
fi
echo "[CoffeeOS optimize] binary cache: $CACHE_DIR"
echo "[CoffeeOS optimize] parallel jobs: $JOBS"
echo "[CoffeeOS optimize] cache ABI: $CACHE_ABI"

latest_source_version() {
  local source=$1 best='' v
  while read -r v; do
    [[ -n $v ]] || continue
    if [[ -z $best ]] || dpkg --compare-versions "$v" gt "$best"; then best=$v; fi
  done < <(apt-cache showsrc "$source" 2>/dev/null | sed -n 's/^Version: //p')
  printf '%s\n' "$best"
}

cache_key() {
  local source=$1 source_version=$2 tier=$3 opt=$4 regex=$5
  local gccver dpkgver arch material
  gccver=$(gcc -dumpfullversion -dumpversion 2>/dev/null || gcc -dumpversion 2>/dev/null || echo unknown)
  dpkgver=$(dpkg-query -W -f='${Version}' dpkg-dev 2>/dev/null || echo unknown)
  arch=$(dpkg --print-architecture)
  material="source=$source\nversion=$source_version\ntier=$tier\nopt=$opt\nregex=$regex\narch=$arch\ngcc=$gccver\ndpkg-dev=$dpkgver\ncache-abi=$CACHE_ABI\n"
  printf '%b' "$material" | sha256sum | awk '{print $1}'
}

cache_restore() {
  local source=$1 source_version=$2 tier=$3 opt=$4 regex=$5
  local key dir deb pkg version copied=()
  key=$(cache_key "$source" "$source_version" "$tier" "$opt" "$regex")
  dir="$CACHE_DIR/$source/$key"
  [[ -s "$dir/SHA256SUMS" && -s "$dir/METADATA" ]] || return 1
  grep -Fxq "source=$source" "$dir/METADATA" || { rm -rf -- "$dir"; return 1; }
  grep -Fxq "source_version=$source_version" "$dir/METADATA" || { rm -rf -- "$dir"; return 1; }
  grep -Fxq "tier=$tier" "$dir/METADATA" || { rm -rf -- "$dir"; return 1; }
  grep -Fxq "optimization=$opt" "$dir/METADATA" || { rm -rf -- "$dir"; return 1; }
  grep -Fxq "cache_abi=$CACHE_ABI" "$dir/METADATA" || { rm -rf -- "$dir"; return 1; }
  (cd "$dir" && sha256sum -c SHA256SUMS >/dev/null 2>&1) || { rm -rf -- "$dir"; return 1; }
  local matched_primary=0 arch
  shopt -s nullglob
  for deb in "$dir"/*.deb; do
    pkg=$(dpkg-deb -f "$deb" Package 2>/dev/null || true)
    version=$(dpkg-deb -f "$deb" Version 2>/dev/null || true)
    arch=$(dpkg-deb -f "$deb" Architecture 2>/dev/null || true)
    [[ -n $pkg && $version == *"+coffee$PACKAGE_REVISION" && ( $arch == amd64 || $arch == all ) ]] || {
      shopt -u nullglob; rm -rf -- "$dir"; return 1;
    }
    [[ $pkg =~ $regex ]] && matched_primary=1
    cp -f -- "$deb" "$PKGDIR/"
    copied+=("$pkg")
  done
  shopt -u nullglob
  (( ${#copied[@]} > 0 && matched_primary == 1 )) || { rm -rf -- "$dir"; return 1; }
  local joined
  joined=$(IFS=,; echo "${copied[*]}")
  record_status "$source" "$tier" "$opt" cached "$joined"
  echo "[CoffeeOS optimize] CACHE HIT: $source $source_version -> $joined"
  return 0
}

cache_store() {
  local source=$1 source_version=$2 tier=$3 opt=$4 regex=$5
  shift 5
  local key dir tmp deb
  key=$(cache_key "$source" "$source_version" "$tier" "$opt" "$regex")
  dir="$CACHE_DIR/$source/$key"
  tmp="$dir.new.$$"
  rm -rf -- "$tmp"
  mkdir -p "$tmp"
  for deb in "$@"; do cp -f -- "$deb" "$tmp/"; done
  (cd "$tmp" && sha256sum ./*.deb > SHA256SUMS)
  {
    echo "source=$source"
    echo "source_version=$source_version"
    echo "tier=$tier"
    echo "optimization=$opt"
    echo "cache_abi=$CACHE_ABI"
    echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$tmp/METADATA"
  rm -rf -- "$dir"
  mkdir -p "$(dirname "$dir")"
  mv -- "$tmp" "$dir"
}

bump_changelog() {
  local changelog=$1
  COFFEE_PACKAGE_REVISION="$PACKAGE_REVISION" python3 - "$changelog" <<'PY'
from pathlib import Path
import os, re, sys
p=Path(sys.argv[1])
lines=p.read_text(encoding='utf-8').splitlines()
if not lines:
    raise SystemExit('empty changelog')
m=re.match(r'^(\S+) \(([^)]+)\)(.*)$', lines[0])
if not m:
    raise SystemExit('unrecognized changelog header')
version=m.group(2)
if '+coffee' not in version:
    version += '+coffee' + os.environ['COFFEE_PACKAGE_REVISION']
lines[0] = f'{m.group(1)} ({version}){m.group(3)}'
p.write_text('\n'.join(lines)+'\n', encoding='utf-8')
PY
}

declare -A PRE_CACHED=() PRE_VERSION=()
BATCH_BUILD_DEPS_OK=0

build_one() {
  local source=$1 tier=$2 opt=$3 regex=$4 build_jobs=${5:-$JOBS}
  local source_version planned_version box srcdir
  if [[ ${PRE_CACHED[$source]:-0} == 1 ]]; then return 0; fi
  planned_version=${PRE_VERSION[$source]:-}
  source_version=$planned_version
  [[ -n $source_version ]] || source_version=$(latest_source_version "$source")
  if [[ -z $source_version ]]; then
    echo "WARNING: cannot resolve source version for $source; using Debian binary." >&2
    record_status "$source" "$tier" "$opt" fallback-version '(none)'
    return 0
  fi
  echo
  echo "[CoffeeOS optimize] $source $source_version ($tier / $opt)"
  if cache_restore "$source" "$source_version" "$tier" "$opt" "$regex"; then return 0; fi
  echo "[CoffeeOS optimize] CACHE MISS: compiling $source"
  box="$WORK/$source"
  mkdir -p "$box"
  if ! (cd "$box" && apt-get source "$source=$source_version") >"$box/source.log" 2>&1; then
    # Some source names/versions are only accepted without an explicit version.
    if ! (cd "$box" && apt-get source "$source") >>"$box/source.log" 2>&1; then
      echo "WARNING: source download failed for $source; using Debian binary." >&2
      record_status "$source" "$tier" "$opt" fallback-source '(none)'
      return 0
    fi
  fi
  srcdir=$(find "$box" -mindepth 1 -maxdepth 1 -type d -exec test -f '{}/debian/changelog' ';' -print | head -n1)
  if [[ -z $srcdir ]]; then
    echo "WARNING: source tree not found for $source; using Debian binary." >&2
    record_status "$source" "$tier" "$opt" fallback-source-tree '(none)'
    return 0
  fi
  source_version=$(dpkg-parsechangelog -l"$srcdir/debian/changelog" -SVersion)
  # The cache lookup used apt metadata. If apt-get selected a different version,
  # try the exact content key once more before compiling.
  if cache_restore "$source" "$source_version" "$tier" "$opt" "$regex"; then return 0; fi
  if (( BATCH_BUILD_DEPS_OK == 0 )) || [[ -n $planned_version && $source_version != "$planned_version" ]]; then
    if ! apt-get build-dep -y --no-install-recommends --only-source "$source" >"$box/build-dep.log" 2>&1; then
      echo "WARNING: build dependencies failed for $source; using Debian binary." >&2
      record_status "$source" "$tier" "$opt" fallback-build-dep '(none)'
      return 0
    fi
  else
    echo 'Build dependencies satisfied by the combined Ultra Fast Deep transaction.' >"$box/build-dep.log"
  fi
  bump_changelog "$srcdir/debian/changelog"

  # Debian's buildflags keep security hardening. LTO is an official
  # dpkg-buildflags optimization feature. O3 is limited to curated leaf apps.
  export DEB_BUILD_OPTIONS="parallel=$build_jobs nocheck nodoc noautodbgsym terse"
  export DEB_BUILD_MAINT_OPTIONS='hardening=+all optimize=+lto'
  unset DEB_CFLAGS_MAINT_APPEND DEB_CXXFLAGS_MAINT_APPEND
  if [[ $opt == o3-lto ]]; then
    export DEB_CFLAGS_MAINT_APPEND='-O3'
    export DEB_CXXFLAGS_MAINT_APPEND='-O3'
  fi
  # Compatibility invariant for one ISO intended for old and new x86-64 CPUs.
  if env | grep -E '^(CFLAGS|CXXFLAGS|DEB_.*FLAGS).*march=native' >/dev/null; then
    echo 'Refusing -march=native in distributable CoffeeOS package builds.' >&2
    exit 8
  fi

  if ! (cd "$srcdir" && dpkg-buildpackage -b -us -uc -j"$build_jobs") >"$box/build.log" 2>&1; then
    echo "WARNING: optimized build failed for $source; using Debian binary. See $box/build.log" >&2
    record_status "$source" "$tier" "$opt" fallback-build '(none)'
    return 0
  fi

  local copied=() cache_debs=() deb pkg deps changed
  declare -A deb_for_pkg=() selected=()
  shopt -s nullglob
  for deb in "$box"/*.deb; do
    pkg=$(dpkg-deb -f "$deb" Package 2>/dev/null || true)
    [[ -n $pkg ]] || continue
    deb_for_pkg["$pkg"]="$deb"
    if [[ $pkg =~ $regex ]]; then selected["$pkg"]=1; fi
  done
  changed=1
  while (( changed )); do
    changed=0
    for pkg in "${!selected[@]}"; do
      deb=${deb_for_pkg[$pkg]:-}
      [[ -n $deb ]] || continue
      deps="$(dpkg-deb -f "$deb" Pre-Depends Depends 2>/dev/null || true)"
      for candidate in "${!deb_for_pkg[@]}"; do
        [[ ${selected[$candidate]:-0} == 1 ]] && continue
        if grep -Eq "(^|[ ,|])${candidate//+/\\+}(:[a-z0-9-]+)?([ (>,<|]|$)" <<<"$deps"; then
          selected["$candidate"]=1
          changed=1
        fi
      done
    done
  done
  for pkg in "${!selected[@]}"; do
    deb=${deb_for_pkg[$pkg]}
    case "$pkg" in
      *-dbgsym|*-dev|*-doc|*-tests|*-test)
        echo "WARNING: runtime dependency closure for $source requested non-runtime package $pkg; falling back to Debian binary." >&2
        record_status "$source" "$tier" "$opt" fallback-nonruntime-dependency "$pkg"
        shopt -u nullglob
        return 0
        ;;
    esac
    cp -f -- "$deb" "$PKGDIR/"
    copied+=("$pkg")
    cache_debs+=("$deb")
  done
  shopt -u nullglob
  if (( ${#copied[@]} == 0 )); then
    echo "WARNING: $source built but no approved runtime package matched; using Debian binary." >&2
    record_status "$source" "$tier" "$opt" fallback-no-runtime-deb '(none)'
  else
    local joined
    joined=$(IFS=,; echo "${copied[*]}")
    record_status "$source" "$tier" "$opt" optimized "$joined"
    cache_store "$source" "$source_version" "$tier" "$opt" "$regex" "${cache_debs[@]}"
    echo "Optimized runtime packages: $joined"
    echo "[CoffeeOS optimize] cached for future builds: $source $source_version"
  fi
}

# First resolve cache hits. Only true misses participate in one combined
# apt-get build-dep transaction, avoiding 10+ separate dpkg/apt resolver passes
# on a cold Deep build. If the combined transaction fails, each package falls
# back to the older per-package dependency path for robustness.
miss_specs=()
while IFS='|' read -r source tier opt regex; do
  [[ -n ${source:-} && ${source:0:1} != '#' ]] || continue
  [[ $tier == core || $tier == deep ]] || { echo "Bad tier in $MANIFEST: $tier" >&2; exit 4; }
  [[ $MODE == core && $tier == deep ]] && continue
  source_version=$(latest_source_version "$source")
  PRE_VERSION["$source"]=$source_version
  [[ -n $source_version ]] || continue
  if cache_restore "$source" "$source_version" "$tier" "$opt" "$regex"; then
    PRE_CACHED["$source"]=1
  else
    miss_specs+=("$source=$source_version")
  fi
done < "$MANIFEST"

if (( ${#miss_specs[@]} > 0 )); then
  echo "[CoffeeOS optimize] installing build dependencies for ${#miss_specs[@]} cache miss(es) in one APT transaction."
  if apt-get build-dep -y --no-install-recommends --only-source "${miss_specs[@]}" >"$WORK/build-deps-batch.log" 2>&1; then
    BATCH_BUILD_DEPS_OK=1
  else
    echo 'WARNING: combined build-dependency transaction failed; retrying dependencies per source package.' >&2
  fi
fi

# Compile independent source packages concurrently while keeping the total compiler
# job budget bounded. This is substantially faster than feeding all cores to one
# small package at a time, and it still leaves the CoffeeKernel build split in
# control of the machine-wide budget.
workers=1
if [[ ${COFFEE_LOW_MEMORY_BUILD:-0} == 1 ]]; then
  workers=1
elif (( JOBS >= 16 )); then
  workers=4
elif (( JOBS >= 9 )); then
  workers=3
elif (( JOBS >= 6 )); then
  workers=2
fi
per_build_jobs=$((JOBS / workers))
(( per_build_jobs < 1 )) && per_build_jobs=1
echo "[CoffeeOS optimize] source-package concurrency: $workers build(s) x $per_build_jobs job(s) (budget=$JOBS)"

running=0
parallel_fail=0
while IFS='|' read -r source tier opt regex; do
  [[ -n ${source:-} && ${source:0:1} != '#' ]] || continue
  [[ $tier == core || $tier == deep ]] || { echo "Bad tier in $MANIFEST: $tier" >&2; exit 4; }
  if [[ $MODE == core && $tier == deep ]]; then
    record_status "$source" "$tier" "$opt" skipped-by-mode '(none)'
    continue
  fi
  build_one "$source" "$tier" "$opt" "$regex" "$per_build_jobs" &
  ((running+=1))
  if (( running >= workers )); then
    if ! wait -n; then parallel_fail=1; fi
    ((running-=1))
  fi
done < "$MANIFEST"
while (( running > 0 )); do
  if ! wait -n; then parallel_fail=1; fi
  ((running-=1))
done
(( parallel_fail == 0 )) || { echo 'ERROR: one or more optimized package worker processes failed unexpectedly.' >&2; exit 9; }

mkdir -p "$ROOT/live-build/config/includes.chroot/usr/share/coffeeos"
cp "$STATUS" "$ROOT/live-build/config/includes.chroot/usr/share/coffeeos/optimized-packages.tsv"

count=$(find "$PKGDIR" -maxdepth 1 -type f -name '*.deb' | wc -l)
hits=$(awk -F '\t' '$4=="cached"{n++} END{print n+0}' "$STATUS")
built=$(awk -F '\t' '$4=="optimized"{n++} END{print n+0}' "$STATUS")
echo
printf 'CoffeeOS optimized package stage complete: %s custom runtime .deb package(s) staged.\n' "$count"
printf 'Deep cache summary: %s source package(s) reused, %s source package(s) compiled.\n' "$hits" "$built"
echo "Audit report: $STATUS"
command -v ccache >/dev/null 2>&1 && ccache -s || true
