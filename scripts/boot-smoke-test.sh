#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE=--bios
if [[ ${1:-} == --bios || ${1:-} == --uefi ]]; then MODE=$1; shift; fi
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing ISO: $ISO" >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || { echo 'Missing qemu-system-x86_64 (install qemu-system-x86).' >&2; exit 3; }

LOG=$(mktemp)
TMPVARS=''
cleanup(){ rm -f -- "$LOG" "${TMPVARS:-}"; }
trap cleanup EXIT

args=(
  -m 2048 -smp 2
  -drive "file=$ISO,media=cdrom,readonly=on"
  -boot d
  -display none
  -serial stdio
  -monitor none
  -nic user,model=virtio-net-pci
  -no-reboot
  -no-shutdown
)

case "$MODE" in
  --bios)
    args=(-machine pc,accel=tcg "${args[@]}")
    ;;
  --uefi)
    OVMF=''
    VARS=''
    for fw in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do
      [[ -r "$fw" ]] && { OVMF="$fw"; break; }
    done
    for fw in /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
      [[ -r "$fw" ]] && { VARS="$fw"; break; }
    done
    [[ -n "$OVMF" && -n "$VARS" ]] || { echo 'OVMF firmware/variable store missing; install ovmf.' >&2; exit 4; }
    TMPVARS=$(mktemp --suffix=.fd)
    cp -- "$VARS" "$TMPVARS"
    args=(-machine q35,accel=tcg
      -drive "if=pflash,format=raw,readonly=on,file=$OVMF"
      -drive "if=pflash,format=raw,file=$TMPVARS"
      "${args[@]}")
    ;;
  *) echo 'Usage: boot-smoke-test.sh [--bios|--uefi] [ISO]' >&2; exit 2;;
esac

echo "[CoffeeOS] Starting headless ${MODE#--} QEMU boot test (TCG software emulation)."
echo '[CoffeeOS] Waiting up to 150 seconds for COFFEEOS_BOOT_OK...'
set +e
timeout 150s qemu-system-x86_64 "${args[@]}" >"$LOG" 2>&1
rc=$?
set -e
cat "$LOG"
if grep -q 'COFFEEOS_BOOT_OK' "$LOG"; then
  echo "[CoffeeOS] ${MODE#--^^} BOOT TEST PASSED: kernel + initramfs reached multi-user userspace."
  exit 0
fi
echo "[CoffeeOS ERROR] ${MODE#--} boot test failed: COFFEEOS_BOOT_OK was not observed." >&2
if [[ $rc -eq 124 ]]; then echo '[CoffeeOS ERROR] QEMU timed out after 150 seconds.' >&2; fi
exit 10
