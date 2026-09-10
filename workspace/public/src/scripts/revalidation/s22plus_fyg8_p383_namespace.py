"""P383 native-baseline namespace over immutable P382 source inputs."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p382_namespace as parent
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
_definitions=parent._definitions
IMAGE_SHA='776e5a2461b2c3260bf084ef30844628dcaf562d38f958433e3204b02899c4f4'
P382_SOURCES={'prepare_s22plus_fyg8_p382_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p382_process_v2.py', '2b9f1565032713593305c1544ad6fb4dbd90e9bce8b76d3fb3891c61a1310a46'), 's22plus_fyg8_p382_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p382_display_renderer.py', 'c3e2c4551d01ea3a540c3b06aa69a429e10efff297de6b259e751aae2c67264d'), 's22plus_fyg8_p382_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p382_process_v2_candidate_static.py', '0af5f2ce2eafd9b9ea4c0151ee8b800fffffbe0166a09beec772cf4f7b53eddd'), 's22plus_fyg8_p382_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p382_stock_candidate_build.py', '63991cb0ee39729bbfc0984dedbc2ec2f799598b7b571cd4aabf9c84c0744b3e'), 's22plus_fyg8_p382_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_artifact_identity.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_console_owner.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_namespace.py', '45c44b9b947ee7631eb44d45abd654a7b1e9e88d9e5da7f36c9a609191b18794'), 's22plus_fyg8_p382_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_progress.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_research_shell_observer.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_research_shell_runtime.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_return_host.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_return_spec.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a'), 's22plus_fyg8_p382_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p382_stock_process_v2_adapter.py', '39d095ae0bb8e16e80ef79bf6341d37f4c14b835f45f5b3a7c1227ff80b7265a')}
for _ordinal in range(375,382):
    globals()[f'P{_ordinal}_SOURCES']=getattr(parent,f'P{_ordinal}_SOURCES')

def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c382f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c383f1e0a90b5e6d7c8a9b0c0d2e3f0b').replace(b'P382',b'P383').replace(b'p382',b'p383')

def projected(name):
    return project_bytes(parent.projected(name.replace('p383','p382')))

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p383','p382')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p383').replace(b'P371',b'P383')")
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
    return project_bytes(parent._project_from(raw,ordinal))

def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p383','p375')
    raw=_project_from(_read(P375_SOURCES,name),375)
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')

def _load_ordinal(namespace,ordinal):
    name=Path(namespace['__file__']).name.replace('p383',f'p{ordinal}')
    raw=_project_from(_read(globals()[f'P{ordinal}_SOURCES'],name),ordinal)
    if ordinal>376:raw=raw.replace(b'load_predecessor',f'load_p{ordinal-1}'.encode())
    _execute(namespace,raw,f'#sealed-p{ordinal}')

def load_p376(namespace):
    _load_ordinal(namespace,376)

def load_p377(namespace):
    _load_ordinal(namespace,377)

def load_p378(namespace):
    _load_ordinal(namespace,378)

def load_p379(namespace):
    _load_ordinal(namespace,379)

def load_p380(namespace):
    _load_ordinal(namespace,380)

def load_p381(namespace):
    _load_ordinal(namespace,381)

def load_predecessor(namespace):
    _load_ordinal(namespace,382)
