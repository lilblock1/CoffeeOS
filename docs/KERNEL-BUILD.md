# CoffeeKernel — ONE build, four runtime profiles

CoffeeKernel is **one Debian-compatible custom kernel**, not two separate
balanced/performance flavors. The `linux-image-*-coffee` package and its
matching `linux-headers-*-coffee` package always contain the **same kernel**.

Its kernel configuration uses full preemption with `CONFIG_PREEMPT_DYNAMIC=y`
and a 1000 Hz timer. These are build-time parameters. CPU governor and
energy-performance preference changes are runtime parameters: switching them
**does not need a new kernel, new package, or reboot**. Profile changes do not
recompile the kernel or change the kernel's timer frequency.

Debian's regular `linux-image-amd64` remains installed as a **recovery fallback**.
It is not a second CoffeeKernel mode and is not selected during normal profile
switching. In v0.6, **Core and Deep Windows-builder modes compile CoffeeKernel during the ISO build and stage its image package into the live filesystem**. Stock mode skips it. The regular Debian kernel stays installed as a recovery fallback, and the matching CoffeeKernel headers are preserved under `dist/kernels/coffee/` as a build artifact rather than installed into the live image.

## Build dependencies (Debian 13 Trixie amd64)

Use a disposable VM with Internet, 8+ GB RAM, and ideally 30+ GB disk.

```bash
sudo apt update
sudo apt install --no-install-recommends \
  build-essential bc bison flex kmod cpio rsync \
  libelf-dev libssl-dev libncurses-dev dwarves \
  debhelper dpkg-dev fakeroot python3 xz-utils \
  linux-source-6.12 linux-config-6.12 \
  linux-image-amd64 linux-headers-amd64 \
  initramfs-tools grub2-common
```

Debian's `linux-source-6.12` and `linux-config-6.12` package versions must
match. Their source is Debian patched, not an untrusted upstream repository.
No Testing/Unstable repositories are needed.

## Build and install (isolated VM only)

```bash
bash scripts/validate.sh
bash scripts/build-kernel.sh --dry-run
bash scripts/build-kernel.sh --jobs 4
# Output: dist/kernels/coffee/ (one image, one headers, hashes, provenance)
bash scripts/install-kernel.sh                   # validate packages; no installation
sudo bash scripts/install-kernel.sh --apply      # explicitly install in test VM
```

The build uses Debian's kernel configuration, an audited CoffeeKernel fragment,
Linux `make olddefconfig` plus strict config verification, and `make bindeb-pkg`.
Generated Debian `.deb` packages are **unsigned**; on UEFI the installer blocks
installation unless `mokutil` confirms Secure Boot is disabled. No GRUB default,
EFI variables, disks, or original Debian kernel packages are removed. The
usual Debian initramfs/bootloader package hooks are used.

After installing, reboot manually and choose CoffeeKernel from GRUB. Verify:

```bash
uname -r                      # expected suffix: -coffee
bash scripts/kernel-smoke.sh coffee
```

If it fails, use the regular Debian kernel in GRUB's Advanced options. Test
in a disposable QEMU disk with:

```bash
bash scripts/test-kernel-vm.sh --disk /path/to/TEST-DISK.qcow2 --bios
```

## Switch profiles while CoffeeKernel is running

The runtime control tool is available under
`live-build/config/includes.chroot/usr/local/sbin/coffee-kernel-profile`.
The `coffee-profile` front end is included in the live filesystem recipe.
Once running on CoffeeOS, use:

```bash
coffee-profile list
coffee-profile status
coffee-profile plan performance
sudo coffee-profile apply performance
sudo coffee-profile apply balanced
sudo coffee-profile apply lite
sudo coffee-profile apply portable
sudo coffee-profile restore
```

**You do not need to reboot to change the CPU profile.** It modifies only
supported CPUFreq `scaling_governor` and
`energy_performance_preference` policy settings under `/sys`.
For unsupported CPUs or virtual machines it fails without silently claiming
an applied optimization. Applying the first profile saves original values in
root-owned `/var/lib/coffeeos/kernel-profile.json`, and subsequent switches
retain that original baseline for `restore`. There is no background service.

Profiles use *preferences*, not enforced frequency limits:

| Profile | Governor preference | Energy preference (EPP) |
|---|---|---|
| Lite | powersave / schedutil / ondemand | power / balance_power |
| Balanced | schedutil / powersave / ondemand | balance_performance / balance_power |
| Performance | performance / schedutil / powersave | performance / balance_performance |
| Portable | powersave / schedutil / ondemand | balance_power / power |

The tool chooses the first *available* value for each CPU policy; not all
systems provide all controls. `powersave` under Intel's active `intel_pstate`
does **not** imply a fixed minimum clock. External tools (TLP,
`power-profiles-daemon`, desktop power managers) may overwrite these settings;
configure only one active power manager. CPU temperatures and fan limits are
never bypassed. Linux `CONFIG_HZ`, built-in kernel drivers, and compile-time
settings **cannot** be switched in this way. `CONFIG_PREEMPT_DYNAMIC` supports
scheduler preemption selection on kernels with an available runtime interface,
but this controller intentionally **does not mount debugfs or expose unsafe
scheduler debug knobs**. A later validated phase can opt into this separately.

Running `coffee-profile set NAME` only saves a *user preference* and does not
change the CPU. Use `sudo coffee-profile apply NAME` for real runtime changes.

## Security and testing status

- The mode controller writes only supported CPUFreq governor/EPP knobs with
  root privileges, no unprivileged sysfs writes or automatic root escalation.
- Changes are transactional on ordinary errors with best-effort rollback; a
  journal retains the baseline in case of unexpected interruption. `restore`
  is available; power-management daemons may still compete.
- The source tests exercise temporary **fake CPUFreq directories**, not real
  hardware, to verify modes, rollback, restore, no-policy failures, and
  supported-only selection.
- Source/unit tests verify the kernel recipe and mocked package pipeline. The v0.6 builder now **attempts the real CoffeeKernel compile** in Core/Deep mode, but this development environment has not completed that full compile or hardware boot. QEMU/physical boot, DKMS verification, temperatures, battery endurance and game benchmarks must still be measured before performance claims.
- Rebuild from each Debian security-patched kernel release. Custom kernels do
  **not** automatically inherit Debian kernel security fixes without rebuilding.
- A signed CoffeeOS package repository, automatic kernel updates, signed
  Secure Boot builds, and tested physical-hardware installer remain pending.
