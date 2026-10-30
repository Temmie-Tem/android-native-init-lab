"""Private H0 VM capture bindings and offline rechecks; no execution entry point."""
import json
from pathlib import Path
import shutil
import time

from prepare import HERE, ROOT, digest, require
from verify import request, verify


def record(path):
    path=Path(path).resolve()
    return {'path':str(path),'sha256':digest(path)}


def inputs(prepared, init, kernel_label):
    require(bool(kernel_label) and all(c.isalnum() or c=='-' for c in kernel_label),'kernel label')
    manifest_path=init/'result.json'
    kernel_path=prepared/(kernel_label+'-result.json')
    manifest=json.loads(manifest_path.read_text())
    kernel=json.loads(kernel_path.read_text())
    require(manifest['vm'] is True,'VM-only input')
    artifacts={'kernel':{'path':kernel['image'],'sha256':kernel['sha256']},
               'initramfs':manifest['initramfs'],'init':manifest['init']}
    for value in artifacts.values():
        require(digest(value['path'])==value['sha256'],'VM artifact changed')
    binding={name:record(value['path']) for name,value in artifacts.items()}
    binding.update(manifest=record(manifest_path),kernel_record=record(kernel_path),
                   key=record(manifest['key_path']))
    return binding


def snapshot(output):
    source=output/'source';source.mkdir()
    paths=[HERE/name for name in ('vm.py','vm_evidence.py','verify.py','prepare.py',
                                 'retained_kernel_vm.py','retained_marker.py','retained_trace.py',
                                 'retained_probe.py','qualify_retained.py')]
    paths.append(ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_p319_max77705_irq_dt_audit.py')
    for path in paths:shutil.copyfile(path,source/path.name)
    return {path.name:digest(source/path.name) for path in paths}


def capture(output, binding, source, *, bad_key, elapsed, returncode):
    # Called only after complete socket reception and QEMU process settlement.
    evidence={name:digest(output/name) for name in
              ('command.json','nonce.bin','request.raw','response.raw','serial.log','qemu.stderr')}
    receipt={'schema':'g0q-h0-vm-capture-v1','inputs':binding,'source':source,
             'evidence':evidence,'bad_key':bad_key,'elapsed_seconds':elapsed,
             'qemu_returncode':returncode,'device_actions':0}
    with (output/'capture.json').open('x') as stream:
        stream.write(json.dumps(receipt,indent=2)+'\n')


def recheck(prepared, init, previous, output, *, kernel_label='kernel-1'):
    prepared,init,previous,output=[Path(p).resolve() for p in (prepared,init,previous,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private recheck output')
    require(not output.is_relative_to(previous),'recheck output must be outside original run')
    started=time.monotonic()
    receipt_path=previous/'capture.json'
    receipt=json.loads(receipt_path.read_text())
    require(receipt['schema']=='g0q-h0-vm-capture-v1' and receipt['bad_key'] is False,
            'complete positive VM capture required')
    binding=inputs(prepared,init,kernel_label)
    require(receipt['inputs']==binding,'VM inputs differ from captured execution')
    required={'command.json','nonce.bin','request.raw','response.raw','serial.log','qemu.stderr'}
    require(set(receipt['evidence'])==required,'capture evidence incomplete')
    for name,expected in receipt['evidence'].items():
        require(digest(previous/name)==expected,'captured evidence changed: '+name)
    command=json.loads((previous/'command.json').read_text())
    if 'fixture_dtb' in command:
        fixture=command['fixture_dtb'];path=Path(fixture['path'])
        require(path.is_relative_to(previous) and digest(path)==fixture['sha256'], 'VM fixture DTB changed')
        from prepare import nodes,fixed_reservations,uncovered
        require(not uncovered([(0x800200000,0x800400000)],fixed_reservations(nodes(path),coverage=True)),
                'VM fixture lacks no-map log hole')
    sources={'vm.py','vm_evidence.py','verify.py','prepare.py','s22plus_fyg8_p319_max77705_irq_dt_audit.py'}
    expanded=sources|{'retained_kernel_vm.py','retained_marker.py','qualify_retained.py'}
    require(set(receipt['source']) in (sources,expanded,expanded|{'retained_trace.py'},
                                     expanded|{'retained_trace.py','retained_probe.py'}),'capture source incomplete')
    kernel_record=json.loads((prepared/(kernel_label+'-result.json')).read_text())
    if 'retained_marker' in kernel_record:
        marker_source=kernel_record['retained_marker']
        require(digest(marker_source['path'])==marker_source['sha256'],'rechecked VM marker source changed')
        marker_config=json.loads(Path(marker_source['path']).read_text())['config']
        require(digest(marker_config['path'])==marker_config['sha256'],'rechecked VM marker config changed')
        if json.loads(Path(marker_config['path']).read_text())['schema']=='s22plus-mainline-retained-initcall-trace-v8':
            require(set(receipt['source']) in (expanded|{'retained_trace.py'},expanded|{'retained_trace.py','retained_probe.py'}) and 'fixture_dtb' in command,
                    'V8 VM capture lacks trace source or no-map fixture')
        if json.loads(Path(marker_config['path']).read_text())['schema']=='s22plus-mainline-retained-deferred-probe-v9':
            require(set(receipt['source'])==expanded|{'retained_trace.py','retained_probe.py'} and 'fixture_dtb' in command,
                    'V9 VM capture lacks probe source or no-map fixture')
    for name,expected in receipt['source'].items():
        require(digest(previous/'source'/name)==expected,'capture source changed')
    manifest=json.loads((init/'result.json').read_text())
    nonce=(previous/'nonce.bin').read_bytes()
    expected=request(Path(manifest['key_path']).read_bytes(),bytes.fromhex(manifest['candidate_id']),nonce)
    require((previous/'request.raw').read_bytes()==expected,'captured request binding')
    # Scratch belongs to the new output, never to the retained evidence directory.
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    shutil.copyfile(previous/'response.raw',output/'response.raw')
    result=verify(output/'response.raw',manifest,nonce,vm=True)
    result.update(observation_status=result['status'],status='PASS_H0_VM_EVIDENCE_RECHECK',
                  capture=record(receipt_path),validator_source=snapshot(output),
                  kernel_sha256=binding['kernel']['sha256'],
                  original_elapsed_seconds=receipt['elapsed_seconds'],
                  elapsed_seconds=round(time.monotonic()-started,6),
                  vm_executions=0,builds=0,device_actions=0)
    with (output/'result.json').open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','elapsed_seconds','vm_executions','builds')}))
    return result
