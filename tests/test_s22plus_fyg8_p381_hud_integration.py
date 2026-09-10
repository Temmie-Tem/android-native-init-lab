"""Status collector, generated PID1, real IPC, and fixture DRM integration."""
from pathlib import Path
import os
import base64
import subprocess
import tempfile
import unittest
from unittest import mock
import test_s22plus_fyg8_p376_hud_integration as base
import test_s22plus_fyg8_p381_hud_renderer as renderer_test
import s22plus_fyg8_p381_research_shell_runtime as runtime
import s22plus_fyg8_p381_research_shell_observer as observer
import s22plus_fyg8_p381_console_owner as owner


def source():
    with mock.patch.object(base,'runtime',runtime):value=base.source().replace('p376','p381')
    value=value.replace(' fx_mark("hud-child",0);',r'''
 if(!strcmp(a[1],"--collect-status")) {
  fx_mark("metrics-child",0);
  if(fx_case("metrics-blocked"))for(;;)usleep(10000);
  if(fx_case("metrics-exit"))_Exit(7);
  char *args[]={getenv("METRICS_COLLECTOR"),a[2],NULL};return neg(execve(args[0],args,e));
 }
 fx_mark("hud-child",0);''')
    value=value.replace('const char *command=text;', '''const char *command=text;char snapshot[1024];
 if(!strcmp(command,"/s22-display --memory-snapshot early")||!strcmp(command,"sleep 2; /s22-display --memory-snapshot late")){
  int late=strstr(command,"late")!=NULL;
  int size=snprintf(snapshot,sizeof(snapshot),"%s\\\"%s\\\" --memory-snapshot %s",late?"sleep 2; ":"",getenv("SNAPSHOT_BINARY"),late?"late":"early");
  if(size<=0||size>=(int)sizeof(snapshot))_Exit(126);command=snapshot;
 }''')
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
        # Actual generated executable on the host: memory mode must complete
        # before any DRM/module operation. Missing native paths remain N/A.
        cls.snapshot=cls.folder/'snapshot-generated'
        built=subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-I',str(headers),
            '-I',str(renderer_test.ROOT/'workspace/public/src/native-init'),
            str(cls.folder/'renderer.c'),'-o',str(cls.snapshot)],capture_output=True,text=True)
        if built.returncode:raise AssertionError(built.stderr)
        cls.collector=cls.folder/'collector'
        from test_s22plus_status_metrics_v2 import SOURCE
        prefix=SOURCE[:SOURCE.index('int main(')]
        metrics=(renderer_test.ROOT/'workspace/public/src/native-init/s22plus_status_metrics_v3.inc.c').read_text()
        diag=(renderer_test.ROOT/'workspace/public/src/native-init/s22plus_gauge_diagnostics_v1.inc.c').read_text()
        diag=diag.replace('static struct gauge_read_result gauge_read_text(',
            'static struct gauge_read_result gauge_read_text(const char *,char *,size_t);\nstatic struct gauge_read_result actual_gauge_read_text(',1)
        metrics=metrics.replace('#include "s22plus_gauge_diagnostics_v1.inc.c"',diag)
        hook=r'''
static struct gauge_read_result gauge_read_text(const char *path,char *out,size_t size){
 static unsigned seq;struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);
 unsigned long long ms=(unsigned long long)ts.tv_sec*1000+ts.tv_nsec/1000000;
 int n;
 if(!strcmp(path,"/sys/module/s22plus_max77705_telemetry/parameters/sample"))
  n=snprintf(out,size,"S22FG1 seq=%u start_ms=%llu valid=7 error=0 soc_raw=12800 voltage_raw=51200 current_raw=65408 soc_permille=500 voltage_uv=4000000 current_ua=-100000\n",++seq,ms);
 else if(!strcmp(path,"/sys/module/s22plus_max77705_telemetry/parameters/diagnostic"))
  n=snprintf(out,size,"S22FGD1 probe=13 probe_error=0 bound=1 read=35 read_error=0 attempts=%u stopped=0\n",seq);
 else return actual_gauge_read_text(path,out,size);
 assert(n>0&&(size_t)n<size);return (struct gauge_read_result){.size=(size_t)n};
}
'''
        prefix=prefix.replace('#include "s22plus_status_metrics_v2.inc.c"',metrics+hook)
        text=prefix+ '\nint main(int argc,char **argv){return argc==2?status_collect(argv[1]):126;}\n'
        built=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-I',str(renderer_test.ROOT/'workspace/public/src/native-init'),'-o',str(cls.collector)],input=text,capture_output=True,text=True)
        if built.returncode:raise AssertionError(built.stderr)

    def run_case(self,case,plan=None):
        self.renderer=str(self.real_renderer)
        with mock.patch.object(base,'runtime',runtime),mock.patch.object(base,'observer',observer),mock.patch.dict(os.environ,{'METRICS_COLLECTOR':str(self.collector),'SNAPSHOT_BINARY':str(self.snapshot),'HUD_RENDERER':self.renderer}):
            if plan is not None:
                before=set(self.folder.iterdir())
                with mock.patch.object(base.predecessor,'runtime',runtime),mock.patch.object(base.predecessor,'observer',observer):
                    result,error,marks,intents,_=base.predecessor.IntegrationTests.run_case(self,case,
                        lambda session,events,deadline:owner.run(session,events,deadline,plan),60)
                self.assertEqual(len(intents),1)
                created=set(self.folder.iterdir())-before;self.assertEqual(len(created),1)
                log=(created.pop()/'hud.log').read_bytes()
                return result,error,log,marks
            return base.HudIntegration.run_case(self,case)

    def test_combined_console_collector_renderer_and_replay(self):
        result,error,log,marks=self.run_case('normal')
        if error:raise AssertionError((repr(error.__cause__),log[-3000:]))
        self.assertTrue(result.receipt['proved'])
        self.assertIn(b'GAUGE_DIAG ',log)
        self.assertEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)
        self.assertEqual(log.count(b'METRICS_SIGNAL_ATTEMPT '),1)
        self.assertEqual(marks.count('metrics-child 0'),1)
        audit=result.sessions[0].session.audit
        self.assertEqual(result.receipt['commands'][5]['stderr']['size'],0)
        self.assertNotIn(b'MEM_SNAPSHOT',bytes(audit.rx))
        codec=base.live._open_header_initial_observer_module(runtime,observer,'p381-replay')
        self.assertEqual(observer.replay_session(codec,bytes(audit.rx),bytes(audit.tx),b'k'*32),result.receipt)

    def test_memory_plan_follows_qualification_and_replays_optional_data(self):
        commands=[b"printf 'RC4_RAM_CHECK\\n'",observer.memory_snapshot.EARLY_COMMAND,observer.memory_snapshot.LATE_COMMAND]
        plan={'schema':owner.SCHEMA,'commands':[{'command_base64':base64.b64encode(command).decode(),
            'cwd':'/s22-root-work','timeout_ms':15000} for command in commands]}
        result,error,log,marks=self.run_case('normal',plan)
        if error:raise AssertionError((repr(error.__cause__),log[-3000:]))
        proof=result.receipt;self.assertTrue(proof['proved']);self.assertEqual(proof['qualified_command_count'],6)
        self.assertEqual(len(proof['commands']),9)
        self.assertTrue(all('memory_snapshot' not in row for row in proof['commands'][:7]))
        early,late=[row['memory_snapshot'] for row in proof['commands'][7:]]
        for snapshot in (early,late):
            self.assertTrue(snapshot['valid'],snapshot);self.assertTrue(snapshot['command_complete'])
            self.assertLessEqual(snapshot['raw']['size'],4096)
            self.assertFalse(snapshot['reclaimability_proved'])
        self.assertGreaterEqual(late['start_ms']-early['end_ms'],2000)
        self.assertLessEqual(len(log),262144);self.assertIn(b'HUD_MEM ',log)
        self.assertTrue(owner.execution_projection(plan,proof['commands'][6:])['all_planned_terminal'])
        audit=result.sessions[0].session.audit
        codec=base.live._open_header_initial_observer_module(runtime,observer,'p381-memory-replay')
        self.assertEqual(observer.replay_session(codec,bytes(audit.rx),bytes(audit.tx),b'k'*32),proof)

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
