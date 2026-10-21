# CoffeeOS test matrix — 0.10.0-dev

## CI/static tests (can run on any system with Python3 and Bash)

- Bash syntax for build, utility and chroot-hook scripts
- Python syntax for CLI tools
- Package manifest sanity and no Testing/Unstable repo mixing
- Waybar JSONC parse (Python with comments/trailing-comma tolerance via existing file format)
- `labwc` rc.xml XML parse
- Profiles allowlist/config persistence
- No disk erase commands present in build/test scripts

## MUST be tested on networked Debian builder

- `lb config` completes, `lb build` exits successfully
- ISO contents and El Torito entries are present; SHA256 verifies
- BIOS+UEFI boot, live user login via greetd, waybar, terminal, file manager
- Wired/Wi-Fi, sound (PipeWire), Intel/AMD GPU, Bluetooth (physical HW)
- Installed OS boots, APT update works, installer supports chosen layout
- Installer warns and asks before destructive disk operations

## MUST be tested before public release

- Calamares installs in QEMU to disposable virtual disk (UEFI+BIOS), reinstall, encrypted/Btrfs/ext4 options
- Safe behavior with existing partitions/Windows dual boot on disposable test disks
- Installer copies CoffeeOS customization and does not leave live services misconfigured
- NVIDIA proprietary drivers, Steam/Proton, Steam 32-bit libs, suspend, VRR, controllers
- Secure Boot signing (not implemented), upgrades/recovery from failed kernel updates
- Measure idle RAM and boot time vs standard Debian on equivalent hardware; record logs and FPS/1%-low with same games/settings

*No claim in this project equates passing static tests with a successfully booted ISO.*

## Phase 2 kernel tests

Run `bash scripts/validate.sh` for Python and shell checks, Debian kernel config
fragment tests, and a **mock** build/publish/checksum/install-dry-run integration
fixture. Test fixture `.deb` packages are placeholders, not bootable kernels.

For actual kernel builds, see `docs/KERNEL-BUILD.md`. Record:
- `dpkg-query -W linux-source-6.12 linux-config-6.12`
- `sha256sum dist/kernels/<variant>/*.deb`
- A successful post-boot `uname -r`, `dmesg`, initramfs/GRUB checks, fallback boot
- A real 3D game frame-time comparison before making any performance claims

**CoffeeKernel source/config logic is tested here, but a v0.6 CoffeeKernel built by the native Debian pipeline still requires the builder's QEMU Boot Test and physical-hardware validation.**

## v0.6 optimization checks

Automated tests verify the one-kernel config invariants, generic-CPU policy (no `-march=native`), source-rebuild allowlist/fallback behavior, zram/sysctl/journald/storage tuning, and the single-ISO Calamares optional-software page. These are recipe tests, not benchmark results. The actual Deep build must compile sources in native Debian and then pass ISO verification and QEMU boot testing.
