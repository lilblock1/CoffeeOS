# Coffee Control Center

Phase 5 adds a single lightweight GTK3 settings application, `coffee-control-center`.
It is a frontend for CoffeeOS tools that already existed in the image; privileged
operations go through polkit (`pkexec`) and an allow-listed backend instead of
running arbitrary shell strings.

## Pages

- **Overview** — CoffeeOS version, kernel, architecture, memory, GPU/driver summary,
  live-vs-installed state, and shortcuts for network, sound and terminal system info.
- **Performance** — Lite, Balanced, Performance and Portable CoffeeKernel profiles.
  The GUI applies only governor/EPP controls supported by the hardware and can
  restore the original values recorded by `coffee-kernel-profile`.
- **Gaming** — persistent per-user defaults for MangoHud and Gamescope when games
  are launched with `coffee-gaming-mode`. CLI overrides remain available.
- **Appearance** — Espresso/Latte themes, effects and per-user wallpaper selection.
- **Software & Drivers** — post-install access to the same optional software offered
  by the one Calamares ISO (Steam, Wine/DXVK, Gamescope, Lutris, Heroic), plus an
  explicit Debian NVIDIA driver action. Optional installs are disabled in the live
  session because Calamares is the correct place to choose them there.
- **Updates** — Debian 13 Trixie Stable package refresh, safe `apt-get upgrade`, and
  explicit cleanup. Upgrade/cleanup are disabled in the disposable live session.

## Security boundaries

The Control Center never evaluates text as shell code. Root actions are fixed argv
lists passed to `pkexec`. The update helper only accepts `list`, `check`, `upgrade`
and `cleanup`. Gaming installs continue to use the curated `coffee-gaming-setup`
actions. Heroic remains an explicit third-party Flathub opt-in.

The Control Center does not disable CPU security mitigations, overclock hardware,
or silently add Debian Testing/Unstable repositories.

## Launching

Open it from the application launcher, click the Waybar gear, or press **Super+C**.
The original compact Quick Settings remains on **Super+S**.


## Display, Bluetooth and audio

Coffee Control Center includes native lightweight pages for:
- Display resolution, refresh rate, scale, rotation and multi-monitor position using `wlr-randr`. Applied display settings are restored on later logins.
- Bluetooth power, discovery, pairing, connection and disconnection using BlueZ. Blueman remains available for pairing workflows that require a PIN.
- PipeWire output/input selection, speaker and microphone volume, and mute controls. Pavucontrol remains available as the advanced mixer.

## First-boot welcome

Installed CoffeeOS sessions show `coffee-first-boot` on the first desktop login only. The live ISO skips it. The welcome screen links directly to Display, Audio, Bluetooth, Updates and Software & Drivers pages and records completion in the user's CoffeeOS config directory.


## Daily-driver controls

Coffee Control Center now also covers:
- Power and battery status, automatic lock/suspend, lock-before-sleep, suspend/hibernate and laptop lid behavior.
- Pointer speed, natural scrolling, tap-to-click, keyboard repeat settings, keyboard layout, timezone, network time, locale and 12/24-hour panel clock format.
- Account display name, avatar, password shortcut and opt-in automatic login.
- CoffeeOS nftables firewall controls and persistent Do Not Disturb/notification timeout settings.
- Default browser/text/image apps, startup application toggles, optional Flatpak + Flathub, and optional CUPS printing support.
- Storage status, safe user/system cleanup, SMART health checks, CoffeeKernel/Debian fallback status, one-boot fallback selection, package rollback, build metadata and support-bundle creation.
- Night Light with manual temperature and schedule.
- Gaming Mode panel status, controller detection, MangoHud presets, and per-game GameMode/MangoHud/Gamescope/FPS-cap overrides.

CoffeeOS keeps the Debian kernel installed as a recovery fallback and keeps the GRUB menu visible for five seconds. The updater saves up to five CoffeeOS/CoffeeKernel package snapshots before upgrades when the current versions can still be downloaded from configured repositories.
