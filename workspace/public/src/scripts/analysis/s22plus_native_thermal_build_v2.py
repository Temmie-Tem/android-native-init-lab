"""Thermal V2 packages: extended IPC in both actual PID1 and renderer.

Reuse the reviewed boot-only package and module-linkage consumers. Regenerate
the V2 init source and metadata from the sealed platform on every audit.
"""
from pathlib import Path
import re
import subprocess

import s22plus_native_thermal_build_v1 as previous
import s22plus_native_thermal_source_v2 as source

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_thermal_source_v2.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_thermal_observer_v2.py',
    'docs/operations/S22PLUS_NATIVE_THERMAL_V2.md']


class Builder(previous.Builder):
    __file__=__file__
    source=source
    provider_profile=source

    def __init__(self,declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-thermal-v2/'+declaration.IDENTITY.namespace+'/build-3')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def native_sources(self):
        _,sources=shared.reference_inputs()
        runtime=sources[shared.packager.RUNTIME_INCLUDE_NAME]
        match=re.findall(rb'static const uint8_t p328_auth_key\[P328_AUTH_KEY_SIZE\] = \{ ([^}]+) \};',runtime)
        if len(match)!=1:raise ValueError('frozen native key declaration differs')
        key=bytes(int(v.strip().removesuffix(b'U'),16) for v in match[0].split(b','))
        if packaging.identity(key)!=self.declaration.artifact.auth_key_identity():raise ValueError('V2 native key identity differs')
        joined=source.resident.join_platform(runtime,shared.REFERENCE_IDENTITY,key)
        joined=source.resident.replace(joined,source.resident.materialize_helper(shared.REFERENCE_IDENTITY,key),
            source.materialize_helper(self.declaration.IDENTITY,key))
        if b'p383' in joined or b'P383' in joined or shared.REFERENCE_IDENTITY.run_id_hex.encode() in joined:
            raise ValueError('old identity remains in V2 native helper')
        return {name:joined if name==shared.packager.RUNTIME_INCLUDE_NAME else raw for name,raw in sources.items()}

    def build_native_init(self,out,resident):
        shared.write(out/'inputs/child-source.c',packaging.stable(shared.REFERENCE/'inputs/child-source.c',
            expected=shared.packager.CHILD_SOURCE_IDENTITY))
        for name,raw in self.native_sources().items():shared.write(out/'native-sources'/name,raw)
        old=shared.packager.RUN_ID
        try:
            shared.packager.RUN_ID=bytes.fromhex(self.declaration.IDENTITY.run_id_hex)
            builds=[shared.packager._compile_userspace(out/'native-sources',out/('userspace-'+side),
                label='thermal-v2-'+side) for side in ('a','b')]
        finally:shared.packager.RUN_ID=old
        if builds[0]!=builds[1]:raise ValueError('V2 native init A/B differs')
        self.native_init_value(out)

    def native_init_value(self,out):
        child_source=packaging.stable(out/'inputs/child-source.c',expected=shared.packager.CHILD_SOURCE_IDENTITY)
        expected=self.native_sources()
        if {p.name for p in (out/'native-sources').iterdir()}!=set(expected):
            raise ValueError('V2 native source inventory differs')
        for name,raw in expected.items():
            if packaging.stable(out/'native-sources'/name)!=raw:raise ValueError('V2 native helper source differs: '+name)
        binaries=[packaging.stable(out/('userspace-'+side)/'init') for side in ('a','b')]
        if binaries[0]!=binaries[1]:raise ValueError('V2 native init A/B bytes differ')
        self.declaration.artifact._validate_init(binaries[0])
        tools=shared.packager._bind_tools();path=out/'userspace-a/init'
        description=subprocess.check_output([tools['file'],'-b',path],text=True).strip()
        elf=subprocess.check_output([tools['readelf'],'-W','-l',path])
        if 'ARM aarch64' not in description or 'statically linked' not in description or b'INTERP' in elf:
            raise ValueError('V2 native init ELF differs')
        return dict(init=packaging.identity(binaries[0]),file=description,ab_identical=True,
            sources={name:packaging.identity(raw) for name,raw in sorted(expected.items())},
            preserved_child_source=packaging.identity(child_source),
            private_ipc=dict(sample_bytes=304,view_bytes=656,sample_magic=0x32525353,view_magic=0x32565253))

    def runtime_value(self,out,resident,thermal):
        value=super().runtime_value(out,resident,thermal)
        native=self.native_init_value(out)
        return dict(value,schema='s22plus-native-thermal-runtime-v2',init=native['init'],native_init=native)

    def init_input(self,out,runtime):
        return out/'userspace-a/init',runtime['init']


if __name__=='__main__':
    import argparse,json
    import s22plus_native_baseline_v2_candidates as catalog
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',choices=tuple(catalog.DECLARATIONS));parser.add_argument('--thermal-input',type=Path)
    parser.add_argument('--runtime-input',type=Path);parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args();builder=Builder(catalog.DECLARATIONS[args.candidate])
    value=builder.audit_existing() if args.audit_only else builder.build(thermal_input=args.thermal_input,runtime_input=args.runtime_input)
    print(json.dumps(dict(verdict=value['verdict'],candidate=value['candidate']['a']['ap_tar_md5']),sort_keys=True))
