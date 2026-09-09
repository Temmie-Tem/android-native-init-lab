"""Reuse root-console receipt invariants with the actual generated P376 peer."""
from pathlib import Path
import ast
_source=Path(__file__).with_name('test_s22plus_fyg8_p375_live_receipt.py').read_text()
_source=_source.replace('p375','p376').replace('P375','P376').replace(
    'test_s22plus_fyg8_p376_console_integration','test_s22plus_fyg8_p376_hud_integration')
_tree=ast.parse(_source)
_tree.body=[n for n in _tree.body if not (isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree),__file__+'#shared-receipt-invariants','exec'),globals())


# Use the fixture's bound variant rather than a growing registry count.
def _hud_claim_test(self):
    fixture=Fixture(Path(self.temporary.name)/('hud-change-'+str(time.monotonic_ns())),self.binary)
    candidate=copy.deepcopy(fixture.value)
    candidate[fixture.variant.proof_key]['commands'][5]['hud']['last_sequence']+=1
    fixture.publish(candidate)
    with self.assertRaises(live.F1LiveError):self.validate(fixture)
P376LiveReceiptTests.test_changed_hud_claim_cannot_replace_raw_frames=_hud_claim_test
