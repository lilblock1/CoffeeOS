from __future__ import annotations
import json, os
from pathlib import Path
import subprocess, tempfile, unittest

ROOT=Path(__file__).resolve().parents[1]
INC=ROOT/'live-build/config/includes.chroot'
BIN=INC/'usr/local/bin'
SBIN=INC/'usr/local/sbin'

class TestControlCenterIntegration(unittest.TestCase):
    def test_control_center_is_real_frontend(self):
        text=(BIN/'coffee-control-center').read_text()
        for title in ('Overview','Performance','Gaming','Appearance','Software & Drivers','Updates'):
            self.assertIn(title,text)
        for backend in ('coffee-kernel-profile','coffee-gaming-setup','coffee-update','coffee-appearance'):
            self.assertIn(backend,text)
        self.assertIn("['pkexec'",text)
        self.assertNotIn('shell=True',text)
        self.assertNotIn('os.system(',text)
        pkgs=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        self.assertIn('pkexec',pkgs)

    def test_desktop_and_panel_integration(self):
        desktop=(INC/'usr/share/applications/coffee-control-center.desktop').read_text()
        rc=(INC/'etc/xdg/labwc/rc.xml').read_text()
        waybar=(INC/'etc/xdg/waybar/config.jsonc').read_text()
        quick=(BIN/'coffee-quick-settings').read_text()
        self.assertIn('Exec=coffee-control-center',desktop)
        self.assertIn('key="W-c"',rc)
        self.assertIn('command="coffee-control-center"',rc)
        self.assertIn('"on-click": "coffee-control-center"',waybar)
        self.assertIn('Open Coffee Control Center',quick)

    def test_update_backend_is_allow_listed_and_live_safe(self):
        text=(SBIN/'coffee-update').read_text()
        for cmd in ("'status'","'list'","'check'","'upgrade'","'cleanup'","'set-feed'","'clear-feed'"):
            self.assertIn(cmd,text)
        self.assertIn("'boot=live' in Path('/proc/cmdline').read_text()",text)
        self.assertIn("['apt-get','-y','dist-upgrade']",text)
        self.assertIn("p.scheme not in ('https','file')",text)
        self.assertIn("Signed-By:",text)
        self.assertNotIn('shell=True',text)
        compat=(SBIN/'coffee-system-update').read_text()
        self.assertIn('exec /usr/local/sbin/coffee-update',compat)

    def test_phase5_iso_verifier_exists(self):
        verify=(ROOT/'scripts/verify-control-center-image.sh').read_text()
        for path in ('/usr/local/bin/coffee-control-center','/usr/local/bin/coffee-gaming-preferences',
                     '/usr/local/sbin/coffee-update','/usr/share/applications/coffee-control-center.desktop'):
            self.assertIn(path,verify)
        main=(ROOT/'scripts/verify-iso.sh').read_text()
        self.assertIn('verify-control-center-image.sh',main)

class TestGamingPreferences(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name); self.env=dict(os.environ,HOME=str(self.home),XDG_CONFIG_HOME=str(self.home/'cfg'))
        self.app=BIN/'coffee-gaming-preferences'

    def invoke(self,*args):
        return subprocess.run(['python3',str(self.app),*args],env=self.env,text=True,capture_output=True,check=True)

    def test_defaults_set_reset_and_private_file(self):
        data=json.loads(self.invoke('show').stdout); self.assertEqual(data,{'gamescope':False,'hud':False})
        data=json.loads(self.invoke('set','hud','on').stdout); self.assertTrue(data['hud'])
        path=self.home/'cfg/coffeeos/gaming.json'; self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        data=json.loads(self.invoke('reset').stdout); self.assertEqual(data,{'gamescope':False,'hud':False})

    def test_gaming_mode_reads_json_defaults_as_data(self):
        script=(BIN/'coffee-gaming-mode').read_text()
        self.assertIn('coffee-gaming-preferences show',script)
        self.assertIn('--no-hud',script); self.assertIn('--no-gamescope',script)
        self.assertNotIn('source "$HOME/.config/coffeeos/gaming',script)

if __name__=='__main__': unittest.main()
