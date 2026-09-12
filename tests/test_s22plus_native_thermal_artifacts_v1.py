"""Mutated publications through actual readers over verified unchanged APs.

Large immutable boot parsers are memoized, not replaced by synthetic answers.
The private A/B build is optional in a checkout; the local qualification runs it.
"""
from contextlib import ExitStack
import copy
from functools import lru_cache
import json
from pathlib import Path
import unittest
from unittest import mock

import s22plus_native_baseline_v2_candidates as catalog
import s22plus_native_thermal_build_v1 as build

BUILDER=build.Builder(catalog.DECLARATIONS['p389'])
OUT=BUILDER.DEFAULT_OUTPUT_ROOT


def changed(value,path,replacement):
    result=copy.deepcopy(value);cursor=result
    for key in path[:-1]:cursor=cursor[key]
    cursor[path[-1]]=replacement
    return result


@unittest.skipUnless((OUT/'result.json').is_file(),'private thermal A/B package is not present')
class ThermalArtifacts(unittest.TestCase):
    builder=BUILDER
    @classmethod
    def setUpClass(cls):
        cls.stack=ExitStack();cls.addClassCleanup(cls.stack.close)
        for module,name in ((build.shared,'entries'),(build.shared.boot,'decompress_lz4_frame_python'),
                            (build.shared.boot,'decompress_lz4_stream_python')):
            cls.stack.enter_context(mock.patch.object(module,name,lru_cache(maxsize=4)(getattr(module,name))))
        cls.value=cls.builder.audit_existing()
        cls.runtime=cls.builder.runtime_inputs()

    def altered_read(self,target,value):
        stable=build.packaging.stable
        def read(path,*args,**kwargs):
            return build.shared.canonical(value) if Path(path)==target else stable(path,*args,**kwargs)
        return mock.patch.object(build.packaging,'stable',side_effect=read)

    def test_package_metadata_cannot_disagree_with_real_AP_and_runtime(self):
        mutations=[(('run_id_hex',),'0'*32),(('init','sha256'),'0'*64),(('renderer','size'),1),
            (('provider','sha256'),'0'*64),(('child','sha256'),'0'*64),(('byte_identical',),False),
            (('byte_identical',),1),(('scope','device_contact'),True),(('scope','candidate_transfers'),1),
            (('thermal_modules','qcom-spmi-adc5.ko','identity','sha256'),'0'*64),
            (('candidate','a','ap_structure','members'),['recovery.img.lz4']),
            (('candidate','a','ap_structure','tar_md5'),'0'*32),(('unexpected',),True)]
        # Every mutation changes only this publication. Reuse the actual
        # previously rederived runtime while still reopening both real APs.
        with mock.patch.object(self.builder,'runtime_inputs',return_value=self.runtime):
            for path,replacement in mutations:
                with self.subTest(field=path),self.altered_read(self.builder.DEFAULT_OUTPUT_ROOT/'result.json',changed(self.value,path,replacement)):
                    with self.assertRaises(ValueError):self.builder.audit_existing()

    def test_runtime_description_and_identities_are_derived_from_actual_ELF(self):
        mutations=[(('file',),'invented ELF'),(('renderer','size'),1),(('ab_identical',),False),
            (('profile','thermal_profile'),'other-board'),(('run_id_hex',),'0'*32),(('unexpected',),True)]
        for path,replacement in mutations:
            with self.subTest(field=path),self.altered_read(self.builder.DEFAULT_OUTPUT_ROOT/'runtime/result.json',changed(self.runtime,path,replacement)):
                with self.assertRaises(ValueError):self.builder.runtime_inputs()

    def test_provider_effect_and_source_metadata_is_rederived(self):
        path=self.builder.DEFAULT_OUTPUT_ROOT/'runtime/thermal-provider';value=build.provider.audit(path,profile=self.builder.provider_profile)
        read_text=Path.read_text
        for keys,replacement in [(('device_contact',),True),(('live_authorized',),True),
            (('hardware_effects','adc_configuration_writes'),False),(('limitations',),[]),
            (('module_order',),list(reversed(value['module_order']))),(('unexpected',),True)]:
            mutant=changed(value,keys,replacement)
            def read(p,*args,**kwargs):
                return json.dumps(mutant) if p==path/'result.json' else read_text(p,*args,**kwargs)
            with self.subTest(field=keys),mock.patch.object(Path,'read_text',read):
                with self.assertRaises(ValueError):build.provider.audit(path,profile=self.builder.provider_profile)


if __name__=='__main__':unittest.main()
