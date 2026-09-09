"""Actual diagnostic wrapper: binding status and snapshots add no I2C calls."""
from unittest import mock
import unittest
import subprocess
import test_s22plus_max77705_telemetry_wrapper as base

class DiagnosticWrapper(base.Wrapper):
    @classmethod
    def setUpClass(cls):
        stub=base.STUB.replace('static unsigned resistor=5,calls,fault;',
            'static unsigned resistor=5,calls,fault;static int id_reply=0x15,rev_reply=2;').replace('return reg?2:0x15;','return reg?rev_reply:id_reply;')
        main=base.MAIN.replace(' struct platform_device child=', ' char diag[PAGE_SIZE];\n assert(diagnostic_get(diag,NULL)>0&&!calls&&strstr(diag,"probe=0 probe_error=0 bound=0"));\n struct platform_device child=')
        main=main.replace('assert(telemetry_probe(&child)==-ENODEV&&!calls&&!bound_parent);return 0;', '''assert(telemetry_probe(&child)==-ENODEV&&!calls&&!bound_parent);
          unsigned expected=!strcmp(test,"wrong-parent")?3:!strcmp(test,"wrong-fg")||!strcmp(test,"wrong-abi")?10:!strcmp(test,"wrong-model")?7:!strcmp(test,"wrong-resistor")?9:5;
          assert(probe_stage==expected&&probe_error==-ENODEV);
          assert(diagnostic_get(diag,NULL)>0&&!calls&&strstr(diag,"probe_error=-19 bound=0"));return 0;''')
        main=main.replace(' assert(telemetry_probe(&child)==-EBUSY', ' assert(diagnostic_get(diag,NULL)>0&&!calls&&strstr(diag,"probe=13 probe_error=0 bound=1"));\n assert(telemetry_probe(&child)==-EBUSY')
        main=main.replace('sample_lock.held=1;assert', 'sample_lock.held=1;assert(diagnostic_get(diag,NULL)==-EAGAIN&&!calls);assert')
        main=main.replace('if(fault){assert(calls==4', 'if(fault){assert(diagnostic_get(diag,NULL)>0&&calls==4&&strstr(diag,"read=34 read_error=-5 read_ret=-5 attempts=1 stopped=-5"));assert(calls==4')
        main=main.replace(' assert(calls==5&&', ' assert(diagnostic_get(diag,NULL)>0&&calls==5&&strstr(diag,"read=35 read_error=0 read_ret=65408 attempts=1 stopped=0"));\n assert(calls==5&&')
        main=main.replace(' if(!strcmp(test,"fault"))fault=4;', ' if(!strcmp(test,"bad-id"))id_reply=22;\n if(!strcmp(test,"bad-revision"))rev_reply=3;\n if(!strcmp(test,"fault"))fault=4;')
        main=main.replace(' if(!strcmp(test,"emit"))', '\n if(!strncmp(test,"bad-",4)){unsigned before=calls;assert(read_error==-ENODEV&&read_return==(!strcmp(test,"bad-id")?22:3));assert(diagnostic_get(diag,NULL)>0&&calls==before);clock_ms+=10000;assert(sample_get(text,NULL)>0&&calls==before);return 0;}\n if(!strcmp(test,"emit"))')
        with mock.patch.object(base,'STUB',stub),mock.patch.object(base,'MODULE' ,base.MODULE.with_name('s22plus_max77705_telemetry_v2')),mock.patch.object(base,'MAIN',main):
            base.Wrapper.setUpClass.__func__(cls)

    def test_identity_rejection_keeps_raw_return(self):
        for case in ('bad-id','bad-revision'):
            p=subprocess.run([self.binary,case],capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':unittest.main()
