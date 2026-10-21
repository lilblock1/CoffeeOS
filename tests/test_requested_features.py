from __future__ import annotations
import ast
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[1]
INC=ROOT/'live-build/config/includes.chroot'
BIN=INC/'usr/local/bin'
SBIN=INC/'usr/local/sbin'

def load_script(name,path):
    loader=importlib.machinery.SourceFileLoader(name,str(path))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    mod=importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

class TestRequestedCoffeeOSFeatures(unittest.TestCase):
    def test_kernel_manager_inventory_next_boot_and_safety(self):
        m=load_script('coffee_kernel_manager_feature_test',SBIN/'coffee-kernel-manager')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); boot=root/'boot'; grub=root/'grub.cfg'; boot.mkdir()
            for version in ('6.12.113-coffee','6.12.57-amd64'):
                (boot/f'vmlinuz-{version}').write_text('')
                (boot/f'initrd.img-{version}').write_text('')
            grub.write_text("""submenu 'Advanced options for CoffeeOS' {
menuentry 'CoffeeOS, with Linux 6.12.113-coffee' {}
menuentry 'CoffeeOS, with Linux 6.12.57-amd64' {}
}
""")
            m.BOOT=boot; m.GRUB=grub
            with mock.patch.object(m.platform,'release',return_value='6.12.113-coffee'),                  mock.patch.object(m,'held_packages',return_value={'linux-image-6.12.57-amd64'}),                  mock.patch.object(m,'installed',return_value=True):
                items=m.inventory()
            self.assertEqual(len(items),2)
            coffee=next(x for x in items if x['coffee'])
            stock=next(x for x in items if not x['coffee'])
            self.assertTrue(coffee['current'])
            self.assertTrue(stock['held'])
            self.assertTrue(stock['grub_entry'])
            self.assertIn('Advanced options for CoffeeOS>',m.grub_target('6.12.57-amd64'))

        with mock.patch.object(m,'root'), mock.patch.object(m,'live',return_value=False),              mock.patch.object(m,'require_version',return_value={'current':True,'package_installed':True,'package':'linux-image-test'}):
            with self.assertRaisesRegex(SystemExit,'currently running'):
                m.remove('test')

        calls=[]
        with mock.patch.object(m,'root'), mock.patch.object(m,'live',return_value=False),              mock.patch.object(m,'require_version',return_value={'version':'stock'}),              mock.patch.object(m,'grub_target',return_value='Advanced options>stock'),              mock.patch.object(m,'run',side_effect=lambda argv,**kw:calls.append(argv) or subprocess.CompletedProcess(argv,0)):
            with redirect_stdout(io.StringIO()):
                m.next_boot('stock')
        self.assertEqual(calls,[['grub-reboot','Advanced options>stock']])

    def test_real_plymouth_splash_matches_approved_design(self):
        theme=INC/'usr/share/plymouth/themes/coffeeos'
        bg=(theme/'coffeeos-background.svg').read_text()
        steam=(theme/'steam.svg').read_text()
        script=(theme/'coffeeos.script').read_text()
        for phrase in ('CoffeeOS','Brewing your session...','#090504','#4b2415'):
            self.assertIn(phrase,bg)
        self.assertIn('filter',steam)
        self.assertIn('Plymouth.SetBootProgressFunction(progress_callback)',script)
        self.assertIn('Plymouth.SetRefreshFunction(refresh_callback)',script)
        self.assertIn('progress-fill.png',script)
        self.assertIn('steam.png',script)
        packages=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        self.assertIn('librsvg2-bin',packages)
        hook=(ROOT/'live-build/config/hooks/live/050-coffeeos-plymouth.hook.chroot').read_text()
        for asset in ('coffeeos-background','steam','progress-track','progress-fill'):
            self.assertIn(asset+'.png',hook)
        self.assertIn('rsvg-convert',hook)

    def test_plymouth_theme_is_complete_and_packaged(self):
        packages=set((ROOT/'live-build/config/package-lists/10-desktop.list.chroot').read_text().split())
        self.assertTrue({'plymouth','plymouth-themes'} <= packages)
        theme=INC/'usr/share/plymouth/themes/coffeeos/coffeeos.plymouth'
        script=INC/'usr/share/plymouth/themes/coffeeos/coffeeos.script'
        hook=ROOT/'live-build/config/hooks/live/050-coffeeos-plymouth.hook.chroot'
        grub=INC/'etc/default/grub.d/50-coffeeos-plymouth.cfg'
        self.assertIn('ModuleName=script',theme.read_text())
        self.assertIn('CoffeeOS',script.read_text())
        self.assertIn('Brewing your session',script.read_text())
        self.assertIn('plymouth-set-default-theme coffeeos',hook.read_text())
        self.assertIn('quiet',grub.read_text())
        self.assertIn('splash',grub.read_text())

    def test_gpu_switcher_detects_multiple_gpus_and_blocks_single_gpu(self):
        m=load_script('coffee_gpu_manager_feature_test',BIN/'coffee-gpu-manager')
        sample="""00:02.0 VGA compatible controller: Intel Corporation UHD Graphics
	Kernel driver in use: i915
01:00.0 3D controller: NVIDIA Corporation GA107M
	Kernel driver in use: nvidia
"""
        with mock.patch.object(m,'cap',return_value=(0,sample)):
            items=m.gpus()
        self.assertEqual([x['vendor'] for x in items],['intel','nvidia'])
        self.assertEqual([x['driver'] for x in items],['i915','nvidia'])
        with mock.patch.object(m,'gpus',return_value=items[:1]):
            with self.assertRaisesRegex(SystemExit,'two or more GPUs'):
                m.set_mode('discrete')
        with tempfile.TemporaryDirectory() as td,              mock.patch.object(m,'gpus',return_value=items),              mock.patch.object(m,'cfg',return_value=Path(td)/'gpu-mode'):
            with redirect_stdout(io.StringIO()):
                m.set_mode('discrete')
            self.assertEqual((Path(td)/'gpu-mode').read_text().strip(),'discrete')
        control=(BIN/'coffee-control-center').read_text()
        self.assertIn("if self.multi_gpu: self.add_page('gpu', 'GPU Switching'",control)
        self.assertIn("self.multi_gpu=bool(self.gpu_boot_info.get('multi_gpu'))",control)

    def test_controller_detection_and_tools(self):
        m=load_script('coffee_desktop_settings_feature_test',BIN/'coffee-desktop-settings')
        sample="""I: Bus=0003 Vendor=045e Product=02fd Version=0301
N: Name="Xbox Wireless Controller"
H: Handlers=event18 js0

I: Bus=0011 Vendor=0001 Product=0001 Version=ab41
N: Name="AT Keyboard"
H: Handlers=sysrq kbd event3
"""
        with mock.patch.object(Path,'read_text',return_value=sample):
            out=io.StringIO()
            with redirect_stdout(out): m.controllers()
        data=json.loads(out.getvalue())
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]['name'],'Xbox Wireless Controller')
        self.assertIn('js0',data[0]['handlers'])
        gaming=set((ROOT/'live-build/config/package-lists/30-gaming.list.chroot').read_text().split())
        self.assertIn('jstest-gtk',gaming)
        self.assertIn('joystick',gaming)
        control=(BIN/'coffee-control-center').read_text()
        self.assertIn("'jstest-gtk'",control)
        self.assertIn("'fftest'",control)
        self.assertIn('steam://open/controller_base',control)

    def test_flatpak_permission_parser_and_allowlisted_commands(self):
        m=load_script('coffee_flatpak_permissions_feature_test',BIN/'coffee-flatpak-permissions')
        app='org.example.Game'
        with mock.patch.object(m,'known',return_value=True),              mock.patch.object(m,'cap',return_value=(0,'[Context]\nshared=network;ipc;\nsockets=wayland;pulseaudio;\ndevices=dri;\nfilesystems=home;\n')):
            out=io.StringIO()
            with redirect_stdout(out): m.permissions(app)
        data=json.loads(out.getvalue())
        self.assertTrue(data['network']); self.assertTrue(data['audio'])
        self.assertTrue(data['gpu']); self.assertTrue(data['home'])

        calls=[]
        def fake_cap(argv,t=12):
            calls.append(argv); return 0,''
        with mock.patch.object(m,'known',return_value=True), mock.patch.object(m,'cap',side_effect=fake_cap):
            with redirect_stdout(io.StringIO()):
                m.set_perm(app,'network',False)
                m.set_perm(app,'gpu',True)
                m.reset(app)
        self.assertIn(['flatpak','override','--user','--unshare=network',app],calls)
        self.assertIn(['flatpak','override','--user','--device=dri',app],calls)
        self.assertIn(['flatpak','override','--user','--reset',app],calls)

    def test_bluetooth_battery_parsing(self):
        m=load_script('coffee_hardware_settings_feature_test',BIN/'coffee-hardware-settings')
        addr='11:22:33:44:55:66'
        def fake_capture(argv,timeout=8):
            if argv==['bluetoothctl','show']:
                return 0,'Controller AA:BB:CC:DD:EE:FF Coffee Bluetooth [default]\n\tPowered: yes'
            if argv==['bluetoothctl','devices']:
                return 0,f'Device {addr} Coffee Headphones'
            if argv==['bluetoothctl','devices','Paired']:
                return 0,f'Device {addr} Coffee Headphones'
            if argv==['bluetoothctl','devices','Connected']:
                return 0,f'Device {addr} Coffee Headphones'
            if argv==['bluetoothctl','info',addr]:
                return 0,'Name: Coffee Headphones\nConnected: yes\nBattery Percentage: 0x49 (73)'
            return 1,''
        with mock.patch.object(m,'capture',side_effect=fake_capture):
            data=m.bt_data()
        self.assertTrue(data['available']); self.assertTrue(data['powered'])
        self.assertEqual(data['devices'][0]['battery_percent'],73)
        control=(BIN/'coffee-control-center').read_text()
        self.assertIn('Battery {battery}%',control)

    def test_bug_reporter_is_privacy_first(self):
        source=(BIN/'coffee-bug-report').read_text()
        ast.parse(source)
        self.assertIn('https://github.com/lilblock1/CoffeeOS/issues/new',source)
        self.assertIn('CoffeeOS never uploads diagnostics automatically.',source)
        self.assertIn('Nothing was attached automatically.',source)
        self.assertIn("['xdg-open',url]",source)
        self.assertIn("['coffee-support-bundle']",source)
        self.assertNotIn('gh issue create',source)
        self.assertNotIn('requests.post',source)
        self.assertNotIn('urllib.request.urlopen',source)
        desktop=(INC/'usr/share/applications/coffee-bug-report.desktop').read_text()
        self.assertIn('Exec=coffee-bug-report',desktop)

    def test_welcome_2_is_hardware_aware_and_buttons_target_real_pages(self):
        source=(BIN/'coffee-first-boot').read_text()
        ast.parse(source)
        for phrase in ('Recommended for this PC','multi_gpu','nvidia','bluetooth','controllers'):
            self.assertIn(phrase,source)
        for page in ("'updates'","'gpu'","'software'","'bluetooth'","'controllers'","'flatpak'"):
            self.assertIn(page,source)
        self.assertIn("['/usr/local/bin/coffee-control-center','--page',page]",source)
        self.assertIn("GLib.child_watch_add(proc.pid,self.control_center_closed)",source)
        control=(BIN/'coffee-control-center').read_text()
        for page in ("'controllers'","'gpu'","'flatpak'"):
            self.assertIn(page,control)

    def test_iso_payload_verifier_covers_all_requested_features(self):
        verify=(ROOT/'scripts/verify-control-center-image.sh').read_text()
        for path in (
          '/usr/local/sbin/coffee-kernel-manager',
          '/usr/local/bin/coffee-gpu-manager',
          '/usr/local/bin/coffee-flatpak-permissions',
          '/usr/local/bin/coffee-bug-report',
          '/usr/share/plymouth/themes/coffeeos/coffeeos.plymouth',
          '/usr/share/applications/coffee-bug-report.desktop',
          '/usr/bin/jstest-gtk',
          '/usr/bin/fftest',
          '/usr/bin/switcherooctl',
        ):
            self.assertIn(path,verify)

if __name__=='__main__':
    unittest.main()
