from __future__ import annotations
import json, os, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INC=ROOT/'live-build/config/includes.chroot'

class TestPerformanceEngine(unittest.TestCase):
    def test_runtime_tools_exist(self):
        for rel in ('usr/local/bin/coffee-hardware-info','usr/local/bin/coffee-performance-status',
                    'usr/local/bin/coffee-benchmark','usr/local/bin/coffee-autotune',
                    'usr/local/bin/coffee-gaming-session','usr/local/sbin/coffee-memory-tune',
                    'usr/local/sbin/coffee-performance-daemon','usr/local/sbin/coffee-scheduler'):
            p=INC/rel; self.assertTrue(p.is_file(),rel); self.assertTrue(os.access(p,os.X_OK),rel)

    def test_hardware_probe_json(self):
        p=subprocess.run([str(INC/'usr/local/bin/coffee-hardware-info'),'--json'],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout)
        self.assertIn(d['cpu']['feature_level'],('x86-64-v1','x86-64-v2','x86-64-v3','x86-64-v4'))
        self.assertGreaterEqual(d['cpu']['logical_cpus'],1)
        self.assertIn('sched_ext',d)

    def test_memory_tune_status_is_unprivileged(self):
        p=subprocess.run([str(INC/'usr/local/sbin/coffee-memory-tune'),'status','--json'],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout); self.assertIn(d['profile'].split('-')[0],('low','mainstream','high'))
        self.assertEqual(d['settings']['page_cluster'],0)

    def test_sched_ext_kernel_support_configured_but_not_forced(self):
        cfg=(ROOT/'kernel/configs/coffee.conf').read_text()
        for line in ('CONFIG_BPF=y','CONFIG_BPF_SYSCALL=y','CONFIG_BPF_JIT=y','CONFIG_SCHED_CLASS_EXT=y','CONFIG_DEBUG_INFO_BTF=y'):
            self.assertIn(line,cfg)
        sched=(INC/'usr/local/sbin/coffee-scheduler').read_text()
        self.assertIn("CANDIDATES=('scx_lavd'",sched)
        self.assertNotIn('ExecStart=/usr/local/sbin/coffee-scheduler start', '\n'.join(p.read_text() for p in (INC/'usr/lib/systemd/system').glob('*') if p.is_file()))

    def test_performance_daemon_is_reversible_and_conservative(self):
        s=(INC/'usr/local/sbin/coffee-performance-daemon').read_text()
        self.assertIn("coffee-kernel-profile','apply','performance",s)
        self.assertIn("coffee-kernel-profile','restore",s)
        self.assertIn("coffee-memory-tune','gaming",s)
        self.assertNotIn('mitigations=off',s); self.assertNotIn('chrt',s); self.assertNotIn('overclock',s.lower().replace('never overclocks',''))
        unit=(INC/'usr/lib/systemd/system/coffee-performance-daemon.service').read_text()
        self.assertIn('NoNewPrivileges=yes',unit); self.assertIn('Restart=on-failure',unit)

    def test_gaming_mode_uses_cgroup_weights_and_per_game_preferences(self):
        s=(INC/'usr/local/bin/coffee-gaming-mode').read_text()
        self.assertIn('CPUWeight=10000',s); self.assertIn('IOWeight=10000',s)
        self.assertIn('systemd-run --user --scope',s); self.assertIn('SteamAppId',s)
        self.assertIn('game-show',s)
        pref=INC/'usr/local/bin/coffee-gaming-preferences'
        with tempfile.TemporaryDirectory() as td:
            env=dict(os.environ,XDG_CONFIG_HOME=td)
            subprocess.run([str(pref),'game-set','123','hud','on'],env=env,check=True,capture_output=True,text=True)
            p=subprocess.run([str(pref),'game-show','123'],env=env,check=True,capture_output=True,text=True)
            self.assertTrue(json.loads(p.stdout)['hud'])

    def test_gaming_session_and_minimal_autostart(self):
        session=(INC/'usr/share/wayland-sessions/coffee-gaming.desktop').read_text()
        self.assertIn('Exec=coffee-gaming-session',session)
        script=(INC/'usr/local/bin/coffee-gaming-session').read_text()
        self.assertIn('steam -gamepadui',script); self.assertIn('COFFEE_GAMING_SESSION=1',script)
        auto=(INC/'etc/xdg/labwc/autostart').read_text(); self.assertIn('COFFEE_GAMING_SESSION',auto)

    def test_benchmark_and_autotune_are_non_destructive(self):
        bench=(INC/'usr/local/bin/coffee-benchmark').read_text(); tune=(INC/'usr/local/bin/coffee-autotune').read_text()
        self.assertIn('not an FPS score',bench); self.assertIn('benchmark.json',bench)
        self.assertIn("profile='performance'",tune); self.assertNotIn('pkexec',tune)

    def test_updatable_system_package_carries_engine(self):
        s=(ROOT/'scripts/build-coffeeos-system-package.sh').read_text()
        self.assertIn('coffee-performance-daemon.service',s); self.assertIn('coffee-memory-tune.service',s)
        self.assertIn('coffee-gaming.desktop',s)
        hook=(ROOT/'live-build/config/hooks/live/050-enable-coffee-tuning.hook.chroot').read_text()
        self.assertIn('coffee-performance-daemon.service',hook); self.assertIn('coffee-memory-tune.service',hook)

    def test_control_center_exposes_engine_tools(self):
        s=(INC/'usr/local/bin/coffee-control-center').read_text()
        for text in ('Hardware Probe','Quick Benchmark','Performance Engine Status','coffee-autotune'):
            self.assertIn(text,s)

if __name__=='__main__': unittest.main()
