"""Shared receipt invariants with generated status HUD and real collector."""
from pathlib import Path
import ast
_source=Path(__file__).with_name('test_s22plus_fyg8_p375_live_receipt.py').read_text()
_source=_source.replace('p375','p378').replace('P375','P378').replace('test_s22plus_fyg8_p378_console_integration','test_s22plus_fyg8_p378_hud_integration')
_tree=ast.parse(_source)
_tree.body=[n for n in _tree.body if not (isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree),__file__+'#shared-receipt-invariants','exec'),globals())


@classmethod
def setup(cls):
    integration.StatusIntegration.setUpClass.__func__(cls)
    cls.temporary=cls.temp
    patch=mock.patch.dict(os.environ,{'HUD_RENDERER':str(cls.real_renderer),'METRICS_COLLECTOR':str(cls.collector)})
    patch.start();cls.addClassCleanup(patch.stop)


P378LiveReceiptTests.setUpClass=setup


def changed_hud_claim(self):
    fixture=Fixture(Path(self.temporary.name)/('hud-change-'+str(time.monotonic_ns())),self.binary)
    candidate=copy.deepcopy(fixture.value)
    candidate[fixture.variant.proof_key]['commands'][5]['hud']['last_sequence']+=1
    fixture.publish(candidate)
    with self.assertRaises(live.F1LiveError):self.validate(fixture)


P378LiveReceiptTests.test_changed_hud_claim_cannot_replace_raw_frames=changed_hud_claim
