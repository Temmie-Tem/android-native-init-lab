"""P353 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p351_stock_process_v2_adapter.py')
P351_TEMPLATE_SHA = '1c0ca1c0857dcbe4b22691c92d32e0aa488a5870b9bfebc5d071aabd6606a58e'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P353 predecessor template identity differs")
_source = _source.replace(b'P351', b'P353').replace(b'p351', b'p353')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p353', 'exec'), globals())

# P353 terminates the authenticated console after one-way display dispatch.
INITIAL_SESSION_COUNT = SAME_FD_SESSION_COUNT = 1
TOTAL_COMMANDS = 2
POLICY_PREIMAGE = OVERLAY_CONTRACT_ID + "|" + P353_RUN_ID_HEX + "|one-authenticated-prefix|parent-id|static-display-dispatch|no-post-display-io|visual-witness-separate|rollback-required"
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
_p353_contract = _contract

def _contract():
    value = _p353_contract()
    value.update(initial_session_count=1,same_fd_session_count=1,authenticated_cancel=False,
        dispatch_only=True,display_response_required=False,framed_session_close_required=False)
    return value

_p353_acceptance = acceptance_fixture

def acceptance_fixture():
    value = _p353_acceptance()
    value.update(initial_session_count=1,same_fd_session_count=1)
    return value

_p353_audit = audit

def audit():
    value = _p353_audit()
    value.update(initial_session_count=1,total_commands=2,contract=_contract())
    return value
