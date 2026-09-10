"""P382 compact-journal qualification namespace; all consumed ancestors remain sealed inputs."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p381_namespace as parent
import s22plus_fyg8_p380_namespace as p380
import s22plus_fyg8_p379_namespace as p379
import s22plus_fyg8_p378_namespace as p378
import s22plus_fyg8_p377_namespace as p377
import s22plus_fyg8_p376_namespace as p376
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="4d1fc63ef2172ac932e868155af4a3a931e6853f33c939dad52c1793cdb444b1"
_definitions=parent._definitions
P375_SOURCES=parent.P375_SOURCES
P376_SOURCES=parent.P376_SOURCES
P377_SOURCES=parent.P377_SOURCES
P378_SOURCES=parent.P378_SOURCES
P379_SOURCES=parent.P379_SOURCES
P380_SOURCES=parent.P380_SOURCES
P381_SOURCES={'prepare_s22plus_fyg8_p381_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p381_process_v2.py', 'a7fa8cf58ee4f12f8e3df224286e359ed827d292db307bd71e4226bea7376c4f'), 's22plus_fyg8_p381_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p381_display_renderer.py', '2060ef955772a6442894c6eeee9d9b39edac175cede3c22dbaaaa4e68d662cf1'), 's22plus_fyg8_p381_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p381_process_v2_candidate_static.py', '704d505698da5c7001fb281f4b2274527bfab5fa748840312da59123b1ffbac4'), 's22plus_fyg8_p381_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p381_stock_candidate_build.py', '418c512aeee87cc4b45abbcbad04fd044b3757c095d24f2fd978445c172a0caf'), 's22plus_fyg8_p381_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_artifact_identity.py', 'e30721b3def773e949c857cecfa1de33cad104dc63065f662a4a976957093d9f'), 's22plus_fyg8_p381_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_console_owner.py', 'e30721b3def773e949c857cecfa1de33cad104dc63065f662a4a976957093d9f'), 's22plus_fyg8_p381_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_namespace.py', 'd730e8b014a4046bd4c60e1fba809bc13c6f1ec63c4e9d2b9e2843007bf21207'), 's22plus_fyg8_p381_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_progress.py', 'e30721b3def773e949c857cecfa1de33cad104dc63065f662a4a976957093d9f'), 's22plus_fyg8_p381_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_research_shell_observer.py', 'd30238fb7d894a7b122b164d335a1726aa7b7b9e8a481e891384478bc0eed380'), 's22plus_fyg8_p381_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_research_shell_runtime.py', '5f3c205ac24cf18121fe45b5078c17d34cb0bca2ccae8a8d582f2d1bdeb7c88b'), 's22plus_fyg8_p381_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_return_host.py', 'e30721b3def773e949c857cecfa1de33cad104dc63065f662a4a976957093d9f'), 's22plus_fyg8_p381_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_return_spec.py', 'e30721b3def773e949c857cecfa1de33cad104dc63065f662a4a976957093d9f'), 's22plus_fyg8_p381_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p381_stock_process_v2_adapter.py', 'e30721b3def773e949c857cecfa1de33cad104dc63065f662a4a976957093d9f')}

def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c381f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c382f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(b'P381',b'P382').replace(b'p381',b'p382')

def projected(name):
    return project_bytes(parent.projected(name.replace('p382','p381')))

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p381')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p382').replace(b'P371',b'P382')")
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
    for number,transform in ((376,p376.project_bytes),(377,p377.project_bytes),(378,p378.project_bytes),(379,p379.project_bytes),(380,p380.project_bytes),(381,parent.project_bytes),(382,project_bytes)):
        if number>ordinal:raw=transform(raw)
    return raw

def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p382','p375')
    raw=_project_from(_read(P375_SOURCES,name),375)
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')

def load_p376(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p376')
    _execute(namespace,_project_from(_read(P376_SOURCES,name),376),'#sealed-p376')

def load_p377(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p377')
    raw=_project_from(_read(P377_SOURCES,name),377).replace(b'load_predecessor',b'load_p376')
    _execute(namespace,raw,'#sealed-p377')

def load_p378(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p378')
    raw=_project_from(_read(P378_SOURCES,name),378).replace(b'load_predecessor',b'load_p377')
    _execute(namespace,raw,'#sealed-p378')

def load_p379(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p379')
    raw=_project_from(_read(P379_SOURCES,name),379).replace(b'load_predecessor',b'load_p378')
    _execute(namespace,raw,'#sealed-p379')


def load_p380(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p380')
    raw=_project_from(_read(P380_SOURCES,name),380).replace(b'load_predecessor',b'load_p379')
    _execute(namespace,raw,'#sealed-p380')


def load_predecessor(namespace):
    name=Path(namespace['__file__']).name.replace('p382','p381')
    raw=_project_from(_read(P381_SOURCES,name),381).replace(b'load_predecessor',b'load_p380')
    _execute(namespace,raw,'#sealed-p381')
