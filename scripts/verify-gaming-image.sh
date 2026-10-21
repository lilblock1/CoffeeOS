#!/usr/bin/env bash
# Verify Phase 4 payload in an already-built CoffeeOS ISO without booting it.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing or empty ISO: $ISO" >&2; exit 2; }
for exe in xorriso unsquashfs; do command -v "$exe" >/dev/null || { echo "$exe is required." >&2; exit 3; }; done

tmp=''
if [[ -n ${COFFEEOS_VERIFY_SQUASHFS:-} && -s ${COFFEEOS_VERIFY_SQUASHFS:-} && -s ${COFFEEOS_VERIFY_SQUASHFS_LIST:-} ]]; then
  squashfs=$COFFEEOS_VERIFY_SQUASHFS
  listing=$COFFEEOS_VERIFY_SQUASHFS_LIST
else
  tmp=$(mktemp -d)
  trap 'rm -rf -- "$tmp"' EXIT
  squashfs="$tmp/filesystem.squashfs"
  xorriso -osirrox on -indev "$ISO" -extract /live/filesystem.squashfs "$squashfs" >/dev/null 2>&1 || {
    echo 'ERROR: could not extract live filesystem.squashfs from ISO.' >&2; exit 4;
  }
  listing="$tmp/squashfs.list"
  unsquashfs -ll "$squashfs" > "$listing"
fi
required=(
  '/usr/games/gamemoderun'
  '/usr/bin/mangohud'
  '/usr/bin/vulkaninfo'
  '/usr/local/bin/coffee-gaming-mode'
  '/usr/local/bin/coffee-gaming-info'
  '/usr/local/sbin/coffee-gaming-setup'
  '/usr/local/bin/coffee-proton-manager'
  '/etc/gamemode.ini'
)
for path in "${required[@]}"; do
  grep -Fq "squashfs-root$path" "$listing" || { echo "ERROR: Phase 4 payload missing: $path" >&2; exit 5; }
done

echo 'Phase 4 gaming payload is present in the ISO filesystem.'
