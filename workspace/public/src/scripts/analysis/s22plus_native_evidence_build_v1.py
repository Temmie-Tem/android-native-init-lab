"""Package the fixed mountless reader over the existing native UFS runtime."""
from pathlib import Path
import s22plus_native_root_inspect_build_v1 as previous
import s22plus_native_evidence_source_v1 as source
import s22plus_native_evidence_h0 as producer
from s22plus_native_records_v3 import require

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_evidence_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_evidence_profile_v1.py',
    'workspace/public/src/scripts/analysis/s22plus_native_evidence_h0.py',
    'docs/operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md']


class Builder(previous.Builder):
    __file__=__file__
    source=source
    helper_member='s22-root-evidence'
    extra_member_modes={helper_member:0o500,'s22-root-inspect.table':0o400}

    def __init__(self,declaration):
        super().__init__(declaration)
        require(declaration.ROOT_EVIDENCE_PROFILE==source.ROOT_EVIDENCE_PROFILE,'unselected evidence reader image')
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-root-evidence-v1/'+declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def native_selection(self):
        return dict(super().native_selection(),runtime_profile=source.profile_contract(
            record_run=self.declaration.ROOT_EVIDENCE_RUN,selection=self.declaration.ROOT_EVIDENCE_SELECTION))

    def runtime_value(self,out,resident,thermal):
        return dict(super().runtime_value(out,resident,thermal),profile=source.profile_contract(
            record_run=self.declaration.ROOT_EVIDENCE_RUN,selection=self.declaration.ROOT_EVIDENCE_SELECTION))

    def build_native_init(self,out,resident):
        previous.previous.Builder.build_native_init(self,out,resident)
        producer.build(out/'root-inspector',self.declaration.IDENTITY.run_id_hex,
            record_run=self.declaration.ROOT_EVIDENCE_RUN,selection=self.declaration.ROOT_EVIDENCE_SELECTION)

    def inspection_value(self,out):return producer.audit(out/'root-inspector',self.declaration.IDENTITY.run_id_hex,
        record_run=self.declaration.ROOT_EVIDENCE_RUN,selection=self.declaration.ROOT_EVIDENCE_SELECTION)

    def result_value(self,runtime,image,transform,packages):
        return dict(super().result_value(runtime,image,transform,packages),
            root_evidence=producer.evidence_binding(self.declaration.ROOT_EVIDENCE_RUN,self.declaration.ROOT_EVIDENCE_SELECTION))
