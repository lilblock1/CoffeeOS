from __future__ import annotations
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
INC=ROOT/'live-build/config/includes.chroot'
UPDATER=INC/'usr/local/sbin/coffee-update'


def load_updater():
    loader=importlib.machinery.SourceFileLoader('coffee_update_test',str(UPDATER))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    mod=importlib.util.module_from_spec(spec); loader.exec_module(mod)
    return mod

class TestInPlaceUpdates(unittest.TestCase):
    def test_release_metadata_and_timer_exist(self):
        rel=(INC/'usr/share/coffeeos/release').read_text()
        self.assertIn('COFFEEOS_VERSION=0.10.0-dev',rel)
        timer=(INC/'usr/lib/systemd/system/coffee-update-check.timer').read_text()
        self.assertIn('OnUnitActiveSec=6h',timer)
        self.assertIn('Persistent=true',timer)
        svc=(INC/'usr/lib/systemd/system/coffee-update-check.service').read_text()
        self.assertIn('/usr/local/sbin/coffee-update check --background',svc)

    def test_updater_accepts_only_signed_https_or_local_feed(self):
        m=load_updater()
        self.assertEqual(m.normalize_url('https://updates.example.com/coffeeos'),'https://updates.example.com/coffeeos')
        self.assertEqual(m.normalize_url('file:///srv/coffeeos'),'file:///srv/coffeeos')
        with self.assertRaises(SystemExit): m.normalize_url('http://updates.example.com/coffeeos')
        with self.assertRaises(SystemExit): m.normalize_url('ftp://updates.example.com/coffeeos')
        text=UPDATER.read_text()
        self.assertIn("Signed-By: {KEYRING}",text)
        self.assertIn("CHANNELS={'stable','beta','dev'}",text)
        self.assertIn('ROLLBACK=',text)
        self.assertIn('save_rollback',text)
        self.assertIn('rollback-latest',text)
        self.assertIn("Refusing to install a secret signing key",text)

    def test_status_json_is_non_privileged(self):
        p=subprocess.run(['python3',str(UPDATER),'status','--json'],text=True,capture_output=True,check=True)
        data=json.loads(p.stdout)
        for key in ('version','feed_url','feed_configured','upgrade_count','coffeeos_upgrade_count','reboot_required'):
            self.assertIn(key,data)

    def test_coffeeos_system_package_builder_is_explicit_and_versioned(self):
        script=(ROOT/'scripts/build-coffeeos-system-package.sh').read_text()
        self.assertIn('Package: coffeeos-system',script)
        self.assertIn('usr/local/bin usr/local/sbin',script)
        self.assertIn('usr/lib/systemd/system/coffee-update-check.timer',script)
        self.assertIn('COFFEEOS_PACKAGE_VERSION',script)
        self.assertIn('dpkg-deb --root-owner-group --build',script)
        self.assertNotIn('/etc/shadow',script)
        self.assertNotIn('/home/',script)

    def test_publisher_requires_signing_by_default(self):
        script=(ROOT/'scripts/make-update-repo.sh').read_text()
        self.assertIn("Signed update repositories require --key GPG_KEY_ID",script)
        self.assertIn('gpg --batch --yes --default-key',script)
        self.assertIn('InRelease',script)
        self.assertIn('Release.gpg',script)
        self.assertIn('--unsigned',script)

    def test_deep_packages_use_policy_revision_and_cache(self):
        opt=(ROOT/'scripts/build-optimized-packages.sh').read_text()
        kernel=(ROOT/'scripts/build-kernel.sh').read_text()
        policy=(ROOT/'optimization/cache-policy.conf').read_text()
        self.assertIn('COFFEE_PACKAGE_REVISION',opt)
        self.assertIn('COFFEE_OPT_CACHE_ABI=1000',policy)
        self.assertIn('COFFEE_KERNEL_REVISION',kernel)
        self.assertIn('COFFEE_KERNEL_CACHE_ABI=1000',policy)
        # Point releases must not force expensive source recompilation.
        self.assertNotIn('rv_major * 10000 + 10#$rv_minor * 100 + 10#$rv_patch',opt)
        self.assertNotIn('rv_major * 10000 + 10#$rv_minor * 100 + 10#$rv_patch',kernel)

    def test_control_center_exposes_feed_and_install(self):
        text=(INC/'usr/local/bin/coffee-control-center').read_text()
        for phrase in ('Check Now','Install Updates','Update Source','set-feed','clear-feed','Set Update Channel','Rollback Last Update'):
            self.assertIn(phrase,text)
        self.assertIn("['pkexec','/usr/local/sbin/coffee-update','upgrade']",text)


    def test_waybar_update_indicator_is_read_only(self):
        indicator=(INC/'usr/local/bin/coffee-update-indicator').read_text()
        self.assertIn('/var/lib/coffeeos/update-status.json',indicator)
        self.assertNotIn('apt-get',indicator)
        waybar=json.loads((INC/'etc/xdg/waybar/config.jsonc').read_text())
        self.assertIn('custom/updates',waybar['modules-right'])
        self.assertEqual(waybar['custom/updates']['exec'],'coffee-update-indicator')
        self.assertEqual(waybar['custom/updates']['on-click'],'coffee-control-center')

    def test_build_pipeline_stages_updatable_system_package(self):
        # CoffeeOS source validation runs from a staged copy containing only the
        # CoffeeOS tree. Do not reach into the Windows-builder wrapper that lives
        # outside ROOT; wrapper-specific assertions belong in tests/test_builder.py.
        build=(ROOT/'scripts/build-iso.sh').read_text()
        self.assertIn('build-coffeeos-system-package.sh',build)

if __name__=='__main__': unittest.main()
