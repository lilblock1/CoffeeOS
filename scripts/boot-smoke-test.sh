#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing ISO: $ISO" >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || { echo 'Missing qemu-system-x86_64 (install qemu-system-x86).' >&2; exit 3; }
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

echo '[CoffeeOS] Starting headless BIOS QEMU boot test (software emulation).'
echo '[CoffeeOS] Waiting up to 120 seconds for COFFEEOS_BOOT_OK...'
set +e
timeout 120s qemu-system-x86_64 \
  -machine pc,accel=tcg -m 2048 -smp 2 \
  -cdrom "$ISO" -boot d \
  -display none -serial stdio -monitor none \
  -no-reboot -no-shutdown >"$LOG" 2>&1
rc=$?
set -e
cat "$LOG"
if grep -q 'COFFEEOS_BOOT_OK' "$LOG"; then
  echo '[CoffeeOS] BOOT TEST PASSED: kernel + initramfs reached multi-user userspace.'
  exit 0
fi
echo '[CoffeeOS ERROR] BOOT TEST FAILED: COFFEEOS_BOOT_OK was not observed.' >&2
if [[ $rc -eq 124 ]]; then echo '[CoffeeOS ERROR] QEMU timed out after 120 seconds.' >&2; fi
exit 10
