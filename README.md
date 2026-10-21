# CoffeeOS Update Repository

This repository publishes **signed APT updates** for installed CoffeeOS systems. It does **not** contain an ISO builder, ISO images, or the operating system source tree.

## How to publish an update

1. Build the changed CoffeeOS Debian packages locally (for example `coffeeos-system_0.10.1_amd64.deb`).
2. Open **Actions → Publish CoffeeOS Updates → Run workflow**.
3. Select `dev`, `beta`, or `stable` and supply the GitHub Release tag that contains your built `.deb` assets.
4. The workflow downloads the packages, validates them, builds signed APT indexes and publishes them through GitHub Pages.

**Before first use:** configure GitHub Pages (Source: GitHub Actions), create a dedicated GPG signing key, and add the repository secrets `COFFEEOS_GPG_PRIVATE_KEY` and `COFFEEOS_GPG_PASSPHRASE` (if applicable). See [SETUP.md](docs/SETUP.md).

**Safety:** Do not publish a Stable release until packages are tested on your own CoffeeOS installation. Publishing metadata does not prove package compatibility.

APT feed URL after Pages is enabled: `https://lilblock1.github.io/CoffeeOS/`

Channel suites: `dev`, `beta`, `stable`. The workflow updates only the selected suite and retains the other suites from the existing Pages deployment.

## Local package example

```bash
dpkg-deb --info coffeeos-system_0.10.1_all.deb
gh release create v0.10.1 --title 'CoffeeOS 0.10.1'
gh release upload v0.10.1 coffeeos-system_0.10.1_all.deb
```

Then run the publishing workflow with tag `v0.10.1`.

This repository intentionally does not automatically compile CoffeeKernel, Mesa, or an ISO. Those artifacts must be built and tested before uploading them to the Release.
