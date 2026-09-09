"""P379 diagnostics namespace; all consumed ancestors remain sealed inputs."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p378_namespace as parent
import s22plus_fyg8_p377_namespace as p377
import s22plus_fyg8_p376_namespace as p376
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="dea3a66b619be3ad1e649162bac576571d1e206dba2f84bc18c2c7f9d82a342e"
_definitions=parent._definitions
P375_SOURCES=parent.P375_SOURCES
P376_SOURCES=parent.P376_SOURCES
P377_SOURCES=parent.P377_SOURCES
P378_SOURCES={'prepare_s22plus_fyg8_p378_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p378_process_v2.py', '35a8630ea061608643397c64225f34d75d3556a01322ce7018a5bc721b3d0d3e'), 's22plus_fyg8_p378_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p378_display_renderer.py', '31bde4c707d2ddfa535beea3af53a367cba67073a93051fe2cbd89cfe37985fb'), 's22plus_fyg8_p378_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p378_process_v2_candidate_static.py', '294a4a03172cb0fae4220bb183eb36b54a9ced70c3d3362fbc6d36e0c627ee25'), 's22plus_fyg8_p378_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p378_stock_candidate_build.py', 'bd7f306d61195c8ca8a3787ba6df39d2fccd84f64c0962a5432d03726c93de9f'), 's22plus_fyg8_p378_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_artifact_identity.py', '6cd2b162e6cd0d2f4d0735da6d92aff7849af7db0342e410d386ce01e30b0a33'), 's22plus_fyg8_p378_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_console_owner.py', 'df49ca0cf3cd4d65b59df5c571a3abe5af3b3f8f50364526dbd93044e3862cad'), 's22plus_fyg8_p378_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_namespace.py', '3129557527fcb90f73023aec110fbcf1e67dd688072a84900fe76947bfaf4ec0'), 's22plus_fyg8_p378_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_progress.py', 'df49ca0cf3cd4d65b59df5c571a3abe5af3b3f8f50364526dbd93044e3862cad'), 's22plus_fyg8_p378_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_research_shell_observer.py', '97d344e0435b31356694bc3b9cbbdc177da110e55f9cdcf63f5e9f49cdd8ee6c'), 's22plus_fyg8_p378_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_research_shell_runtime.py', 'c1a33f95ca86a9c31b43b67c73a6456ed85481ab0f546d240502d7ba2eb643b5'), 's22plus_fyg8_p378_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_return_host.py', 'df49ca0cf3cd4d65b59df5c571a3abe5af3b3f8f50364526dbd93044e3862cad'), 's22plus_fyg8_p378_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_return_spec.py', 'df49ca0cf3cd4d65b59df5c571a3abe5af3b3f8f50364526dbd93044e3862cad'), 's22plus_fyg8_p378_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p378_stock_process_v2_adapter.py', 'df49ca0cf3cd4d65b59df5c571a3abe5af3b3f8f50364526dbd93044e3862cad')}

def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c378f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c379f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(b'P378',b'P379').replace(b'p378',b'p379')

def projected(name):
    return project_bytes(parent.projected(name.replace('p379','p378')))

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p379','p378')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p379').replace(b'P371',b'P379')")
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
    for number,transform in ((376,p376.project_bytes),(377,p377.project_bytes),(378,parent.project_bytes),(379,project_bytes)):
        if number>ordinal:raw=transform(raw)
    return raw

def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p379','p375')
    raw=_project_from(_read(P375_SOURCES,name),375)
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')

def load_p376(namespace):
    name=Path(namespace['__file__']).name.replace('p379','p376')
    _execute(namespace,_project_from(_read(P376_SOURCES,name),376),'#sealed-p376')

def load_p377(namespace):
    name=Path(namespace['__file__']).name.replace('p379','p377')
    raw=_project_from(_read(P377_SOURCES,name),377).replace(b'load_predecessor',b'load_p376')
    _execute(namespace,raw,'#sealed-p377')

def load_predecessor(namespace):
    name=Path(namespace['__file__']).name.replace('p379','p378')
    raw=_project_from(_read(P378_SOURCES,name),378).replace(b'load_predecessor',b'load_p377')
    _execute(namespace,raw,'#sealed-p378')
