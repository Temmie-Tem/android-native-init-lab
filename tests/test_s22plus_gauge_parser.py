"""Join actual kernel-wrapper output to the ARM64 userspace parser."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_s22plus_max77705_telemetry_wrapper as wrapper
from test_s22plus_status_metrics_v2 import SOURCE,ROOT

class GaugeParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wrapper.Wrapper.setUpClass()
        cls.addClassCleanup(wrapper.Wrapper.doClassCleanups)
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.binary=Path(cls.temp.name)/'parser'
        text=SOURCE[:SOURCE.index('int main(')]+r'''
int main(void){
 assert(status_collect("invalid")==126);
 char text[1024];assert(fgets(text,sizeof(text),stdin));struct gauge_sample sample;
 if(!gauge_parse(text,&sample))return 7;
 printf("%llu %llu %lld\n",(unsigned long long)sample.soc_permille,(unsigned long long)sample.voltage_uv,(long long)sample.current_ua);return 0;
}
'''
        p=subprocess.run(['aarch64-linux-gnu-gcc','-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'workspace/public/src/native-init'),'-o',str(cls.binary)],input=text,text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
        cls.record=subprocess.check_output([wrapper.Wrapper.binary,'emit'],text=True)

    def run_record(self,text):
        return subprocess.run(['qemu-aarch64',self.binary],input=text,text=True,capture_output=True,timeout=5)

    def test_real_producer_to_consumer(self):
        p=self.run_record(self.record);self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout,'500 4000000 -100000\n')

    def test_bad_records(self):
        for text in (self.record.replace('valid=7','valid=8'),self.record.replace('error=0','error=-5'),self.record.replace('seq=1','seq=0'),self.record.replace('voltage_uv=4000000','voltage_uv=4000001'),self.record.replace('current_ua=-100000','current_ua=100000'),self.record.rstrip()+' extra\n',self.record.replace('soc_raw=12800','soc_raw=18446744073709551616')):
            with self.subTest(text=text):self.assertEqual(self.run_record(text).returncode,7)

if __name__=='__main__':unittest.main()
