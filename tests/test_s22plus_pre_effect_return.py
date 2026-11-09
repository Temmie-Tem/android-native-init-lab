"""H0 pre-overlay rejection certificate and actual guest/host return decisions."""
from pathlib import Path
import errno
import subprocess
import tempfile
import unittest

from test_s22plus_stage2_diagnostics import ROOT, SOURCE, function
from test_s22plus_ml030_wire import KEY, ID, WIT, GOOD, record, w


def compile_pre_effect(out, *, compiler='cc', enabled=True, guest=False):
    out.mkdir(parents=True, exist_ok=True)
    (out/'linux').mkdir(exist_ok=True)
    (out/'linux/types.h').touch()
    stage=(SOURCE/'g0q_stage.c').read_text()
    (out/'board.inc').write_text(stage[stage.index('struct board {'):stage.index('static int remaining(')])
    (out/'entry.inc').write_text('\n'.join(function(stage,s) for s in
                                          ('static int remaining(', 'static int report(', 'static int __init start(')))
    arena=(SOURCE/'transport/authority.inc.c').read_text()
    (out/'arena.inc').write_text('\n'.join(function(arena,s) for s in
                                          ('static bool g0q_issuer(', 'void g0q_rpmh_end(', 'void g0q_rpmh_status(')))
    (out/'guest.inc').write_text(function((SOURCE/'link-runtime.h').read_text(),'static int ml030_module_result('))
    exe=out/('guest' if guest else 'entry')
    flags=(['-DG0Q_PRE_EFFECT_RETURN'] if enabled else [])+(['-static'] if compiler!='cc' else [])
    subprocess.run([compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
                    '-Wno-unused-variable',*flags,'-I',out,'-I',SOURCE,
                    ROOT/('tests/s22plus_pre_effect_guest_fixture.c' if guest else 'tests/s22plus_pre_effect_fixture.c'),
                    '-o',exe],check=True)
    return exe


def module_report(exe,scenario,runner=()):
    return subprocess.check_output([*runner,exe,scenario],timeout=5)


class PreEffectReturnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-pre-effect-')
        cls.out=Path(cls.temp.name)
        cls.module=compile_pre_effect(cls.out/'module')
        cls.guest=compile_pre_effect(cls.out/'guest',guest=True)
        cls.oldguest=compile_pre_effect(cls.out/'old-guest',guest=True,enabled=False)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def accepted(self,guest,data,runner=()):
        return int(subprocess.check_output([*runner,guest],input=data,timeout=5))==0

    def host(self,data):
        return w.result(record(raw_bytes=data),WIT,KEY,ID,report_version=4)

    def exercise(self,module,guest,runner=()):
        data=module_report(module,'refuse',runner)
        facts=self.host(data)
        self.assertEqual(facts['status'],'NO_PROOF')
        self.assertEqual(facts['return_reason'],'PRE_EFFECT_REJECTION')
        self.assertTrue(facts['normal_return'])
        self.assertEqual(facts['operation_errno'],16)
        self.assertTrue(self.accepted(guest,data,runner))
        for scenario in ('refuse-held','refuse-pending','refuse-power-error','refuse-run-state',
                         'post-cover-expired','overlay-failed','rails-failed','probe-failed','stage2'):
            with self.subTest(scenario=scenario):
                data=module_report(module,scenario,runner)
                self.assertFalse(self.accepted(guest,data,runner))
                try:facts=self.host(data)
                except ValueError:continue
                self.assertFalse(facts['normal_return'])
                self.assertNotIn('control_nonce',facts)
        for scenario,error in (('early',110),('late',110),('wrong-board',19),('begin-failed',16)):
            self.assertEqual(module_report(module,scenario,runner),f'LOAD -{error}\n'.encode())

    def test_actual_module_and_guest_host(self):self.exercise(self.module,self.guest)

    def test_actual_arm64_module_and_guest_host(self):
        module=compile_pre_effect(self.out/'arm-module',compiler='aarch64-linux-gnu-gcc')
        guest=compile_pre_effect(self.out/'arm-guest',compiler='aarch64-linux-gnu-gcc',guest=True)
        for exe in (module,guest):self.assertIn('ARM aarch64',subprocess.check_output(['file',exe],text=True))
        self.exercise(module,guest,('qemu-aarch64',))

    def test_opt_in_and_result_integrity(self):
        data=module_report(self.module,'refuse')
        self.assertFalse(self.accepted(self.oldguest,data))
        for version in (1,2,3):
            with self.assertRaises(ValueError):w.result(record(raw_bytes=data),WIT,KEY,ID,report_version=version)
        values=list(map(int,data.split()))
        for i,value in ((1,2),(11,1),(16,-5),(17,1),(18,1),(21,0x40010001),(22,1)):
            changed=values.copy();changed[i]=value;line=(' '.join(map(str,changed))+'\n').encode()
            with self.subTest(i=i):
                self.assertFalse(self.accepted(self.guest,line))
                with self.assertRaises(ValueError):self.host(line)
        for bad in (data[:-1],b'-0'+data[3:],b' '+data,data+b' ',data.replace(b'-16',b'-016',1),
                    data.replace(b'-16',b'-2147483649',1)):
            self.assertFalse(self.accepted(self.guest,bad))
            with self.assertRaises(ValueError):self.host(bad)
        success=(' '.join(map(str,GOOD+[1<<16,0,0x40000000,0x7ff]))+'\n').encode()
        self.assertTrue(self.accepted(self.guest,success))
        self.assertTrue(self.host(success)['normal_return'])
        self.assertEqual(self.host(success)['status'],'UFS_LINK_COMPLETED')
        raw=record(raw_bytes=data)
        with self.assertRaises(ValueError):w.result(raw[:-1]+bytes([raw[-1]^1]),WIT,KEY,ID,report_version=4)


if __name__=='__main__':unittest.main()
