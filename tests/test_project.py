from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INC = ROOT/'live-build/config/includes.chroot'

class TestCoffeeOS(unittest.TestCase):
    def test_manifest_and_repositories(self):
        cfg=(ROOT/'live-build/auto/config').read_text()
        self.assertIn('--distribution trixie',cfg)
        self.assertIn('--uefi-secure-boot disable',cfg)
        self.assertNotIn('deb.debian.org/debian-testing',cfg)
        for path in (ROOT/'live-build/config/package-lists').glob('*.list.chroot'):
            self.assertFalse(any(x in path.read_text() for x in ('apt-key add','trusted=yes','sid main','testing main')))

    def test_required_packages(self):
        pkgs='\n'.join(p.read_text() for p in (ROOT/'live-build/config/package-lists').glob('*.list.chroot'))
        for pkg in ('labwc','greetd','linux-image-amd64','calamares','calamares-settings-debian','live-boot','live-config','user-setup','network-manager','systemd-zram-generator'):
            self.assertIn(pkg,pkgs)


    def test_live_user_is_buildable_with_no_recommends(self):
        cfg=(ROOT/'live-build/auto/config').read_text()
        foundation=(ROOT/'live-build/config/package-lists/00-foundation.list.chroot').read_text().splitlines()
        self.assertIn('--apt-recommends false', cfg)
        self.assertIn('user-setup', foundation)
        self.assertIn('username=coffeeos', cfg)

    def test_desktop_configs(self):
        ET.parse(INC/'etc/xdg/labwc/rc.xml')
        s=(INC/'etc/xdg/waybar/config.jsonc').read_text()
        # Config is plain JSON, legal subset of JSONC
        obj=json.loads(s)
        self.assertEqual(obj['position'],'top')
        self.assertIn("_greetd", (INC/"etc/greetd/config.toml").read_text())
        runtime=(INC/'usr/local/sbin/coffee-greetd-config').read_text()
        self.assertIn('[initial_session]', runtime)
        self.assertIn('user = "coffeeos"', runtime)
        self.assertTrue((INC/'usr/share/backgrounds/coffeeos/espresso.svg').exists())

    def test_profiles_persist_to_temp_home(self):
        script=INC/'usr/local/bin/coffee-profile'
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ, XDG_CONFIG_HOME=tmp)
            def call(*args):
                return subprocess.run(['python3',str(script),*args],env=env,text=True,capture_output=True,check=True).stdout.strip()
            self.assertEqual(call('show'),'balanced')
            self.assertIn('performance',call('list'))
            self.assertIn('Saved portable',call('set','portable'))
            self.assertEqual(call('show'),'portable')
            self.assertTrue((Path(tmp)/'coffeeos/profile.json').exists())

    def test_readonly_info(self):
        p=subprocess.run(['python3',str(INC/'usr/local/bin/coffee-info')],text=True,capture_output=True,check=True)
        self.assertIn('CoffeeOS',p.stdout)

    def test_gaming_wrapper_fallback(self):
        p=subprocess.run([str(INC/'usr/local/bin/coffee-gaming-mode'),'--','/bin/echo','ok'],text=True,capture_output=True,check=True)
        self.assertEqual(p.stdout.strip(),'ok')

if __name__ == '__main__': unittest.main()
