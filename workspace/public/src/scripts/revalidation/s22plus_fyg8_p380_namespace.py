"""P380 model correction and memory observation namespace; all consumed ancestors remain sealed inputs."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p379_namespace as parent
import s22plus_fyg8_p378_namespace as p378
import s22plus_fyg8_p377_namespace as p377
import s22plus_fyg8_p376_namespace as p376
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="13e482969b6ecd0498de901e8bb223434d4dbca4f70437740f5b7ad195825417"
_definitions=parent._definitions
P375_SOURCES=parent.P375_SOURCES
P376_SOURCES=parent.P376_SOURCES
P377_SOURCES=parent.P377_SOURCES
P378_SOURCES=parent.P378_SOURCES
P379_SOURCES={'prepare_s22plus_fyg8_p379_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p379_process_v2.py', 'e90cf5df16f56788c3f27e5fd0f507cf2c23c1a03c5389b32974a41163d15328'), 's22plus_fyg8_p379_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p379_display_renderer.py', '5ec91b97830e51512fa9030c157ee1b63129a52f1f5aa2f123c98a6ac315c148'), 's22plus_fyg8_p379_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p379_process_v2_candidate_static.py', 'fd9dee6aa5a9e7999e86fa2daa197bb8f9c47554cb6d9d3a0a9dc387623d3cc5'), 's22plus_fyg8_p379_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p379_stock_candidate_build.py', '66e8bb789d8efd07b5dea2a769c5e3741398a53103f6ca303f26aeb67fc82f9e'), 's22plus_fyg8_p379_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_artifact_identity.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_console_owner.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_namespace.py', '3a284e9c6c66ad4151b6ccba81c79a02cd23af1b80f602f74c36faa2c070eeec'), 's22plus_fyg8_p379_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_progress.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_research_shell_observer.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_research_shell_runtime.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_return_host.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_return_spec.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328'), 's22plus_fyg8_p379_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p379_stock_process_v2_adapter.py', '196679310ca7d0711c63f9b944c8f0e1e9c70ab1b77cd09dc97e8ae7efa59328')}

def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c379f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c380f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(b'P379',b'P380').replace(b'p379',b'p380')

def projected(name):
    return project_bytes(parent.projected(name.replace('p380','p379')))

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p380','p379')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p380').replace(b'P371',b'P380')")
    exec(compile(_definitions(raw),str(namespace['__file__'])+'#sealed-base','exec'),namespace)

def _execute(namespace,raw,label):
    tree=ast.parse(raw)
    tree.body=[node for node in tree.body if not (isinstance(node,ast.If) and '__name__' in ast.unparse(node.test))]
    exec(compile(ast.fix_missing_locations(tree),str(namespace['__file__'])+label,'exec'),namespace)

def _read(mapping,name):
    path,digest=mapping[name];raw=(ROOT/path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('sealed predecessor differs: '+name)
    return raw

def _project_from(raw,ordinal):
    for number,transform in ((376,p376.project_bytes),(377,p377.project_bytes),(378,p378.project_bytes),(379,parent.project_bytes),(380,project_bytes)):
        if number>ordinal:raw=transform(raw)
    return raw

def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p380','p375')
    raw=_project_from(_read(P375_SOURCES,name),375)
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')

def load_p376(namespace):
    name=Path(namespace['__file__']).name.replace('p380','p376')
    _execute(namespace,_project_from(_read(P376_SOURCES,name),376),'#sealed-p376')

def load_p377(namespace):
    name=Path(namespace['__file__']).name.replace('p380','p377')
    raw=_project_from(_read(P377_SOURCES,name),377).replace(b'load_predecessor',b'load_p376')
    _execute(namespace,raw,'#sealed-p377')

def load_p378(namespace):
    name=Path(namespace['__file__']).name.replace('p380','p378')
    raw=_project_from(_read(P378_SOURCES,name),378).replace(b'load_predecessor',b'load_p377')
    _execute(namespace,raw,'#sealed-p378')

def load_predecessor(namespace):
    name=Path(namespace['__file__']).name.replace('p380','p379')
    raw=_project_from(_read(P379_SOURCES,name),379).replace(b'load_predecessor',b'load_p378')
    _execute(namespace,raw,'#sealed-p379')
