# SPDX-License-Identifier: MIT
"""Install CoffeeOS optional software selected in Calamares.

The chooser uses legacy mode deliberately: Debian's stock `packages` job runs
while the target is still pointed at live media. This job runs after
`sources-final`, when network repositories are configured.
"""

import subprocess

import libcalamares
from libcalamares.utils import check_target_env_call


PACKAGE_GROUPS = {
    "steam": [
        "steam-installer",
        "steam-devices",
        "libvulkan1:i386",
        "mesa-vulkan-drivers:i386",
        "libgl1-mesa-dri:i386",
        "libglx-mesa0:i386",
        "libgamemode0:i386",
    ],
    "wine": [
        "wine",
        "wine64",
        "wine32:i386",
        "dxvk",
        "dxvk-wine64",
        "dxvk-wine32:i386",
    ],
    "lutris": ["lutris", "winetricks"],
    "gamescope": ["gamescope"],
}


def pretty_name():
    return "Install selected CoffeeOS software."


def pretty_status_message():
    return "Installing optional gaming software..."


def _selected_ids():
    value = libcalamares.globalstorage.value("packagechooser_coffeeapps")
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def run():
    from pathlib import Path
    if Path('/tmp/coffeeos-oem-mode').exists():
        check_target_env_call(['mkdir','-p','/etc/coffeeos'])
        check_target_env_call(['touch','/etc/coffeeos/oem-firstboot'])
        libcalamares.utils.debug('CoffeeOS: new-owner onboarding marker installed')

    # The installer launcher and its live-only helpers belong only to the live
    # session. Calamares copies the SquashFS into the target, so remove them
    # from the installed system before finishing.
    check_target_env_call([
        "rm", "-f",
        "/usr/share/applications/coffeeos-installer.desktop",
        "/usr/local/bin/coffeeos-installer",
        "/usr/local/bin/coffee-installer-preflight",
        "/usr/local/bin/coffee-installer-report",
    ])

    selected = _selected_ids()
    if not selected:
        libcalamares.utils.debug("CoffeeOS: no optional software selected")
        return None

    unknown = sorted(set(selected) - set(PACKAGE_GROUPS))
    if unknown:
        return (
            "Unknown CoffeeOS software selection",
            "The installer received unsupported selection(s): " + ", ".join(unknown),
        )

    if not libcalamares.globalstorage.value("hasInternet"):
        return (
            "Internet connection required",
            "Optional CoffeeOS software was selected, but no internet connection is available. "
            "Connect to the internet or go back and deselect the optional software.",
        )

    packages = []
    for group in selected:
        for package in PACKAGE_GROUPS[group]:
            if package not in packages:
                packages.append(package)

    try:
        # Steam/Wine need i386. Adding the foreign architecture is harmless for
        # other choices and keeps one deterministic path through APT.
        check_target_env_call(["dpkg", "--add-architecture", "i386"])
        check_target_env_call(["apt-get", "update"])
        check_target_env_call(
            ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-q", "-y", "install"]
            + packages
        )
    except subprocess.CalledProcessError as exc:
        return (
            "Optional software installation failed",
            "APT could not install the selected CoffeeOS software (exit code {}). "
            "The base operating system was unpacked, but the installer will stop rather than "
            "silently omit software you requested.".format(exc.returncode),
        )

    libcalamares.utils.debug("CoffeeOS: installed optional groups: " + ", ".join(selected))
    return None
