from __future__ import annotations
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INC = ROOT / 'live-build/config/includes.chroot'

class TestOptimizationPipeline(unittest.TestCase):
    def test_curated_source_rebuild_manifest(self):
        manifest=(ROOT/'optimization/packages.tsv').read_text()
        for source in ('wlroots','labwc','gamemode','mangohud','waybar','fuzzel','foot',
                       'seatd','libinput','libdrm','wayland','pipewire','wireplumber','mesa','xwayland'):
            self.assertRegex(manifest, rf'(?m)^{re.escape(source)}\\|')
        self.assertIn('|core|',manifest)
        self.assertIn('|deep|',manifest)

    def test_rebuilds_keep_debian_hardening_and_generic_cpu(self):
        script=(ROOT/'scripts/build-optimized-packages.sh').read_text()
        self.assertIn("hardening=+all optimize=+lto",script)
        self.assertIn("DEB_CFLAGS_MAINT_APPEND='-O3'",script)
        self.assertIn("version += '+coffee' + os.environ['COFFEE_PACKAGE_REVISION']",script)
        self.assertIn('COFFEE_OPT_CACHE_DIR', script)
        self.assertIn('CACHE HIT', script)
        self.assertIn('DEBIAN_ARCHIVE_KEYRING', script)
        self.assertIn('debian-archive-keyring.pgp', script)
        self.assertIn('debian-archive-keyring.gpg', script)
        self.assertIn('ccache', script)
        self.assertIn('nocheck nodoc noautodbgsym terse', script)
        policy=(ROOT/'optimization/cache-policy.conf').read_text()
        self.assertIn('COFFEE_OPT_CACHE_ABI=1000', policy)
        self.assertIn('Failed optimized package builds are logged and skipped',script)
        # -march=native may occur only in comments/guard text; it must never be assigned.
        self.assertNotRegex(script, r"(?:CFLAGS|CXXFLAGS).*=['\"]?[^\n]*-march=native")
        self.assertIn('fallback-build',script)
        self.assertIn('dpkg-deb -f "$deb" Package',script)

        self.assertIn("! -name 'linux-image-*-coffee_*.deb'", script)
        self.assertIn("! -name 'coffeeos-system_*.deb'", script)


    def test_fast_deep_cache_is_release_independent(self):
        script=(ROOT/'scripts/build-optimized-packages.sh').read_text()
        self.assertIn('cache_key()', script)
        self.assertIn('source_version', script)
        self.assertIn('gccver', script)
        self.assertIn('cache_abi=$CACHE_ABI', script)
        # Normal CoffeeOS point releases must not force Mesa/etc to rebuild.
        self.assertNotIn('rv_major * 10000', script)
        kernel=(ROOT/'scripts/build-coffeekernel-for-iso.sh').read_text()
        self.assertIn('COFFEE_KERNEL_CACHE_DIR', kernel)
        self.assertIn('CACHE HIT', kernel)
        self.assertIn('fragment_sha', kernel)
        build=(ROOT/'scripts/build-kernel.sh').read_text()
        self.assertIn('COFFEE_KERNEL_CACHE_ABI', build)
        self.assertIn('ccache', build)

    def test_ultra_fast_deep_build_speed_features(self):
        opt=(ROOT/'scripts/build-optimized-packages.sh').read_text()
        self.assertIn('jobs > 24', opt)
        self.assertIn('noautodbgsym terse', opt)
        self.assertIn('miss_specs', opt)
        self.assertIn('one APT transaction', opt)
        self.assertIn('--only-source "${miss_specs[@]}"', opt)
        self.assertIn('source-package concurrency', opt)
        self.assertIn('wait -n', opt)
        self.assertIn('flock -x 9', opt)
        auto=(ROOT/'live-build/auto/config').read_text()
        self.assertIn('--cache-packages true', auto)
        self.assertIn('--cache-stages bootstrap', auto)
        self.assertIn('--cache-indices false', auto)
        self.assertIn('--chroot-squashfs-compression-type zstd', auto)
        self.assertIn('--chroot-squashfs-compression-level 1', auto)
        self.assertIn('Dpkg::Options::=--force-unsafe-io', auto)
        iso=(ROOT/'scripts/build-iso.sh').read_text()
        self.assertIn('COFFEE_LIVE_BUILD_CACHE_DIR', iso)
        self.assertIn('packages.bootstrap', iso)
        self.assertIn('packages.chroot', iso)
        self.assertNotIn('ln -s "$COFFEE_LIVE_BUILD_CACHE_DIR" "$WORK/cache"', iso)
        verify=(ROOT/'scripts/verify-iso.sh').read_text()
        self.assertIn('COFFEEOS_VERIFY_SQUASHFS', verify)
        self.assertIn('verify_pids', verify)
        workflow=(ROOT/'.github/workflows/build-custom-iso.yml').read_text()
        self.assertIn('Restore reusable Deep optimization cache', workflow)
        self.assertIn('COFFEE_OPT_CACHE_DIR=/workspace/.cache/optimized-packages', workflow)
        self.assertIn('build-optimized-packages.sh --mode deep', workflow)
        self.assertIn('Save reusable Deep optimization cache', workflow)
        self.assertIn('dist/optimized/STATUS.tsv', workflow)

    def test_kernel_is_one_runtime_tunable_performance_kernel(self):
        cfg=(ROOT/'kernel/configs/coffee.conf').read_text()
        for line in ('CONFIG_PREEMPT=y','CONFIG_PREEMPT_DYNAMIC=y','CONFIG_HZ_1000=y',
                     'CONFIG_HIGH_RES_TIMERS=y','CONFIG_SCHED_AUTOGROUP=y',
                     'CONFIG_X86_INTEL_PSTATE=y','CONFIG_X86_AMD_PSTATE=y',
                     'CONFIG_MQ_IOSCHED_DEADLINE=y','CONFIG_IOSCHED_BFQ=m',
                     'CONFIG_ZRAM=m','CONFIG_ZRAM_MULTI_COMP=y',
                     'CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y'):
            self.assertIn(line,cfg)
        self.assertIn('# CONFIG_SCHED_DEBUG is not set',cfg)
        self.assertNotIn('CONFIG_HZ_250=y',cfg)
        self.assertNotIn('-march=native', '\n'.join(
            line for line in cfg.splitlines() if not line.lstrip().startswith('#')))

    def test_kernel_wrapper_stages_single_coffeekernel_and_keeps_fallback(self):
        script=(ROOT/'scripts/build-coffeekernel-for-iso.sh').read_text()
        self.assertIn('build-kernel.sh',script)
        self.assertIn('linux-image-*-coffee',script)
        self.assertIn('linux-headers-*-coffee',script)
        self.assertIn('cp -f -- "${images[0]}" "${headers[0]}" "$PKGDIR/"',script)
        foundation=(ROOT/'live-build/config/package-lists/00-foundation.list.chroot').read_text()
        self.assertIn('linux-image-amd64',foundation)


    def test_coffeekernel_is_preferred_in_live_boot_without_removing_fallback(self):
        auto=(ROOT/'live-build/auto/config').read_text()
        self.assertIn('config/packages.chroot/linux-image-*-coffee_*.deb',auto)
        self.assertIn('COFFEE_LINUX_PACKAGES="linux-image-$coffee_version"',auto)
        self.assertIn('COFFEE_LINUX_FLAVOURS=coffee',auto)
        self.assertIn('--linux-packages "$COFFEE_LINUX_PACKAGES"',auto)
        self.assertIn('--linux-flavours "$COFFEE_LINUX_FLAVOURS"',auto)
        foundation=(ROOT/'live-build/config/package-lists/00-foundation.list.chroot').read_text()
        self.assertIn('linux-image-amd64',foundation)

        init_hook=(ROOT/'live-build/config/hooks/live/045-coffeekernel-initramfs.hook.chroot').read_text()
        self.assertIn('update-initramfs -c -k "$version"',init_hook)
        self.assertIn('failed to create CoffeeKernel initrd',init_hook)

        hook=(ROOT/'live-build/config/hooks/live/060-prefer-coffeekernel.hook.binary').read_text()
        self.assertIn('binary/live/vmlinuz-$version',hook)
        self.assertIn('binary/live/initrd.img-$version',hook)
        self.assertIn('live-build selected CoffeeKernel as live boot default',hook)
        self.assertNotIn('rm -f binary/live/vmlinuz',hook)

        grub=(ROOT/'live-build/config/bootloaders/grub-pc/grub.cfg').read_text()
        self.assertNotIn('nomodeset',grub)
        self.assertIn('@LB_BOOTAPPEND_LIVE_FAILSAFE@',grub)
        verify=(ROOT/'scripts/verify-optimization-image.sh').read_text()
        self.assertIn("Lutris was unexpectedly preinstalled",verify)
        self.assertIn("CoffeeKernel not copied to ISO /live",verify)
        self.assertIn("was not selected by the live boot menu",verify)
        self.assertIn("CoffeeOS stock optimization manifest verified",verify)
        self.assertIn("CoffeeOS Deep optimization manifest contains custom Core and Deep packages",verify)

    def test_xorriso_quoted_live_paths_are_normalized(self):
        verify=(ROOT/'scripts/verify-optimization-image.sh').read_text()
        self.assertIn('normalize_xorriso_paths()', verify)
        self.assertGreaterEqual(verify.count('| normalize_xorriso_paths'), 2)
        # Regression for run 39617695618: xorriso printed a valid custom
        # kernel as '/live/vmlinuz-6.12.113-coffee', including presentation
        # quotes, while the verifier expected an unquoted path.
        sample="'/live/vmlinuz-6.12.113-coffee'\n"
        proc=subprocess.run(
            ['sed','-e',"s/^'//",'-e',"s/'$//"],
            input=sample,text=True,capture_output=True,check=True)
        self.assertEqual(proc.stdout.strip(),'/live/vmlinuz-6.12.113-coffee')

    def test_memory_storage_and_logging_defaults_are_conservative(self):
        zram=(INC/'usr/lib/systemd/zram-generator.conf.d/60-coffeeos.conf').read_text()
        self.assertIn('min(ram / 2, 4096)',zram)
        self.assertIn('compression-algorithm = lz4 zstd',zram)
        sysctl=(INC/'usr/lib/sysctl.d/60-coffeeos.conf').read_text()
        for setting in ('kernel.sched_autogroup_enabled = 1','vm.swappiness = 100',
                        'vm.page-cluster = 0','vm.dirty_background_ratio = 5'):
            self.assertIn(setting,sysctl)
        journal=(INC/'etc/systemd/journald.conf.d/60-coffeeos.conf').read_text()
        self.assertIn('Compress=yes',journal)
        self.assertIn('SystemMaxUse=256M',journal)
        storage=(INC/'usr/local/sbin/coffee-storage-tune').read_text()
        self.assertIn('/sys/block/nvme*',storage)
        self.assertIn('/sys/block/sd*',storage)
        self.assertIn('/sys/block/mmcblk*',storage)
        self.assertNotIn('/sys/block/dm-',storage)

    def test_single_iso_calamares_optional_software(self):
        chooser=(INC/'etc/calamares/modules/packagechooser-coffeeapps.conf').read_text()
        self.assertIn('mode: optionalmultiple',chooser)
        self.assertIn('method: legacy',chooser)
        for item in ('id: steam','id: wine','id: lutris','id: gamescope'):
            self.assertIn(item,chooser)
        base='\n'.join(p.read_text() for p in (ROOT/'live-build/config/package-lists').glob('*.list.chroot'))
        self.assertNotIn('\nlutris\n', '\n'+base+'\n')
        module=(INC/'usr/lib/calamares/modules/coffeeapps/main.py').read_text()
        self.assertIn('PACKAGE_GROUPS',module)
        self.assertIn('packagechooser_coffeeapps',module)
        self.assertIn('DEBIAN_FRONTEND=noninteractive',module)
        c=subprocess.run(['python3','-m','py_compile',str(INC/'usr/lib/calamares/modules/coffeeapps/main.py')],capture_output=True,text=True)
        self.assertEqual(c.returncode,0,c.stderr)

    def test_stock_mode_is_non_destructive_and_help_runs(self):
        p=subprocess.run(['bash',str(ROOT/'scripts/build-optimized-packages.sh'),'--help'],
                         text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('stock',p.stdout)
        self.assertIn('deep',p.stdout)

if __name__ == '__main__':
    unittest.main()
