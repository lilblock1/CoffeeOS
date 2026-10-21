#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/build"
OUT="$ROOT/dist"
RECIPE="$ROOT/live-build"
ISO="$OUT/coffeeos-0.10.0-dev-amd64.iso"

if [[ $EUID -ne 0 ]]; then
  echo 'Run with sudo/root on a dedicated Debian builder.' >&2; exit 2
fi
for exe in lb debootstrap mksquashfs xorriso sha256sum rsync; do
  if ! command -v "$exe" >/dev/null; then
    echo "Missing dependency: $exe (see README.md)" >&2; exit 3
  fi
done
if [[ ${1:-} == --clean ]]; then
  [[ -d "$WORK" ]] && (cd "$WORK" && lb clean --purge) || true
  rm -rf -- "$WORK"
  echo 'Cleared CoffeeOS build directory.'
  exit 0
fi
if (( $# > 0 )); then echo 'Usage: sudo bash scripts/build-iso.sh [--clean]' >&2; exit 2; fi
mkdir -p "$WORK" "$WORK/config" "$OUT"
# Persist only live-build's downloaded package archives. Do NOT persist the
# bootstrap/chroot stage snapshots or apt indices: those can hide repository
# updates. Fresh indices still select current Debian versions, while matching
# .deb files are reused from the package cache.
if [[ -n ${COFFEE_LIVE_BUILD_CACHE_DIR:-} ]]; then
  mkdir -p "$WORK/cache" "$COFFEE_LIVE_BUILD_CACHE_DIR/packages.bootstrap" "$COFFEE_LIVE_BUILD_CACHE_DIR/packages.chroot"
  rm -rf -- "$WORK/cache/packages.bootstrap" "$WORK/cache/packages.chroot"
  ln -s "$COFFEE_LIVE_BUILD_CACHE_DIR/packages.bootstrap" "$WORK/cache/packages.bootstrap"
  ln -s "$COFFEE_LIVE_BUILD_CACHE_DIR/packages.chroot" "$WORK/cache/packages.chroot"
  echo "Using persistent live-build package cache: $COFFEE_LIVE_BUILD_CACHE_DIR"
fi
# Stamp reproducibility/support metadata into the image before packaging.
mkdir -p "$RECIPE/config/includes.chroot/usr/share/coffeeos"
commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
built_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '{"commit":"%s","built_at":"%s","version":"0.10.0-dev"}\n' "$commit" "$built_at" > "$RECIPE/config/includes.chroot/usr/share/coffeeos/build-info.json"

baseline_tag="$(git -C "$ROOT" for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags/coffeeos-stock-* refs/tags/coffeeos-coffeekernel-* 2>/dev/null | head -n1 || true)"
if [[ -n "$baseline_tag" ]]; then
  git -C "$ROOT" log --no-merges --pretty=format:%s "$baseline_tag..HEAD" | head -50 > "$OUT/coffeeos-changes.txt" || true
else
  git -C "$ROOT" log --no-merges -20 --pretty=format:%s HEAD > "$OUT/coffeeos-changes.txt" || true
fi
python3 - "$OUT/coffeeos-changes.txt" "$baseline_tag" "$built_at" "$RECIPE/config/includes.chroot/usr/share/coffeeos/changelog.json" <<'PYCHANGE'
import json,sys
src,baseline,built_at,dst=sys.argv[1:]
try:
    changes=[x.strip() for x in open(src,encoding='utf-8') if x.strip()]
except OSError:
    changes=[]
with open(dst,'w',encoding='utf-8') as out:
    json.dump({'baseline':baseline or None,'built_at':built_at,'changes':changes},out,indent=2)
    out.write('\n')
PYCHANGE

# Always rebuild the updatable CoffeeOS system package from the current source.
# This makes CoffeeOS-owned files part of dpkg state so future releases can
# replace them through APT, and prevents a stale package from an earlier build.
bash "$ROOT/scripts/build-coffeeos-system-package.sh"
# Copy declarative recipe only. Refuse stale live-build state: a prior build can
# be resumed with `lb build`, but only if the inputs have not changed.
if [[ -e "$WORK/.build/config" ]]; then
  echo 'Existing build state found. Run --clean before rebuilding changed sources.' >&2
  exit 4
fi
cp -a "$RECIPE/auto" "$WORK/"
cp -a "$RECIPE/config/." "$WORK/config/"
cd "$WORK"
# live-build executes auto/config, generating config/* while preserving includes.
lb config
lb build 2>&1 | tee "$OUT/build.log"
image=$(find "$WORK" -maxdepth 1 -type f \( -name '*.hybrid.iso' -o -name '*.iso' \) -print -quit)
if [[ -z "$image" ]]; then echo 'ERROR: lb build did not produce an ISO.' >&2; exit 5; fi
cp -- "$image" "$ISO"
( cd "$OUT" && sha256sum "$(basename "$ISO")" > "$(basename "$ISO").sha256" )
echo "ISO created: $ISO"
echo 'Next: bash scripts/verify-iso.sh && bash scripts/test-qemu.sh --bios'
