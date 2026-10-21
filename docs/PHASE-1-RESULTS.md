# Phase 1 verification — 2026-10-19

**Status: source/configuration milestone, NOT a tested or released operating system.**

## Actual local checks run

- Host inspected: Debian GNU/Linux 13 (trixie), x86_64; root container.
- `bash scripts/validate.sh`: PASS (6 Python unit tests; Bash syntax and Python AST syntax checks).
- `bash scripts/preflight.sh`: executes correctly. Reports missing `live-build` (`lb`), `debootstrap`, `mksquashfs`, `xorriso`, `qemu-system-x86_64`.
- `bash scripts/build-iso.sh`: correctly stopped with `Missing dependency: lb` (no ISO written).
- `bash scripts/verify-iso.sh`: correctly stopped because ISO is absent (no SHA256 fabricated).
- `bash scripts/test-qemu.sh --bios`: correctly stopped because ISO is absent (no VM boot fabricated).
- Network: DNS lookup for `deb.debian.org` did not resolve; system cannot currently fetch Debian build dependencies.
- Wallpaper: generated 2560×1440 PNG from included original editable SVG and inspected as an image. This is an **art asset**, not a screenshot of the OS running.

## Tested vs not tested

| Item | Observed |
|---|---|
| Source file existence/static tests | Passed |
| Package availability according to Debian's public package catalog | Researched, not installed |
| `lb config` against installed live-build | Not run, `lb` absent |
| Dependency resolution and ISO generation | Not run, offline build container |
| ISO boot in QEMU (BIOS/UEFI) | Not run, no ISO or QEMU |
| Live login, Wayland render, Calamares | Not run |
| GPU/Wi-Fi/audio/Steam benchmarks | Not run |
| Secure Boot | Explicitly not supported in prototype |

## Next required milestone

Use a networked **Debian 13 amd64** builder: install listed packages, run `sudo bash scripts/build-iso.sh`, then verify ISO checksums and boot in both QEMU firmware modes. Fix actual build/runtime errors discovered and document logs before making a release claim.
