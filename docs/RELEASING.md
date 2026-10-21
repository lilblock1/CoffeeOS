# Releasing CoffeeOS

## Developer channel

Use **Actions → Publish CoffeeOS Channel → Run workflow** and select `dev`.

Example development package version:

```text
0.10.0~dev2
```

## Beta channel

Promote a tested development build to `beta`. Beta should only receive artifacts that have passed source validation and QEMU boot testing.

## Stable channel

Stable publication should happen only after:

- CoffeeOS tests pass.
- CoffeeKernel package verification passes.
- ISO payload verification passes.
- BIOS/UEFI QEMU boot smoke tests pass.
- Desktop startup has been manually verified for the release candidate.
- Known hardware limitations are documented.

The Stable release process must never claim physical-hardware FPS or latency results that were not measured.

## Client update flow

Installed machines keep Debian Stable repositories for Debian packages and add the signed CoffeeOS repository for CoffeeOS-owned packages.

Typical client operations:

```bash
sudo coffee-update check
sudo coffee-update upgrade
```

A CoffeeKernel update can be installed while the old kernel is running; the new kernel becomes active after reboot.
