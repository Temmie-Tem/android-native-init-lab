"""Actual V3 package/ELF/source metadata and same-size IPC identity audit."""
import unittest

import test_s22plus_native_thermal_artifacts_v2 as previous
import s22plus_native_thermal_build_v3 as build
import s22plus_native_baseline_v2_candidates as catalog

BUILDER=build.Builder(catalog.DECLARATIONS['p391'])


@unittest.skipUnless((BUILDER.DEFAULT_OUTPUT_ROOT/'result.json').is_file(),'private P391 A/B package not present')
class ThermalArtifactsV3(previous.ThermalArtifactsV2):
    builder=BUILDER

    def test_same_size_V2_magic_metadata_is_not_V3(self):
        path=self.builder.DEFAULT_OUTPUT_ROOT/'runtime/result.json'
        for name,value in (('sample_magic',0x32525353),('view_magic',0x32565253)):
            mutant=previous.previous.changed(self.runtime,('native_init','private_ipc',name),value)
            with self.subTest(field=name),self.altered_read(path,mutant):
                with self.assertRaises(ValueError):self.builder.runtime_inputs()


if __name__=='__main__':unittest.main()
