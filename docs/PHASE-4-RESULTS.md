# Phase 4 — Gaming optimization integration

**Version:** 0.5.1-dev. **Base:** Debian 13 Trixie amd64.

## Implemented in source

- Core low-overhead gaming packages: GameMode, MangoHud, Vulkan loader/Mesa,
  Vulkan diagnostics, Steam/controller udev rules and joystick utilities.
- Conservative `/etc/gamemode.ini`: performance governor request, I/O priority,
  screensaver inhibition, no overclocking, no scheduler hacks, no split-lock
  mitigation disablement.
- Reversible `coffee-gaming-mode` wrapper with desktop-effects suppression,
  notification DND, GameMode, optional MangoHud/Gamescope and reference-counted
  restoration for concurrent games.
- `coffee-gaming-info` read-only GPU/Vulkan/gaming stack diagnostics.
- `coffee-gaming-setup` for explicit i386 Steam support, Wine/DXVK,
  controlled Trixie-Backports Gamescope, installed-system NVIDIA driver setup,
  an explicit optional Lutris action, and explicit third-party Heroic/Flathub opt-in.
- Safe local `coffee-proton-manager` for importing/removing custom Proton/GE
  archives into the user's Steam compatibility-tools directory.
- Desktop entries and gaming documentation.

## Verified in this development environment

- Bash/Python syntax checks and the existing CoffeeOS validation suite.
- Unit tests for gaming package manifests and conservative GameMode settings.
- Isolated fake-command test of Coffee Gaming Mode proving effects/DND are
  entered and restored and wrapper arguments are passed without shell eval.
- Isolated Proton-manager tests for valid custom-tool import/remove and archive
  path-traversal rejection.
- Dry-run inspection of the package setup helper without changing APT.

## Not claimed/tested here

- Steam client login/download, Valve Proton game launch, Proton-GE game launch.
- Working Vulkan on AMD/Intel/NVIDIA physical GPUs or VM 3D acceleration.
- Proprietary NVIDIA DKMS build/reboot.
- Gamescope gameplay, VRR/HDR, multi-monitor, controller/Bluetooth/VR hardware.
- FPS, 1% lows, frame-time, power or latency improvements.
- Heroic/Flathub installation or third-party network content.

Those require a freshly built ISO/installed system and real hardware or a VM
with a functional virtual GPU. Record actual logs/benchmarks before making any
performance claims.
