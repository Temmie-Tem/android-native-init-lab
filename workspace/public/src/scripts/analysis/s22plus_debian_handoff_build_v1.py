"""Archive-free native-first Debian handoff boot image."""
from pathlib import Path
import s22plus_switch_root_build_v1 as base
import s22plus_debian_handoff_h0 as producer
import s22plus_debian_handoff_source_v1 as source
from s22plus_native_records_v3 import pin,verify

ROOT=base.ROOT
EXTRA_SOURCES=base.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_debian_handoff_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_debian_handoff_profile_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_debian_handoff_protocol_v1.py',
    'docs/operations/S22PLUS_DEBIAN_HANDOFF_V1.md']


class Builder(base.Builder):
    __file__=__file__
    source=source
    producer=producer
    profile_attribute='DEBIAN_HANDOFF_PROFILE'
    extra_member_modes=dict(base.Builder.extra_member_modes,**{
        's22-debian-hook':0o500,'s22-debian-inittab':0o400,'s22-debian-qualify':0o500})

    def __init__(self,declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-debian-handoff-v1/'+declaration.IDENTITY.namespace+'/build-1')

    def helper_options(self):
        identity=self.declaration.IDENTITY
        return dict(namespace=identity.namespace,version=identity.display_version)

    def source_receipts(self):
        rows=super().source_receipts()
        for p in source.source_files():rows[str(p.relative_to(ROOT))]=base.packaging.identity(base.packaging.stable(p))
        rows[str(Path(__file__).relative_to(ROOT))]=base.packaging.identity(base.packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def replacements(self,runtime):
        rows=super().replacements(runtime);helpers=self.helper_value(self.DEFAULT_OUTPUT_ROOT/'runtime')
        rows.update({'s22-debian-'+name:verify(value).read_bytes() for name,value in helpers['assets'].items()})
        return rows

    def result_value(self,runtime,image,transform,packages):
        result=super().result_value(runtime,image,transform,packages)
        result['root_admission']=result.pop('root_inspection');result.pop('switch_root')
        helpers=runtime['switch_root_helpers']
        selection={name:helpers[name] for name in ('prepare','witness','busybox','checker','assets','installed_init')}
        selection.update(seconds=300,request=37,init_request=39,release_request=40,root_readonly=False,
            installed_exec=True,persistent_writes=True,helpers_result=pin(self.DEFAULT_OUTPUT_ROOT/'runtime/switch-root/result.json'))
        result['debian_handoff']=selection
        return result
