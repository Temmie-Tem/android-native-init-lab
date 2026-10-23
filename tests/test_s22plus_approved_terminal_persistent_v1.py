"""Persistent transport, fresh backend and existing-owner fixtures; no device I/O."""
import importlib.util
import concurrent.futures
import json
import os
import py_compile
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import test_s22plus_approved_terminal_v1 as previous

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'workspace/public/src/scripts/host_tools'
sys.path.insert(0,str(HOST))
import s22plus_approved_terminal_persistent_v1 as transport
import s22plus_approved_terminal_tasks_v1 as backend

# Exercise all existing continuation states against the extracted owner.
# These aliases exist only in the test harness, never in the backend process.
for name in ('Server','Handler','forward','tools'):
    setattr(backend,name,getattr(transport,name))


class ContinuationRegression(previous.ContinuationTests):
    def setUp(self):
        patch=mock.patch.object(previous,'bridge',backend);patch.start();self.addCleanup(patch.stop)
        super().setUp()


class PersistentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='s22p-',dir='/tmp')
        self.root=Path(self.temp.name)
        for source in backend.review_sources(ROOT):
            target=self.root/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        self.body=self.root/transport.BACKEND
        # Harmless fixture process retains the test runner's inherited NNP.
        # Production startup/backend guards are separately checked unchanged.
        code=self.body.read_text().replace('nnp() == 0','nnp() in (0, 1)')
        code=code.replace('no_new_privileges=nnp(), root=str(self.root)',
            "no_new_privileges=nnp(), backend_revision='first', fixture_schema=records.SCHEMA, root=str(self.root)")
        self.body.write_text(code)
        self.base=previous.fixture(self.root,entry=
            "from pathlib import Path\nimport time\ntime.sleep(0.7)\n(Path(__file__).parent/'fixture-finished').write_text('once')\n")
        self.review(1)
        self.gateway=transport.Gateway(self.root)

    def tearDown(self):
        for intent in self.root.glob('workspace/private/outputs/*/'+backend.DISPATCH+'/intent.json'):
            if not (intent.parent/'result.json').exists():self.wait_result(intent.parent.parent)
        self.temp.cleanup()

    def review(self,version):
        value=dict(schema='s22plus-approved-terminal-review-v1',verdict='PASS_GO',findings=[],
            scope='HOST_APPROVED_TASK_DISPATCH',fixture_version=version,
            sources=[transport.pin(self.root/p.relative_to(ROOT)) for p in backend.review_sources(ROOT)],
            worker_sources=[transport.pin(self.root/name) for name in sorted((transport.WORKER,transport.POLICY))])
        path=self.root/f'workspace/public/src/device-action/bindings/s22plus_approved_terminal_persistent_v{version}_review.json'
        receipt=previous.save(path,value)
        previous.save(self.root/transport.SELECTOR,dict(schema='s22plus-approved-terminal-current-review-v1',review=receipt))
        return receipt

    def wait_result(self,base=None):
        path=(base or self.base)/backend.DISPATCH/'result.json';deadline=time.monotonic()+4
        while not path.exists() and time.monotonic()<deadline:time.sleep(0.01)
        self.assertTrue(path.exists());return previous.records.read(path)

    def call(self,tool='start_approved_task'):
        return self.gateway.call(tool,{} if tool=='bridge_status' else dict(preparation_directory=str(self.base)))

    def test_same_resident_loads_reviewed_backend_update_without_restart(self):
        worker_sources=self.gateway.worker_sources
        first=self.call('bridge_status');old=first['bridge_review']
        self.assertEqual(first['backend_revision'],'first')
        self.body.write_text(self.body.read_text().replace("backend_revision='first'","backend_revision='second'"))
        new=self.review(2)
        second=self.call('bridge_status')
        self.assertEqual(second['backend_revision'],'second')
        self.assertEqual(second['bridge_review'],new)
        self.assertEqual(transport.pin(Path(old['path'])),old)
        self.assertEqual(self.gateway.worker_sources,worker_sources)
        self.assertTrue(second['fresh_backend_per_request'])

    def test_unreviewed_helper_change_rejected_before_process_creation(self):
        path=self.root/'workspace/public/src/scripts/revalidation/s22plus_native_records_v3.py'
        path.write_text(path.read_text()+'\n# changed\n')
        with mock.patch.object(transport.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'reviewed source changed'):self.call()
            spawn.assert_not_called()

    def test_same_size_same_second_helper_bytecode_cannot_override_reviewed_source(self):
        helper=self.root/'workspace/public/src/scripts/revalidation/s22plus_native_records_v3.py'
        before=helper.read_bytes();stamp=int(time.time())
        os.utime(helper,(stamp,stamp))
        cached=Path(py_compile.compile(str(helper),doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP))
        stale=cached.read_bytes()
        changed=before.replace(b"SCHEMA = 's22plus-native-session-v3'",b"SCHEMA = 's22plus-native-session-v4'")
        self.assertNotEqual(changed,before);self.assertEqual(len(changed),len(before))
        helper.write_bytes(changed);os.utime(helper,(stamp,stamp));self.review(2)
        result=self.call('bridge_status')
        self.assertEqual(result['fixture_schema'],'s22plus-native-session-v4')
        self.assertEqual(cached.read_bytes(),stale)

    def test_changed_transport_cannot_inherit_new_backend_review(self):
        path=self.root/transport.POLICY;path.write_text(path.read_text()+'\nchanged\n');self.review(2)
        with mock.patch.object(transport.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'stable transport itself changed'):self.call()
            spawn.assert_not_called()

    def test_selector_cannot_choose_an_executable_or_external_review(self):
        value=previous.records.read(self.root/transport.SELECTOR);value['review']=transport.pin(self.body)
        previous.save(self.root/transport.SELECTOR,value)
        with mock.patch.object(transport.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'immutable backend review'):self.call()
            spawn.assert_not_called()

    def test_review_update_between_parent_and_child_rejects_before_dispatch(self):
        real=transport.subprocess.Popen
        def race(*args,**kwargs):
            self.review(2)
            return real(*args,**kwargs)
        with mock.patch.object(transport.subprocess,'Popen',side_effect=race):
            with self.assertRaisesRegex(ValueError,'selected backend review changed'):self.call()
        self.assertFalse((self.base/backend.DISPATCH/'intent.json').exists())

    def test_response_precedes_completion_and_result_owner_finishes(self):
        start=time.monotonic();result=self.call();elapsed=time.monotonic()-start
        self.assertTrue(result['dispatched']);self.assertLess(elapsed,0.6)
        self.assertFalse((self.base/'fixture-finished').exists())
        self.assertEqual(self.wait_result()['returncode'],0)
        self.assertTrue((self.base/'fixture-finished').exists())
        self.assertFalse(self.call()['dispatched'])
        original=previous.records.read(self.base/backend.DISPATCH/'intent.json')['bridge_review']
        self.assertEqual(original,self.gateway.call('bridge_status',{})['bridge_review'])
        self.review(2)
        self.assertFalse(self.call()['dispatched'])
        self.assertEqual(transport.pin(Path(original['path'])),original)

    def test_two_fresh_backends_cannot_admit_different_tasks_together(self):
        other=previous.fixture(self.root,2)
        def start(base):
            try:return self.gateway.call('start_approved_task',dict(preparation_directory=str(base)))
            except ValueError:return {'dispatched':False}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(start,(self.base,other)))
        self.assertEqual(sum(row['dispatched'] for row in results),1)
        self.assertEqual(len(list(self.root.glob('workspace/private/outputs/*/'+backend.DISPATCH+'/intent.json'))),1)

    def test_closed_rpc_pipe_preserves_dispatched_result_owner(self):
        _,review=transport.selected_review(self.root)
        process=subprocess.Popen(['/usr/bin/python3',str(self.body)],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
        process.stdout.close()
        process.stdin.write(transport.canonical(dict(tool='start_approved_task',
            arguments=dict(preparation_directory=str(self.base)),review=review)))
        process.stdin.close()
        self.assertEqual(self.wait_result()['returncode'],0)
        self.assertEqual(process.wait(timeout=4),0)

    def test_resident_exit_does_not_kill_backend_or_entry(self):
        script=("import sys,os\nfrom pathlib import Path\n"+
            f"sys.path.insert(0,{str(self.root/transport.WORKER).rsplit('/',1)[0]!r})\n"+
            "import s22plus_approved_terminal_persistent_v1 as m\n"+
            f"g=m.Gateway(Path({str(self.root)!r}))\n"+
            f"v=g.call('start_approved_task',{{'preparation_directory':{str(self.base)!r}}})\n"+
            "assert v['dispatched'];os._exit(0)\n")
        result=subprocess.run(['/usr/bin/python3','-c',script],capture_output=True,timeout=3)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.wait_result()['returncode'],0)
        self.assertFalse(self.call()['dispatched'])

    def test_rpc_timeout_does_not_kill_or_replay_dispatch(self):
        real=transport.response_line
        def late(process):
            response=real(process)
            raise ValueError('fixture lost response after dispatch')
        with mock.patch.object(transport,'response_line',side_effect=late):
            with self.assertRaisesRegex(ValueError,'lost response'):self.call()
        self.assertEqual(self.wait_result()['returncode'],0)
        self.assertFalse(self.call()['dispatched'])

    def test_real_socket_uses_fresh_backend_and_fixed_schema(self):
        endpoint=self.root/'persistent.sock'
        with transport.Server(str(endpoint),transport.Handler) as server:
            endpoint.chmod(0o600);server.controller=self.gateway
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                response=transport.forward('bridge_status',{},endpoint=endpoint)
                self.assertTrue(response['ok']);self.assertTrue(response['value']['fresh_backend_per_request'])
                invalid=transport.forward('arbitrary_shell',{'command':'anything'},endpoint=endpoint)
                self.assertFalse(invalid['ok'])
            finally:server.shutdown();thread.join()
        self.assertEqual({row['name'] for row in transport.tools()},
            {'bridge_status','task_status','task_log','start_approved_task','continue_approved_task','resume_approved_health'})

    def test_shared_admission_excludes_a_second_backend_process(self):
        script=(f"import sys\nsys.path.insert(0,{str(HOST)!r})\n"+
            "from pathlib import Path\nfrom s22plus_approved_terminal_tasks_v1 import AdmissionLock\n"+
            f"with AdmissionLock(Path({str(self.root)!r})): print('unexpected')\n")
        with backend.AdmissionLock(self.root):
            result=subprocess.run(['/usr/bin/python3','-c',script],capture_output=True,timeout=3)
        self.assertNotEqual(result.returncode,0);self.assertNotIn(b'unexpected',result.stdout)
        result=subprocess.run(['/usr/bin/python3','-c',script],capture_output=True,timeout=3)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_production_backend_refuses_restricted_identity_before_review(self):
        script=('import ctypes,os\nassert ctypes.CDLL(None).prctl(38,1,0,0,0)==0\n'+
            f'os.execv("/usr/bin/python3",["/usr/bin/python3",{str(ROOT/transport.BACKEND)!r}])\n')
        result=subprocess.run(['/usr/bin/python3','-c',script],input=b'',capture_output=True,timeout=3)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'ordinary-terminal worker identity',result.stderr)


if __name__=='__main__':unittest.main()
