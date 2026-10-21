#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso"
MODE=${1:---bios}
[[ -s "$ISO" ]] || { echo "Build ISO first: $ISO" >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || { echo 'Install qemu-system-x86' >&2; exit 3; }
args=(-m 3072 -smp 2 -machine q35 -drive "file=$ISO,media=cdrom,readonly=on" -boot d -vga std -nic user,model=virtio-net-pci -no-reboot)
case "$MODE" in
  --bios) ;;
  --uefi)
    OVMF=''
    for fw in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do
      [[ -f "$fw" ]] && { OVMF="$fw"; break; }
    done
    [[ -n "$OVMF" ]] || { echo 'OVMF firmware not found; install ovmf.' >&2; exit 4; }
    args+=(-drive "if=pflash,format=raw,readonly=on,file=$OVMF")
    ;;
  *) echo 'Usage: test-qemu.sh [--bios|--uefi]' >&2; exit 2;;
esac
printf '%s\n' 'Starting interactive, read-only live ISO boot. No disk to overwrite is attached.'
exec qemu-system-x86_64 "${args[@]}"
