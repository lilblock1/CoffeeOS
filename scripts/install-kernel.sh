#!/usr/bin/env bash
# Explicit, conservative kernel install: never uninstall Debian fallback.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${COFFEE_KERNEL_DIST:-$ROOT/dist/kernels}"
APPLY=0
while (( $# )); do
  case "$1" in
    --apply) APPLY=1; shift;;
    -h|--help) echo 'Usage: sudo bash scripts/install-kernel.sh [--apply]'; exit 0;;
    *) echo "Unrecognized option: $1" >&2; exit 2;;
  esac
done
DIR="$DEST/coffee"
[[ -d "$DIR" ]] || { echo "No built kernel packages at $DIR" >&2; exit 3; }
( cd "$DIR" && sha256sum -c SHA256SUMS ) || { echo 'Kernel package checksum failed!' >&2; exit 4; }
shopt -s nullglob
packages=("$DIR"/*.deb)
[[ ${#packages[@]} == 2 ]] || { echo 'Expected image and matching headers (exactly two .deb files)' >&2; exit 4; }
image=0; headers=0; version=''
for deb in "${packages[@]}"; do
  pkg="$(dpkg-deb -f "$deb" Package)"
  ver="$(dpkg-deb -f "$deb" Version)"
  [[ -z $version || $version == "$ver" ]] || { echo 'Kernel image and headers versions differ!' >&2; exit 4; }
  version="$ver"
  case "$pkg" in
    linux-image-*-coffee) ((image+=1));;
    linux-headers-*-coffee) ((headers+=1));;
    *) echo "Unexpected kernel package: $pkg" >&2; exit 4;;
  esac
done
[[ $image == 1 && $headers == 1 ]] || { echo 'Missing image/header package pair' >&2; exit 4; }
printf 'CoffeeKernel (one tunable kernel), package version %s\n' "$version"
if [[ $APPLY == 0 ]]; then
  echo 'Dry run only. Pass --apply to make changes to this computer.'
  exit 0
fi
[[ $EUID -eq 0 ]] || { echo 'Run with sudo to install.' >&2; exit 2; }
if [[ -d /sys/firmware/efi/efivars ]]; then
  command -v mokutil >/dev/null || { echo 'Install mokutil to check Secure Boot before using unsigned kernels.' >&2; exit 5; }
  if ! sb_state=$(mokutil --sb-state 2>&1); then
    echo "Could not verify Secure Boot state: $sb_state" >&2; exit 5
  fi
  if ! grep -qi '^SecureBoot disabled' <<< "$sb_state"; then
    echo "Unsigned CoffeeKernel requires disabled Secure Boot. State: $sb_state" >&2; exit 5
  fi
fi
if ! dpkg-query -W -f='${Status}' linux-image-amd64 2>/dev/null | grep -qx 'install ok installed'; then
  echo 'Debian linux-image-amd64 fallback must be installed first. Aborting.' >&2; exit 5
fi
if [[ -z $(compgen -G "/boot/vmlinuz-*") ]]; then
  echo 'No bootable kernel in /boot. Aborting.' >&2; exit 5
fi
# Debian package scripts invoke kernel postinst hooks for initramfs and GRUB.
# Do not change GRUB_DEFAULT, purge kernels, modify EFI variables or mount disks.
apt-get install --no-install-recommends -- "${packages[@]}"
echo 'Installed one CoffeeKernel package pair. REBOOT MANUALLY and select CoffeeKernel in GRUB.'
echo 'After boot: sudo coffee-kernel-profile apply balanced|lite|performance|portable'
echo 'If it fails to boot, select the original Debian kernel from GRUB Advanced options.'
