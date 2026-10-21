#!/usr/bin/env bash
# Compile CoffeeKernel image and matching header Debian packages from Debian's
# patched kernel source, using upstream make bindeb-pkg. No foreign repo.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${COFFEE_KERNEL_WORK:-$ROOT/build/kernel}"
DEST="${COFFEE_KERNEL_DIST:-$ROOT/dist/kernels}"
SOURCE_DIR="${COFFEE_KERNEL_SOURCE_DIR:-}"
SOURCE_IS_DIRECTORY=0
SOURCE_TAR="${COFFEE_KERNEL_SOURCE_TARBALL:-/usr/src/linux-source-6.12.tar.xz}"
BASE_CONFIG="${COFFEE_KERNEL_BASE_CONFIG:-/usr/src/linux-config-6.12/config.amd64_none_amd64.xz}"
JOBS="${COFFEE_KERNEL_JOBS:-2}"
REVISION="${COFFEE_KERNEL_REVISION:-}"
POLICY="$ROOT/optimization/cache-policy.conf"
# shellcheck disable=SC1090
[[ ! -f $POLICY ]] || source "$POLICY"
[[ -n $REVISION ]] || REVISION=${COFFEE_KERNEL_CACHE_ABI:-1000}
DRY_RUN=0
usage() {
  cat <<'EOF'
Usage: scripts/build-kernel.sh [--jobs N]
       [--source DIR] [--source-tarball FILE] [--base-config FILE]
       [--dry-run]
Use a disposable Debian 13 amd64 build environment. Needs 30+ GB free per
build (and time/RAM for kernel builds). Source & Debian config must match.
EOF
}
while (( $# )); do
  case "$1" in
    --jobs) JOBS="${2:?missing jobs}"; shift 2;;
    --source) SOURCE_DIR="${2:?missing path}"; SOURCE_IS_DIRECTORY=1; shift 2;;
    --source-tarball) SOURCE_TAR="${2:?missing path}"; shift 2;;
    --base-config) BASE_CONFIG="${2:?missing path}"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2;;
  esac
done
[[ $JOBS =~ ^[1-9][0-9]*$ && $REVISION =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid jobs/revision (positive integer required)' >&2; exit 2; }
if [[ $DRY_RUN == 1 ]]; then
  printf 'CoffeeKernel plan: ONE kernel, jobs=%s source=%s base-config=%s\n' "$JOBS" "${SOURCE_DIR:-$SOURCE_TAR}" "$BASE_CONFIG"
  printf '%s\n' 'Source: Debian trixie patched kernel; unsigned amd64 .deb image+headers; fallback Debian linux-image-amd64 untouched.'
  exit 0
fi
[[ $(uname -m) == x86_64 ]] || { echo 'This builder targets amd64 only.' >&2; exit 3; }
for bin in make tar dpkg-deb python3 sha256sum gcc bc flex bison rsync xz dpkg-query; do
  command -v "$bin" >/dev/null || { echo "Missing command: $bin" >&2; exit 3; }
done
# ccache is optional but dramatically reduces repeated kernel compile time. The
# wrapper points CCACHE_DIR at a persistent build cache that survives source staging.
if command -v ccache >/dev/null 2>&1; then
  export CCACHE_DIR=${CCACHE_DIR:-/var/cache/coffeeos/ccache}
  mkdir -p "$CCACHE_DIR"
  ccache -M "${COFFEE_CCACHE_MAXSIZE:-15G}" >/dev/null 2>&1 || true
  [[ -d /usr/lib/ccache ]] && export PATH="/usr/lib/ccache:$PATH"
fi
[[ -f $BASE_CONFIG ]] || { echo "Missing Debian baseline config: $BASE_CONFIG" >&2; exit 3; }
mkdir -p "$WORK" "$DEST"
if [[ -z $SOURCE_DIR ]]; then
  [[ -f $SOURCE_TAR ]] || { echo "Missing Debian kernel source: $SOURCE_TAR" >&2; exit 3; }
  mkdir -p "$WORK/source"
  # Extract once into a disposable build directory, not into system locations.
  current_sha="$(sha256sum "$SOURCE_TAR" | awk '{print $1}')"
  if [[ -f $WORK/source/.extracted ]] && [[ $(cat "$WORK/source/.extracted") != "$current_sha" ]]; then
    echo 'Source archive changed since extraction. Remove build/kernel/source and rebuild.' >&2; exit 4
  fi
  if [[ ! -e $WORK/source/.extracted ]]; then
    [[ -z $(ls -A "$WORK/source") ]] || { echo 'Existing source extraction found; remove build/kernel/source first.' >&2; exit 4; }
    tar -xf "$SOURCE_TAR" -C "$WORK/source"
    printf "%s\n" "$current_sha" > "$WORK/source/.extracted"
  fi
  mapfile -t candidates < <(find "$WORK/source" -mindepth 2 -maxdepth 2 -type f -name Makefile | sort)
  [[ ${#candidates[@]} == 1 ]] || { echo 'Cannot identify unique extracted kernel Makefile' >&2; exit 4; }
  SOURCE_DIR="$(dirname "${candidates[0]}")"
fi
[[ -f $SOURCE_DIR/Makefile && -f $SOURCE_DIR/scripts/Makefile.package ]] || { echo "Not a full Linux source tree: $SOURCE_DIR" >&2; exit 3; }
SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
BASE_CONFIG="$(realpath "$BASE_CONFIG")"
KERNEL_VERSION="$(make -s -C "$SOURCE_DIR" kernelversion | tail -n 1)"
[[ $KERNEL_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Unexpected kernel version: $KERNEL_VERSION" >&2; exit 4; }
# Do not accidentally pair a 6.12 Debian baseline with an unrelated upstream tree.
BASE_SERIES="$(basename "$(dirname "$BASE_CONFIG")" | sed -n 's/^linux-config-//p')"
if [[ -n $BASE_SERIES && $KERNEL_VERSION != "$BASE_SERIES".* ]]; then
  echo "Mismatched config series: $BASE_SERIES vs $KERNEL_VERSION" >&2; exit 4
fi
# Use Debian's *complete* source-package version when building from the
# installed Debian source. This avoids collisions when Debian republishes a
# security-fix revision without changing the upstream 6.12.x patch number.
DEB_VERSION="${KERNEL_VERSION}-1coffee${REVISION}"
if [[ $SOURCE_IS_DIRECTORY == 0 && -z ${COFFEE_KERNEL_SOURCE_DIR:-} ]]; then
  src_version="$(dpkg-query -W -f='${Version}' linux-source-6.12 2>/dev/null || true)"
  cfg_version="$(dpkg-query -W -f='${Version}' linux-config-6.12 2>/dev/null || true)"
  [[ -n $src_version && $src_version == "$cfg_version" ]] || {
    echo "Source and config Debian packages must match: linux-source=$src_version linux-config=$cfg_version" >&2; exit 4
  }
  [[ $src_version == "$KERNEL_VERSION"-* ]] || {
    echo "Installed Debian source package $src_version does not match extracted $KERNEL_VERSION" >&2; exit 4
  }
  DEB_VERSION="${src_version}+coffee${REVISION}"
fi
kind=coffee
{
  OBJECT="$WORK/$kind/object"
  TARGET="$DEST/$kind"
  FRAGMENT="$ROOT/kernel/configs/$kind.conf"
  mkdir -p "$OBJECT" "$TARGET"
  # One isolated kernel build; stale .config/packages are rejected.
  if [[ -e "$OBJECT/.config" || -e "$OBJECT/debian" ]]; then
    echo "Existing output tree ($OBJECT). Delete it before a new build." >&2
    exit 4
  fi
  python3 "$ROOT/kernel/tools/configure.py" --base "$BASE_CONFIG" --fragment "$FRAGMENT" --output "$OBJECT/.config"
  make -C "$SOURCE_DIR" O="$OBJECT" olddefconfig
  python3 "$ROOT/kernel/tools/configure.py" --base "$OBJECT/.config" --fragment "$FRAGMENT" --verify
  expected_hz=1000
  if ! grep -qx "CONFIG_HZ=$expected_hz" "$OBJECT/.config"; then
    echo "Expected HZ=$expected_hz after olddefconfig; kernel config is inconsistent." >&2; exit 5
  fi
  printf '\nBuilding CoffeeKernel (%s), %s jobs\n' "$DEB_VERSION" "$JOBS"
  # LOCALVERSION fixes one CoffeeKernel ABI/uname -r suffix and package
  # name; KDEB_PKGVERSION allows revisioned APT upgrades of the binary .deb.
  make -C "$SOURCE_DIR" O="$OBJECT" -j "$JOBS" bindeb-pkg \
    LOCALVERSION="-coffee" KDEB_PKGVERSION="$DEB_VERSION" \
    KDEB_SOURCENAME=linux-coffeekernel \
    KBUILD_BUILD_USER=coffeeos KBUILD_BUILD_HOST=builder
  # With O=, packages are written to the parent of the object directory.
  shopt -s nullglob
  debs=("$WORK/$kind"/*.deb)
  images=() headers=()
  for deb in "${debs[@]}"; do
    pkg="$(dpkg-deb -f "$deb" Package)"
    case "$pkg" in
      linux-image-*-coffee) images+=("$deb");;
      linux-headers-*-coffee) headers+=("$deb");;
      *) echo "Not publishing additional upstream output: $pkg";;
    esac
  done
  [[ ${#images[@]} == 1 && ${#headers[@]} == 1 ]] || {
    echo "FAILED: expected 1 image and 1 headers package for CoffeeKernel (got ${#images[@]} and ${#headers[@]})." >&2; exit 5;
  }
  for deb in "${images[@]}" "${headers[@]}"; do
    [[ $(dpkg-deb -f "$deb" Version) == "$DEB_VERSION" ]] || { echo "Unexpected package version in $deb" >&2; exit 5; }
    cp -- "$deb" "$TARGET/"
  done
  ( cd "$TARGET" && sha256sum ./*.deb > SHA256SUMS )
  env COFFEE_PROVENANCE_SOURCE_DIR="$SOURCE_DIR" \
    COFFEE_PROVENANCE_BASE_CONFIG="$BASE_CONFIG" \
    COFFEE_PROVENANCE_FRAGMENT="$FRAGMENT" \
    COFFEE_PROVENANCE_KERNEL_VERSION="$KERNEL_VERSION" \
    COFFEE_PROVENANCE_PACKAGE_VERSION="$DEB_VERSION" \
    COFFEE_PROVENANCE_CONFIG="$OBJECT/.config" \
    COFFEE_PROVENANCE_TARBALL="$(if [[ $SOURCE_IS_DIRECTORY == 1 || -n ${COFFEE_KERNEL_SOURCE_DIR:-} ]]; then echo ""; else echo "$SOURCE_TAR"; fi)" \
    COFFEE_PROVENANCE_OUT="$TARGET/build-info.json" \
    python3 "$ROOT/kernel/tools/provenance.py"
  echo "Created verified ONE CoffeeKernel package pair: $TARGET"
}
printf '\nCoffeeKernel packages staged at %s. NOT installed or boot-tested.\n' "$DEST"
