"""P376 boot HUD identity and sealed P375 source projection; H0 only.

Consumed P375 files are read-only inputs. Changed HUD behavior lives in new
sources, and each inherited custom template is hash-bound before projection.
"""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p375_namespace as parent
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="9d30f9b5b45725b8e39ea81b39290f86e144f3d2f0aaa9189c0d2e259ef7fe74"
_definitions=parent._definitions
P375_SOURCES={'prepare_s22plus_fyg8_p375_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p375_process_v2.py', '8a004a2acde09a99f53b12215c2be428abde2d7082abe27a8f40a81a9aeee5a4'), 's22plus_fyg8_p375_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p375_display_renderer.py', 'f167e523d187f50769cf4952822bc4e81a698b271965ecfd1f2aafe9c63ed039'), 's22plus_fyg8_p375_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p375_process_v2_candidate_static.py', '2a413b5749a38a45c49fc3b70b466d8f87aaf2a81ec5bbaade13f450506a67a6'), 's22plus_fyg8_p375_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p375_stock_candidate_build.py', 'b3eee7793b4fcb914cedd66c752d3d5fac067acb801bc0d7a87619a1f00a1466'), 's22plus_fyg8_p375_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_artifact_identity.py', 'c8356f01725a820e4f7ce0f9db85e6d36eb2187c67a8f4b6ff24aa0e1b392826'), 's22plus_fyg8_p375_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_console_owner.py', 'bfd39425d837b91b94e324f9bfd02a9a7bfbf48d609a8fd355e0f64b87f94d7a'), 's22plus_fyg8_p375_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_namespace.py', 'afb37cd2cdffb0d6d9a645e401f0b1c051b74b629fecbdc5a4aef41244631031'), 's22plus_fyg8_p375_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_progress.py', '675a634ab325094b02ddaee262baef25b8bdf2d8f5c051fe53996f11a77789b8'), 's22plus_fyg8_p375_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_research_shell_observer.py', '6573be490753c7836803c6acf22dcf42b24bc39c22252e21db777d7d19413a23'), 's22plus_fyg8_p375_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_research_shell_runtime.py', '04ce5cabc9cac67a0fe8c72337075c058db9b79f94dd94f663a009bc653a0be3'), 's22plus_fyg8_p375_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_return_host.py', 'd4074c910512c765f01fa70c5c8a85d00b7b47167c47a7244b74899cc9f4915b'), 's22plus_fyg8_p375_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_return_spec.py', '3271605a453a01d7292e22d778eb395e2e7f6838856cd8b809b4317e95ffe090'), 's22plus_fyg8_p375_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_stock_process_v2_adapter.py', 'b92e8d498f2e9b1184f756835b3a12cbb8b39b73a5ca97ae8656948e76476fed')}


def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c375f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c376f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(
        b'P375',b'P376').replace(b'p375',b'p376')


def projected(name):
    return project_bytes(parent.projected(name.replace("p376","p375")))


def load(namespace):
    name=Path(namespace['__file__']).name.replace('p376','p375')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p376').replace(b'P371',b'P376')")
    exec(compile(_definitions(raw),str(namespace['__file__'])+'#sealed-base','exec'),namespace)


def load_template(namespace, transform=None):
    name=Path(namespace['__file__']).name.replace('p376','p375')
    path,digest=P375_SOURCES[name];raw=(ROOT/path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('P376 sealed predecessor differs: '+name)
    raw=project_bytes(raw)
    if transform is not None:raw=transform(raw)
    tree=ast.parse(raw)
    tree.body=[node for node in tree.body if not (isinstance(node,ast.If) and '__name__' in ast.unparse(node.test))]
    exec(compile(ast.fix_missing_locations(tree),str(namespace['__file__'])+'#sealed-p375','exec'),namespace)
