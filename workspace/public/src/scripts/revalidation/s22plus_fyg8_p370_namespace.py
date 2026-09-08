"""P370 one planned handoff; P369 sources remain sealed."""
from pathlib import Path
import ast,hashlib
ROOT=Path(__file__).resolve().parents[5]
P369_SOURCES={'prepare_s22plus_fyg8_p369_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p369_process_v2.py', 'bb22a3473a868cec21e4bde24e6c7677ea65bce744e43289dcada699feea936c'), 's22plus_fyg8_p369_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p369_display_renderer.py', '54d0c3f1da9d3b5ece18078dbce883510c506b0e4a10cab52b98d4289aa39c19'), 's22plus_fyg8_p369_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p369_process_v2_candidate_static.py', '6b33800ddda4970d3876121e60c1c0a368b802b6e6149de289f8bb5dd681be21'), 's22plus_fyg8_p369_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p369_stock_candidate_build.py', '0ae1dadb4a14f7e84055c059da076ce08c0d3e6190edded3a1c271c935ecf67d'), 's22plus_fyg8_p369_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_research_shell_runtime.py', '6e8372de2b6a49704789229897282d74a470f8432f2fc497b54abe45a91024f2'), 's22plus_fyg8_p369_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_return_spec.py', '7a6f914d7c6acfaae58a94042172a9b1850b4aaaf5f506ddc2696267e57088eb'), 's22plus_fyg8_p369_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_artifact_identity.py', 'ace3d311cd4eb6aefbddac22dcb174eac505c9dbbc7f97a49024bbc5138853c5'), 's22plus_fyg8_p369_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_progress.py', 'b20318b90105c5ed7bbcb0eaceae7632270922074ea3d0cacde02a0e10d2b0b1'), 's22plus_fyg8_p369_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_stock_process_v2_adapter.py', 'ace3d311cd4eb6aefbddac22dcb174eac505c9dbbc7f97a49024bbc5138853c5'), 's22plus_fyg8_p369_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_research_shell_observer.py', '24a902e02110097135da8f4806eb7768313aad2b0fb33aa9d8481a44b7cc1d2d'), 's22plus_fyg8_p369_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p369_return_host.py', 'ace3d311cd4eb6aefbddac22dcb174eac505c9dbbc7f97a49024bbc5138853c5')}
NAMESPACE_SHA='40853ac7d73e082c848d36f3afcea029d5c4b9f801cd51b70f92ca8a46a406bb'
IMAGE_SHA='bdbe6db27d54eb894914501acf69fe53a4dd6fe29e034c73bfcb92a00c6bdcaf'
_ns_path=Path(__file__).with_name('s22plus_fyg8_p369_namespace.py')
if hashlib.sha256(_ns_path.read_bytes()).hexdigest()!=NAMESPACE_SHA:raise ValueError('P370 sealed namespace differs')
import s22plus_fyg8_p369_namespace as _p369
PREDECESSORS=dict(_p369.PREDECESSORS)|P369_SOURCES|{'p369_namespace':(str(_ns_path.relative_to(ROOT)),NAMESPACE_SHA)}
_read=_p369._read
_definitions=_p369._definitions

def _p369_base(name):
    old=name.replace('p369','p368')
    raw=_read(_p369.P368_SOURCES[old])
    header=b'from s22plus_fyg8_p368_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p369._p368_base(old)))
    raw=raw.replace(b'P368',b'P369').replace(b'p368',b'p369')
    raw=raw.replace(b'c368f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c369f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p369._p368.IMAGE_SHA.encode(),_p369.IMAGE_SHA.encode())
    if name.endswith('_research_shell_observer.py'):
        raw=raw.replace(b'ready[3] == 0 and ready[1] != 10',b'ready[3] != 0 or ready[1] != 0')
        raw=raw.replace(b'not child_exited and swaps != 10',b'child_exited or swaps != 0')
    return raw

def load(namespace):
    name=Path(namespace['__file__']).name.replace('p370','p369')
    raw=_read(P369_SOURCES[name])
    header=b'from s22plus_fyg8_p369_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(_p369_base(name)))
    raw=raw.replace(b'P369',b'P370').replace(b'p369',b'p370')
    raw=raw.replace(b'c369f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c370f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    raw=raw.replace(_p369.IMAGE_SHA.encode(),IMAGE_SHA.encode())
    # Project the sealed C include too; never edit the consumed input.
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'WAIT_SOURCE.read_bytes()',b"WAIT_SOURCE.read_bytes().replace(b'p369',b'p370')")
    if name.endswith('_return_host.py'):
        raw=raw.replace(b'sequence=5',b'sequence=8').replace(b'sequence = 5',b'sequence = 8')
        raw=raw.replace(b"proof['sessions'][0]",b"proof['sessions'][-1]")
    exec(compile(_definitions(raw),str(ROOT/P369_SOURCES[name][0])+'#p370','exec'),namespace)
