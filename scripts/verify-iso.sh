#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/dist/coffeeos-0.10.0-dev-amd64.iso}"
[[ -s "$ISO" ]] || { echo "Missing or empty ISO: $ISO" >&2; exit 2; }
CHECKSUM="$ISO.sha256"
[[ -f "$CHECKSUM" ]] || { echo "Missing checksum: $CHECKSUM" >&2; exit 3; }
(cd "$(dirname "$ISO")" && sha256sum -c "$(basename "$CHECKSUM")")
command -v xorriso >/dev/null || { echo 'xorriso is required for boot verification.' >&2; exit 4; }

report=$(mktemp)
trap 'rm -f "$report"' EXIT
xorriso -indev "$ISO" -report_el_torito plain >"$report" 2>&1 || {
  cat "$report" >&2; echo 'ERROR: could not inspect ISO boot structures.' >&2; exit 5;
}
cat "$report" | grep -E 'El Torito|Boot|boot' || true

# Require a BIOS boot entry and an EFI boot entry.
grep -qiE 'BIOS|El Torito.*boot' "$report" || { echo 'ERROR: BIOS boot entry not detected.' >&2; exit 6; }
grep -qiE 'UEFI|EFI' "$report" || { echo 'ERROR: UEFI boot entry not detected.' >&2; exit 7; }

# Require the live kernel and initrd directory entries.
listing=$(xorriso -indev "$ISO" -find /live -maxdepth 1 -type file -- 2>/dev/null || true)
printf '%s\n' "$listing"
grep -q '/live/vmlinuz' <<<"$listing" || { echo 'ERROR: live kernel missing from ISO.' >&2; exit 8; }
grep -q '/live/initrd' <<<"$listing" || { echo 'ERROR: live initrd missing from ISO.' >&2; exit 9; }

# The payload verifiers all inspect the same large SquashFS. Extract and index it
# once, then run the independent checks concurrently instead of reading the ISO
# four separate times. This noticeably reduces post-build verification time.
command -v unsquashfs >/dev/null || { echo 'unsquashfs is required for payload verification.' >&2; exit 10; }
verify_tmp=$(mktemp -d)
trap 'rm -f "$report"; rm -rf -- "$verify_tmp"' EXIT
shared_squash="$verify_tmp/filesystem.squashfs"
shared_list="$verify_tmp/squashfs.list"
xorriso -osirrox on -indev "$ISO" -extract /live/filesystem.squashfs "$shared_squash" >/dev/null 2>&1 || {
  echo 'ERROR: could not extract live filesystem.squashfs from ISO.' >&2; exit 11;
}
unsquashfs -ll "$shared_squash" > "$shared_list"
export COFFEEOS_VERIFY_SQUASHFS="$shared_squash"
export COFFEEOS_VERIFY_SQUASHFS_LIST="$shared_list"

# Static BIOS menu integrity check. This catches a broken Syslinux default even
# when the slower BIOS QEMU smoke test is intentionally disabled in CI.
bios_cfg="$verify_tmp/isolinux.cfg"
bios_live_cfg="$verify_tmp/live.cfg"
xorriso -osirrox on -indev "$ISO" -extract /isolinux/isolinux.cfg "$bios_cfg" >/dev/null 2>&1 || {
  echo 'ERROR: could not extract BIOS isolinux.cfg.' >&2; exit 13;
}
xorriso -osirrox on -indev "$ISO" -extract /isolinux/live.cfg "$bios_live_cfg" >/dev/null 2>&1 || {
  echo 'ERROR: could not extract BIOS live.cfg.' >&2; exit 13;
}
bios_default="$(awk '$1=="default"{print $2; exit}' "$bios_cfg")"
bios_timeout="$(awk '$1=="ontimeout"{print $2; exit}' "$bios_cfg")"
[[ -n "$bios_default" ]] || { echo 'ERROR: BIOS default label is missing.' >&2; exit 13; }
grep -Eq "^label[[:space:]]+$bios_default$" "$bios_live_cfg" || {
  echo "ERROR: BIOS default label '$bios_default' does not exist in live.cfg." >&2; exit 13;
}
if [[ -n "$bios_timeout" ]]; then
  grep -Eq "^label[[:space:]]+$bios_timeout$" "$bios_live_cfg" || {
    echo "ERROR: BIOS timeout label '$bios_timeout' does not exist in live.cfg." >&2; exit 13;
  }
fi
echo "BIOS Syslinux labels verified: default=$bios_default timeout=${bios_timeout:-none}"

verify_scripts=(
  verify-gaming-image.sh
  verify-optimization-image.sh
  verify-control-center-image.sh
  verify-updates-image.sh
)
verify_pids=()
verify_logs=()
for script in "${verify_scripts[@]}"; do
  log="$verify_tmp/$script.log"
  verify_logs+=("$log")
  bash "$ROOT/scripts/$script" "$ISO" >"$log" 2>&1 &
  verify_pids+=("$!")
done
verify_failed=0
for pid in "${verify_pids[@]}"; do
  if ! wait "$pid"; then verify_failed=1; fi
done
for log in "${verify_logs[@]}"; do cat "$log"; done
(( verify_failed == 0 )) || { echo 'ERROR: one or more ISO payload verifiers failed.' >&2; exit 12; }

echo 'ISO checksum, boot structures, gaming payload, optimization payload, Phase 5 control-center payload, in-place update payload, and kernel policy verified. Runtime boot/game tests are still required.'
