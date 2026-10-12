"""Package the fixed calibration child on the retained UFS/drain carrier."""
from pathlib import Path
import s22plus_native_output_drain_build_v1 as previous
import s22plus_native_log_source_v1 as source
import s22plus_native_log_h0 as producer
from s22plus_native_records_v3 import require,verify

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_log_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_log_profile_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_log_protocol_v1.py',
    'workspace/public/src/scripts/analysis/s22plus_native_log_h0.py',
    'docs/operations/S22PLUS_NATIVE_LOG_CALIBRATION_V1.md']


class Builder(previous.Builder):
    __file__=__file__
    source=source
    extra_member_modes={'s22-log-calibration':0o500,'s22-log-module.ko':0o400}

    def __init__(self,declaration):
        super().__init__(declaration)
        require(declaration.LOG_CALIBRATION_PROFILE==source.LOG_CALIBRATION_PROFILE,'unselected calibration role')
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-log-calibration-v1/'+
            declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def key(self):return producer.native_key(self.declaration.artifact.auth_key_identity())

    def build_native_init(self,out,resident):
        super().build_native_init(out,resident)
        producer.build(out/'log-calibration',self.declaration.IDENTITY.run_id_hex,self.key())

    def calibration_value(self,out):
        return producer.binding(out/'log-calibration',self.declaration.IDENTITY.run_id_hex,self.key())

    def runtime_value(self,out,resident,thermal):
        return dict(super().runtime_value(out,resident,thermal),log_calibration=self.calibration_value(out))

    def replacements(self,runtime):
        rows=super().replacements(runtime);value=self.calibration_value(self.DEFAULT_OUTPUT_ROOT/'runtime')
        rows['s22-log-calibration']=verify(value['helper']).read_bytes()
        rows['s22-log-module.ko']=verify(value['module']).read_bytes()
        return rows

    def result_value(self,runtime,image,transform,packages):
        return dict(super().result_value(runtime,image,transform,packages),
            log_calibration=self.calibration_value(self.DEFAULT_OUTPUT_ROOT/'runtime'))
