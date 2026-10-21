# Reproducing the Phase 1 live image

Host: Debian **13 Trixie amd64**, with Debian repositories available and at least 25 GB of free disk space. Use an isolated root-capable VM or disposable builder; do not mount the user's data disks into it.

1. Install the packages in `README.md` (add `rsync` if not present).
2. Run `bash scripts/validate.sh` and `bash scripts/preflight.sh` (static tests; no network).
3. Run `sudo bash scripts/build-iso.sh`. Failure is a failure; inspect `dist/build.log` and `build/`.
4. On success, `bash scripts/verify-iso.sh` verifies SHA256 and reads ISO metadata (if xorriso is available).
5. Run `bash scripts/test-qemu.sh --bios` and `bash scripts/test-qemu.sh --uefi` **interactively**.
6. Before distributing, boot/try installed system in a throwaway QEMU virtual disk **manually**. The provided `test-qemu.sh` never attaches a writable target disk and cannot test installation.

`live-build/auto/config` is authoritative for `lb config` flags. Packages are in `live-build/config/package-lists/*.list.chroot`. The `includes.chroot` tree is copied to `/` in the resulting live system. No CoffeeOS third-party repository or unsigned APT feed is added. Mirrors use Debian archive keys.

The `/etc/os-release` override in this phase is **not packaged** and may be overwritten when Debian `base-files` upgrades. Future CoffeeOS builds must ship identity via a proper Debian package.

Live-build may generate non-bit-reproducible artifacts because upstream repository state, squashfs timestamps and package versions change. **This is a repeatable recipe, not a claim of bit-for-bit reproducibility.** Lock source snapshots/package versions and build environment before claiming reproducible releases.

## Troubleshooting

- `lb: command not found`: install `live-build` on a Debian builder.
- `Failed to fetch`, `Temporary failure resolving`: fix builder Internet/DNS; no offline ISO build is possible from an empty cache.
- `lb config` reports incompatible bootloader flags: check the version and its manpage on the target Debian release; log the full command/version rather than disabling all firmware/security options blindly.
- Wayland may fail with unsupported virtual GPUs; test a physical AMD/Intel machine before declaring it broken on hardware generally.
- `--clean`: `sudo bash scripts/build-iso.sh --clean` only removes the project `build/` directory.
- For testing without partition risk, use the read-only ISO boot script. Calamares has not been installed-tested in this milestone.
