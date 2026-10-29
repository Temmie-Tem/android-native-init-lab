import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import subprocess

HERE=Path(__file__).resolve().parents[1]/'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0,str(HERE))
import retained_marker as marker

class Frames(unittest.TestCase):
    def setUp(self):
        self.candidate='12'*32;self.key=bytes(range(32))
        self.a=marker.frame(self.candidate,self.key,1);self.b=marker.frame(self.candidate,self.key,2)
    def test_two_stage_positive_only(self):
        v=marker.decode(b'x'+self.a+self.b,self.candidate,self.key)
        self.assertEqual(v['observed_stages'],['kernel-entry','loader-handoff'])
        self.assertFalse(v['same_boot_pair_proved']);self.assertFalse(v['mainline_pid1'])
    def test_duplicates_do_not_count_boots(self):
        v=marker.decode(self.a*3,self.candidate,self.key)
        self.assertEqual(v['observed_stages'],['loader-handoff']);self.assertEqual(len(v['records']),3)
        self.assertFalse(v['last_attempt_proved'])
    def test_v2_does_not_reinterpret_v1_or_claim_a_shared_boot(self):
        cfg=marker.configuration(self.candidate,self.key,version=2)
        marker.validate(cfg,self.candidate,self.key)
        data=b''.join(bytes.fromhex(v) for v in cfg['frames'].values())
        self.assertEqual(marker.decode(data,self.candidate,self.key)['status'],'NO_PROOF')
        self.assertEqual(marker.decode(self.a+self.b,self.candidate,self.key,version=2)['status'],'NO_PROOF')
        result=marker.decode(data,self.candidate,self.key,version=2)
        self.assertEqual(result['observed_stages'],['early-c','pre-mmu'])
        self.assertFalse(result['same_boot_pair_proved']);self.assertFalse(result['last_attempt_proved'])
        cfg['frames']['3']=cfg['frames']['4']
        with self.assertRaises(ValueError):marker.validate(cfg,self.candidate,self.key)
    def test_v3_later_positive_needs_no_earlier_record(self):
        cfg=marker.configuration(self.candidate,self.key,version=3)
        later=bytes.fromhex(cfg['frames']['6'])
        old=marker.frame(self.candidate,self.key,4,version=2)
        result=marker.decode(old+self.a+later,self.candidate,self.key,version=3)
        self.assertEqual(result['observed_stages'],['post-paging'])
        self.assertEqual(result['status'],'RETAINED_STAGE_OBSERVED')
        self.assertFalse(result['stopped_at_last_record']);self.assertFalse(result['reset_cause_proved'])
        self.assertFalse(result['same_boot_pair_proved']);self.assertFalse(result['replay_authorized'])
        self.assertEqual(marker.decode(later,self.candidate,self.key,version=2)['status'],'NO_PROOF')
    def test_v3_exact_hooks_replace_old_sites(self):
        import prepare_marked
        cfg=marker.configuration(self.candidate,self.key,version=3)
        head='SYM_CODE_START(primary_entry)\n\tbl\trecord_mmu_state\nSYM_CODE_END(primary_entry)\n'
        self.assertEqual(prepare_marked.instrumented_head(head,cfg),head)
        source='void __init __no_sanitize_address setup_arch(char **cmdline_p)\n{\n\tearly_ioremap_init();\n\tsetup_machine_fdt(__fdt_pointer);\n\tpaging_init();\n}\n'
        value=prepare_marked.instrumented_setup(source,cfg)
        self.assertIn('\tsetup_machine_fdt(__fdt_pointer);\n\ts22_retained_post_fdt();\n',value)
        self.assertIn('\tpaging_init();\n\ts22_retained_post_paging();\n',value)
        self.assertNotIn('s22_retained_early_c();',value)
        with self.assertRaises(ValueError):prepare_marked.instrumented_setup(value,cfg)
        with self.assertRaises(ValueError):prepare_marked.instrumented_setup(source+'\tpaging_init();\n',cfg)
        rendered=marker.render_c(cfg)
        self.assertNotIn('@',rendered)
        self.assertIn('noinline void __init s22_retained_post_fdt(void)',rendered)
        self.assertIn('noinline void __init s22_retained_post_paging(void)',rendered)
        self.assertIn('0x1ffff0U - 256) + 0;',rendered)
        self.assertIn('0x1ffff0U - 256) + 128;',rendered)
    def test_wrong_key_corrupt_and_truncated(self):
        for data,key in [(self.a,bytes(32)),(self.a[:127],self.key),(self.a[:60]+b'x'+self.a[61:],self.key),
                         (bytes(8)+self.a[8:],self.key),(self.a[:4],self.key)]:
            self.assertEqual(marker.decode(data,self.candidate,key)['status'],'NO_PROOF')
    def test_foreign_frame_is_not_this_candidate(self):
        self.assertEqual(marker.decode(self.a,'34'*32,self.key)['foreign_candidates'],1)
    def test_bounds_and_unknown_stage(self):
        with self.assertRaises(ValueError):marker.decode(bytes(4*1024*1024+1),self.candidate,self.key)
        with self.assertRaises(ValueError):marker.frame(self.candidate,self.key,3)
    def test_partial_kernel_marker_publication_is_not_plain_kernel(self):
        import build_kernel
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);head=p/'source/arch/arm64/kernel/head.S';head.parent.mkdir(parents=True)
            head.write_text('s22_retained_kernel:\n')
            with self.assertRaisesRegex(ValueError,'partial marker'):build_kernel.marker_provenance(p,p/'source')
            head.write_text('unmarked entry\n');(p/'marker-source.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'partial marker'):build_kernel.marker_provenance(p,p/'source')
    def test_no_header_or_outside_slot_store_in_actual_assembly(self):
        import qualify_retained as qualify
        cfg=marker.configuration(self.candidate,self.key)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            for stage in (1,2):
                name='s22_retained_'+('loader' if stage==1 else 'kernel')
                (p/'marker.S').write_text('.text\n'+marker.render(cfg,stage))
                subprocess.run(['aarch64-linux-gnu-gcc','-c',p/'marker.S','-o',p/'marker.o'],check=True,capture_output=True)
                subprocess.run(['aarch64-linux-gnu-ld','-Ttext=0x40000000','-e',name,p/'marker.o','-o',p/'marker.elf'],check=True,capture_output=True)
                subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary',p/'marker.elf',p/'marker.bin'],check=True,capture_output=True)
                routine=qualify.linked((p/'marker.bin').read_bytes(),qualify.symbols(p/'marker.elf'),0x40000000,0x40000000,name)
                self.assertGreater(len(qualify.matrix(routine,stage,cfg)),30)

if __name__=='__main__':unittest.main()
