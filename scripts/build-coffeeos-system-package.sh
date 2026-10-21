#!/usr/bin/env bash
# Package CoffeeOS-owned desktop/config/update files so installed systems can be
# upgraded in place from a signed APT repository.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INC="$ROOT/live-build/config/includes.chroot"
PKGDIR="$ROOT/live-build/config/packages.chroot"
WORK="${COFFEEOS_SYSTEM_PACKAGE_WORK:-}"
RELEASE_VERSION=$(sed -n 's/^COFFEEOS_VERSION=//p' "$INC/usr/share/coffeeos/release" | head -n1)
DEFAULT_VERSION=${RELEASE_VERSION/-dev/~dev1}
VERSION=${COFFEEOS_PACKAGE_VERSION:-$DEFAULT_VERSION}
ARCH=all
OUT="$PKGDIR/coffeeos-system_${VERSION}_${ARCH}.deb"
command -v dpkg-deb >/dev/null || { echo 'Missing dpkg-deb.' >&2; exit 3; }
if [[ -z $WORK ]]; then
  WORK=$(mktemp -d /tmp/coffeeos-system-package.XXXXXX)
  trap 'rm -rf "$WORK"' EXIT
else
  rm -rf "$WORK"; mkdir -p "$WORK"
fi
mkdir -p "$WORK/DEBIAN" "$PKGDIR"
chmod 0755 "$WORK" "$WORK/DEBIAN"
rm -f "$PKGDIR"/coffeeos-system_*.deb
cat > "$WORK/DEBIAN/control" <<CTRL
Package: coffeeos-system
Version: $VERSION
Section: admin
Priority: optional
Architecture: $ARCH
Maintainer: CoffeeOS Community
Depends: bash, python3, apt, ca-certificates, gnupg, curl, systemd
Description: CoffeeOS desktop, updater, profiles and system integration
 Updatable CoffeeOS-owned files. Debian base packages remain managed by APT.
CTRL
cat > "$WORK/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
if [ -d /run/systemd/system ]; then
  systemctl daemon-reload || true
  systemctl enable --now coffee-update-check.timer >/dev/null 2>&1 || true
  systemctl enable --now coffee-memory-tune.service >/dev/null 2>&1 || true
  systemctl enable --now coffee-performance-daemon.service >/dev/null 2>&1 || true
fi
exit 0
POST
chmod 755 "$WORK/DEBIAN/postinst"

copy_path(){
  src="$INC/$1"; [ -e "$src" ] || return 0
  mkdir -p "$WORK/$(dirname "$1")"
  cp -a "$src" "$WORK/$1"
}
# Explicit allow-list: files that should be replaceable by an installed-system
# CoffeeOS release without touching the Debian package database ownership of
# unrelated base files.
for p in \
  usr/local/bin usr/local/sbin usr/local/lib/coffeeos \
  usr/share/applications/coffee-control-center.desktop \
  usr/share/applications/coffee-gaming-info.desktop \
  usr/share/applications/coffee-gaming-setup.desktop \
  usr/share/applications/coffee-info.desktop \
  usr/share/applications/coffee-power-menu.desktop \
  usr/share/applications/coffee-quick-settings.desktop \
  usr/share/backgrounds/coffeeos usr/share/themes \
  usr/share/icons/hicolor/scalable/apps/coffeeos.svg \
  usr/share/wayland-sessions/coffee.desktop usr/share/wayland-sessions/coffee-gaming.desktop usr/share/coffeeos \
  etc/coffeeos \
  etc/systemd/journald.conf.d/60-coffeeos.conf \
  usr/lib/sysctl.d/60-coffeeos.conf \
  usr/lib/systemd/system/coffee-storage-tune.service \
  usr/lib/systemd/system/coffee-memory-tune.service \
  usr/lib/systemd/system/coffee-performance-daemon.service \
  usr/lib/systemd/system/coffee-update-check.service \
  usr/lib/systemd/system/coffee-update-check.timer
  do copy_path "$p"; done

find "$WORK" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$WORK" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# Only CoffeeOS-owned paths are packaged here. Do not claim files already
# owned by Debian packages (for example /etc/greetd/config.toml); live-build's
# includes.chroot overlay still applies those defaults to the ISO without dpkg
# ownership conflicts.
dpkg-deb --root-owner-group --build "$WORK" "$OUT" >/dev/null
printf 'Built in-place update package: %s\n' "$OUT"
dpkg-deb -f "$OUT" Package Version Architecture
