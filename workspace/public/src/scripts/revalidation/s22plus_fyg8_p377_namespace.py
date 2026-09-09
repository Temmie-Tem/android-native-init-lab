"""v0.1.1-rc.1 status HUD; sealed v0.1.0 projections, H0 only."""
from pathlib import Path
import ast
import hashlib
import s22plus_fyg8_p376_namespace as parent
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
IMAGE_SHA="23e816116278d637a33b354f8bf735c550060ba6ee98fea697098795e8aa3074"
_definitions=parent._definitions
P376_SOURCES={'prepare_s22plus_fyg8_p376_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p376_process_v2.py', '014b0c8741c793ab91db84f351c0dd094be3cfaf180180b041d546a2b6720a0b'), 's22plus_fyg8_p376_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p376_display_renderer.py', 'ff0a70b8bbc29ae6970e0e6631f2f7d3a56511eec9a996a24d56c4c6ebe6fffe'), 's22plus_fyg8_p376_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p376_process_v2_candidate_static.py', '17a81f5a4fc58bb527667f6b1c9abe9f83f884beca9f33b85ee48792eef62038'), 's22plus_fyg8_p376_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p376_stock_candidate_build.py', '0e8d5ffeead9c991f90c25bfd285c02e5254ca4be8758cb413507925d5618640'), 's22plus_fyg8_p376_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_artifact_identity.py', '665a32138bc7da1ab48ed5889327d5f2363043fffffa98a6bca0984c54618306'), 's22plus_fyg8_p376_console_owner.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_console_owner.py', '396aa4fcc5675063fcc711a04bcb9da26b0b62c9ddcdd38fce8d5766d1d08eb5'), 's22plus_fyg8_p376_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_namespace.py', 'c4704b67b7a91593205e13370170415a37997378e1f887587349120382eb4c79'), 's22plus_fyg8_p376_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_progress.py', '396aa4fcc5675063fcc711a04bcb9da26b0b62c9ddcdd38fce8d5766d1d08eb5'), 's22plus_fyg8_p376_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_research_shell_observer.py', '318d8b519ae7d2aef64d70226944587efc570c9f5f05fa6746c0e7fa70b8b708'), 's22plus_fyg8_p376_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_research_shell_runtime.py', '26281c867ef7f2d6429833d8826783e2c058230e9365d4eafaacdd688b44a64e'), 's22plus_fyg8_p376_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_return_host.py', '396aa4fcc5675063fcc711a04bcb9da26b0b62c9ddcdd38fce8d5766d1d08eb5'), 's22plus_fyg8_p376_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_return_spec.py', '396aa4fcc5675063fcc711a04bcb9da26b0b62c9ddcdd38fce8d5766d1d08eb5'), 's22plus_fyg8_p376_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p376_stock_process_v2_adapter.py', 'c46ffb80635ce807c27b769dd561e644abfb99888cac9fc42bb5dbca98d1f675')}


def project_bytes(raw):
    return raw.replace(parent.IMAGE_SHA.encode(),IMAGE_SHA.encode()).replace(
        b'c376f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c377f1e0a90b5e6d7c8a9b0c1d2e3f0b').replace(b'P376',b'P377').replace(b'p376',b'p377')


def projected(name):
    return project_bytes(parent.projected(name.replace('p377','p376')))


def load(namespace):
    name=Path(namespace['__file__']).name.replace('p377','p376')
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p377').replace(b'P371',b'P377')")
    exec(compile(_definitions(raw),str(namespace['__file__'])+'#sealed-base','exec'),namespace)


def _execute(namespace,raw,label):
    tree=ast.parse(raw)
    tree.body=[node for node in tree.body if not (isinstance(node,ast.If) and '__name__' in ast.unparse(node.test))]
    exec(compile(ast.fix_missing_locations(tree),str(namespace['__file__'])+label,'exec'),namespace)


def load_template(namespace,transform=None):
    name=Path(namespace['__file__']).name.replace('p377','p375')
    path,digest=parent.P375_SOURCES[name];raw=(ROOT/path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('sealed P375 predecessor differs: '+name)
    raw=project_bytes(parent.project_bytes(raw))
    if transform is not None:raw=transform(raw)
    _execute(namespace,raw,'#sealed-p375')


def load_predecessor(namespace):
    name=Path(namespace['__file__']).name.replace('p377','p376')
    path,digest=P376_SOURCES[name];raw=(ROOT/path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('sealed P376 predecessor differs: '+name)
    _execute(namespace,project_bytes(raw),'#sealed-p376')

P375_SOURCES=parent.P375_SOURCES
