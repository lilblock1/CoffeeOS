#!/usr/bin/env bash
# Boots an existing *disposable* installed Debian test VM disk using QEMU snapshot mode.
set -Eeuo pipefail
DISK=''; MODE=bios
TMPVARS=''
while (( $# )); do
  case "$1" in
    --disk) DISK="${2:?missing disk}"; shift 2;;
    --uefi) MODE=uefi; shift;;
    --bios) MODE=bios; shift;;
    -h|--help) echo 'Usage: scripts/test-kernel-vm.sh --disk debian-test.qcow2 [--bios|--uefi]'; exit 0;;
    *) echo "Unknown argument: $1" >&2; exit 2;;
  esac
done
[[ -n $DISK && -f $DISK ]] || { echo 'Provide an EXISTING disposable VM disk.' >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || { echo 'Install qemu-system-x86' >&2; exit 3; }
args=(-m 4096 -smp 4 -machine q35 -nic user,model=virtio-net-pci -snapshot \
  -drive "file=$DISK,format=qcow2,if=virtio" -vga virtio -no-reboot)
if [[ $MODE == uefi ]]; then
  OVMF=''
  for fw in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do
    [[ -r $fw ]] && { OVMF="$fw"; break; }
  done
  [[ -n $OVMF ]] || { echo 'Install ovmf for UEFI testing.' >&2; exit 3; }
  VARS=''
  for fw in /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
    [[ -r $fw ]] && { VARS="$fw"; break; }
  done
  [[ -n "$VARS" ]] || { echo 'OVMF variable store template is required for UEFI testing.' >&2; exit 3; }
  TMPVARS="$(mktemp --suffix=.fd)"
  trap 'rm -f -- "$TMPVARS"' EXIT
  cp -- "$VARS" "$TMPVARS"
  args+=(-drive "if=pflash,format=raw,readonly=on,file=$OVMF" \
         -drive "if=pflash,format=raw,file=$TMPVARS")
fi
echo 'QEMU snapshot: changes inside this VM will NOT persist.'
echo 'Select CoffeeKernel at GRUB and run: uname -r; sudo bash scripts/kernel-smoke.sh'
qemu-system-x86_64 "${args[@]}"
