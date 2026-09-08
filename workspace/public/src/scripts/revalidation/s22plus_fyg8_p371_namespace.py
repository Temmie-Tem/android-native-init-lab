"""P371 fixed status queries over sealed P370 sources; no device authority."""
from pathlib import Path
import ast,hashlib
ROOT=Path(__file__).resolve().parents[5]
P370_SOURCES={'s22plus_fyg8_p370_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_progress.py', '74485cbc595409a77e4712f3e9860352937b7ddfb2ad45a921de965d1e69d0bc'), 's22plus_fyg8_p370_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_research_shell_observer.py', 'd6affd65d3fb4ce4c07ddc01eec1b33854a9fde2224561cc6e46a830706ad953'), 's22plus_fyg8_p370_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_artifact_identity.py', 'ed012d7e453ec833522a909cea5a86192ed8bcd19f1f819bbc70368b038ef311'), 's22plus_fyg8_p370_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_return_host.py', '74485cbc595409a77e4712f3e9860352937b7ddfb2ad45a921de965d1e69d0bc'), 's22plus_fyg8_p370_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_stock_process_v2_adapter.py', '64e304381c8e0bfb5926d3a5ca9070d8b9a1afe27c9907ac2c8ff4a96ba69f0e'), 's22plus_fyg8_p370_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_research_shell_runtime.py', 'bab5d3bb1d0be05a8011021ca937d59ddd5b5a26054c84e8aba033853f4af13a'), 's22plus_fyg8_p370_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p370_return_spec.py', '110069791e795915cc9b4ab5eab075fc1b6405cef69ba9fcdb3339906caace7b'), 's22plus_fyg8_p370_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p370_display_renderer.py', 'a83f3a74060f79d448d7697b3b7228b4c3981b4bfa8782359f6d030de09665e6'), 's22plus_fyg8_p370_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p370_process_v2_candidate_static.py', '0f04b61c85873f8d501354931a3f1b591a586c1f38d933f1c19b3a343956d759'), 's22plus_fyg8_p370_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p370_stock_candidate_build.py', 'c2c55de1a7bcef01c2028e4925b96957102cfd9151409268548efb86be7a19c9'), 'prepare_s22plus_fyg8_p370_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p370_process_v2.py', 'a83f3a74060f79d448d7697b3b7228b4c3981b4bfa8782359f6d030de09665e6'), 's22plus_fyg8_p370_planned_handoff.py': ('workspace/public/src/scripts/revalidation/s22plus_native_planned_handoff_v1.py', 'e09608c96d515b44d45c3b36786a27b0088ac2f62618e067512e2bbb8654e14d')}
NAMESPACE_SHA='b94e9a538be92b642abe71bf076d14a0e3e866223b3423735a3e7f336282dbe0'
IMAGE_SHA='0720fd9e661f4003c9cfd7b09e48b028ea64d9fb9b5965eee576a43bf6881cdc'
_ns_path=Path(__file__).with_name('s22plus_fyg8_p370_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest()!=NAMESPACE_SHA:raise ValueError('P371 sealed namespace differs')
import s22plus_fyg8_p370_namespace as _p370
PREDECESSORS=dict(_p370.PREDECESSORS)|P370_SOURCES|{'p370_namespace':(str(_ns_path.relative_to(ROOT)),NAMESPACE_SHA)}
_read=_p370._read
_definitions=_p370._definitions

def _p370_base(name):
    old=name.replace('p370','p369')
    raw=_read(_p370.P369_SOURCES[old])
    header=b'from s22plus_fyg8_p369_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p370._p369_base(old)))
    raw=raw.replace(b'P369',b'P370').replace(b'p369',b'p370')
    raw=raw.replace(b'c369f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c370f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p370._p369.IMAGE_SHA.encode(),_p370.IMAGE_SHA.encode())
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'WAIT_SOURCE.read_bytes()',b"WAIT_SOURCE.read_bytes().replace(b'p369',b'p370')")
    if name.endswith('_return_host.py'):
        raw=raw.replace(b'sequence=5',b'sequence=8').replace(b'sequence = 5',b'sequence = 8')
        raw=raw.replace(b"proof['sessions'][0]",b"proof['sessions'][-1]")
    return raw

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p371','p370')
    raw=_read(P370_SOURCES[name])
    header=b'from s22plus_fyg8_p370_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p370_base(name)))
    raw=raw.replace(b'P370',b'P371').replace(b'p370',b'p371')
    raw=raw.replace(b'c370f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c371f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p370.IMAGE_SHA.encode(),IMAGE_SHA.encode())
    if name.endswith('_research_shell_runtime.py'):
        # The consumed native include still has its original identifiers.
        raw=raw.replace(b'HANDOFF_SOURCE.read_bytes()',b"HANDOFF_SOURCE.read_bytes().replace(b'p370',b'p371').replace(b'P370',b'P371')")
    if name.endswith('_return_host.py'):
        raw=raw.replace(b'sequence=8',b'sequence=10').replace(b'sequence = 8',b'sequence = 10')
    if name.endswith('_research_shell_observer.py'):
        pairs=[
            (b'control.FRAME_CONTROL_READY,8,',b'control.FRAME_CONTROL_READY,10,'),
            (b'_request(b,8,',b'_request(b,10,'),
            (b'control.FRAME_CONTROL,8,',b'control.FRAME_CONTROL,10,'),
            (b'control.DOMAIN_CONTROL,b.nonce,8,',b'control.DOMAIN_CONTROL,b.nonce,10,'),
            (b'control.FRAME_CONTROL_ACK,8,',b'control.FRAME_CONTROL_ACK,10,'),
            (b'dict(sequence=8,command=identity(control.CONTROL_BODY)',b'dict(sequence=10,command=identity(control.CONTROL_BODY)'),
            (b'b.authenticated=True;b.ready_seen=True',b'b.authenticated=True;b.ready_seen=True\n    _query_statuses(io,b)'),
            (b'commands=[dict(sequence=10,',b'commands=_status_command_rows(a)+[dict(sequence=10,'),
            (b'total_command_count=4,completed_command_count=2',b'total_command_count=6,completed_command_count=6'),
            (b"'native_progress'}",b"'native_progress','status_samples'}"),
            (b'native_progress=progress_projection(shells[0].session.audit))',b'native_progress=progress_projection(shells[0].session.audit),status_samples=_samples(shells[-1].session.audit))'),
            (b'native_progress=progress_projection(io.audit))) from exc',b'native_progress=progress_projection(io.audit),status_samples=_samples(io.audit))) from exc'),
            (b'len(second)!=1',b'len(second)!=3'),
            (b'second[0]!=dict(sequence=10,',b'second[2]!=dict(sequence=10,'),
            (b'partial=False,handoff_evidence=False',b'partial=False,handoff_evidence=False,status_evidence=False'),
            (b'    if handoff_evidence:',b'    if status_evidence:return _samples(io.audits[-1])\n    if handoff_evidence:'),
        ]
        for old,new in pairs:
            count=2 if old==b'dict(sequence=8,command=identity(control.CONTROL_BODY)' else 1
            if raw.count(old)!=count:raise ValueError('P371 observer seam differs: '+old.decode())
            raw=raw.replace(old,new,count)
    exec(compile(_definitions(raw),str(ROOT/P370_SOURCES[name][0])+'#p371','exec'),namespace)
