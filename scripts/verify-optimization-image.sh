#!/usr/bin/env bash
# Verify optimization/kernel/installer payload inside a built CoffeeOS ISO.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing or empty ISO: $ISO" >&2; exit 2; }
for exe in xorriso unsquashfs; do command -v "$exe" >/dev/null || { echo "$exe is required." >&2; exit 3; }; done

tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
if [[ -n ${COFFEEOS_VERIFY_SQUASHFS:-} && -s ${COFFEEOS_VERIFY_SQUASHFS:-} && -s ${COFFEEOS_VERIFY_SQUASHFS_LIST:-} ]]; then
  squashfs=$COFFEEOS_VERIFY_SQUASHFS
  listing=$COFFEEOS_VERIFY_SQUASHFS_LIST
else
  squashfs="$tmp/filesystem.squashfs"
  xorriso -osirrox on -indev "$ISO" -extract /live/filesystem.squashfs "$squashfs" >/dev/null 2>&1 || {
    echo 'ERROR: could not extract live filesystem.squashfs from ISO.' >&2; exit 4;
  }
  listing="$tmp/squashfs.list"
  unsquashfs -ll "$squashfs" > "$listing"
fi
required=(
  '/usr/share/coffeeos/kernel-build-status.txt'
  '/usr/share/coffeeos/optimized-packages.tsv'
  '/usr/lib/systemd/zram-generator.conf.d/60-coffeeos.conf'
  '/usr/lib/sysctl.d/60-coffeeos.conf'
  '/etc/systemd/journald.conf.d/60-coffeeos.conf'
  '/usr/local/sbin/coffee-storage-tune'
  '/etc/calamares/modules/packagechooser-coffeeapps.conf'
  '/usr/lib/calamares/modules/coffeeapps/module.desc'
  '/usr/lib/calamares/modules/coffeeapps/main.py'
  '/etc/calamares/settings.conf'
)
for path in "${required[@]}"; do
  grep -Fq "squashfs-root$path" "$listing" || { echo "ERROR: optimization payload missing: $path" >&2; exit 5; }
done
# Calamares must show the chooser, then run CoffeeOS' network installer job
# after Debian's sources-final module has restored normal network repositories.
settings=$(unsquashfs -cat "$squashfs" etc/calamares/settings.conf 2>/dev/null || true)
grep -q 'packagechooser@coffeeapps' <<<"$settings" || { echo 'ERROR: CoffeeOS optional-software chooser is not in Calamares settings.' >&2; exit 6; }
python3 - "$settings" <<'PYVERIFY'
import sys
text=sys.argv[1]
source=text.find('- sources-final')
job=text.find('- coffeeapps', source + 1)
if source < 0 or job < 0 or job <= source:
    raise SystemExit('ERROR: CoffeeOS optional-software job is not scheduled after sources-final.')
PYVERIFY
chooser=$(unsquashfs -cat "$squashfs" etc/calamares/modules/packagechooser-coffeeapps.conf 2>/dev/null || true)
grep -q '^method: legacy$' <<<"$chooser" || { echo 'ERROR: CoffeeOS optional chooser is not using the safe post-sources-final path.' >&2; exit 6; }

# Lutris must remain an installer option, not preinstalled in the live image.
if grep -Fq 'squashfs-root/usr/bin/lutris' "$listing"; then
  echo 'ERROR: Lutris was unexpectedly preinstalled in the base live image.' >&2; exit 11
fi

kernel_status=$(unsquashfs -cat "$squashfs" usr/share/coffeeos/kernel-build-status.txt 2>/dev/null || true)
printf '%s\n' "$kernel_status"
if grep -q '^kernel=CoffeeKernel$' <<<"$kernel_status"; then
  grep -Eq 'squashfs-root/boot/vmlinuz-.*-coffee$' "$listing" || { echo 'ERROR: CoffeeKernel status claims custom kernel but /boot image is missing.' >&2; exit 7; }
  # The binary stage should have copied the custom kernel and the binary hook
  # should have selected it for CoffeeOS' live boot menu.
  iso_live=$(xorriso -indev "$ISO" -find /live -maxdepth 1 -type file -- 2>/dev/null || true)
  grep -Eq '/live/vmlinuz-.*-coffee$' <<<"$iso_live" || { echo 'ERROR: CoffeeKernel not copied to ISO /live.' >&2; exit 8; }
  for bootcfg in /boot/grub/grub.cfg /isolinux/live.cfg; do
    if xorriso -indev "$ISO" -find "$bootcfg" -type file -- 2>/dev/null | grep -q .; then
      xorriso -osirrox on -indev "$ISO" -extract "$bootcfg" "$tmp/$(basename "$bootcfg")" >/dev/null 2>&1 || true
    fi
  done
  if ! grep -RqsE '/live/vmlinuz-.*-coffee' "$tmp/grub.cfg" "$tmp/live.cfg" 2>/dev/null; then
    echo 'ERROR: CoffeeKernel exists but was not selected by the live boot menu.' >&2; exit 9
  fi
elif grep -q '^kernel=debian-stock$' <<<"$kernel_status"; then
  : # Explicit stock mode.
else
  echo 'ERROR: unrecognized kernel build status.' >&2; exit 10
fi

echo 'CoffeeOS optimization, one-kernel policy, and optional-software payload verified.'
