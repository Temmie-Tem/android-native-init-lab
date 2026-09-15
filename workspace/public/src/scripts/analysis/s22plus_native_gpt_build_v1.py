"""Build the sealed GPT successor without altering historical native images."""
from pathlib import Path

import s22plus_native_output_drain_build_v1 as previous
import s22plus_native_gpt_source_v1 as source

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_gpt_source_v1.py',
    'docs/operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md']


class Builder(previous.Builder):
    __file__=__file__
    source=source

    def __init__(self,declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-gpt-v1/'
            +declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def runtime_value(self,out,resident,thermal):
        return dict(super().runtime_value(out,resident,thermal),
            schema='s22plus-native-gpt-runtime-v1',gpt=source.runtime_input_receipt())

    def result_value(self,runtime,image,transform,packages):
        return dict(super().result_value(runtime,image,transform,packages),gpt=runtime['gpt'])
