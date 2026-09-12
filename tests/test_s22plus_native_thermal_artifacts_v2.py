"""V2 actual init/AP audit, including the extended private IPC composition."""
from pathlib import Path
import unittest
from unittest import mock

import test_s22plus_native_thermal_artifacts_v1 as previous
import s22plus_native_thermal_build_v2 as build
import s22plus_native_baseline_v2_candidates as catalog

BUILDER=build.Builder(catalog.DECLARATIONS['p390'])


@unittest.skipUnless((BUILDER.DEFAULT_OUTPUT_ROOT/'result.json').is_file(),'private P390 A/B package not present')
class ThermalArtifactsV2(previous.ThermalArtifacts):
    builder=BUILDER

    def test_native_init_metadata_is_rederived_from_actual_helper_and_ELF(self):
        out=self.builder.DEFAULT_OUTPUT_ROOT/'runtime'
        helper=build.shared.packager.RUNTIME_INCLUDE_NAME
        changes=[(('init','sha256'),'0'*64),(('native_init','init','sha256'),'0'*64),
                 (('native_init','file'),'invented ELF'),(('native_init','ab_identical'),False),
                 (('native_init','sources',helper,'sha256'),'0'*64),
                 (('native_init','preserved_child_source','size'),1),
                 (('native_init','private_ipc','sample_bytes'),128),
                 (('native_init','private_ipc','view_bytes'),304),
                 (('native_init','private_ipc','sample_magic'),0x31525353)]
        for path,replacement in changes:
            with self.subTest(field=path),self.altered_read(out/'result.json',previous.changed(self.runtime,path,replacement)):
                with self.assertRaises(ValueError):self.builder.runtime_inputs()

    def test_native_helper_and_each_actual_init_side_are_reopened(self):
        out=self.builder.DEFAULT_OUTPUT_ROOT/'runtime';stable=build.packaging.stable
        paths=[out/'native-sources'/build.shared.packager.RUNTIME_INCLUDE_NAME,
               out/'inputs/child-source.c',out/'userspace-a/init',out/'userspace-b/init']
        for target in paths:
            original=stable(target);mutated=original[:-1]+bytes([original[-1]^1])
            def read(path,*args,**kwargs):
                return mutated if Path(path)==target else stable(path,*args,**kwargs)
            with self.subTest(path=target.name),mock.patch.object(build.packaging,'stable',side_effect=read):
                with self.assertRaises(ValueError):self.builder.runtime_inputs()


if __name__=='__main__':unittest.main()
