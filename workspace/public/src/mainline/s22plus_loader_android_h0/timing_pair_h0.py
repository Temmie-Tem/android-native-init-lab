"""Verify the actual FYG8 timing pair before the isolated H0 packager."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import struct

import build as builder
from build import pin, require
import qualify as arm64
import s22plus_loader_android_profile_v1 as profile
from s22plus_loader_android_profile_v1 import LOGM_PROPERTY, logm_report
import s22plus_fyg8_retained_snapshot_model as snapshot_model
import timing


def project_arm(properties, build):
    """Decode fixed FDT bytes using the exact arm's candidate descriptor."""
    config = build['logm_control']['configuration']
    armed = build['timing_control']['logm_enabled']
    report = timing.project(properties[timing.PROPERTY], build['marker'], armed)
    logm = properties[LOGM_PROPERTY]
    if armed:
        writer = logm_report(logm, config)
        if writer['status'] != 'READBACK_MATCH' or writer['header_changed_after_commit']:
            raise ValueError('LOGM on arm did not supply stable matching readback')
    else:
        if logm != bytes.fromhex(config['report_seed_hex']):
            raise ValueError('LOGM off arm did not preserve the complete seed')
        writer = {'status': 'DISABLED'}
    return dict(report, writer=writer)


def check_arm(folder, mode, writer_cases):
    build_path = folder/f'build-{mode}/result.json'
    vm_path = folder/f'vm-{mode}/result.json'
    build, vm = (json.loads(p.read_text()) for p in (build_path, vm_path))
    armed = mode == 'on'
    require(build['timing_control']==vm['timing_control']==dict(logm_enabled=armed, report_property=timing.PROPERTY)
            and vm['status']=='PASS_H0_QEMU_ACTUAL_EL_LOADER_TIMING' and vm['device_actions']==0
            and vm['loader_sha256']==build['loader']['sha256'] and vm['retained_fdt']==build['retained_fdt'],
            'actual entry proof differs')
    for key in ('loader','elf','kernel','retained_fdt'):
        require(pin(build[key]['path'])==build[key], 'build bytes changed: '+key)
    blob = Path(build['loader']['path']).read_bytes()
    syms = arm64.symbols(build['elf']['path'])
    guard_offset = syms['_guard_passed'][0] - syms['_head'][0]
    require(blob[guard_offset:guard_offset+8] == struct.pack('<II',0xd5033fdf,0xd53be05b),
            'linked guard does not sample CNTVCT_EL0 into x27')
    fdt = Path(build['retained_fdt']['path']).read_bytes()
    tested = []
    for label,data,outcome in (
        ('live-tree-valid', fdt, 'guard'),
        ('malformed-fdt-magic', b'BAD!'+fdt[4:], 'reject'),
        ('preexisting-timing-property', arm64.set_property(fdt,'/chosen',timing.PROPERTY,bytes(128)), 'reject'),
    ):
        row,_ = arm64.run_case(blob,build,syms,0xa8000000,data,expected=outcome)
        require(row['write_bytes']==0, 'guard wrote memory')
        tested.append(dict(row, name=label, stimulus_sha256=hashlib.sha256(data).hexdigest()))
    for row in vm['cases']:
        level = row['actual_entry_el']
        if level==3:
            require(row['terminal']=='reject','EL3 must reject before the timer')
            continue
        final = Path(row['timing_report']['path'])
        require(pin(final)==row['timing_report'],'retained final FDT changed')
        full = arm64.nodes(final)
        data = full['/chosen'][timing.PROPERTY]
        projected = project_arm(full['/chosen'],build)
        require(projected['stages']==row['timing']['stages'],'retained timing report differs')
        require(0 < projected['stages']['guard_passed'] <= 240*projected['counter_hz'] and
                projected['intervals_ns']['guard_to_report_commit_sample'] < 240_000_000_000,
                'emulated guard or handoff tick falls outside the QEMU window')
        negatives = (
            data[:-1],
            data[:15]+b'\0'+data[16:],
            data[:48]+struct.pack('>I',int(not armed))+data[52:],
            data[:52]+bytes(4)+data[56:],
            data[:56]+bytes([255])*8+data[64:],
        )
        for bad in negatives:
            try:
                timing.project(bad,build['marker'],armed)
            except ValueError:
                pass
            else:
                raise ValueError('malformed timing evidence accepted')

    conf = build['logm_control']['configuration']
    if armed:
        result = json.loads(writer_cases.read_text())
        require(result['status']=='PASS_H0_ACTUAL_LOADER_LOGM_CONTROL' and result['configuration']==conf,
                'actual linked LOGM guard qualification differs')
    data_spans = {
        'g0q_logm_frame': bytes.fromhex(conf['frame_hex']),
        'g0q_logm_report_seed': bytes.fromhex(conf['report_seed_hex']),
        'g0q_timing_seed': timing.seed(build['marker']),
        'g0q_timing_logm': struct.pack('<I',int(armed)),
    }
    origin = syms['_head'][0]
    marker = build['marker'].encode()
    require(blob.count(marker)==1,'expected one CHOSEN candidate marker')
    spans = {'android_candidate_marker':(blob.index(marker),len(marker))}
    masked = bytearray(blob)
    for name,expected in data_spans.items():
        address,length = syms[name]
        offset = address - origin
        require(length==len(expected) and blob[offset:offset+length]==expected, 'wrong linked data '+name)
        spans[name]=(offset,length)
    for start,size in spans.values():
        masked[start:start+size]=bytes(size)
    return build,vm,masked,spans,tested


def writer_shard(folder,shard,shards):
    build=json.loads((folder/'build-on/result.json').read_text())
    entry=json.loads((folder/'vm-on/result.json').read_text())
    for key in ('loader','elf'):
        require(pin(build[key]['path'])==build[key], 'writer input differs')
    evidence=entry['cases'][0]['timing_report']
    require(pin(evidence['path'])==evidence,'writer fixture differs')
    blob=Path(build['loader']['path']).read_bytes()
    cloned=Path(evidence['path']).read_bytes()
    out=folder/f'writer-shard-{shard:02}'
    out.mkdir(mode=0o700)
    arm64.logm_cases(blob,build,arm64.symbols(build['elf']['path']),cloned,out,shard=shard,shards=shards)
    return pin(out/'logm-cases.json')


def qualify_linked_writer(folder,shards):
    require(1<=shards<=8,'writer corpus supports one to eight workers')
    with ProcessPoolExecutor(max_workers=shards) as executor:
        receipts=list(executor.map(writer_shard,[folder]*shards,range(shards),[shards]*shards))
    results=[json.loads(Path(row['path']).read_text()) for row in receipts]
    common={key:value for key,value in results[0].items() if key!='cases'}
    require(all({key:value for key,value in result.items() if key!='cases'}==common for result in results),
            'writer shards disagree about linked evidence')
    cases=[case for result in results for case in result['cases']]
    require(len(cases)==len({case['name'] for case in cases}),'writer shards are not disjoint')
    merged=folder/'linked-writer-results.json'
    merged.write_text(json.dumps(dict(common,cases=cases),indent=2)+'\n')
    build=json.loads((folder/'build-on/result.json').read_text())
    receipt=folder/'linked-writer.json'
    receipt.write_text(json.dumps(dict(schema='s22plus-linked-timing-logm-cases-v1',
        elf=build['elf'],loader=build['loader'],results=pin(merged),shards=receipts),indent=2)+'\n')
    return receipt


def verify_pair(folder, writer_cases):
    folder = Path(folder).resolve()
    # The caller can run the existing linked-writer corpus before pair packaging.
    # Bind its executable and configuration to the candidate below.
    writer_cases = Path(writer_cases).resolve()
    writer = json.loads(writer_cases.read_text())
    require(pin(writer['results']['path'])==writer['results'],'writer corpus bytes differ')
    results = {mode:check_arm(folder,mode,Path(writer['results']['path'])) for mode in ('off','on')}
    require(writer['loader']==results['on'][0]['loader'] and writer['elf']==results['on'][0]['elf'],
            'writer qualification belongs to another executable')
    off, on = results['off'], results['on']
    require(off[2]==on[2] and off[3]==on[3], 'executable bytes or data placement differs')
    for key in ('configuration','extents','runtime_symbols','retained_fdt','original_a'):
        require(off[0][key]==on[0][key], 'pair inputs not identical: '+key)
    require(off[0]['kernel']['sha256']==on[0]['kernel']['sha256']
            and off[0]['marker']!=on[0]['marker'],'kernel or fresh arm identity differs')
    pair = dict(schema='s22plus-timing-pair-h0-v1',masked_loader_sha256=hashlib.sha256(off[2]).hexdigest(),
                data_only_spans=off[3],vendor_kernel_sha256=off[0]['kernel']['sha256'],
                retained_fdt=off[0]['retained_fdt'],source=pin(__file__),device_actions=0,
                arms={mode:dict(loader=build['loader'],elf=build['elf'],marker=build['marker'])
                      for mode,(build,_,_,_,_) in results.items()},
                physical_counter_access_proved=False)
    (folder/'pair.json').write_text(json.dumps(pair,indent=2)+'\n')
    for mode,(build,_,_,_,tested) in results.items():
        out = folder/f'qualify-{mode}'
        out.mkdir(mode=0o700)
        result=dict(status='PASS_H0_LOADER_TIMING_PAIR_ARM',loader_sha256=build['loader']['sha256'],
                    timing_control=build['timing_control'],pair=pin(folder/'pair.json'),
                    actual_arm64_guard=tested,actual_entry=pin(folder/f'vm-{mode}/result.json'),
                    source=pin(__file__),source_pins=[pin(p) for p in (
                        arm64.__file__,arm64.shared.__file__,builder.__file__,timing.__file__,
                        profile.__file__,snapshot_model.__file__,builder.COMMON/'prepare.py')],
                    logm_configuration=build['logm_control']['configuration'],
                    linked_writer=pin(writer_cases),report_rejection_cases_per_el=5,device_actions=0)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS_H0_LOADER_TIMING_PAIR_ARM off/on with identical normalized ARM64 code')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args()
    folder=args.folder.resolve()
    verify_pair(folder,qualify_linked_writer(folder,args.workers))
