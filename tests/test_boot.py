from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
LB=ROOT/'live-build'

class TestBootRecipe(unittest.TestCase):
    def test_bios_uses_syslinux_and_efi_uses_grub(self):
        cfg=(LB/'auto/config').read_text()
        self.assertIn("--bootloaders 'syslinux grub-efi'", cfg)
        self.assertNotIn("--bootloaders 'grub-pc grub-efi'", cfg)

    def test_bios_autoboot_is_text_safe(self):
        cfg=(LB/'config/bootloaders/isolinux/isolinux.cfg').read_text()
        self.assertIn('default live-amd64', cfg)
        self.assertIn('timeout 50', cfg)
        self.assertNotIn('vesamenu', cfg.lower())
        self.assertNotIn('splash', cfg.lower())

    def test_coffeekernel_binary_hook_retargets_bios_autoboot(self):
        hook=(LB/'config/hooks/live/060-prefer-coffeekernel.hook.binary').read_text()
        self.assertIn('coffee_label="live-coffee"', hook)
        self.assertIn('default $coffee_label', hook)
        self.assertIn('ontimeout $coffee_label', hook)
        self.assertIn('BIOS Syslinux default now selects', hook)
        verify=(ROOT/'scripts/verify-iso.sh').read_text()
        self.assertIn("BIOS default label '$bios_default' does not exist in live.cfg.", verify)
        self.assertIn('BIOS Syslinux labels verified', verify)

    def test_uefi_grub_is_text_mode_with_timeout(self):
        cfg=(LB/'config/bootloaders/grub-pc/config.cfg').read_text()
        self.assertIn('set timeout=5', cfg)
        self.assertIn('terminal_output console', cfg)
        self.assertNotIn('gfxterm', cfg)
        self.assertNotIn('splash', cfg)

    def test_live_boot_has_serial_marker_service(self):
        svc=LB/'config/includes.chroot/etc/systemd/system/coffeeos-boot-ok.service'
        self.assertTrue(svc.exists())
        self.assertIn('COFFEEOS_BOOT_OK', svc.read_text())
        hook=LB/'config/hooks/live/030-enable-boot-marker.hook.chroot'
        self.assertIn('systemctl enable coffeeos-boot-ok.service', hook.read_text())

    def test_full_install_smoke_test(self):
        s=(ROOT/'scripts/install-smoke-test.sh').read_text()
        self.assertIn('coffeeos.ci-install=1',s)
        self.assertIn('COFFEEOS_CI_INSTALL_OK',s)
        self.assertIn('COFFEEOS_BOOT_OK',s)
        self.assertIn('qemu-img create',s)
        service=(LB/'config/includes.chroot/etc/systemd/system/coffeeos-ci-install.service').read_text()
        self.assertIn('ConditionKernelCommandLine=coffeeos.ci-install=1',service)
        helper=(LB/'config/includes.chroot/usr/local/sbin/coffeeos-ci-install').read_text()
        self.assertIn('unsquashfs',helper)
        self.assertIn('grub-install',helper)
        self.assertNotIn('\\${disk}',helper)
        self.assertIn('"${disk}1"',helper)
        self.assertIn('"${disk}2"',helper)
        self.assertNotIn('\\${BASH_SOURCE[0]}',s)
        self.assertNotIn('ISO="\\${1:-',s)

    def test_installed_safe_graphics_grub_entry(self):
        cfg=(LB/'config/includes.chroot/etc/grub.d/41_coffeeos_safe_graphics').read_text()
        self.assertIn("CoffeeOS (Safe Graphics)",cfg)
        self.assertIn('coffeeos.software-render=1',cfg)
        self.assertIn('nomodeset',cfg)

    def test_qemu_smoke_test_requires_marker(self):
        s=(ROOT/'scripts/boot-smoke-test.sh').read_text()
        self.assertIn('qemu-system-x86_64', s)
        self.assertIn("grep -q 'COFFEEOS_BOOT_OK'", s)

if __name__=='__main__': unittest.main()
