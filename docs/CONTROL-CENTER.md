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
