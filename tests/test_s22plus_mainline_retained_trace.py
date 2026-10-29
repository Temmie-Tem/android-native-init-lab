import json
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'))
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import retained_marker as marker
import retained_trace as trace
import s22plus_fyg8_retained_snapshot_model as snapshot
import s22plus_mainline_profile_v1 as profile
from s22plus_native_records_v3 import publish


class TraceFrames(unittest.TestCase):
    def setUp(self):
        self.candidate = '12' * 32
        self.key = bytes(range(32))
        self.config = marker.configuration(self.candidate, self.key, version=8, initcall_count=3)

    def decode(self, data, config=None):
        return marker.decode(data, self.candidate, self.key, version=8, config=config or self.config)

    def test_fixed_milestones_and_entry_return_are_distinct(self):
        cfg = self.config
        marker.validate(cfg, self.candidate, self.key)
        value = self.decode(bytes.fromhex(cfg['frames']['7']) + bytes.fromhex(cfg['frames']['5']))
        self.assertEqual(value['observed_stages'], ['post-async-sync', 'initcall-0000-return'])
        for field in ('same_boot_pair_proved', 'last_attempt_proved', 'stopped_at_last_record',
                      'reset_cause_proved', 'initcall_success_proved', 'mainline_pid1', 'authenticated_usb'):
            self.assertFalse(value[field])

    def test_count_identity_and_old_formats_cannot_be_relabelled(self):
        data = trace.frame(self.candidate, self.key, 5, 4)
        self.assertEqual(self.decode(data)['status'], 'NO_PROOF')
        self.assertEqual(self.decode(data)['damaged_candidates'], 1)
        for version in range(1, 8):
            old = marker.configuration(self.candidate, self.key, version=version)
            self.assertEqual(self.decode(b''.join(bytes.fromhex(x) for x in old['frames'].values()))['status'], 'NO_PROOF')
            self.assertEqual(marker.decode(data, self.candidate, self.key, version=version)['status'], 'NO_PROOF')

    def test_corrupt_uncommitted_truncated_and_foreign(self):
        frame = bytes.fromhex(self.config['frames']['0'])
        for bad in (frame[:-1], bytes(8) + frame[8:], frame[:70] + b'x' + frame[71:],
                    trace.frame(self.candidate, bytes(32), 0, 3)):
            self.assertEqual(self.decode(bad)['status'], 'NO_PROOF')
        self.assertEqual(self.decode(trace.frame('34' * 32, self.key, 0, 3))['foreign_candidates'], 1)

    def test_finite_count_and_event_bound(self):
        for count in (0, -1, True, trace.MAX_INITCALLS + 1):
            with self.assertRaises(ValueError):trace.configuration(self.candidate, self.key, count)
        for event in (-1, 12, True):
            with self.assertRaises(ValueError):trace.frame(self.candidate, self.key, event, 3)
        with self.assertRaises(ValueError):self.decode(bytes(4 * 1024 * 1024 + 1))

    def test_complete_and_short_history_survive_actual_reader_model(self):
        cfg = self.config
        frames = b''.join(bytes.fromhex(x) for x in cfg['frames'].values())
        for idx in (128, 255, 256, cfg['span'] - 1, cfg['span'], snapshot.PAYLOAD_SIZE,
                    snapshot.PAYLOAD_SIZE + 1, snapshot.PAYLOAD_SIZE + cfg['span'], 0xffffffff):
            available = min(idx, cfg['span']) // 128 * 128
            payload, _ = snapshot.place_precursor(bytes(snapshot.PAYLOAD_SIZE), idx, frames[:available])
            raw = snapshot.stock_snapshot(payload, snapshot.Header(7, snapshot.LOG_MAGIC, idx, 123)).data
            result = self.decode(raw)
            self.assertEqual(result['record_count'], available // 128)
            self.assertEqual([r['event'] for r in result['events']], list(range(available // 128)))

    def test_maximum_capture_projection_fits_existing_record_bound(self):
        cfg = trace.configuration(self.candidate, self.key, trace.MAX_INITCALLS)
        self.assertEqual(cfg['span'], 512 * 1024)
        self.assertLess(len(json.dumps(cfg, indent=2).encode()), 2 * 1024 * 1024)
        records = b''.join(bytes.fromhex(x) for x in cfg['frames'].values())
        result = self.decode(records * 8, cfg)
        self.assertEqual(result['record_count'], 32768)
        self.assertLess(len(json.dumps(result, indent=2).encode()), 2 * 1024 * 1024)
        self.assertFalse(result['last_attempt_proved'])


class TraceAdmission(unittest.TestCase):
    def fixture(self, folder):
        """Fixed one-entry synthetic artifact, independent of live activation."""
        cfg = trace.configuration('12' * 32, bytes(32), 1)
        image_hash, elf_hash = '11' * 32, '22' * 32
        table = publish(Path(folder) / 'table.json', dict(status='PASS_H0_FINAL_PREL32_TABLE',
            regular_count=1, image={'sha256':image_hash}, elf={'sha256':elf_hash}, frame_array_matches=True,
            boundaries=[4096]+[4100]*8, counts_by_level=[1]+[0]*7,
            entries=[dict(ordinal=0,level=0,entry_address=4096,functions=['fixture_init'])]))
        initrd = dict(path='fixture-initramfs',size=1,sha256='33'*32)
        compiler = dict(path='fixture-compiler',sha256='44'*32,version='fixture')
        actual = dict(status='PASS_H0_ACTUAL_INITCALL_TRACE_C',kernel_sha256=image_hash,
            elf_sha256=elf_hash,declared_slots=8,declared_span=1024,table=table,
            layout_compiler=compiler,layout_config_sha256='55'*32,mapping_initramfs=initrd)
        layout = dict(status='PASS_H0_SAME_BUILD_TASK_LAYOUT',config_sha256='55'*32,
            command={'compiler':{k:compiler[k] for k in ('path','sha256')}})
        attrs = {'normal-el1':[0,6,5],'normal-el2':[0,6,5],'page-crossing':[0,6,5],
            'short-history':[0,5],'bad-header':[],'header-map-full':[6,5],
            'slot-map-full':[6,5],'drift-before':[0],'drift-commit':[0,6]}
        cases = []
        for label in [*attrs,'timing-el1','timing-el2']:
            timing=label.startswith('timing-')
            samples=[(0,'entry'),(5,'return')] if timing else [(s,p) for s in (0,6,5) for p in ('entry','return')]
            contexts=[dict(event=s,phase=p,pid=1,initial_namespace_reaper=True,same_task_as_kernel_init_entry=True,
                init_task_pid=0,kthreadd_pid=2,boot_cpu=0,online_cpus=1,preempt_count_low32=0,
                irq_masked=False,system_state=1,late_selector=1) for s,p in samples]
            cases.append(dict(case=label,full_pre_free_init_traversal=True,real_mmu_boot=True,real_mapping_api=True,
                mapping_slots_restored=True,header_and_outside_window_preserved=True,post_paging_no_linear_alias_proved=True,
                no_linear_alias_events=[0,5] if timing else [0,6,5],temporary_mapping_attribute_events=[] if timing else attrs[label],
                init_thread_contexts=contexts,actual_c_el=1 if label in ('normal-el1','timing-el1') else 2,
                counter_breakpoints_used=not timing,per_event_counts=None if timing else [1]*8,
                event_order=None if timing else [0,1,2,6,7,3,4,5],physical_timing_proved=False))
        mapped = dict(status='PASS_H0_ACTUAL_KERNEL_MMU_INITCALL_TRACE',kernel_sha256=image_hash,
            declared_slots=8,declared_span=1024,task_layout=layout,mapping_initramfs=initrd,
            init_thread_context_proved=True,late_fixmap_proved=True,post_paging_no_linear_alias_proved=True,cases=cases)
        return cfg,{'mmu_on':actual},{'mmu_on':mapped},{'runtime_sources':{'kernel':{'sha256':image_hash},'initramfs':initrd}}

    def test_rejects_two_site_and_incomplete_or_repeated_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg,tests,vm,image=self.fixture(folder)
            profile.trace_binding(cfg,tests,vm,image)
            variants=[]
            old=copy.deepcopy(tests);old['mmu_on']['status']='PASS_H0_ACTUAL_EARLY_C';variants.append((old,vm))
            missing=copy.deepcopy(vm);missing['mmu_on']['cases'].pop();variants.append((tests,missing))
            repeated=copy.deepcopy(vm);repeated['mmu_on']['cases'][0]['per_event_counts'][6]=2;variants.append((tests,repeated))
            order=copy.deepcopy(vm);order['mmu_on']['cases'][0]['event_order'][3:5]=[7,6];variants.append((tests,order))
            timing=copy.deepcopy(vm);timing['mmu_on']['cases'][-1]['counter_breakpoints_used']=True;variants.append((tests,timing))
            attrs=copy.deepcopy(vm);attrs['mmu_on']['cases'][0]['temporary_mapping_attribute_events'].pop();variants.append((tests,attrs))
            for changed_tests,changed_vm in variants:
                with self.assertRaises(ValueError):profile.trace_binding(cfg,changed_tests,changed_vm,image)


if __name__ == '__main__':
    unittest.main()
