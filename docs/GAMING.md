# CoffeeOS Gaming Stack — Phase 4

CoffeeOS keeps the always-present gaming layer small and installs heavyweight
launchers/32-bit compatibility only when requested.

## Included in the live/base image

- GameMode (`gamemoderun` / `gamemoded`)
- MangoHud
- Vulkan loader + Mesa Vulkan drivers
- `vulkaninfo`
- Steam/controller udev rules (`steam-devices`) and joystick test tools
- `coffee-gaming-mode`, `coffee-gaming-info`, `coffee-proton-manager`

The GameMode configuration requests the performance governor where supported,
uses best-effort I/O priority, inhibits the screensaver during games, leaves
renice disabled by default, and explicitly leaves GPU overclocking and split-lock
mitigation changes disabled.

## Coffee Gaming Mode

Use it as a Steam launch option:

```text
coffee-gaming-mode -- %command%
coffee-gaming-mode --hud -- %command%
coffee-gaming-mode --hud --gamescope -- %command%
```

For the lifetime of wrapped game processes it:

1. requests Feral GameMode (if available),
2. disables Coffee Desktop visual effects,
3. enables Mako's `gaming` mode so nonessential popups are hidden,
4. optionally enables MangoHud and Gamescope,
5. restores the previous desktop-effects state and notifications when the last
   wrapped game exits.

The wrapper is reference-counted so two simultaneous wrapped games do not cause
the first game to restore settings while the second is still running.

## Steam + Proton and 32-bit gaming

Steam on Debian needs i386 multiarch. CoffeeOS deliberately does not add a
foreign architecture just to boot the live desktop. Install it explicitly:

```bash
sudo coffee-gaming-setup steam
```

That enables i386, updates APT, and installs Debian Stable's Steam installer plus
32-bit Vulkan/Mesa and GameMode libraries. Steam itself manages Valve
Proton versions. Proton includes its own DXVK/VKD3D-Proton for Steam games.

## Wine and DXVK

```bash
sudo coffee-gaming-setup wine
# Install the main gaming stack without third-party/game launchers:
sudo coffee-gaming-setup full
```

The Wine action enables i386 and installs Debian's 64/32-bit Wine and DXVK
packages. The `full` action installs Steam, Wine/DXVK and Gamescope only.

## Optional Lutris

Lutris is **not installed in the base image and is not included in `full`**.
Install it only when you explicitly want it:

```bash
sudo coffee-gaming-setup lutris
```

That installs Debian Trixie's `lutris` and `winetricks` packages.

## Gamescope

Gamescope is not in Debian 13 Stable itself. CoffeeOS adds **only the official
Trixie Backports repository when this action is requested**, then installs only
Gamescope from that target:

```bash
sudo coffee-gaming-setup gamescope
```

No Testing or Unstable repository is added.

## Proton-GE / custom Proton

Download a trusted Proton-GE/custom-Proton tar archive yourself, then import it
without root:

```bash
coffee-proton-manager install-archive ~/Downloads/GE-Proton*.tar.gz
coffee-proton-manager list
```

The importer rejects absolute paths, `..` traversal and symlink/hardlink archive
members, requires `compatibilitytool.vdf`, and installs only under the current
user's Steam `compatibilitytools.d` directory. Restart Steam afterwards.

## NVIDIA

AMD and Intel use the in-kernel DRM drivers plus Mesa/Vulkan stack included in
CoffeeOS. Proprietary NVIDIA is intentionally an explicit **installed-system**
action because it builds a kernel module:

```bash
sudo coffee-gaming-setup nvidia
```

The action refuses to run when no NVIDIA display controller is detected or when
booted from the disposable live ISO. It requires headers matching the running
kernel and uses Debian Stable's `nvidia-driver`; no GPU overclocking is enabled.

## Heroic

Heroic is not provided by Debian Stable. To keep third-party repositories opt-in:

```bash
sudo coffee-gaming-setup heroic
```

This asks for confirmation before installing Flatpak, adding Flathub, and
installing Heroic. Use `--yes` only when you intentionally want the third-party
source.

## Diagnostics

```bash
coffee-gaming-info
coffee-gaming-mode --status
vulkaninfo --summary
gamemoded -t
```

A successful command is not an FPS benchmark. Real GPU, controller, VRR,
Gamescope, Proton and frame-time testing still requires physical/VM hardware.
