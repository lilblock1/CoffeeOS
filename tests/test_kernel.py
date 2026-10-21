"""Single CoffeeKernel: real config merge, mocked package build, runtime sysfs fixtures.

Mock .debs DO NOT contain a compiled kernel. Test fixtures NEVER access real
sysfs or install packages.
"""
from __future__ import annotations
import importlib.util
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_TOOL = ROOT/'kernel/tools/configure.py'
PROFILE_TOOL = ROOT/'live-build/config/includes.chroot/usr/local/sbin/coffee-kernel-profile'

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:  # `sbin` file has no .py suffix
        from importlib.machinery import SourceFileLoader
        spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

configure = module(CONFIG_TOOL, 'coffee_kernel_configure')
runtime = module(PROFILE_TOOL, 'coffee_kernel_runtime')

class TestKernelConfig(unittest.TestCase):
    def test_one_config_and_dynamic_preemption(self):
        self.assertEqual([p.name for p in (ROOT/'kernel/configs').glob('*.conf')], ['coffee.conf'])
        vals = configure.fragment_lines((ROOT/'kernel/configs/coffee.conf').read_text())
        self.assertEqual(vals['CONFIG_PREEMPT_DYNAMIC'], 'y')
        self.assertEqual(vals['CONFIG_PREEMPT'], 'y')
        self.assertEqual(vals['CONFIG_HZ_1000'], 'y')
        self.assertEqual(vals['CONFIG_PREEMPT_RT'], 'n')

    def test_one_build_dry_run_and_no_variant_option(self):
        p = subprocess.run(['bash', str(ROOT/'scripts/build-kernel.sh'), '--dry-run'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('ONE kernel', p.stdout)
        p = subprocess.run(['bash', str(ROOT/'scripts/build-kernel.sh'), '--variant', 'both', '--dry-run'], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)

    def test_real_debian_baseline_if_available(self):
        configs = list(Path('/boot').glob('config-6.12*'))
        if not configs:
            self.skipTest('No Debian 6.12 baseline on this host')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'.config'
            frag = ROOT/'kernel/configs/coffee.conf'
            subprocess.run([sys.executable, str(CONFIG_TOOL), '--base', str(configs[-1]), '--fragment', str(frag), '--output', str(out)], check=True, capture_output=True)
            subprocess.run([sys.executable, str(CONFIG_TOOL), '--base', str(out), '--fragment', str(frag), '--verify'], check=True, capture_output=True)
            self.assertIn('CONFIG_HZ_1000=y', out.read_text())

    def test_compressed_config_and_fail_closed_on_changed_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)/'base.xz'; out = Path(tmp)/'out'
            cfg.write_bytes(lzma.compress(b'CONFIG_HZ_250=y\nCONFIG_SYSTEM_TRUSTED_KEYS="debian/certs/missing.pem"\n'))
            frag = ROOT/'kernel/configs/coffee.conf'
            subprocess.run([sys.executable, str(CONFIG_TOOL), '--base', str(cfg), '--fragment', str(frag), '--output', str(out)], check=True, capture_output=True)
            self.assertIn('CONFIG_SYSTEM_TRUSTED_KEYS=""', out.read_text())
            out.write_text(out.read_text().replace('CONFIG_PREEMPT_DYNAMIC=y', '# CONFIG_PREEMPT_DYNAMIC is not set'))
            p = subprocess.run([sys.executable, str(CONFIG_TOOL), '--base', str(out), '--fragment', str(frag), '--verify'], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('FAILED: CONFIG_PREEMPT_DYNAMIC', p.stdout)

    def test_duplicate_config_rejected(self):
        with self.assertRaises(ValueError):
            configure.parse('CONFIG_HZ_250=y\n# CONFIG_HZ_250 is not set\n')

class TestRuntimeProfiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'cpufreq'
        self.root.mkdir()
        self.state = Path(self.temp.name)/'state'/'profile.json'
        self.create_policy('policy0', 'schedutil', 'balance_performance')
        self.create_policy('policy1', 'schedutil', 'balance_performance')

    def create_policy(self, name, gov, epp):
        folder = self.root/name; folder.mkdir()
        for key, val in {
            'scaling_governor': gov,
            'scaling_available_governors': 'performance powersave schedutil ondemand',
            'energy_performance_preference': epp,
            'energy_performance_available_preferences': 'performance balance_performance balance_power power',
            'scaling_driver': 'amd-pstate-epp',
        }.items():
            (folder/key).write_text(val+'\n')

    def test_all_four_profiles_apply_and_restore_baseline(self):
        for mode in ('lite','balanced','performance','portable'):
            runtime.apply(mode, self.root, self.state)
            self.assertEqual(runtime.load(self.state)['profile'], mode)
            for item in runtime.observe(self.root).values():
                self.assertIn(item['governor'], ('powersave', 'schedutil', 'performance'))
        runtime.restore(self.root, self.state)
        self.assertFalse(self.state.exists())
        for item in runtime.observe(self.root).values():
            self.assertEqual(item['governor'], 'schedutil')
            self.assertEqual(item['epp'], 'balance_performance')

    def test_performance_governor_and_epp(self):
        runtime.apply('performance', self.root, self.state)
        for item in runtime.observe(self.root).values():
            self.assertEqual(item['governor'], 'performance')
            self.assertEqual(item['epp'], 'performance')

    def test_lite_energy_saving_preferences(self):
        runtime.apply('lite', self.root, self.state)
        for item in runtime.observe(self.root).values():
            self.assertEqual(item['governor'], 'powersave')
            self.assertEqual(item['epp'], 'power')

    def test_missing_cpu_policies_error_without_state(self):
        empty = Path(self.temp.name)/'empty'; empty.mkdir()
        with self.assertRaises(runtime.ProfileError):
            runtime.apply('performance', empty, self.state)
        self.assertFalse(self.state.exists())

    def test_missing_governor_and_epp_error_without_change(self):
        folder = self.root/'policy0'
        (folder/'scaling_available_governors').write_text('userspace\n')
        (folder/'energy_performance_available_preferences').write_text('default\n')
        with self.assertRaises(runtime.ProfileError):
            runtime.apply('performance', self.root, self.state)
        self.assertFalse(self.state.exists())
        self.assertEqual((folder/'scaling_governor').read_text().strip(), 'schedutil')

    def test_rollback_if_sysfs_write_fails(self):
        orig_write = runtime.write
        def flaky(root, changes):
            if not hasattr(flaky, 'called'):
                flaky.called = True
                orig_write(root, {'policy0': changes['policy0']})
                raise OSError('simulated sysfs write failure')
            orig_write(root, changes)
        runtime.write = flaky
        try:
            with self.assertRaises(runtime.ProfileError) as c:
                runtime.apply('performance', self.root, self.state)
            self.assertIn('previous values restored', str(c.exception))
        finally:
            runtime.write = orig_write
        self.assertFalse(self.state.exists())
        self.assertEqual(runtime.observe(self.root)['policy0']['governor'], 'schedutil')

    def test_state_permissions_and_reapply_original(self):
        runtime.apply('performance', self.root, self.state)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state.parent.stat().st_mode & 0o777, 0o700)
        before = runtime.load(self.state)['original']
        runtime.apply('portable', self.root, self.state)
        self.assertEqual(runtime.load(self.state)['original'], before)

    def test_older_cpu_with_no_epp_still_switches_governor(self):
        for name in ('policy0', 'policy1'):
            (self.root/name/'energy_performance_available_preferences').unlink()
            (self.root/name/'energy_performance_preference').unlink()
        runtime.apply('performance', self.root, self.state)
        self.assertEqual(runtime.observe(self.root)['policy0']['governor'], 'performance')
        runtime.restore(self.root, self.state)
        self.assertEqual(runtime.observe(self.root)['policy1']['governor'], 'schedutil')

    def test_rollback_preserves_selected_profile_on_failed_switch(self):
        runtime.apply('lite', self.root, self.state)
        orig = runtime.write
        def failing(root, changes):
            if not hasattr(failing, 'called'):
                failing.called = True
                orig(root, {'policy0': changes['policy0']})
                raise OSError('simulated second profile failure')
            orig(root, changes)
        runtime.write = failing
        try:
            with self.assertRaises(runtime.ProfileError):
                runtime.apply('performance', self.root, self.state)
        finally:
            runtime.write = orig
        self.assertEqual(runtime.load(self.state)['profile'], 'lite')
        self.assertEqual(runtime.observe(self.root)['policy0']['governor'], 'powersave')

    def test_missing_restore_baseline_fails(self):
        with self.assertRaises(runtime.ProfileError):
            runtime.restore(self.root, self.state)

    def test_read_only_status(self):
        p = subprocess.run([sys.executable, str(PROFILE_TOOL), 'list'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip().splitlines(), list(runtime.PROFILES))

@unittest.skipUnless(shutil.which('dpkg-deb') and shutil.which('make'), 'needs dpkg-deb and make')
class TestMockPackagePipeline(unittest.TestCase):
    def test_single_mock_package_pair_and_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp); src=t/'fake-linux'; (src/'scripts').mkdir(parents=True)
            (src/'scripts/Makefile.package').write_text('# fake only\n')
            base=t/'base.config'; base.write_text('CONFIG_HZ=250\nCONFIG_HZ_250=y\nCONFIG_PREEMPT_VOLUNTARY=y\nCONFIG_PREEMPT_DYNAMIC=y\n')
            (src/'Makefile').write_text('''
.PHONY: kernelversion olddefconfig bindeb-pkg
kernelversion:
\t@echo 6.12.113
olddefconfig:
\t@sed -i 's/^CONFIG_HZ=.*/CONFIG_HZ=1000/' '$(O)/.config'
bindeb-pkg:
\t@python3 '$(CURDIR)/mock.py' '$(O)' '$(LOCALVERSION)' '$(KDEB_PKGVERSION)'
''')
            (src/'mock.py').write_text('''
import subprocess, sys
from pathlib import Path
obj,suffix,ver=sys.argv[1:]
for kind in ('image','headers'):
    name='linux-'+kind+'-6.12.113'+suffix
    root=Path(obj).parent/('mock-'+kind)
    (root/'DEBIAN').mkdir(parents=True, exist_ok=True)
    (root/'DEBIAN/control').write_text('Package: '+name+'\\nVersion: '+ver+'\\nSection: kernel\\nPriority: optional\\nArchitecture: amd64\\nMaintainer: Test <mock@example.invalid>\\nDescription: MOCK ONLY NOT A KERNEL\\n')
    subprocess.run(['dpkg-deb','--build','--root-owner-group',str(root),str(Path(obj).parent/(name+'.deb'))],check=True,capture_output=True)
''')
            tools=t/'tools'; tools.mkdir()
            for name in ('bc','flex','bison','rsync','xz'):
                if not shutil.which(name):
                    stub=tools/name; stub.write_text('#!/bin/sh\nexit 0\n'); stub.chmod(0o755)
            env=dict(os.environ, COFFEE_KERNEL_WORK=str(t/'work'), COFFEE_KERNEL_DIST=str(t/'dist'),PATH=str(tools)+':'+os.environ['PATH'])
            p=subprocess.run(['bash',str(ROOT/'scripts/build-kernel.sh'),'--source',str(src),'--base-config',str(base)],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual([p.name for p in (t/'dist').iterdir()], ['coffee'])
            folder=t/'dist/coffee'
            self.assertEqual(len(list(folder.glob('*.deb'))),2)
            self.assertEqual(subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=folder,capture_output=True).returncode,0)
            p=subprocess.run(['bash',str(ROOT/'scripts/install-kernel.sh')],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn('Dry run only',p.stdout)
            deb=next(folder.glob('linux-image-*.deb'))
            deb.write_bytes(deb.read_bytes()+b'TAMPER')
            p=subprocess.run(['bash',str(ROOT/'scripts/install-kernel.sh')],env=env,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('checksum failed',p.stderr.lower())

if __name__=='__main__':
    unittest.main()
