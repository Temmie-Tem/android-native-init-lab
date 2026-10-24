"""Fixed baseline stream joins the existing exact GPT read; fixtures stay H0."""
from pathlib import Path
import contextlib
import subprocess
import tempfile
import unittest
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_reboot_baseline_v1 as baseline


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.parent='/sys/devices/platform/soc/1d84000.ufshc/host0/target0:0:0/0:0:0:0/block/sda'
        self.fields=[self.parent+'/sda41','8:41','41','96923648','401516544','8:0','498442240','4096','8:29']
        self.gpt=b'G0\n'+('\n'.join([self.parent+'/sda40','8:40','29814784','67108864','8:0','498442240','4096','8:0'])+'\n').encode()
        self.block=b'B'*4096
    def stream(self,fields=None,last=None,block=None):
        fields=fields or self.fields;last=last or fields
        return b'S22_REBOOT_BASELINE_BEGIN\n'+('\n'.join(fields)+'\n').encode()+(
            self.block if block is None else block)+b'S22_REBOOT_BASELINE_AFTER\n'+('\n'.join(last)+'\n').encode()+b'S22_REBOOT_BASELINE_END\n'
    def parse(self,data):
        with mock.patch.object(baseline,'block_projection',side_effect=lambda blob: (
                dict(initial_mount_count=7) if blob==self.block else (_ for _ in ()).throw(ValueError('block differs')))):
            return baseline.decode(data,self.gpt)
    def test_exact_stream_and_fixed_script_shell_syntax(self):
        self.assertEqual(self.parse(self.stream())['initial_mount_count'],7)
        result=subprocess.run(['bash','-n'],input=baseline.SCRIPT.encode(),capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_geometry_mismatch_and_changed_after_read_reject(self):
        for index,value in ((0,self.parent+'/sda40'),(1,'8:42'),(2,'40'),(3,'96923656'),(4,'8'),
                (5,'8:16'),(6,'498442248'),(7,'512'),(8,'8:2a')):
            changed=list(self.fields);changed[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):self.parse(self.stream(changed))
            with self.subTest(after=index),self.assertRaises(ValueError):self.parse(self.stream(last=changed))
    def test_truncated_extra_or_moved_binary_boundaries_reject(self):
        data=self.stream()
        for changed in (data[:-1],data+b'\n',b'X'+data,self.stream(block=self.block[:-1]),self.stream(block=self.block+b'X')):
            with self.assertRaises(ValueError):self.parse(changed)
    def test_synthetic_baseline_cannot_admit_physical_use(self):
        value=dict(schema=baseline.SCHEMA,kind='H0_SYNTHETIC',device_actions=0,physical_readiness=False)
        with mock.patch.object(baseline,'read',return_value=value),mock.patch.object(baseline,'verify'):
            with self.assertRaisesRegex(ValueError,'synthetic baseline cannot'):baseline.binding({},physical=True)
    def test_count_overflow_is_rejected_without_narrowing(self):
        for count in (-1,65532,65535,65536,True,0.0):
            with self.assertRaises(ValueError):baseline.spec.count(count)
        self.assertEqual(baseline.spec.count(65531),65531)


class DispatchTests(unittest.TestCase):
    def test_storage_admission_precedes_baseline_and_health_brackets_failures(self):
        for failed in (None,'metadata','stat','admission','baseline','after'):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory() as tmp,contextlib.ExitStack() as stack:
                calls=[];root=Path(tmp);task=dict(target={'serial':'fixture'},A={},adb={})
                def event(name):
                    calls.append(name)
                    if name==failed:raise OSError(name)
                class Android:
                    def __init__(self,*args,**kw):self.where=args[3].name
                    def health(self):event(self.where)
                    def command(self,args,name,**kw):event(name)
                changes=[(baseline,'private_path',lambda root,path,**kw:Path(path)),
                    (baseline.registry,'target_session_lease',lambda root:contextlib.nullcontext()),
                    (baseline.registry,'require_no_f1_owner',lambda root:None),
                    (baseline,'authorization',lambda root:{}),
                    (baseline.census,'closed_android',lambda *args:(task,{})),
                    (baseline.inspection,'prior_inputs',lambda:(None,None,task)),
                    (baseline.census,'snapshot_current',lambda *args:{}),
                    (baseline.target.lane,'capture_binding',lambda *args:{}),
                    (baseline.target.lane,'revalidate_binding',lambda *args,**kw:None),
                    (baseline.target,'Android',Android),
                    (baseline.census,'command',lambda reader:event('metadata')),
                    (baseline,'storage_admission',lambda *args:event('admission')),
                    (baseline,'projection',lambda *args:{}),(baseline,'pin',lambda *args:{}),
                    (baseline,'publish',lambda path,value:value)]
                for obj,name,value in changes:stack.enter_context(mock.patch.object(obj,name,value))
                if failed:
                    with self.assertRaises(OSError):baseline.observe(root/'new',root/'task')
                else:baseline.observe(root/'new',root/'task')
                self.assertEqual(calls[0],'before');self.assertEqual(calls[-1],'after')
                self.assertEqual(calls.count('after'),1)
                if failed in ('metadata','stat','admission'):self.assertNotIn('baseline',calls)
                else:self.assertEqual(calls.count('baseline'),1)
                if failed is None:self.assertEqual(calls,['before','metadata','stat','admission','baseline','after'])


if __name__=='__main__':unittest.main()
