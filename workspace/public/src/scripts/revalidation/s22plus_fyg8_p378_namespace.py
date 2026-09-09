"""v0.1.2-rc.1 gauge HUD namespace; consumed predecessors are sealed inputs."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p377_namespace as parent
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="45ca04ed855b767085f2ea813216e2a9f0b593d79fd065469f0c1a6e5831dcbd"
_definitions=parent._definitions
P375_SOURCES=parent.P375_SOURCES
P376_SOURCES=parent.P376_SOURCES
P377_SOURCES={'prepare_s22plus_fyg8_p377_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p377_process_v2.py', '13142179ee334e977445da890b075aaaaf4f4cf53a7fd54a0b75b7fa981261f2'), 's22plus_fyg8_p377_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p377_display_renderer.py', '7579b3412123fba0d719521e8623d9f221e2d99594cffb9676dd8eec8496a81e'), 's22plus_fyg8_p377_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p377_process_v2_candidate_static.py', 'a77f0b12ff8769f2cd4ac6108741d5edba524639eb627a70a324c272e70eab97'), 's22plus_fyg8_p377_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p377_stock_candidate_build.py', '1a661791b6a8e3ccb218ea7605fa338d157c6a5952717966319d22d9e6c967c3'), 's22plus_fyg8_p377_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_artifact_identity.py', '0caa7ce1221e495bb7ead723ec1702ef1ca85e294e73241792cf086f27934389'), 's22plus_fyg8_p377_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_console_owner.py', '0caa7ce1221e495bb7ead723ec1702ef1ca85e294e73241792cf086f27934389'), 's22plus_fyg8_p377_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_namespace.py', 'a61a7ee6119b472ecf7bb947e42e8abd9435a25d2b0376245bd7fb0ffd8562ed'), 's22plus_fyg8_p377_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_progress.py', '0caa7ce1221e495bb7ead723ec1702ef1ca85e294e73241792cf086f27934389'), 's22plus_fyg8_p377_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_research_shell_observer.py', '0f44cf2b4349ed5dc27d1ddb74bcda1582eca47d9f8c2e45956e8cf8a669cd53'), 's22plus_fyg8_p377_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_research_shell_runtime.py', '4420e1c53a645a6fa64f512710bade50ba99e772f4668720b4cfc8adba11316a'), 's22plus_fyg8_p377_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_return_host.py', '0caa7ce1221e495bb7ead723ec1702ef1ca85e294e73241792cf086f27934389'), 's22plus_fyg8_p377_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_return_spec.py', '0caa7ce1221e495bb7ead723ec1702ef1ca85e294e73241792cf086f27934389'), 's22plus_fyg8_p377_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p377_stock_process_v2_adapter.py', '0caa7ce1221e495bb7ead723ec1702ef1ca85e294e73241792cf086f27934389')}

def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c377f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c378f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(b'P377',b'P378').replace(b'p377',b'p378')

def projected(name):
    return project_bytes(parent.projected(name.replace('p378','p377')))

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p378','p377')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p378').replace(b'P371',b'P378')")
    exec(compile(_definitions(raw),str(namespace['__file__'])+'#sealed-base','exec'),namespace)

def _execute(namespace,raw,label):
    tree=ast.parse(raw)
    tree.body=[node for node in tree.body if not (isinstance(node,ast.If) and '__name__' in ast.unparse(node.test))]
    exec(compile(ast.fix_missing_locations(tree),str(namespace['__file__'])+label,'exec'),namespace)

def _read(mapping,name):
    path,digest=mapping[name];raw=(ROOT/path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('sealed predecessor differs: '+name)
    return raw

def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p378','p375')
    raw=project_bytes(parent.project_bytes(parent.parent.project_bytes(_read(P375_SOURCES,name))))
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')

def load_p376(namespace):
    name=Path(namespace['__file__']).name.replace('p378','p376')
    raw=project_bytes(parent.project_bytes(_read(P376_SOURCES,name)))
    _execute(namespace,raw,'#sealed-p376')

def load_predecessor(namespace):
    name=Path(namespace['__file__']).name.replace('p378','p377')
    raw=project_bytes(_read(P377_SOURCES,name)).replace(b'load_predecessor',b'load_p376')
    _execute(namespace,raw,'#sealed-p377')
