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
        for title in ('Overview','Display','Bluetooth','Audio','Network+','Power & Battery','Input & Region','Accessibility','Account & Security','Apps & Startup','System','Hardware & Firmware','Recovery Center','Performance','Gaming','Appearance','Software & Drivers','Updates'):
            self.assertIn(title,text)
        for backend in ('coffee-kernel-profile','coffee-gaming-setup','coffee-update','coffee-appearance','coffee-hardware-settings','coffee-desktop-settings','coffee-admin-settings','coffee-support-bundle','coffee-network-settings','coffee-accessibility','coffee-hardware-health','coffee-driver-info','coffee-recovery','coffee-secure-boot','coffee-platform-admin','coffee-app-center'):
            self.assertIn(backend,text)
        self.assertIn("['pkexec'",text)
        self.assertNotIn('shell=True',text)
        self.assertNotIn('os.system(',text)
        pkgs=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        self.assertIn('pkexec',pkgs)
        self.assertIn('wlr-randr',pkgs)
        self.assertIn('pulseaudio-utils',pkgs)
        self.assertIn('bluez',pkgs)
        for pkg in ('swaylock','swayidle','gammastep','upower','nftables','smartmontools','udiskie'):
            self.assertIn(pkg,pkgs)

    def test_desktop_and_panel_integration(self):
        desktop=(INC/'usr/share/applications/coffee-control-center.desktop').read_text()
        rc=(INC/'etc/xdg/labwc/rc.xml').read_text()
        waybar=(INC/'etc/xdg/waybar/config.jsonc').read_text()
        wifi=(BIN/'coffee-wifi-menu').read_text()
        self.assertIn('Exec=coffee-control-center',desktop)
        self.assertIn('key="W-c"',rc)
        self.assertIn('command="coffee-control-center"',rc)
        self.assertIn('"on-click": "coffee-control-center"',waybar)
        self.assertIn('coffee-wifi-menu',waybar)
        self.assertIn("'nmcli'",wifi)
        self.assertIn('nm-connection-editor',wifi)
        self.assertNotIn('shell=True',wifi)
        hardware=(BIN/'coffee-hardware-settings').read_text()
        welcome=(BIN/'coffee-first-boot').read_text()
        for tool in ('wlr-randr','bluetoothctl','pactl','wpctl'):
            self.assertIn(tool,hardware)
        self.assertNotIn('shell=True',hardware)
        self.assertIn("--page',page",welcome.replace(' ',''))
        self.assertIn('welcome-complete',welcome)

    def test_welcome_shortcuts_open_visible_control_center_pages(self):
        welcome=(BIN/'coffee-first-boot').read_text()
        self.assertIn("'/usr/local/bin/coffee-control-center','--page',page",welcome.replace(' ',''))
        self.assertIn('self.hide()',welcome)
        self.assertIn('GLib.child_watch_add',welcome)
        self.assertIn('self.present()',welcome)
        control=(BIN/'coffee-control-center').read_text()
        for page in ('overview','display','audio','bluetooth','updates','software'):
            self.assertIn("'"+page+"'",control)

    def test_kernel_manager_page_and_backend(self):
        control=(BIN/'coffee-control-center').read_text()
        self.assertIn("'kernel', 'Kernel'",control)
        self.assertIn('Kernel Manager',control)
        self.assertIn('coffee-kernel-manager',control)
        manager=(ROOT/'live-build/config/includes.chroot/usr/local/sbin/coffee-kernel-manager').read_text()
        self.assertIn('Refusing to remove the currently running kernel.',manager)
        self.assertIn('Refusing to remove the last bootable kernel.',manager)
        self.assertIn('grub-reboot',manager)
        self.assertIn('apt-mark',manager)

    def test_update_backend_is_allow_listed_and_live_safe(self):
        text=(SBIN/'coffee-update').read_text()
        for cmd in ("'status'","'list'","'check'","'upgrade'","'cleanup'","'set-feed'","'clear-feed'","'set-channel'","'rollback-list'","'rollback-latest'"):
            self.assertIn(cmd,text)
        self.assertIn("'boot=live' in Path('/proc/cmdline').read_text()",text)
        self.assertIn("['apt-get','-y','dist-upgrade']",text)
        self.assertIn("p.scheme not in ('https','file')",text)
        self.assertIn("Signed-By:",text)
        self.assertIn('save_rollback',text)
        self.assertIn("cwd=target",text)
        self.assertNotIn('shell=True',text)
        compat=(SBIN/'coffee-system-update').read_text()
        self.assertIn('exec /usr/local/sbin/coffee-update',compat)

    def test_phase5_iso_verifier_exists(self):
        verify=(ROOT/'scripts/verify-control-center-image.sh').read_text()
        for path in ('/usr/local/bin/coffee-control-center','/usr/local/bin/coffee-hardware-settings','/usr/local/bin/coffee-first-boot','/usr/local/bin/coffee-desktop-settings','/usr/local/bin/coffee-lock','/usr/local/bin/coffee-night-light','/usr/local/bin/coffee-support-bundle','/usr/local/bin/coffee-gaming-preferences','/usr/local/sbin/coffee-admin-settings',
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
        data=json.loads(self.invoke('show').stdout); self.assertEqual(data,{'gamemode':True,'gamescope':False,'hud':False})
        data=json.loads(self.invoke('set','hud','on').stdout); self.assertTrue(data['hud'])
        path=self.home/'cfg/coffeeos/gaming.json'; self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        data=json.loads(self.invoke('reset').stdout); self.assertEqual(data,{'gamemode':True,'gamescope':False,'hud':False})

    def test_gaming_mode_reads_json_defaults_as_data(self):
        script=(BIN/'coffee-gaming-mode').read_text()
        self.assertIn('coffee-gaming-preferences show',script)
        self.assertIn('--no-hud',script); self.assertIn('--no-gamescope',script); self.assertIn('--no-gamemode',script); self.assertIn('--fps-limit',script)
        self.assertIn('game-fps',(BIN/'coffee-gaming-preferences').read_text())
        self.assertNotIn('source "$HOME/.config/coffeeos/gaming',script)

if __name__=='__main__': unittest.main()
