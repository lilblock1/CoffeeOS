#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing ISO: $ISO" >&2; exit 2; }
for exe in qemu-system-x86_64 qemu-img xorriso; do command -v "$exe" >/dev/null || { echo "Missing $exe" >&2; exit 3; }; done
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
disk="$work/coffeeos.qcow2"; kernel="$work/vmlinuz"; initrd="$work/initrd"; install_log="$work/install.log"; boot_log="$work/boot.log"
kernel_path=$(xorriso -indev "$ISO" -find /live -maxdepth 1 -type f -- 2>/dev/null | grep -E '/live/vmlinuz' | head -1)
initrd_path=$(xorriso -indev "$ISO" -find /live -maxdepth 1 -type f -- 2>/dev/null | grep -E '/live/initrd' | head -1)
[[ -n "$kernel_path" && -n "$initrd_path" ]] || { echo 'Could not find live kernel/initrd.' >&2; exit 4; }
xorriso -osirrox on -indev "$ISO" -extract "$kernel_path" "$kernel" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract "$initrd_path" "$initrd" >/dev/null 2>&1
qemu-img create -q -f qcow2 "$disk" 28G

echo '[CoffeeOS] Installing to a blank virtual disk...'
set +e
timeout 420s qemu-system-x86_64 \
  -machine pc,accel=tcg -m 3072 -smp 2 \
  -kernel "$kernel" -initrd "$initrd" \
  -append 'boot=live components username=coffeeos user-fullname=CoffeeOS hostname=coffeeos coffeeos.ci-install=1 console=ttyS0,115200n8' \
  -drive "file=$ISO,media=cdrom,readonly=on" \
  -drive "file=$disk,if=virtio,format=qcow2" \
  -display none -serial stdio -monitor none -nic user,model=virtio-net-pci -no-reboot \
  >"$install_log" 2>&1
install_rc=$?
set -e
cat "$install_log"
grep -q 'COFFEEOS_CI_INSTALL_OK' "$install_log" || {
  echo "Full-disk install failed (QEMU exit $install_rc)." >&2; exit 10;
}

code=
vars=
for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do [[ -r "$f" ]] && { code="$f"; break; }; done
for f in /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do [[ -r "$f" ]] && { vars="$f"; break; }; done
[[ -n "$code" && -n "$vars" ]] || { echo 'OVMF firmware missing.' >&2; exit 11; }
cp "$vars" "$work/vars.fd"

echo '[CoffeeOS] Booting the installed disk without the ISO...'
set +e
timeout 180s qemu-system-x86_64 \
  -machine q35,accel=tcg -m 2048 -smp 2 \
  -drive "if=pflash,format=raw,readonly=on,file=$code" \
  -drive "if=pflash,format=raw,file=$work/vars.fd" \
  -drive "file=$disk,if=virtio,format=qcow2" \
  -boot c -display none -serial stdio -monitor none -nic user,model=virtio-net-pci -no-reboot \
  >"$boot_log" 2>&1
boot_rc=$?
set -e
cat "$boot_log"
if grep -q 'COFFEEOS_BOOT_OK' "$boot_log"; then
  echo '[CoffeeOS] FULL INSTALL TEST PASSED: blank disk -> installed UEFI system -> userspace.'
  exit 0
fi
echo "Installed-system boot failed (QEMU exit $boot_rc)." >&2
exit 12
