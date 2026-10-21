#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing ISO: $ISO" >&2; exit 2; }
for exe in xorriso unsquashfs; do command -v "$exe" >/dev/null || { echo "$exe is required." >&2; exit 3; }; done
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
if [[ -n ${COFFEEOS_VERIFY_SQUASHFS:-} && -s ${COFFEEOS_VERIFY_SQUASHFS:-} && -s ${COFFEEOS_VERIFY_SQUASHFS_LIST:-} ]]; then
  rootfs=$COFFEEOS_VERIFY_SQUASHFS
  listing=$(cat "$COFFEEOS_VERIFY_SQUASHFS_LIST")
else
  squash=$(xorriso -indev "$ISO" -find /live -type f -- 2>/dev/null | sed -n 's#.*\(/live/filesystem\.squashfs\).*#\1#p' | head -1)
  [[ -n "$squash" ]] || { echo 'ERROR: live SquashFS not found.' >&2; exit 4; }
  rootfs="$work/rootfs.squashfs"
  xorriso -osirrox on -indev "$ISO" -extract "$squash" "$rootfs" >/dev/null 2>&1
  listing=$(unsquashfs -ll "$rootfs")
fi
for path in \
  /usr/local/bin/coffee-control-center \
  /usr/local/bin/coffee-gaming-preferences \
  /usr/local/sbin/coffee-system-update \
  /usr/local/sbin/coffee-update \
  /usr/share/applications/coffee-control-center.desktop; do
  grep -Fq "$path" <<<"$listing" || { echo "ERROR: Phase 5 payload missing: $path" >&2; exit 5; }
done
echo 'Phase 5 Coffee Control Center payload verified inside SquashFS.'
