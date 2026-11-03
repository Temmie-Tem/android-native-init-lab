"""Fixed diagnostic cannot silently become an ordinary V1 kernel."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]/'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0,str(HERE))
import entry_park
import prepare_marked
import retained_marker
sys.path.insert(0,str(HERE.parents[1]/'scripts/revalidation'))
import s22plus_mainline_profile_v1 as profile
from s22plus_native_records_v3 import pin


class EntryParkSource(unittest.TestCase):
    def setUp(self):
        self.head=('SYM_CODE_START(primary_entry)\n\tbl\trecord_mmu_state\n'
                   '\tbl\tpreserve_boot_args\nSYM_CODE_END(primary_entry)\n')
        self.config=retained_marker.configuration('12'*32,bytes(range(32)),version=1)

    def test_declared_park_preserves_both_v1_frame_bytes_and_unreachable_tail(self):
        ordinary=prepare_marked.instrumented_head(self.head,self.config)
        parked=prepare_marked.instrumented_head(self.head,self.config,entry_park=True)
        self.assertEqual(parked.replace(entry_park.LOOP,''),ordinary)
        self.assertIn('\tbl\ts22_retained_kernel\n'+entry_park.LOOP+'\tbl\trecord_mmu_state\n',parked)
        self.assertEqual(self.config,retained_marker.configuration('12'*32,bytes(range(32)),version=1))

    def test_other_writer_formats_cannot_select_the_park(self):
        for version in range(2,8):
            cfg=retained_marker.configuration('12'*32,bytes(range(32)),version=version)
            with self.subTest(version=version),self.assertRaises(ValueError):
                prepare_marked.instrumented_head(self.head,cfg,entry_park=True)

    def test_duplicate_or_displaced_hook_rejected(self):
        ordinary=prepare_marked.instrumented_head(self.head,self.config)
        for value in (ordinary+ordinary,ordinary.replace('\tbl\trecord_mmu_state\n','\tnop\n\tbl\trecord_mmu_state\n')):
            with self.assertRaises(ValueError):entry_park.instrument(value)

    def test_reinstrumentation_rejected(self):
        parked=prepare_marked.instrumented_head(self.head,self.config,entry_park=True)
        with self.assertRaises(ValueError):entry_park.instrument(parked)
        with self.assertRaises(ValueError):prepare_marked.instrumented_head(parked,self.config,entry_park=True)

    def test_ordinary_v1_has_no_park_or_vm_condition(self):
        ordinary=prepare_marked.instrumented_head(self.head,self.config)
        self.assertNotIn('s22_entry_park',ordinary)
        self.assertNotIn('#if',entry_park.LOOP)

    def test_pinned_source_cannot_lose_all_surface_declarations(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.json'
            path.write_text(json.dumps({'entry_park':entry_park.declaration()}))
            loader={'kernel':{},'retained_marker':{'kernel_source':pin(path)}}
            with self.assertRaisesRegex(ValueError,'lacks diagnostic admission'):
                profile.entry_park_presence({},loader)
            loader['entry_park']=loader['kernel']['entry_park']=pin(path)
            profile.entry_park_presence({'entry_park':pin(path)},loader)


if __name__=='__main__':unittest.main()
