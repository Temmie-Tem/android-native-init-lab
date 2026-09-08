"""Three fixed display-step variants projected from sealed P371 sources.

Projection preserves consumed predecessors; all new behavior lives in shared
step extensions. Scenario selection is derived from the module name, never a
live caller argument.
"""
from pathlib import Path
import ast
import hashlib

ROOT=Path(__file__).resolve().parents[5]
REVALIDATION=Path(__file__).resolve().parent
import s22plus_fyg8_p371_namespace as parent
SCENARIOS={'p372':(1,False),'p373':(2,False),'p374':(1,True)}
# Filled from the current consumed source bytes at implementation time.
P371_SOURCES={'s22plus_fyg8_p371_display_renderer.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p371_display_renderer.py', 'aaad8e6f83784f0b71be50bde018a918dd2bce6fe13b1caa73d1a6dd71404e7c'), 's22plus_fyg8_p371_process_v2_candidate_static.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p371_process_v2_candidate_static.py', 'bf90c38c9bc3982c4849f28868d3c6ac5be73cbd9a52ec7e98a10551e0999f4b'), 's22plus_fyg8_p371_stock_candidate_build.py': ('workspace/public/src/scripts/analysis/s22plus_fyg8_p371_stock_candidate_build.py', '112b4cb1e69fe467d65253ce9bf2d24b9e5892515a053ac34db16c62054e8c98'), 's22plus_fyg8_p371_artifact_identity.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_artifact_identity.py', '22a574a8f2c9b55eb179d2e657630ee8de9a1f70620637f689e10cd081c66eab'), 's22plus_fyg8_p371_namespace.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_namespace.py', 'cbc1e3852352c588a8ede5435a0cb609456de936eacfea2c91115a02069567dd'), 's22plus_fyg8_p371_planned_handoff.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_planned_handoff.py', '0b1bf99fe2b23c9e62b33027bdc3acf27ddbf960ecdde681652cfd6455fe2548'), 's22plus_fyg8_p371_progress.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_progress.py', 'd2587946533729f7ac98ef8b5bb42d30825cde57285452f7e9348ed23ff2a2e4'), 's22plus_fyg8_p371_research_shell_observer.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_research_shell_observer.py', '30f9ccd22dfc2a247ad3093c773113113134d8bc04b3983a8a0f353c6e3dba19'), 's22plus_fyg8_p371_research_shell_runtime.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_research_shell_runtime.py', 'ad8dfe5e7fead43d2ad32f2783a5840b8f15fdf93156c6bb2a70604d834e46bd'), 's22plus_fyg8_p371_return_host.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_return_host.py', 'd2587946533729f7ac98ef8b5bb42d30825cde57285452f7e9348ed23ff2a2e4'), 's22plus_fyg8_p371_return_spec.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_return_spec.py', '643f70cdccf3785bba91deda193b36896403ef100bdc26db9a7797a4342a3233'), 's22plus_fyg8_p371_stock_process_v2_adapter.py': ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_stock_process_v2_adapter.py', 'b2b51b05a7da64a3875b0c6e792f646426b4f8bb78b2b9e683eec6ebb1d33905'), 'prepare_s22plus_fyg8_p371_process_v2.py': ('workspace/public/src/scripts/analysis/prepare_s22plus_fyg8_p371_process_v2.py', 'aaad8e6f83784f0b71be50bde018a918dd2bce6fe13b1caa73d1a6dd71404e7c')}
PREDECESSORS=dict(parent.PREDECESSORS)|P371_SOURCES
IMAGE_SHA=parent.IMAGE_SHA
IMAGE_HASHES={'p372': 'd0beb144ccd9609b0732f5571f1c3a031b93a6cc16ed1276e8053dea516b14bc', 'p373': 'a71b6eb1f52f241d7ea98b6926cf15d42801cb04564593248774fde8a90d3603', 'p374': '280e6eb92fb32a8768004bf23cf791377b099c4e596c93c947eb65606ec8bbd6'}
_read=parent._read
_definitions=parent._definitions


def predecessor(name):
    """Expose the parent's deterministic source projection without executing it."""
    path,digest=P371_SOURCES['s22plus_fyg8_p371_namespace.py']
    raw=_read((path,digest))
    tree=ast.parse(raw)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='load')
    last=function.body[-1]
    if not isinstance(last,ast.Expr) or not isinstance(last.value,ast.Call) or not isinstance(last.value.func,ast.Name) or last.value.func.id!='exec':
        raise ValueError('sealed P371 projection seam differs')
    function.body[-1]=ast.Return(value=ast.Name(id='raw',ctx=ast.Load()))
    unit=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    env=dict(vars(parent));exec(compile(unit,path+'#source-projection','exec'),env)
    return env['load']({'__file__':name})


def projected(name,prefix):
    old=name.replace(prefix,'p371')
    raw=_read(P371_SOURCES[old])
    header=b'from s22plus_fyg8_p371_namespace import load\nload(globals())'
    if header in raw:raw=raw.replace(header,_definitions(predecessor(old)))
    raw=raw.replace(parent.IMAGE_SHA.encode(),IMAGE_HASHES[prefix].encode())
    raw=raw.replace(b'c371f1e0a90b5e6d7c8a9b0c1d2e3f0b',('c'+prefix[1:]+'f1e0a90b5e6d7c8a9b0c1d2e3f0b').encode())
    return raw.replace(b'P371',prefix.upper().encode()).replace(b'p371',prefix.encode())


def load(namespace):
    name=Path(namespace['__file__']).name
    prefix=next((p for p in SCENARIOS if p in name),None)
    if prefix is None:raise ValueError('unknown fixed display-step variant')
    raw=projected(name,prefix)
    if name.endswith('_return_host.py'):
        raw=raw.replace(b'sequence=10',b'sequence=14').replace(b'sequence = 10',b'sequence = 14')
    # Consumed includes retain their original namespace internally.
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'"+prefix.encode()+b"').replace(b'P371',b'"+prefix.upper().encode()+b"')")
    namespace.update(_STEP_MODULE_NAME=name,_STEP_PREFIX=prefix,_STEP_MAX=SCENARIOS[prefix][0],_STEP_EXIT=SCENARIOS[prefix][1])
    if name.endswith('_research_shell_observer.py'):
        for old,new in [(b', 10,',b', 14,'),(b'sequence=10',b'sequence=14'),(b'len(second) != 3',b'len(second) != 3+_STEP_MAX'),(b'second[2] != dict(sequence=14',b'second[-1] != dict(sequence=14')]:raw=raw.replace(old,new)
        start=raw.find(b"    expected = dict(submitted_swaps=3",raw.find(b"    diag = progress.validate_projection(value['native_progress'])"))
        end=raw.find(b"    if rows[0]['progress_range']",start)
        if start<0 or end<start:raise ValueError('step qualification checkpoint seam differs')
        raw=raw[:start]+b'    _validate_step_checkpoint(diag)\n'+raw[end:]
    exec(compile(_definitions(raw),str(ROOT/P371_SOURCES[name.replace(prefix,'p371')][0])+'#'+prefix,'exec'),namespace)

    if name.endswith('_research_shell_runtime.py'):
        extension=REVALIDATION/'s22plus_display_step_v1_runtime.py'
        exec(compile(extension.read_bytes(),str(extension),'exec'),namespace)

    if name.endswith('_display_renderer.py'):
        extension=REVALIDATION/'s22plus_display_step_v1_renderer.py'
        exec(compile(extension.read_bytes(),str(extension),'exec'),namespace)

    if name.endswith('_return_spec.py'):
        namespace['STAGES'][42]='eventfd-create-and-child-clone'
        namespace.update(CONTROL_SEQUENCE=14,FRAME_STEP=11,FRAME_STEP_ACK=0x90,STEP_BODY=bytes((1,0,0,0)),
            STEP_DOMAIN=('S22PLUS-FYG8-'+prefix.upper()+'-DISPLAY-STEP-v1').encode(),
            STEP_ACK_DOMAIN=('S22PLUS-FYG8-'+prefix.upper()+'-DISPLAY-STEP-ACK-v1').encode())
    for suffix,filename in [('_progress.py','progress'),('_research_shell_observer.py','observer')]:
        if name.endswith(suffix):
            extension=REVALIDATION/('s22plus_display_step_v1_'+filename+'.py')
            exec(compile(extension.read_bytes(),str(extension),'exec'),namespace)

    if name.endswith('_return_host.py'):
        # This host owner binds the new fixed CONTROL sequence.
        namespace['CONTROL_SEQUENCE']=14
    if name.endswith(('_artifact_identity.py','_stock_process_v2_adapter.py')):
        extension=REVALIDATION/'s22plus_display_step_v1_metadata.py'
        exec(compile(extension.read_bytes(),str(extension),'exec'),namespace)
    shared={str(p.relative_to(ROOT)):p for p in REVALIDATION.glob('s22plus_display_step_v1_*.py')}
    for relative in ('workspace/public/src/native-init/s22plus_native_display_step_v1.inc.c',
                     'workspace/public/src/scripts/revalidation/s22plus_attended_f1_session_v1.py'):
        shared[relative]=ROOT/relative
    if name.endswith('_stock_candidate_build.py'):
        previous=namespace['source_files']
        namespace['source_files']=lambda:dict(previous())|shared
    if name.endswith('_process_v2_candidate_static.py'):
        namespace['SOURCE_FILES'].update({'display_step_'+Path(k).stem:v for k,v in shared.items()})
