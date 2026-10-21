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
  /usr/bin/unsquashfs \
  /usr/bin/calamares-install-debian \
  /usr/local/bin/coffee-installer-preflight \
  /usr/local/bin/coffee-installer-report \
  /usr/local/bin/coffee-hardware-health \
  /usr/local/bin/coffee-driver-info \
  /usr/local/bin/coffee-network-settings \
  /usr/local/bin/coffee-accessibility \
  /usr/local/bin/coffee-clipboard-history \
  /usr/local/bin/coffee-app-center \
  /usr/local/sbin/coffee-recovery \
  /usr/local/sbin/coffee-secure-boot \
  /usr/local/sbin/coffee-platform-admin \
  /usr/local/sbin/coffeeos-ci-install \
  /etc/systemd/system/coffeeos-ci-install.service \
  /etc/grub.d/41_coffeeos_safe_graphics \
  /usr/share/applications/coffee-app-center.desktop \
  /usr/local/sbin/coffee-kernel-manager \
  /usr/local/bin/coffee-gpu-manager \
  /usr/local/bin/coffee-flatpak-permissions \
  /usr/local/bin/coffee-bug-report \
  /usr/share/applications/coffee-bug-report.desktop \
  /usr/share/plymouth/themes/coffeeos/coffeeos-background.svg \
  /usr/share/plymouth/themes/coffeeos/steam.svg \
  /usr/share/plymouth/themes/coffeeos/progress-track.svg \
  /usr/share/plymouth/themes/coffeeos/progress-fill.svg \
  /usr/share/plymouth/themes/coffeeos/coffeeos-background.png \
  /usr/share/plymouth/themes/coffeeos/steam.png \
  /usr/share/plymouth/themes/coffeeos/progress-track.png \
  /usr/share/plymouth/themes/coffeeos/progress-fill.png \
  /usr/bin/rsvg-convert \
  /usr/share/plymouth/themes/coffeeos/coffeeos.plymouth \
  /usr/share/plymouth/themes/coffeeos/coffeeos.script \
  /etc/default/grub.d/50-coffeeos-plymouth.cfg \
  /usr/bin/plymouth \
  /usr/bin/jstest-gtk \
  /usr/bin/fftest \
  /usr/bin/switcherooctl \
  /usr/local/bin/coffee-control-center \
  /usr/local/bin/coffee-hardware-settings \
  /usr/local/bin/coffee-first-boot \
  /usr/local/bin/coffee-desktop-settings \
  /usr/local/bin/coffee-lock \
  /usr/local/bin/coffee-night-light \
  /usr/local/bin/coffee-support-bundle \
  /usr/local/bin/coffee-gaming-indicator \
  /usr/local/sbin/coffee-admin-settings \
  /usr/local/bin/coffee-gaming-preferences \
  /usr/local/sbin/coffee-system-update \
  /usr/local/sbin/coffee-update \
  /usr/share/applications/coffee-control-center.desktop \
  /usr/share/applications/coffee-welcome.desktop; do
  grep -Fq "$path" <<<"$listing" || { echo "ERROR: Phase 5 payload missing: $path" >&2; exit 5; }
done
installer_launcher=$(unsquashfs -cat "$rootfs" usr/local/bin/coffeeos-installer 2>/dev/null || true)
grep -q 'calamares-install-debian' <<<"$installer_launcher" || {
  echo 'ERROR: CoffeeOS installer does not prefer the Debian 13 privileged Calamares wrapper.' >&2
  exit 6
}
if grep -q '^  exec calamares "\$@" <<<"$installer_launcher"; then
  echo 'ERROR: CoffeeOS installer can launch Calamares unprivileged.' >&2
  exit 6
fi
echo 'Calamares privileged launcher, unpackfs dependency and Phase 5 Coffee Control Center payload verified inside SquashFS.'
