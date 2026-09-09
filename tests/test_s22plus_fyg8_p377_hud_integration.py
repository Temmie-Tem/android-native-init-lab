"""Status collector, generated PID1, real IPC, and fixture DRM integration."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest import mock
import test_s22plus_fyg8_p376_hud_integration as base
import test_s22plus_fyg8_p377_hud_renderer as renderer_test
import s22plus_fyg8_p377_research_shell_runtime as runtime
import s22plus_fyg8_p377_research_shell_observer as observer


def source():
    with mock.patch.object(base,'runtime',runtime):value=base.source().replace('p376','p377')
    value=value.replace(' fx_mark("hud-child",0);',r'''
 if(!strcmp(a[1],"--collect-status")) {
  fx_mark("metrics-child",0);
  if(fx_case("metrics-blocked"))for(;;)usleep(10000);
  if(fx_case("metrics-exit"))_Exit(7);
  char *args[]={getenv("METRICS_COLLECTOR"),a[2],NULL};return neg(execve(args[0],args,e));
 }
 fx_mark("hud-child",0);''')
    return value


class StatusIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name);cls.binary=cls.folder/'native'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation','-o',str(cls.binary)],input=source(),text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
        fixture,headers=renderer_test.fixture()
        (cls.folder/'renderer.c').write_bytes(renderer_test.renderer.render())
        (cls.folder/'renderer-fixture.c').write_text(fixture)
        cls.real_renderer=cls.folder/'renderer'
        built=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),'-I',str(renderer_test.ROOT/'workspace/public/src/native-init'),str(cls.folder/'renderer-fixture.c'),'-o',str(cls.real_renderer)],capture_output=True,text=True)
        if built.returncode:raise AssertionError(built.stderr)
        cls.collector=cls.folder/'collector'
        from test_s22plus_status_metrics import SOURCE
        text=SOURCE[:SOURCE.index('int main(')]+ '\nint main(int argc,char **argv){return argc==2?status_collect(argv[1]):126;}\n'
        built=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-I',str(renderer_test.ROOT/'workspace/public/src/native-init'),'-o',str(cls.collector)],input=text,capture_output=True,text=True)
        if built.returncode:raise AssertionError(built.stderr)

    def run_case(self,case):
        self.renderer=str(self.real_renderer)
        with mock.patch.object(base,'runtime',runtime),mock.patch.object(base,'observer',observer),mock.patch.dict(os.environ,{'METRICS_COLLECTOR':str(self.collector)}):
            return base.HudIntegration.run_case(self,case)

    def test_combined_console_collector_renderer_and_replay(self):
        result,error,log,marks=self.run_case('normal')
        if error:raise AssertionError((repr(error.__cause__),log[-3000:]))
        self.assertTrue(result.receipt['proved'])
        self.assertEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)
        self.assertEqual(log.count(b'METRICS_SIGNAL_ATTEMPT '),1)
        self.assertEqual(marks.count('metrics-child 0'),1)
        audit=result.sessions[0].session.audit
        codec=base.live._open_header_initial_observer_module(runtime,observer,'p377-replay')
        self.assertEqual(observer.replay_session(codec,bytes(audit.rx),bytes(audit.tx),b'k'*32),result.receipt)

    def test_missing_or_blocked_collector_keeps_console_control(self):
        for case in ('metrics-blocked','metrics-exit'):
            with self.subTest(case=case):
                result,error,log,marks=self.run_case(case)
                self.assertIsNone(result);self.assertIsNotNone(error)
                proof=error.partial_receipt
                self.assertTrue(proof['control_acceptance_observed'])
                self.assertTrue(all(row['accepted'] and row['terminal'] is not None for row in proof['commands']))
                self.assertGreaterEqual(log.count(b'HUD_FRAME '),3)
                self.assertLessEqual(log.count(b'METRICS_SIGNAL_ATTEMPT '),1)
                self.assertLessEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)


if __name__=='__main__':unittest.main()
