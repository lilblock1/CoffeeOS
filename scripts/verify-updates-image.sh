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
  /usr/local/sbin/coffee-update \
  /usr/share/coffeeos/release \
  /etc/coffeeos/update.conf \
  /usr/lib/systemd/system/coffee-update-check.service \
  /usr/lib/systemd/system/coffee-update-check.timer; do
  grep -Fq "$path" <<<"$listing" || { echo "ERROR: in-place update payload missing: $path" >&2; exit 5; }
done
status=$(unsquashfs -cat "$rootfs" var/lib/dpkg/status 2>/dev/null || true)
grep -q '^Package: coffeeos-system$' <<<"$status" || { echo 'ERROR: coffeeos-system package is not installed in the image.' >&2; exit 6; }
grep -q '^Status: install ok installed$' <<<"$status" || { echo 'ERROR: dpkg status does not show installed packages correctly.' >&2; exit 7; }
echo 'CoffeeOS in-place updater, periodic checker, release metadata and coffeeos-system package verified inside SquashFS.'
