"""Mainline RAM-only artifact admission, independent of vendor native profiles."""
from pathlib import Path
import hashlib
import json
import re
import sys

from s22plus_native_records_v3 import pin,publish,read,require,verify
import s22plus_boot_only_f1_transport as transport
import s22plus_boot_verify as boot

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src'))
from mainline.s22plus_canary_h0 import verify as codec

PROFILE='mainline-ram-v1'
OPERATION='mainline-ram'
SELECTION='mainline-evidence'
POLICY='docs/operations/S22PLUS_MAINLINE_RAM_V1.md'
REVIEW='workspace/public/src/device-action/bindings/s22plus_mainline_post_la002_v1_review.json'
NAMESPACE='ml001'
VERSION='mainline-ram-1'
SECONDS=1800
OBSERVATION_NS=120_000_000_000
TASK_SCHEMA='s22plus-mainline-task-v1'
REVIEW_SCHEMA='s22plus-mainline-ram-review-v1'
REVIEW_SCOPE='MAINLINE_RAM_F1_CAPABILITY'


def unchanged(receipt,maximum=128*1024*1024):
    from s22plus_native_task_v3 import unchanged as cached
    cached(receipt,maximum=maximum)
    return Path(receipt['path'])


def image_binding(image,*,artifact_bytes=False):
    keys={'schema','profile','namespace','version','run_id_hex','ap','member','key','qualification','runtime_sources'}
    if 'retained_marker' in image:keys.add('retained_marker')
    require(set(image)==keys and image['schema']=='s22plus-mainline-image-v1' and image['profile']==PROFILE and
            image['namespace']==NAMESPACE and image['version']==VERSION and
            re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'mainline image shape differs')
    qualified=read(unchanged(image['qualification']))
    require(set(qualified)=={'schema','status','image','package','loader','init_manifest','entry_review',
                            'loader_tests','entry_tests','device_actions'} and
            qualified['schema']=='s22plus-mainline-qualification-v1' and
            qualified['status']=='PASS_H0_MAINLINE_CANDIDATE' and qualified['device_actions']==0 and
            qualified['image']=={k:v for k,v in image.items() if k!='qualification'},'mainline qualification differs')
    package=read(unchanged(qualified['package']));loader=read(unchanged(qualified['loader']))
    manifest=read(unchanged(qualified['init_manifest']));review=read(unchanged(qualified['entry_review']))
    require(package['status']=='H0_BOOT_V4_PACKAGED_NOT_DEVICE_ADMITTED' and package['activation'] is False and
            package['device_actions']==0 and package['loader_sha256']==loader['loader']['sha256'] and
            package['copies'][0]['ap']==image['ap'] and
            package['copies'][0]['boot']['sha256']==package['copies'][1]['boot']['sha256'] and
            package['copies'][0]['ap']['sha256']==package['copies'][1]['ap']['sha256'], 'mainline package join differs')
    require(loader['status']=='H0_LOADER_BUILT_RUNTIME_PLACEMENT_GUARDED' and loader['device_actions']==0 and
            loader['physical_entry']=='NOT_ADMITTED_H0_ONLY' and
            loader['initramfs_manifest']==qualified['init_manifest']['path'], 'mainline loader join differs')
    require(manifest['vm'] is False and manifest['status']=='H0_INITRAMFS_BUILT_NOT_DEVICE_AUTHORITY' and
            re.fullmatch('[0-9a-f]{64}',manifest['candidate_id']) and
            image['run_id_hex']==manifest['candidate_id'][:32] and manifest['port']==47649 and
            image['key']['path']==manifest['key_path'] and image['key']['size']==32, 'physical canary identity differs')
    key=unchanged(image['key'],32).read_bytes()
    identity=hashlib.sha256(json.dumps({'inputs':manifest['inputs'],'vm':False,
        'key_commitment':hashlib.sha256(key).hexdigest()},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(identity==manifest['candidate_id'],'key does not join the embedded canary identity')
    for record,status,field in [(qualified['loader_tests'],'PASS_H0_ACTUAL_ARM64_LOADER','qualification_sha256'),
                                (qualified['entry_tests'],'PASS_H0_QEMU_ACTUAL_EXCEPTION_LEVELS','entry_vm_sha256')]:
        value=read(unchanged(record))
        require(value['status']==status and value['loader_sha256']==loader['loader']['sha256'] and
                package[field]==record['sha256'] and value['device_actions']==0,'mainline actual-blob tests differ')
    require(review['status']=='PASS_H0_SOURCE_BOUND_LOADER_ENTRY_AND_BOOT_PACKAGE' and not review['findings'],
            'loader/package independent review absent')
    reviewed={r['path']:r for r in review['artifact_and_raw_evidence_pins']}
    for receipt in (qualified['loader'],qualified['package'],qualified['init_manifest'],qualified['loader_tests'],qualified['entry_tests']):
        key=str(Path(receipt['path']).relative_to(ROOT))
        require(key in reviewed and all(reviewed[key][k]==receipt[k] for k in ('size','sha256')),
                'candidate evidence was not covered by retained entry review')
    require(('retained_marker' in image)==('retained_marker' in loader)==('retained_marker' in loader['kernel']),
            'instrumented loader lacks its marker admission')
    if 'retained_marker' in image:
        marked=marker_binding(image,manifest,loader)
        receipts=[image['retained_marker'],marked['config'],marked['tests'],marked['entry_vm']]
        if 'hook_tests' in marked:receipts.append(marked['hook_tests'])
        for receipt in receipts:
            path=str(Path(receipt['path']).relative_to(ROOT))
            require(path in reviewed and all(reviewed[path][k]==receipt[k] for k in ('size','sha256')),
                    'retained marker evidence lacks exact independent coverage')
    for receipt in image['runtime_sources'].values():unchanged(receipt)
    require(image['runtime_sources']=={
        'loader':dict(path=loader['loader']['path'],size=loader['loader']['size'],sha256=loader['loader']['sha256']),
        'kernel':dict(path=loader['kernel']['image'],size=loader['kernel']['file_size'],sha256=loader['kernel']['sha256']),
        'init':pin(Path(manifest['init']['path']),maximum=4*1024*1024),
        'initramfs':manifest['initramfs'],'dtb':pin(Path(manifest['dtb']['path']))},'mainline runtime identity differs')
    require(image['runtime_sources']['init']['sha256']==manifest['init']['sha256'] and
            image['runtime_sources']['dtb']['sha256']==manifest['dtb']['sha256'],'canary measurements differ')
    if artifact_bytes:
        with transport.pin_boot_only_ap(Path(image['ap']['path']),label='mainline RAM candidate',
                expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as ap:
            require(transport.boot_only_member_receipt(ap,label='mainline RAM candidate')==image['member'],
                    'mainline AP member differs')
    return manifest


def marker_codec():
    # A stopped owner may probe historical USB evidence before selecting A.
    # Candidate-only code must be reviewed before import, and an unavailable
    # decoder is an ordinary failed candidate validation, never a new recovery
    # prerequisite or an uncaught import failure.
    from s22plus_mainline_task_v1 import capability
    capability(ROOT)
    try:
        from mainline.s22plus_canary_h0 import retained_marker
    except (ImportError,SyntaxError) as error:
        raise ValueError('reviewed marker codec is unavailable') from error
    return retained_marker


def marker_binding(image,manifest,loader):
    marker=marker_codec()
    value=read(unchanged(image['retained_marker']))
    fields={'schema','status','config','tests','entry_vm','device_actions'}
    require(set(value) in (fields,fields|{'hook_tests'}),'marker qualification fields differ')
    config=read(unchanged(value['config']))
    if marker.version(config) in (9,10):fields.add('hook_tests')
    require(set(value)==fields and
            value['schema']=='s22plus-mainline-marker-qualification-v1' and
            value['status']=='PASS_H0_MAINLINE_RETAINED_MARKER' and value['device_actions']==0,
            'marker qualification shape differs')
    require(value['config']==loader['retained_marker']['config'],'loader marker config differs')
    key=unchanged(image['key'],32).read_bytes()
    marker.validate(config,manifest['candidate_id'],key)
    tests=read(unchanged(value['tests']));vm=read(unchanged(value['entry_vm']))
    for result,status in ((tests,'PASS_H0_ACTUAL_RETAINED_MARKERS'),(vm,'PASS_H0_ACTUAL_EL_RETAINED_MARKERS')):
        require(result['status']==status and result['config']==value['config'] and
                result['loader_sha256']==image['runtime_sources']['loader']['sha256'] and
                result['kernel_sha256']==image['runtime_sources']['kernel']['sha256'] and
                result['device_actions']==0 and result['physical_retention_proved'] is False,
                'actual marker artifact tests differ')
    require(vm['qualification_sha256']==value['tests']['sha256'],'marker actual EL test input differs')
    if marker.version(config) in (9,10):
        probe_binding(config,tests,vm,image,value['hook_tests'])
    elif marker.version(config)==8:
        trace_binding(config,tests,vm,image)
    elif marker.c_stages(config):
        require(tests.get('mmu_on',{}).get('status')=='PASS_H0_ACTUAL_EARLY_C' and
                vm.get('mmu_on',{}).get('status')=='PASS_H0_ACTUAL_KERNEL_MMU_MARKERS' and
                tests['mmu_on']['kernel_sha256']==vm['mmu_on']['kernel_sha256']==
                    image['runtime_sources']['kernel']['sha256'],
                'C marker lacks actual C and MMU-on kernel qualification')
    if marker.version(config) in (3,4,5,6,7):
        require(vm['mmu_on'].get('post_paging_no_linear_alias_proved') is True and
                vm['mmu_on'].get('qualified_c_stages')==tests['mmu_on'].get('qualified_c_stages')==list(marker.c_stages(config)),
                'later C marker lacks post-paging no-map and two-site qualification')
    if marker.version(config) in (4,5,6,7):
        stages=list(marker.c_stages(config))
        cases=vm['mmu_on'].get('cases',[])
        require(vm['mmu_on'].get('late_fixmap_proved') is True and cases and
                all(r.get('late_context_stages')==r.get('no_linear_alias_stages')==stages and
                    r.get('late_fixmap_proved') is True and r.get('first_c_returned') is True and
                    r.get('mapping_slots_restored') is True for r in cases),
                'late marker lacks both contexts, aliases or cleanup')
        normal={r['case']:r for r in cases if r.get('case') in ('normal','normal-el1')}
        require(set(normal)=={'normal','normal-el1'} and
                normal['normal'].get('actual_c_el')==2 and normal['normal-el1'].get('actual_c_el')==1 and
                all(r.get('temporary_mapping_attribute_stages')==stages for r in normal.values()),
                'late marker lacks actual EL1/EL2 mapping attributes at both sites')
        if marker.version(config)==5:
            expected=[dict(stage=s,initial_task=True,boot_cpu=0,online_cpus=1,
                           preempt_count_low32=1,irq_masked=s==9) for s in stages]
            require(vm['mmu_on'].get('bootstrap_context_proved') is True and
                    all(r.get('bootstrap_contexts')==expected for r in cases),
                    'V5 marker lacks exact bootstrap task/CPU/preemption/IRQ context')
        if marker.version(config) in (6,7):
            layout=vm['mmu_on'].get('task_layout',{})
            compiler=tests['mmu_on'].get('layout_compiler',{})
            require(set(compiler)=={'path','sha256','version'} and
                    layout.get('status')=='PASS_H0_SAME_BUILD_TASK_LAYOUT' and
                    layout.get('config_sha256')==tests['mmu_on'].get('layout_config_sha256') and
                    re.fullmatch('[0-9a-f]{64}',str(layout.get('config_sha256'))) is not None and
                    layout.get('command',{}).get('compiler')=={k:compiler[k] for k in ('path','sha256')},
                    'init-thread marker lacks same-build layout toolchain/config binding')
            require(vm['mmu_on'].get('mapping_initramfs')==tests['mmu_on'].get('mapping_initramfs')==
                    image['runtime_sources'].get('initramfs') and image['runtime_sources'].get('initramfs') is not None,
                    'init-thread mapping fixture lacks the physical candidate initramfs')
            expected=[dict(stage=s,phase=phase,pid=1,initial_namespace_reaper=True,
                same_task_as_kernel_init_entry=True,init_task_pid=0,kthreadd_pid=2,boot_cpu=0,
                online_cpus=1,preempt_count_low32=0,irq_masked=False,system_state=1,late_selector=1)
                for s in stages for phase in ('entry','return')]
            require(vm['mmu_on'].get('init_thread_context_proved') is True and
                    all(r.get('init_thread_contexts')==expected for r in cases),
                    'init-thread marker lacks exact PID1 entry/return context and calibration')
    source=read(unchanged(loader['retained_marker']['kernel_source']))
    require(source['config']==value['config'] and source['init_manifest']['sha256']==
            pin(Path(loader['initramfs_manifest']))['sha256'],'kernel marker provenance differs')
    return value


def probe_binding(config,tests,vm,image,hook_ref):
    """Join the selected probe's catalog, contexts and persistent-gate proof."""
    from mainline.s22plus_canary_h0 import retained_probe_v10 as priority
    is_v10=config['schema']==priority.SCHEMA
    fixed=len(priority.FIXED) if is_v10 else 20
    sparse=priority.SPARSE_BASE if is_v10 else 20
    first=priority.FIXED.index('pre-basic-setup') if is_v10 else 0
    worker=priority.FIXED.index('phase-1-worker-enter') if is_v10 else 16
    last=priority.FIXED.index('post-async-sync') if is_v10 else 5
    actual=tests.get('mmu_on',{});mapped=vm.get('mmu_on',{})
    total=len(config['frames']);sparse_end=sparse+2*len(config['initcall_ordinals'])
    required=list(range(fixed))+list(range(sparse,sparse_end))
    require(actual.get('status')=='PASS_H0_ACTUAL_DEFERRED_PROBE_C' and
            mapped.get('status')=='PASS_H0_ACTUAL_KERNEL_MMU_DEFERRED_PROBE' and
            actual.get('kernel_sha256')==mapped.get('kernel_sha256')==image['runtime_sources']['kernel']['sha256'] and
            actual.get('declared_slots')==mapped.get('declared_slots')==total and
            actual.get('declared_span')==mapped.get('declared_span')==config['span'],
            'V9 lacks its actual writer and real worker MMU qualification')
    table=read(unchanged(actual['table']));entries=table.get('entries',[]);bounds=table.get('boundaries',[])
    require(table.get('status')=='PASS_H0_FINAL_PROBE_TABLE' and
            table.get('schema')=='s22plus-mainline-probe-table-v'+('10' if is_v10 else '9') and
            table.get('image')==image['runtime_sources']['kernel'] and
            table.get('dtb')==image['runtime_sources']['dtb'] and
            table.get('elf',{}).get('sha256')==actual.get('elf_sha256') and
            table.get('frame_array_matches') is True and
            table.get('regular_count')==len(entries)==config['initcall_count'] and
            table.get('selected_ordinals')==config['initcall_ordinals'] and
            table.get('node_paths')==config['node_paths'] and
            [r.get('ordinal') for r in entries]==list(range(len(entries))) and
            len(bounds)==9 and all(type(v) is int for v in bounds) and
            bounds[-1]-bounds[0]==4*len(entries) and
            table.get('counts_by_level')==[(b-a)//4 for a,b in zip(bounds,bounds[1:])],
            'V9 final table/catalog artifact identity differs')
    anchors=[r['ordinal'] for r in entries if 'boot_wait_for_devices' in r.get('functions',[])]
    require(len(anchors)==1 and anchors[0]+2<len(entries) and
            'sync_state_resume_initcall' in entries[anchors[0]+1]['functions'] and
            'deferred_probe_initcall' in entries[anchors[0]+2]['functions'] and
            config['initcall_ordinals']==sorted({(b-bounds[0])//4 for b in bounds[:-1]}|set(range(anchors[0],len(entries)))),
            'V9 sparse selection lacks its final-table anchor')
    layout=mapped.get('task_layout',{});compiler=actual.get('layout_compiler',{})
    require(set(compiler)=={'path','sha256','version'} and
            layout.get('status')=='PASS_H0_SAME_BUILD_TASK_LAYOUT' and
            layout.get('config_sha256')==actual.get('layout_config_sha256') and
            layout.get('command',{}).get('compiler')=={k:compiler[k] for k in ('path','sha256')} and
            mapped.get('mapping_initramfs')==actual.get('mapping_initramfs')==image['runtime_sources']['initramfs'] and
            mapped.get('post_paging_no_linear_alias_proved') is True and
            mapped.get('late_fixmap_proved') is True and mapped.get('pid1_and_worker_context_proved') is True,
            'V9 layout, physical initramfs or mapping context differs')
    cases=mapped.get('cases',[]);names={r.get('case') for r in cases}
    expected={'normal-el1','normal-el2','page-crossing','short-history','bad-header','header-map-full',
              'slot-map-full','drift-before','drift-commit','timing-el1','timing-el2'}
    if is_v10:expected|={'earliest-only-short-history','early-drift-before','early-drift-commit'}
    require(names==expected and len(cases)==len(expected),'probe real-MMU case set incomplete')
    samples=([0,1] if is_v10 else [])+[first,worker,last]
    attributes={'normal-el1':samples,'normal-el2':samples,'page-crossing':samples,
        'short-history':[0,1,first] if is_v10 else [0,5],
        'bad-header':[],'header-map-full':samples[1:],'slot-map-full':samples[1:],
        'drift-before':samples[:-2],'drift-commit':samples[:-1],'timing-el1':[],'timing-el2':[]}
    if is_v10:
        attributes.update({'earliest-only-short-history':[0],'early-drift-before':[0],
                           'early-drift-commit':[0,1]})
    for case in cases:
        timing=case['case'].startswith('timing-');early_drift=case['case'].startswith('early-drift-')
        drift=case['case'].startswith('drift-') or early_drift
        events=[0,1] if early_drift else samples[:-1] if drift else samples
        require(all(case.get(k) is True for k in ('real_mmu_boot','real_mapping_api','full_pre_free_init_traversal',
                'worker_dispatch_closed','catalog_refs_released','mapping_slots_restored',
                'header_and_outside_window_preserved','post_paging_no_linear_alias_proved',
                'incoming_fdt_captured_before_c_setup')) and case.get('physical_timing_proved') is False and
                case.get('counter_breakpoints_used') is (not timing) and
                case.get('actual_c_el')==(1 if case['case'] in ('normal-el1','timing-el1') else 2) and
                case.get('no_linear_alias_events')==([first,last] if timing else events) and
                case.get('temporary_mapping_attribute_events')==attributes[case['case']],
                'V9 context/lifetime, actual EL/mapping or timing claim differs')
        if timing:
            require(case.get('per_event_counts') is None and case.get('event_order') is None and
                    type(case.get('wall_seconds_between_boundaries')) in (int,float) and
                    case['wall_seconds_between_boundaries']>0,'V9 timing uses counters or lacks duration')
            continue
        counts=case.get('per_event_counts',[]);order=case.get('event_order',[])
        require(len(counts)==total and all(type(n) is int and n in (0,1) for n in counts) and
                len(order)==sum(counts) and len(set(order))==len(order) and
                set(order)=={i for i,n in enumerate(counts) if n}, 'V9 write cardinality differs')
        if not drift:
            require(all(counts[i]==1 for i in required) and
                    [e for e in order if sparse<=e<sparse_end]==list(range(sparse,sparse_end)),
                    'V9 body/worker/sparse traversal incomplete')
        else:
            require(counts[0]==counts[1 if early_drift else worker]==1 and
                    not any(counts[e] for e in (last-2,last-1,last)),
                    'V9 drift did not close subsequent writer calls')
            if early_drift:require(sum(counts)==2,'early drift did not stop later direct/worker recording')
        missing=case.get('fixture_catalog_unresolved',[])
        require(type(missing) is list and len(set(missing))==len(missing) and
                all(p in config['node_paths'] and p.startswith('/memory@') and p.count('/')==1 for p in missing) and
                case.get('fixture_catalog_resolved')==(None if early_drift else len(config['node_paths'])-len(missing)),
                'V9 fixture catalog lacks actual incoming-DTB lookup accounting')
        if is_v10:
            require(case.get('catalog_lookup_checked') is (not early_drift),
                    'V10 fixture overclaims an unchecked catalog')
            require(case.get('bootstrap_mark_returns')==[
                        dict(event=e,initial_task=True,preempt_count_low32=1,irq_masked=True) for e in (0,1)] and
                    len(case.get('early_no_alias_page_tables',[]))==1 and
                    all(type(r.get('walked_tables')) is int and 0<r['walked_tables']<4096 and
                        type(r.get('roots')) is list and len(r['roots'])==2 and
                        type(r.get('tcr')) is int and r['tcr']&63==r.get('lower_t0sz')==16 and
                        (r['tcr']>>14)&3==r.get('lower_tg0')==0
                        for r in case['early_no_alias_page_tables']),
                    'V10 bootstrap return or complete early-table alias proof missing')
        contexts=case.get('writer_contexts',[])
        require([(r.get('event'),r.get('phase')) for r in contexts]==[(e,p) for e in events for p in ('entry','return')] and
                all(r.get('boot_cpu')==0 and r.get('online_cpus')==1 and
                    (r.get('preempt_count_low32')==2 and r.get('irq_masked') is True and
                     r.get('system_state')==0 and r.get('late_selector')==r['event'] and
                     r.get('pid')==0 and r.get('initial_task') is True
                     if is_v10 and r['event'] in (0,1) else
                     r.get('preempt_count_low32')==1 and r.get('irq_masked') is False and
                     r.get('system_state')==1 and r.get('late_selector')==1 and
                     ((r.get('pid',0)>2 and r.get('initial_namespace_reaper') is False) if r['event']==worker else
                      (r.get('pid')==1 and r.get('initial_namespace_reaper') is True))) for r in contexts),
                'V9 lacks calibrated PID1/worker entry-return contexts')
    hooks=read(unchanged(hook_ref));hook_cases={r.get('name') for r in hooks.get('cases',[])}
    required_hooks={'preprepare-all-ops-inert','prepare-owned-once-and-held-refs',
        'context-hardirq-reject-before-dispatch','context-softirq-reject-before-dispatch',
        'context-nmi-reject-before-dispatch','context-multi-online-cpu-reject-before-dispatch',
        'context-wrong-cpu-reject-before-dispatch','first-entry-token-nested-retry-and-cross-phase-return',
        'null-missing-node-and-unknown-buckets','mapping-failure-consumes-entry-attempt',
        'disabled-recorder-owner-disarm-clears-gate','finish-balanced-references-after-disarm-outside-preempt',
        'postfree-real-init-range-unmapped-all-ops-noop','finish-without-arm-clears-prepared-gate',
        'normal-disarm-preserves-direct-pid1-later-milestones','setup-marker-once-no-token'}
    if is_v10:
        required_hooks|={'bootstrap-mark-restores-pre-scheduler-count',
            'early-late-marks-share-latch-and-priority-layout','early-header-drift-keeps-late-dispatch-closed',
            'tlmm-three-entry-observed-groups-and-first-owner','tlmm-exact-of-and-unresolved-catalog-rejection',
            'tlmm-first-entry-failed-map-is-consumed','tlmm-nested-entry-zero-token-no-donation',
            'tlmm-token-owner-and-encoding-rejection','tlmm-entry-phase-token-survives-phase-changes',
            'tlmm-classified-return-closes-group-no-future-marks','tlmm-inconsistent-global-phase-rejection',
            'tlmm-preprepare-postdisarm-postfree-inert','wrapper-return-class-and-ret-preservation',
            'wrapper-null-token-preserves-return-no-writes'}
        require(hooks.get('wrapper_inner_body_mocked_for_return_abi_cases') is True,
                'V10 wrapper mock boundary is not explicit')
    require(hooks.get('schema')=='s22plus-mainline-v'+('10' if is_v10 else '9')+'-independent-hook-instruction-review-v1' and
            hooks.get('status')=='PASS_H0_ACTUAL_LINKED_HOOK_LIFETIME_TOKENS' and
            hook_cases==required_hooks and len(hooks['cases'])==len(required_hooks) and
            all(hooks.get(k) is True for k in ('actual_kernel_instructions','preemption_count_restored_in_all_cases',
                                             'postfree_init_region_unmapped','cpu_state_mocked',
                                             'of_lookup_and_reference_apis_mocked','mapping_apis_mocked')) and
            hooks.get('real_mmu_translation_proved') is False and hooks.get('device_actions')==0,
            'V9 persistent hook/lifetime qualification incomplete')
    pins=hooks.get('input_pins',[])
    require(image['runtime_sources']['kernel'] in pins and table['elf'] in pins and
            any(p.get('sha256')==actual['layout_config_sha256'] and Path(p['path']).name=='.config' for p in pins),
            'V9 hook fixture used another kernel/layout')
    for receipt in pins:unchanged(receipt)
    for receipt in hooks['layout'].values():
        if type(receipt) is dict and set(receipt)=={'path','size','sha256'}:unchanged(receipt)


def trace_binding(config,tests,vm,image):
    """V8 has parameterized records and full traversal, not two-site evidence."""
    actual=tests.get('mmu_on',{});mapped=vm.get('mmu_on',{})
    count=config['initcall_count'];total=6+2*count
    require(actual.get('status')=='PASS_H0_ACTUAL_INITCALL_TRACE_C' and
            mapped.get('status')=='PASS_H0_ACTUAL_KERNEL_MMU_INITCALL_TRACE' and
            actual.get('kernel_sha256')==mapped.get('kernel_sha256')==image['runtime_sources']['kernel']['sha256'] and
            actual.get('declared_slots')==mapped.get('declared_slots')==total and
            actual.get('declared_span')==mapped.get('declared_span')==config['span'],
            'V8 trace lacks its actual parameterized writer and full-MMU qualification')
    table=read(unchanged(actual['table']))
    entries=table.get('entries',[]);bounds=table.get('boundaries',[])
    require(table.get('status')=='PASS_H0_FINAL_PREL32_TABLE' and
            table.get('regular_count')==len(entries)==count and
            table.get('image',{}).get('sha256')==actual['kernel_sha256'] and
            table.get('elf',{}).get('sha256')==actual.get('elf_sha256') and
            table.get('frame_array_matches') is True and
            [r.get('ordinal') for r in entries]==list(range(count)) and
            len(bounds)==9 and all(type(x) is int for x in bounds) and
            bounds[-1]-bounds[0]==4*count and
            table.get('counts_by_level')==[(b-a)//4 for a,b in zip(bounds,bounds[1:])] and
            all(r.get('entry_address')==bounds[0]+4*r['ordinal'] and
                type(r.get('level')) is int and 0<=r['level']<8 and
                bounds[r['level']]<=r['entry_address']<bounds[r['level']+1] and r.get('functions')
                for r in entries), 'V8 ordinal labels lack the actual final ELF table')
    layout=mapped.get('task_layout',{});compiler=actual.get('layout_compiler',{})
    require(set(compiler)=={'path','sha256','version'} and
            layout.get('status')=='PASS_H0_SAME_BUILD_TASK_LAYOUT' and
            layout.get('config_sha256')==actual.get('layout_config_sha256') and
            layout.get('command',{}).get('compiler')=={k:compiler[k] for k in ('path','sha256')} and
            mapped.get('mapping_initramfs')==actual.get('mapping_initramfs')==image['runtime_sources'].get('initramfs') and
            image['runtime_sources'].get('initramfs') is not None and
            mapped.get('init_thread_context_proved') is True and mapped.get('late_fixmap_proved') is True and
            mapped.get('post_paging_no_linear_alias_proved') is True,
            'V8 lacks current layout, physical initramfs, late mapping or no-alias proof')
    cases=mapped.get('cases',[])
    names={'normal-el1','normal-el2','page-crossing','short-history','bad-header','header-map-full',
           'slot-map-full','drift-before','drift-commit','timing-el1','timing-el2'}
    require(len(cases)==len(names) and {r.get('case') for r in cases}==names,
            'V8 full-loop normal/fault/timing fixture set differs')
    middle=6+2*(count//2);order=[0,1,2]+list(range(6,total))+[3,4,5]
    attrs={'normal-el1':[0,middle,5],'normal-el2':[0,middle,5],'page-crossing':[0,middle,5],
           'short-history':[0,5],'bad-header':[],'header-map-full':[middle,5],
           'slot-map-full':[middle,5],'drift-before':[0],'drift-commit':[0,middle]}
    for case in cases:
        label=case['case'];timing=label.startswith('timing-')
        samples=[(0,'entry'),(5,'return')] if timing else [(s,p) for s in (0,middle,5) for p in ('entry','return')]
        expected=[dict(event=s,phase=p,pid=1,initial_namespace_reaper=True,same_task_as_kernel_init_entry=True,
            init_task_pid=0,kthreadd_pid=2,boot_cpu=0,online_cpus=1,preempt_count_low32=0,
            irq_masked=False,system_state=1,late_selector=1) for s,p in samples]
        require(case.get('full_pre_free_init_traversal') is True and case.get('real_mmu_boot') is True and
                case.get('real_mapping_api') is True and case.get('mapping_slots_restored') is True and
                case.get('header_and_outside_window_preserved') is True and
                case.get('post_paging_no_linear_alias_proved') is True and
                case.get('no_linear_alias_events')==([0,5] if timing else [0,middle,5]) and
                case.get('temporary_mapping_attribute_events')==([] if timing else attrs[label]) and
                case.get('init_thread_contexts')==expected and
                case.get('actual_c_el')==(1 if label in ('normal-el1','timing-el1') else 2),
                'V8 actual context, alias, mapping attributes or cleanup differs')
        require(case.get('counter_breakpoints_used') is (not timing) and
                case.get('per_event_counts')==(None if timing else [1]*total) and
                case.get('event_order')==(None if timing else order) and
                case.get('physical_timing_proved') is False,
                'V8 traversal counts and timing claims are mixed')


def qualify(package_dir,loader_dir,output,*,loader_qualification,entry_vm,marker_qualification=None):
    """Revalidate existing immutable artifacts, without building or contacting a device."""
    package_dir,loader_dir,output=[Path(p).resolve() for p in (package_dir,loader_dir,output)]
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private qualification required')
    package=read(package_dir/'result.json');loader=read(loader_dir/'result.json')
    base=loader_dir.parent
    loader_tests=pin(Path(loader_qualification).resolve()/'result.json')
    entry_tests=pin(Path(entry_vm).resolve()/'result.json')
    require(package['qualification_sha256']==loader_tests['sha256'] and
            package['entry_vm_sha256']==entry_tests['sha256'],
            'explicit test receipts differ from the packaged qualification')
    manifest=read(Path(loader['initramfs_manifest']))
    ap=package['copies'][0]['ap']
    with transport.pin_boot_only_ap(Path(ap['path']),label='mainline H0 image',
            expected_size=ap['size'],expected_sha256=ap['sha256']) as bound:
        member=transport.boot_only_member_receipt(bound,label='mainline H0 image')
        compressed=transport.read_boot_only_member(bound,label='mainline H0 image')
    data=boot.decompress_lz4_stream_python(compressed,maximum=128*1024*1024)
    parsed=boot.parse_boot_v4(data)
    require(len(data)==96*1024*1024 and parsed.kernel==Path(loader['loader']['path']).read_bytes(),
            'actual AP does not contain qualified loader')
    runtime={'loader':pin(Path(loader['loader']['path']),maximum=128*1024*1024),
             'kernel':pin(Path(loader['kernel']['image']),maximum=128*1024*1024),
             'init':pin(Path(manifest['init']['path']),maximum=4*1024*1024),
             'initramfs':manifest['initramfs'],'dtb':pin(Path(manifest['dtb']['path']))}
    image=dict(schema='s22plus-mainline-image-v1',profile=PROFILE,namespace=NAMESPACE,version=VERSION,
        run_id_hex=manifest['candidate_id'][:32],ap=ap,member=member,key=pin(Path(manifest['key_path']),maximum=32),
        runtime_sources=runtime)
    if marker_qualification is not None:image['retained_marker']=pin(Path(marker_qualification).resolve())
    record=dict(schema='s22plus-mainline-qualification-v1',status='PASS_H0_MAINLINE_CANDIDATE',image=image,
        package=pin(package_dir/'result.json'),loader=pin(loader_dir/'result.json'),
        init_manifest=pin(Path(loader['initramfs_manifest'])),
        entry_review=pin(base/'review/independent-loader-entry-package-review-1.json'),
        loader_tests=loader_tests,entry_tests=entry_tests,device_actions=0)
    output.mkdir(mode=0o700,parents=True)
    image=dict(image,qualification=publish(output/'qualification.json',record))
    image_binding(image,artifact_bytes=True)
    return publish(output/'image.json',image)
