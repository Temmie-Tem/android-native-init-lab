"""P353 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p351_artifact_identity.py')
P351_TEMPLATE_SHA = 'bbdb1929de8f848efa2fd3bd04a97ca6c04f3d24aef1dced9c16f5cabfb9ae74'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P353 predecessor template identity differs")
_source = _source.replace(b'P351', b'P353').replace(b'p351', b'p353')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_source = _source.replace(b'4873dc3ac17d9d5fc5da21a969ba48e6b71f122742db08ae3fbfc54442813082', b'68f6aa66cb29cf94cd7c857545cffd54fc0a250f9bb0a98208a7a153a32e84d9')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p353', 'exec'), globals())

_p353_identity = validate_p353_identity

def validate_p353_identity():
    value = _p353_identity()
    value.update(initial_session_count=1,same_fd_session_count=1,total_session_count=1,
        total_command_count=2,authenticated_cancel=False,dispatch_only=True)
    return value
