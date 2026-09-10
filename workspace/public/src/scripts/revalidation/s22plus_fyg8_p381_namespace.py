"""P381 output backpressure and memory snapshot namespace; all consumed ancestors remain sealed inputs."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p380_namespace as parent
import s22plus_fyg8_p379_namespace as p379
import s22plus_fyg8_p378_namespace as p378
import s22plus_fyg8_p377_namespace as p377
import s22plus_fyg8_p376_namespace as p376
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="b1929bfdda66251fac191f6c238dbf73ae65672151820479a6c3171df4b11172"
_definitions=parent._definitions
P375_SOURCES=parent.P375_SOURCES
P376_SOURCES=parent.P376_SOURCES
P377_SOURCES=parent.P377_SOURCES
P378_SOURCES=parent.P378_SOURCES
P379_SOURCES=parent.P379_SOURCES
P380_SOURCES={'prepare_s22plus_fyg8_p380_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p380_process_v2.py', 'dfc95b00261daec8de7c755aff1816454e82cab14a974f4f9177f1e75fd0c6fc'), 's22plus_fyg8_p380_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_artifact_identity.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162'), 's22plus_fyg8_p380_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_console_owner.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162'), 's22plus_fyg8_p380_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p380_display_renderer.py', '951600a4ad84f679210003237274f1668549d6aea95d41189ebcd46c047cc75e'), 's22plus_fyg8_p380_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_namespace.py', '3b2c2907e751980a31c9c6aa680c5069507605e8a3d7a167adff0db65086d369'), 's22plus_fyg8_p380_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p380_process_v2_candidate_static.py', 'dc2caa331ecff721f298ab2329549ae05984fda4d24710d66ff9956a12a54b0f'), 's22plus_fyg8_p380_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_progress.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162'), 's22plus_fyg8_p380_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_research_shell_observer.py', '51b992056d38ed119cc0b15b49c997ba01e36b4384995eb2c6614bb2d5c4fd6a'), 's22plus_fyg8_p380_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_research_shell_runtime.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162'), 's22plus_fyg8_p380_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_return_host.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162'), 's22plus_fyg8_p380_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_return_spec.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162'), 's22plus_fyg8_p380_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p380_stock_candidate_build.py', 'c3ea8c30c553666fcf7c61eb3f1b70f6f64ed805b0ead83c3e1018c39db6577f'), 's22plus_fyg8_p380_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p380_stock_process_v2_adapter.py', '1bc98b08abbf307bd422fc4532a09e5c00726ddbcab25100198be786b21c7162')}

def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c380f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c381f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(b'P380',b'P381').replace(b'p380',b'p381')

def projected(name):
    return project_bytes(parent.projected(name.replace('p381','p380')))

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p381','p380')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p381').replace(b'P371',b'P381')")
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
    for number,transform in ((376,p376.project_bytes),(377,p377.project_bytes),(378,p378.project_bytes),(379,p379.project_bytes),(380,parent.project_bytes),(381,project_bytes)):
        if number>ordinal:raw=transform(raw)
    return raw

def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p381','p375')
    raw=_project_from(_read(P375_SOURCES,name),375)
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')

def load_p376(namespace):
    name=Path(namespace['__file__']).name.replace('p381','p376')
    _execute(namespace,_project_from(_read(P376_SOURCES,name),376),'#sealed-p376')

def load_p377(namespace):
    name=Path(namespace['__file__']).name.replace('p381','p377')
    raw=_project_from(_read(P377_SOURCES,name),377).replace(b'load_predecessor',b'load_p376')
    _execute(namespace,raw,'#sealed-p377')

def load_p378(namespace):
    name=Path(namespace['__file__']).name.replace('p381','p378')
    raw=_project_from(_read(P378_SOURCES,name),378).replace(b'load_predecessor',b'load_p377')
    _execute(namespace,raw,'#sealed-p378')

def load_p379(namespace):
    name=Path(namespace['__file__']).name.replace('p381','p379')
    raw=_project_from(_read(P379_SOURCES,name),379).replace(b'load_predecessor',b'load_p378')
    _execute(namespace,raw,'#sealed-p379')


def load_predecessor(namespace):
    name=Path(namespace['__file__']).name.replace('p381','p380')
    raw=_project_from(_read(P380_SOURCES,name),380).replace(b'load_predecessor',b'load_p379')
    _execute(namespace,raw,'#sealed-p380')
