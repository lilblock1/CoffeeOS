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

    def test_qemu_smoke_test_requires_marker(self):
        s=(ROOT/'scripts/boot-smoke-test.sh').read_text()
        self.assertIn('qemu-system-x86_64', s)
        self.assertIn("grep -q 'COFFEEOS_BOOT_OK'", s)

if __name__=='__main__': unittest.main()
