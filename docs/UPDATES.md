# CoffeeOS in-place updates — 0.10.0-dev

CoffeeOS can now update an installed machine without reinstalling from a new ISO.
There are two independent update sources:

1. **Debian 13 Trixie Stable** — security fixes and normal base-system packages.
2. **CoffeeOS GitHub Releases** — CoffeeOS-owned files and tested CoffeeKernel packages are published to moving `coffeeos-updates-dev`, `coffeeos-updates-beta`, and `coffeeos-updates-stable` releases in `lilblock1/CoffeeOS`.

The live ISO refuses update installation. Updates are for installed systems only.

## Client commands

```bash
coffee-update status
sudo coffee-update check
sudo coffee-update upgrade
sudo coffee-update cleanup
```

A CoffeeKernel update can be installed while the desktop is running. The old
kernel remains on disk and the new kernel is used after the next reboot. Most
userspace updates take effect immediately or when the affected program/session
is restarted.

The Control Center **Updates** page calls the same allow-listed backend through
polkit. A systemd timer checks every six hours (with randomized delay) and stores
non-sensitive status in `/var/lib/coffeeos/update-status.json`. It does not
silently install updates.

## GitHub update source

Installed CoffeeOS systems use `lilblock1/CoffeeOS` GitHub Releases as the built-in update source. The updater downloads the channel's `coffeeos-update.json` manifest over HTTPS, restricts package downloads to that repository's fixed update-release URL, verifies each SHA-256 checksum, and verifies the package name/version/architecture inside each `.deb` before installation.

The development image defaults to:

```bash
sudo coffee-update use-github dev
```

`sudo coffee-update clear-feed` disables CoffeeOS GitHub updates without touching Debian Stable sources. No GitHub Pages setup or repository signing secret is required for the built-in source.

## Configure a custom CoffeeOS release feed

CoffeeOS never enables an unsigned remote repository. Export the publisher's
OpenPGP **public** key, then on a client:

```bash
sudo coffee-update set-feed \
  https://updates.example.com/coffeeos \
  stable \
  /path/to/coffeeos-public-key.gpg
```

`https://` is required for remote feeds. `file://` is accepted for isolated
local testing. The updater installs the public key at
`/usr/share/keyrings/coffeeos-update.gpg` and creates a deb822 source with
`Signed-By=`. It refuses secret-key files.

Remove only the CoffeeOS-specific feed with:

```bash
sudo coffee-update clear-feed
```

Debian Stable repositories remain untouched.

## Publishing an update

Build CoffeeKernel and the Deep optimized packages as usual, then create the
versioned `coffeeos-system` package:

```bash
sudo bash scripts/build-coffeekernel-for-iso.sh --mode deep
sudo bash scripts/build-optimized-packages.sh --mode deep
bash scripts/build-coffeeos-system-package.sh
```

Create a signed APT repository using a publisher signing key that is kept off
client machines:

```bash
bash scripts/make-update-repo.sh \
  --suite stable \
  --key YOUR_GPG_SIGNING_KEY_ID \
  --output dist/update-repo
```

Upload the *contents* of `dist/update-repo/` to the configured HTTPS location.
Clients can then use **Check Now** / **Install Updates** without reinstalling.

For disposable local repository testing only, `--unsigned` can generate an
unsigned tree, but CoffeeOS clients intentionally will not configure an unsigned
remote feed.

## What `coffeeos-system` owns

The package deliberately owns the CoffeeOS-specific desktop and integration
layer: Control Center, CoffeeOS command-line tools, themes/wallpapers, labwc and
Waybar defaults, gaming configuration, update services, and related system
integration. Debian-owned unrelated files are not copied into this package.

Optimized Debian-derived packages (Mesa, PipeWire, wlroots, etc.) remain their
own `.deb` packages with `+coffee` versions. CoffeeKernel also remains a normal
kernel `.deb`. A signed CoffeeOS repository can therefore update each component
through standard APT/dpkg transactions rather than replacing the root filesystem.


## GitHub publishing behavior

Normal CoffeeOS userspace changes update the single `coffeeos-updates-dev` GitHub Release instead of creating a new ISO or a new release each time. The `coffeeos-system` package version includes the Git commit count so the updater can compare versions correctly.

When a tested CoffeeKernel release is published, its `.deb` files are merged into the moving Dev update release. Manual workflow runs can promote tested package sets to Beta or Stable. The moving release contains a JSON manifest and SHA-256 list, and stale package assets are replaced rather than creating release spam.
