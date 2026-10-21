"""Coffee Desktop Phase 3 source and isolated home tests; no live compositor is assumed."""
from __future__ import annotations
import configparser
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CHROOT = ROOT / 'live-build/config/includes.chroot'
BIN = CHROOT/'usr/local/bin'

class TestDesktopConfig(unittest.TestCase):

    def test_installer_has_unsquashfs_dependency(self):
        packages=set((ROOT/'live-build/config/package-lists/20-installer.list.chroot').read_text().split())
        self.assertIn('squashfs-tools', packages)
        self.assertIn('shim-signed',packages)
        self.assertIn('grub-efi-amd64-signed',packages)

    def test_installed_target_removes_live_installer_launcher(self):
        job=(CHROOT/'usr/lib/calamares/modules/coffeeapps/main.py').read_text()
        self.assertIn('/usr/share/applications/coffeeos-installer.desktop',job)
        self.assertIn('/usr/local/bin/coffeeos-installer',job)
        package=(ROOT/'scripts/build-coffeeos-system-package.sh').read_text()
        self.assertIn('/usr/share/applications/coffeeos-installer.desktop',package)
        self.assertIn('Migration cleanup',package)

    def test_coffeeos_installer_replaces_debian_launcher(self):
        launcher=(CHROOT/'usr/share/applications/coffeeos-installer.desktop').read_text()
        self.assertIn('Name=Install CoffeeOS', launcher)
        self.assertIn('Exec=coffeeos-installer', launcher)
        self.assertNotIn('Exec=install-debian', launcher)
        wrapper=(CHROOT/'usr/local/bin/coffeeos-installer').read_text()
        self.assertIn('calamares-install-debian', wrapper)
        self.assertIn('install-debian', wrapper)
        hook=(ROOT/'live-build/config/hooks/live/040-coffeeos-installer-options.hook.chroot').read_text()
        self.assertIn('Install Debian', hook)
        self.assertIn('calamares-install-debian.desktop', hook)
        self.assertIn('org.calamares.calamares.desktop', hook)
        self.assertIn('coffeeos-installer.desktop', hook)

    def test_graphical_wayland_greeter(self):
        cfg=tomllib.loads((CHROOT/'etc/greetd/config.toml').read_text())
        self.assertEqual(cfg['default_session']['user'], '_greetd')
        self.assertEqual(cfg['default_session']['command'], '/usr/local/bin/coffee-greeter')
        self.assertNotIn('initial_session', cfg)
        runtime=(CHROOT/'usr/local/sbin/coffee-greetd-config').read_text()
        self.assertIn('[initial_session]', runtime)
        self.assertIn('user = "coffeeos"', runtime)
        self.assertIn('command = "/usr/local/bin/coffee-session"', runtime)
        self.assertIn("grep -qw 'boot=live' /proc/cmdline", runtime)
        self.assertIn('cp "$base_cfg" "$runtime_cfg"', runtime)
        greeter=(BIN/'coffee-greeter').read_text()
        self.assertIn('gtkgreet',greeter)
        self.assertIn('cage',greeter)
        self.assertIn('WLR_RENDERER=pixman',greeter)
        self.assertIn('LIBSEAT_BACKEND=seatd',greeter)
        self.assertNotIn('tuigreet',cfg['default_session']['command'])
        self.assertIn('coffee-session',(CHROOT/'etc/greetd/environments').read_text())
        self.assertIn('Exec=coffee-session',(CHROOT/'usr/share/wayland-sessions/coffee.desktop').read_text())

    def test_theme_and_compositor_configuration(self):
        tree=ET.parse(CHROOT/'etc/xdg/labwc/rc.xml')
        self.assertEqual(tree.findtext('theme/name'), 'CoffeeOS-Espresso-Noir')
        keys={e.get('key') for e in tree.findall('.//keybind')}
        for key in ('W-space', 'W-s', 'W-p', 'Print', 'XF86AudioMute'):
            self.assertIn(key, keys)
        ET.parse(CHROOT/'etc/xdg/labwc/menu.xml')
        theme_names=('CoffeeOS-Espresso-Noir','CoffeeOS-Latte-Cream','CoffeeOS-Caramel-Sunrise','CoffeeOS-Mocha-Night','CoffeeOS-Hazelnut-Mist','CoffeeOS-Macchiato-Glow')
        for name in theme_names:
            theme=(CHROOT/'usr/share/themes'/name/'labwc/themerc').read_text()
            self.assertIn('window.active.border.color',theme)
            self.assertIn('window.active.shadow.size',theme)
        autostart=(CHROOT/'etc/xdg/labwc/autostart').read_text()
        for name in ('coffee-wallpaper', 'waybar', 'mako', 'coffee-hardware-settings display-restore', 'coffee-first-boot'):
            self.assertIn(name,autostart)
        self.assertNotIn('coffee-quick-settings', (CHROOT/'etc/xdg/labwc/rc.xml').read_text())
        for service in ('coffee-idle-manager','coffee-night-light','udiskie'):
            self.assertIn(service,autostart)

    def test_panel_launcher_notifications_and_packages(self):
        bar=json.loads((CHROOT/'etc/xdg/waybar/config.jsonc').read_text())
        self.assertEqual(bar['position'],'top')
        self.assertIn('custom/controlcenter',bar['modules-right'])
        self.assertIn('coffee-control-center',bar['custom/controlcenter']['on-click'])
        self.assertEqual(bar['network']['on-click'],'coffee-wifi-menu')
        self.assertEqual(bar['network']['on-click-right'],'nm-connection-editor')
        self.assertIn('custom/gaming',bar['modules-right'])
        self.assertEqual(bar['custom/gaming']['exec'],'coffee-gaming-indicator')
        fuzzel=configparser.ConfigParser(interpolation=None)
        fuzzel.read(CHROOT/'etc/xdg/fuzzel/fuzzel.ini')
        self.assertEqual(fuzzel.get('main','terminal'),'foot')
        self.assertTrue((CHROOT/'etc/xdg/mako/config').exists())
        packages=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        for pkg in ('cage','gtkgreet','python3-gi','gir1.2-gtk-3.0','waybar','labwc','swaylock','swayidle','gammastep','upower','nftables','smartmontools','udiskie','fwupd','mokutil','sbsigntool','wl-clipboard','orca','lm-sensors','nvme-cli','bluez-obexd'):
            self.assertIn(pkg,packages)


    def test_welcome_is_hardware_aware_and_bug_reporter_is_private(self):
        welcome=(BIN/'coffee-first-boot').read_text()
        self.assertIn('hardware_summary',welcome)
        self.assertIn('Recommended for this PC',welcome)
        self.assertIn('GPU Switching',welcome)
        self.assertIn('Flatpak Permissions',welcome)
        reporter=(BIN/'coffee-bug-report').read_text()
        self.assertIn('CoffeeOS never uploads diagnostics automatically.',reporter)
        self.assertIn('https://github.com/lilblock1/CoffeeOS/issues/new',reporter)
        self.assertIn('coffee-support-bundle',reporter)
        desktop=(CHROOT/'usr/share/applications/coffee-bug-report.desktop').read_text()
        self.assertIn('Exec=coffee-bug-report',desktop)

    def test_multi_gpu_and_controller_packages(self):
        desktop=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        gaming=set((ROOT/'live-build/config/package-lists/30-gaming.list.chroot').read_text().split())
        self.assertIn('switcheroo-control',desktop)
        self.assertIn('jstest-gtk',gaming)
        session=(BIN/'coffee-session').read_text()
        self.assertIn('coffeeos/gpu-mode',session)
        self.assertIn('DRI_PRIME=1',session)
        self.assertIn('__NV_PRIME_RENDER_OFFLOAD=1',session)

    def test_plymouth_boot_splash(self):
        packages=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        self.assertIn('plymouth',packages)
        self.assertIn('plymouth-themes',packages)
        theme=CHROOT/'usr/share/plymouth/themes/coffeeos/coffeeos.plymouth'
        script=CHROOT/'usr/share/plymouth/themes/coffeeos/coffeeos.script'
        self.assertTrue(theme.exists()); self.assertTrue(script.exists())
        self.assertIn('ModuleName=script',theme.read_text())
        self.assertIn('CoffeeOS',script.read_text())
        grub=(CHROOT/'etc/default/grub.d/50-coffeeos-plymouth.cfg').read_text()
        self.assertIn('quiet',grub); self.assertIn('splash',grub)
        hook=(ROOT/'live-build/config/hooks/live/050-coffeeos-plymouth.hook.chroot').read_text()
        self.assertIn('plymouth-set-default-theme coffeeos',hook)

    def test_lock_screen_is_theme_aware(self):
        lock=(BIN/'coffee-lock').read_text()
        for theme in ('espresso-noir','latte-cream','caramel-sunrise','mocha-night','hazelnut-mist','macchiato-glow'):
            self.assertIn(theme,lock)
        for option in ('--show-failed-attempts','--show-keyboard-layout',
                       '--indicator-caps-lock','--indicator-idle-visible',
                       '--ring-ver-color','--ring-wrong-color',
                       '--inside-wrong-color','--layout-text-color'):
            self.assertIn(option,lock)
        self.assertIn('--scaling fill',lock)
        tree=ET.parse(CHROOT/'etc/xdg/labwc/rc.xml')
        keys={e.get('key'): e.find('action').get('command') for e in tree.findall('.//keybind') if e.find('action') is not None}
        self.assertEqual(keys.get('W-l'),'coffee-lock')

    def test_waybar_is_compact_and_font_safe(self):
        bar=json.loads((CHROOT/'etc/xdg/waybar/config.jsonc').read_text())
        self.assertLessEqual(bar['height'],36)
        self.assertEqual(bar['cpu']['format'],'CPU {usage}%')
        self.assertNotIn('\uf2db',bar['cpu']['format'])
        self.assertEqual(bar['pulseaudio']['format'],'VOL {volume}%')
        style=(CHROOT/'etc/xdg/waybar/style.css').read_text()
        self.assertIn('window#waybar {',style)
        self.assertIn('background: transparent',style)
        self.assertIn('window#waybar > box',style)
        appearance=(BIN/'coffee-appearance').read_text()
        self.assertIn('window#waybar > box',appearance)
        self.assertIn('background: transparent',appearance)

    def test_vm_and_safe_graphics_software_fallback(self):
        session=(BIN/'coffee-session').read_text()
        self.assertIn('WLR_RENDERER_ALLOW_SOFTWARE=1',session)
        self.assertIn('WLR_RENDERER=pixman',session)
        self.assertIn('vmware',session)
        self.assertIn('virtualbox',session)
        self.assertIn('qemu',session)
        self.assertIn('coffeeos.software-render=1',session)
        self.assertIn('LIBSEAT_BACKEND=logind',session)
        hook=(ROOT/'live-build/config/hooks/live/020-enable-greetd.hook.chroot').read_text()
        self.assertIn('usermod -aG video,input _greetd',hook)
        self.assertIn('/usr/sbin/seatd -g video',hook)
        self.assertIn('After=live-config.service seatd.service', hook)
        self.assertIn('ExecStartPre=/usr/local/sbin/coffee-greetd-config', hook)
        self.assertIn('--config /run/coffeeos/greetd.toml', hook)
        auto=(ROOT/'live-build/auto/config').read_text()
        self.assertIn('coffeeos.software-render=1',auto)
        self.assertNotIn('nomodeset noapic nolapic',auto)

    def test_python_files_compile_without_gui(self):
        import ast
        for name in ('coffee-wifi-menu','coffee-power-menu','coffee-appearance','coffee-control-center','coffee-hardware-settings','coffee-first-boot','coffee-desktop-settings','coffee-night-light','coffee-gaming-indicator','coffee-support-bundle','coffee-installer-preflight','coffee-installer-report','coffee-hardware-health','coffee-driver-info','coffee-network-settings','coffee-accessibility','coffee-clipboard-history','coffee-app-center','coffee-gpu-manager','coffee-flatpak-permissions','coffee-bug-report'):
            ast.parse((BIN/name).read_text())

class TestDesktopAppearance(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.env=dict(os.environ,
                      XDG_CONFIG_HOME=str(self.home),
                      COFFEE_LABWC_TEMPLATE=str(CHROOT/'etc/xdg/labwc/rc.xml'),
                      COFFEE_NO_RELOAD='1')
        self.app=BIN/'coffee-appearance'

    def call(self,*args, check=True):
        return subprocess.run(['python3',str(self.app),*args],env=self.env,
                              check=check,capture_output=True,text=True)

    def state(self):
        return json.loads((self.home/'coffeeos/appearance.json').read_text())

    def test_default_and_switch_theme(self):
        default=json.loads(self.call('show').stdout)
        self.assertEqual(default,{'theme':'espresso-noir','effects':True})
        listed=self.call('list').stdout
        for name in ('espresso-noir','latte-cream','caramel-sunrise','mocha-night','hazelnut-mist','macchiato-glow'):
            self.assertIn(name, listed)
        self.assertIn('Latte Cream',self.call('theme','latte-cream').stdout)
        self.assertEqual(self.state()['theme'],'latte-cream')
        palette=(self.home/'waybar/style.css').read_text()
        self.assertIn('#efe1cc',palette)
        self.assertIn('window#waybar',palette)
        self.assertEqual(configparser.ConfigParser().read(self.home/'fuzzel/fuzzel.ini'),[str(self.home/'fuzzel/fuzzel.ini')])
        self.assertIn('gtk-application-prefer-dark-theme=0',(self.home/'gtk-3.0/settings.ini').read_text())
        self.assertTrue((self.home/'gtk-3.0/gtk.css').exists())
        self.assertTrue((self.home/'gtk-4.0/gtk.css').exists())
        self.assertTrue((self.home/'foot/foot.ini').exists())
        self.assertTrue((self.home/'coffeeos/control-center.css').exists())
        self.assertTrue((self.home/'coffeeos/wifi-menu.css').exists())
        self.assertTrue((self.home/'coffeeos/welcome.css').exists())
        self.assertEqual(ET.parse(self.home/'labwc/rc.xml').findtext('theme/name'),'CoffeeOS-Latte-Cream')

    def test_effects_off_preserves_keybinds(self):
        self.call('effects','off')
        tree=ET.parse(self.home/'labwc/rc.xml')
        self.assertEqual(tree.findtext('theme/dropShadows'),'no')
        self.assertTrue(tree.findall('.//keybind'))
        self.assertIn('gtk-enable-animations=0',(self.home/'gtk-3.0/settings.ini').read_text())
        self.call('effects','on')
        self.assertEqual(ET.parse(self.home/'labwc/rc.xml').findtext('theme/dropShadows'),'yes')

    def test_preserves_existing_user_labwc_config(self):
        labwc=self.home/'labwc'
        labwc.mkdir()
        (labwc/'rc.xml').write_text('<labwc_config><keyboard><keybind key="W-f"><action name="Execute" command="example-app" /></keybind></keyboard></labwc_config>')
        self.call('theme','latte')
        tree=ET.parse(labwc/'rc.xml')
        self.assertEqual(tree.find('.//keybind').get('key'),'W-f')
        self.assertEqual(tree.findtext('theme/dropShadows'),'yes')

    def test_all_themes_have_branded_wallpapers_and_static_window_themes(self):
        names=('espresso-noir','latte-cream','caramel-sunrise','mocha-night','hazelnut-mist','macchiato-glow')
        for name in names:
            wall=CHROOT/'usr/share/backgrounds/coffeeos'/f'{name}.svg'
            self.assertTrue(wall.exists(), name)
            self.assertGreater(wall.stat().st_size, 500)
        wall_script=(BIN/'coffee-wallpaper').read_text()
        for name in names: self.assertIn(name,wall_script)
        self.assertIn('coffee-appearance refresh',(CHROOT/'etc/xdg/labwc/autostart').read_text())

    def test_invalid_options_do_not_modify_config(self):
        proc=self.call('theme','mauve',check=False)
        self.assertNotEqual(proc.returncode,0)
        self.assertFalse((self.home/'coffeeos/appearance.json').exists())

    def test_reset_defaults(self):
        self.call('theme','latte')
        self.call('effects','off')
        self.call('reset')
        self.assertEqual(self.state(),{'theme':'espresso-noir','effects':True})

    def test_missing_template_fails_without_partial_state(self):
        self.env['COFFEE_LABWC_TEMPLATE']=str(self.home/'nonexistent.xml')
        p=self.call('theme','espresso',check=False)
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((self.home/'coffeeos/appearance.json').exists())

if __name__=='__main__':
    unittest.main()
