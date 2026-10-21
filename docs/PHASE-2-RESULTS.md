# CoffeeOS Phase 2 revision — one CoffeeKernel

**Target:** Debian 13 Trixie, 64-bit PC. **Version:** 0.2.1-dev.

## Implemented (source)

- Removed the two kernel flavor configs; now `kernel/configs/coffee.conf`.
- One build and one install script producing exactly one CoffeeKernel kernel
  image `.deb` and one matching headers `.deb` (plus hashes and provenance).
- Dynamic-preemption kernel configuration with a fixed 1000 Hz build-time
  tick setting; the runtime power-profile controller does not claim to change
  compile-time kernel settings.
- `coffee-kernel-profile`: runtime CPUFreq governor/EPP profiles: `lite`,
  `balanced`, `performance`, `portable`, with `plan`, `apply`, `status`,
  `restore`, proper privilege checks, and a saved original state.
- `coffee-profile` front end now exposes `plan`, `apply`, `status`, `restore`.
  `set` remains preference-only for backwards compatibility.
- Debian kernel kept installed exclusively for boot failure recovery.

## Verified here

- 23 automated tests passing with `bash scripts/validate.sh`.
- Configuration merge verified against a host Debian 6.12 baseline.
- Mock package creation validated exactly one image/header pair; APT local
  package inspection dry-run and checksum corruption detection passed.
- Runtime controller exercised on **test-only filesystem fixtures** for all
  four profiles, saved-state file permissions, unsupported hardware rejection,
  rollback, and restoring the original values after multiple mode changes.
- Bash and Python syntax validated.

**Not verified:** actual Linux compilation, actual kernel binary `.deb`,
booting a VM, installing to disks, changing real CPUFreq policy values on
AMD/Intel hardware, performance claims, battery use, gaming frame times,
DKMS compatibility, NVIDIA proprietary drivers, Secure Boot signing or an
ISO build. Mock kernel packages contain no bootable payload; tests do not
install those packages.

## Before calling Phase 2 hardware-complete

Build kernel on networked native Debian 13, boot it in a throwaway VM, verify
uname -r and an external module, check old Debian fallback boots, test profile
switching on real AMD/Intel CPUFreq drivers, watch competing power managers,
run thermal/battery/game benchmarks, and test kernel upgrades and recovery.
