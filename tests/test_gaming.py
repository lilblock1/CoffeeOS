from __future__ import annotations
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[1]
INC=ROOT/'live-build/config/includes.chroot'
BIN=INC/'usr/local/bin'
SBIN=INC/'usr/local/sbin'

class TestGamingPackages(unittest.TestCase):
    def test_core_gaming_packages(self):
        pkgs=set((ROOT/'live-build/config/package-lists/30-gaming.list.chroot').read_text().split())
        for pkg in ('gamemode','mangohud','libvulkan1','mesa-vulkan-drivers','vulkan-tools','steam-devices','joystick'):
            self.assertIn(pkg,pkgs)
        # Steam/i386 remains explicit rather than bloating the live image.
        self.assertNotIn('steam-installer',pkgs)

    def test_conservative_gamemode_configuration(self):
        cfg=(INC/'etc/gamemode.ini').read_text()
        self.assertIn('desiredgov=performance',cfg)
        self.assertIn('inhibit_screensaver=1',cfg)
        self.assertIn('disable_splitlock=0',cfg)
        self.assertIn('apply_gpu_optimisations=0',cfg)
        self.assertIn('renice=0',cfg)
        self.assertNotIn('apply_gpu_optimisations=accept-responsibility',cfg)

    def test_gaming_wrapper_handles_debian_usr_games_path(self):
        script=(BIN/'coffee-gaming-mode').read_text()
        self.assertIn('/usr/games/gamemoderun', script)

    def test_mako_gaming_mode(self):
        cfg=(INC/'etc/xdg/mako/config').read_text()
        self.assertIn('[mode=gaming]',cfg)
        self.assertIn('invisible=1',cfg)

    def test_setup_is_stable_plus_controlled_backports(self):
        script=(SBIN/'coffee-gaming-setup').read_text()
        self.assertIn('Suites: trixie-backports',script)
        self.assertIn('Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg',script)
        self.assertIn('-t trixie-backports gamescope',script)
        self.assertIn('steam-installer',script)
        self.assertIn('wine32:i386',script)
        self.assertIn('dxvk-wine32:i386',script)
        self.assertIn('nvidia-driver',script)
        self.assertNotIn('sid main',script)
        self.assertNotIn('testing main',script)


    def test_optional_gaming_apps_are_installer_choices_on_one_iso(self):
        core=(ROOT/'live-build/config/package-lists/30-gaming.list.chroot').read_text().split()
        chooser=(INC/'etc/calamares/modules/packagechooser-coffeeapps.conf').read_text()
        hook=(ROOT/'live-build/config/hooks/live/040-coffeeos-installer-options.hook.chroot').read_text()
        script=(SBIN/'coffee-gaming-setup').read_text()
        # Heavy launchers stay out of the live/base image. They are choices in the
        # same installer, not separate CoffeeOS images.
        self.assertNotIn('lutris', core)
        self.assertIn('mode: optionalmultiple', chooser)
        self.assertIn('method: legacy', chooser)
        self.assertIn('id: lutris', chooser)
        self.assertIn('id: steam', chooser)
        self.assertIn('id: wine', chooser)
        self.assertIn('id: gamescope', chooser)
        self.assertIn('packagechooser@coffeeapps', hook)
        self.assertNotIn('packages@coffeeapps', hook)
        self.assertIn("line.strip() == '- sources-final'", hook)
        self.assertIn("'- coffeeapps'", hook)
        self.assertIn('dpkg --add-architecture i386', hook)
        module=(INC/'usr/lib/calamares/modules/coffeeapps/main.py').read_text()
        self.assertIn('packagechooser_coffeeapps', module)
        self.assertIn('check_target_env_call(["apt-get", "update"])', module)
        self.assertIn('"lutris": ["lutris", "winetricks"]', module)
        # Terminal post-install path remains available, but `full` does not force Lutris.
        self.assertIn('lutris) need_root; install_lutris ;;', script)
        full_line=next(line for line in script.splitlines() if line.strip().startswith('full)'))
        self.assertNotIn('install_lutris', full_line)

    def test_iso_verifier_checks_phase4_payload(self):
        script=(ROOT/'scripts/verify-gaming-image.sh').read_text()
        for path in ('/usr/games/gamemoderun','/usr/bin/mangohud','/usr/bin/vulkaninfo',
                     '/usr/local/bin/coffee-gaming-mode','/usr/local/sbin/coffee-gaming-setup',
                     '/usr/local/bin/coffee-proton-manager'):
            self.assertIn(path,script)
        self.assertIn('unsquashfs -ll',script)

    def test_gaming_info_runs_read_only(self):
        p=subprocess.run(['python3',str(BIN/'coffee-gaming-info')],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('CoffeeOS Gaming Diagnostics',p.stdout)

class TestGamingMode(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.fakebin=self.root/'bin'; self.fakebin.mkdir()
        self.log=self.root/'calls.log'
        self.runtime=self.root/'runtime'; self.runtime.mkdir()
        def write(name,body):
            p=self.fakebin/name
            p.write_text('#!/bin/sh\nset -eu\n'+body)
            p.chmod(0o755)
        write('coffee-appearance', textwrap.dedent(f'''\
            if [ "${{1:-}}" = show ]; then printf '{{"theme":"espresso","effects":true}}\\n'; exit 0; fi
            printf 'appearance %s %s\\n' "${{1:-}}" "${{2:-}}" >> {self.log!s}
        '''))
        write('makoctl', f'printf \'mako %s %s %s\\n\' "${{1:-}}" "${{2:-}}" "${{3:-}}" >> {self.log!s}\n')
        write('gamemoderun', f'echo gamemode >> {self.log!s}\nexec "$@"\n')
        write('mangohud', f'echo mangohud >> {self.log!s}\nexec "$@"\n')
        write('gamescope', textwrap.dedent(f'''\
            echo gamescope >> {self.log!s}
            [ "${{1:-}}" = -f ] && shift
            [ "${{1:-}}" = -- ] && shift
            exec "$@"
        '''))
        self.env=dict(os.environ, PATH=str(self.fakebin)+os.pathsep+os.environ.get('PATH',''),
                      XDG_RUNTIME_DIR=str(self.runtime))
        self.app=BIN/'coffee-gaming-mode'

    def test_enters_wraps_and_restores(self):
        p=subprocess.run([str(self.app),'--hud','--gamescope','--','/bin/echo','ok'],
                         env=self.env,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),'ok')
        calls=self.log.read_text()
        for expected in ('appearance effects off','mako mode -a gaming','gamemode','mangohud','gamescope','mako mode -r gaming','appearance effects on'):
            self.assertIn(expected,calls)
        self.assertFalse((self.runtime/'coffeeos-gaming/state').exists())

    def test_arguments_are_not_shell_evaluated(self):
        marker=self.root/'MUST_NOT_EXIST'
        payload=f'x;touch {marker}'
        p=subprocess.run([str(self.app),'--','python3','-c','import sys; print(sys.argv[1])',payload],
                         env=self.env,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),payload)
        self.assertFalse(marker.exists())

class TestProtonManager(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.env=dict(os.environ,HOME=str(self.home))
        self.app=BIN/'coffee-proton-manager'

    def make_good_archive(self):
        src=self.home/'src'/'GE-Proton-Test'; src.mkdir(parents=True)
        (src/'compatibilitytool.vdf').write_text('"compatibilitytools" {}\n')
        (src/'proton').write_text('test\n')
        archive=self.home/'ge.tar.gz'
        with tarfile.open(archive,'w:gz') as tf: tf.add(src,arcname='GE-Proton-Test')
        return archive

    def test_install_list_remove(self):
        arc=self.make_good_archive()
        p=subprocess.run(['python3',str(self.app),'install-archive',str(arc)],env=self.env,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        tool=self.home/'.local/share/Steam/compatibilitytools.d/GE-Proton-Test'
        self.assertTrue((tool/'compatibilitytool.vdf').is_file())
        p=subprocess.run(['python3',str(self.app),'list'],env=self.env,text=True,capture_output=True,check=True)
        self.assertIn('GE-Proton-Test',p.stdout)
        subprocess.run(['python3',str(self.app),'remove','GE-Proton-Test'],env=self.env,check=True,capture_output=True,text=True)
        self.assertFalse(tool.exists())

    def test_rejects_path_traversal(self):
        arc=self.home/'evil.tar.gz'
        with tarfile.open(arc,'w:gz') as tf:
            info=tarfile.TarInfo('../escape'); data=b'bad'; info.size=len(data); tf.addfile(info,io.BytesIO(data))
        p=subprocess.run(['python3',str(self.app),'install-archive',str(arc)],env=self.env,text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((self.home/'escape').exists())

if __name__=='__main__': unittest.main()
