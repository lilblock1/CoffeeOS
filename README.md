# CoffeeOS

CoffeeOS is an in-development Debian 13 (Trixie) gaming Linux distribution for amd64. This repository is the **Linux source tree used to build the CoffeeOS ISO**. It intentionally does not contain the old Windows/WSL ISO Builder wrapper.

Current development version: **0.10.0-dev**.

## What is in this repository

- Debian `live-build` recipe for a BIOS + UEFI hybrid ISO
- CoffeeKernel source/configuration and package build scripts
- labwc Wayland Coffee Desktop configuration
- Coffee Performance Daemon and runtime performance profiles
- Coffee Control Center and quick settings
- gaming integration for GameMode, MangoHud, Gamescope, Steam/Proton, Wine/DXVK and optional Lutris
- Calamares integration and optional-software page
- CoffeeOS themes and source-friendly SVG wallpapers
- Deep optimized-package build scripts
- signed APT update-repository tooling
- validation, ISO verification and QEMU boot-test scripts

Generated files such as `.iso` and `.deb` packages are intentionally not committed.

## Build host

Use a **native Debian 13 amd64** machine or VM. A dedicated build machine/VM is strongly recommended because `live-build` creates chroots and mounts filesystems.

Recommended resources:

- 8 GB RAM or more
- 40 GB or more free disk space for Deep builds
- working Internet access to Debian repositories
- root/sudo access

Install the core build dependencies:

```bash
sudo apt update
sudo apt install --no-install-recommends \
  live-build debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
  ca-certificates gnupg rsync qemu-system-x86 ovmf python3 \
  build-essential dpkg-dev devscripts fakeroot apt-utils \
  bc bison flex kmod cpio libelf-dev libssl-dev libncurses-dev \
  dwarves debhelper linux-source-6.12 linux-config-6.12 ccache
```

## Validate the source

```bash
bash scripts/validate.sh
bash scripts/preflight.sh
python3 -m unittest discover -s tests -v
```

## Build CoffeeOS

The normal ISO script builds the CoffeeOS-owned package from the current source before invoking Debian `live-build`:

```bash
sudo bash scripts/build-iso.sh
```

Output:

```text
dist/coffeeos-0.10.0-dev-amd64.iso
dist/coffeeos-0.10.0-dev-amd64.iso.sha256
```

For the complete Deep path, build/stage CoffeeKernel and optimized packages first:

```bash
sudo bash scripts/build-coffeekernel-for-iso.sh
sudo bash scripts/build-optimized-packages.sh --mode deep
sudo bash scripts/build-iso.sh
```

The source package builders use persistent caches when `COFFEE_KERNEL_CACHE_DIR`, `COFFEE_OPT_CACHE_DIR`, `CCACHE_DIR`, and `COFFEE_LIVE_BUILD_CACHE_DIR` are configured.

## Verify and boot-test

```bash
bash scripts/verify-iso.sh
bash scripts/test-qemu.sh --bios
bash scripts/test-qemu.sh --uefi
```

QEMU validation is a boot smoke test, not a substitute for physical AMD/Intel/NVIDIA hardware or gaming benchmarks.

## CoffeeKernel

CoffeeOS uses one CoffeeKernel rather than separate kernels for each performance mode. Runtime profiles are:

```text
lite
balanced
performance
portable
```

The stock Debian kernel remains available as a recovery fallback.

## Updates

`scripts/make-update-repo.sh` builds the CoffeeOS APT repository metadata from generated `.deb` packages. Installed systems use Debian Stable for Debian packages and the signed CoffeeOS feed for CoffeeOS-specific packages.

See `docs/UPDATES.md` and `docs/SECURITY.md` before publishing a repository.

## Status

CoffeeOS is still under development. Automated tests and QEMU smoke tests do not prove real-hardware GPU compatibility or performance. Do not treat unmeasured FPS, latency, power or thermal improvements as established results.

## License

Apache-2.0. See `LICENSE`.
