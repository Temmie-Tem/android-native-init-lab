"""One fixed offline hello transaction, exact successful state, no authority."""
import hashlib
import json
from pathlib import Path

import s22plus_debian_download_v1 as previous
from s22plus_native_records_v3 import read,require,verify

ROOT=previous.ROOT
NAMESPACE='p462'
VERSION='v0.23.0-rc.0'
POLICY='docs/operations/S22PLUS_DEBIAN_PACKAGE_V1.md'
HISTORY_SELECTION='post-autoboot-p461-package-v1'
DURABLE_DOMAIN=b'S22PLUS-FYG8-DEBIAN-PACKAGE-DURABLE-v1'
DURABLE_REVISION=10
EXPECTED_MOUNT_COUNT=34
FILES=Path(__file__).with_name('s22plus_debian_package_files_v1.json')
SIZE,IDLE=previous.SIZE,previous.IDLE
PACKAGE_FAULTS={'package-install-error':1,'package-command-timeout':2,'package-wrong-output':3,
    'package-sync-failure':4,'package-repeat-intent':5,'package-orphan-child':6,'package-transaction-remnant':7}
PACKAGE_ROOT_CASES=('package-first-existing','package-first-status','package-first-remnant','package-second-missing',
    'package-second-changed','package-second-linked','package-second-mode','package-second-status',
    'package-second-status-old','package-second-info','package-second-remnant','package-second-foreign',
    'package-second-no-install-proof')
RUNTIME_FAULTS=dict(previous.RUNTIME_FAULTS,**PACKAGE_FAULTS)
ROOT_CASES=previous.ROOT_CASES+PACKAGE_ROOT_CASES
FIRST_PHASE_FAULTS=previous.FIRST_PHASE_FAULTS+tuple(PACKAGE_FAULTS)
config_path,path,schedule=previous.config_path,previous.path,previous.schedule
programs,seal,decode=previous.programs,previous.seal,previous.decode
PRIOR=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-package-p462-h0-20261026-1/p461-expectations.json'),
    size=4542,sha256='bb6f4a6502fbc683b2d63576a840a3f1d2c44e95d1da9a4032e7a74699c1569b')


def declaration(run):
    return dict(previous.declaration(run),initial_mount_count=EXPECTED_MOUNT_COUNT,
        durable_revision=DURABLE_REVISION)


def package_declaration():
    data=read(FILES)
    require(data['schema']=='s22plus-debian-package-files-v1' and
        (data['package'],data['version'],data['architecture'])==('hello','2.10-5','arm64') and
        len(data['rows'])==54 and sum(r['existing'] for r in data['rows'])==2,
        'fixed package effects differ')
    return dict(schema='s22plus-debian-package-v1',package='hello',version='2.10-5',architecture='arm64',
        archive_path='/usr/local/lib/lab-offline/hello.deb',
        archive=data['programs']['usr/local/lib/lab-offline/hello.deb'],
        effects_sha256=hashlib.sha256(FILES.read_bytes()).hexdigest(),
        added_entries=52,replaced_files=2,install_phase=1,verify_phase=2,
        maximum_installations=1,workload_budget_ms=30000,
        function_output='S22_PACKAGE_FUNCTION\n',success_retains_package=True,
        failure_may_retain_partial_state=True,automatic_package_repair=False,
        network=False,maintainer_scripts=False,activated_triggers=False)


def header():
    package_declaration();data=read(FILES)
    return effect_header(data,program_paths=('usr/bin/dpkg','usr/bin/dpkg-deb','usr/bin/dpkg-split',
        'usr/local/lib/lab-offline/hello.deb'),function_path='usr/bin/hello',added=52,budget=30000)


def effect_header(data,*,program_paths,function_path,added,budget,base_added=0):
    """One encoder for the predeclared before/after package state."""
    lines=['#ifndef S22PLUS_DEBIAN_PACKAGE_SEAL_V1_H','#define S22PLUS_DEBIAN_PACKAGE_SEAL_V1_H',
        f'#define PK_ROWS {len(data["rows"])}U',f'#define PK_ADDED {added}U',f'#define PK_BUDGET_MS {budget}U',
        'struct pk_file {const char *path; unsigned mode,existing; uint64_t size,before_size; uint8_t sha[32],before_sha[32];};',
        'static const struct pk_file pk_files[]={']
    def sha(value):return '{'+','.join(map(str,bytes.fromhex(value) if value else bytes(32)))+'}'
    for r in data['rows']:
        lines.append('{'+json.dumps(r['path'])+','+str(r['mode']|(0o040000 if r['kind']=='d' else 0o100000))+','+
            str(int(r['existing']))+','+str(r['size'])+'ULL,'+str(r.get('before_size',0))+'ULL,'+
            sha(r['sha256'])+','+sha(r.get('before_sha256'))+'},')
    lines+=['};','struct pk_program {const char *path; uint64_t size; uint8_t sha[32];};',
        'static const struct pk_program pk_programs[]={']
    for path in program_paths:
        r=data['programs'][path];lines.append('{'+json.dumps('/'+path)+','+str(r['size'])+'ULL,'+sha(r['sha256'])+'},')
    function=next(r for r in data['rows'] if r['path']==function_path)
    lines+=['};','static const struct pk_program pk_hello={'+json.dumps('/'+function_path)+','+
        str(function['size'])+'ULL,'+sha(function['sha256'])+'};']
    if base_added:lines.append(f'#define PK_BASE_ADDED {base_added}U')
    lines.append('#endif')
    return ('\n'.join(lines)+'\n').encode()


def history():
    record=read(verify(PRIOR));closed=read(verify(record['closed']));terminal=read(verify(record['terminal']))
    require(record['schema']=='s22plus-p461-final-producer-expectations-v1' and record['device_actions']==0 and
        record['post_android_retention_proved'] is False and record['current_clean_state_proved'] is False and
        record['expected_post_shutdown_mount_count']==record['source_mount_count']+4==EXPECTED_MOUNT_COUNT and
        closed['terminal_state']==terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        closed['current_android_terminal']==record['terminal'] and
        terminal['debian_autoboot']['automatic_download_return_proved'] is True and
        terminal['debian_autoboot']['cron_configuration_retired'] is True,
        'P461 final producer/return basis differs')
    writer=read(verify(record['writer_build']));verify(record['source']);verify(record['operation']);verify(record['source_snapshot'])
    require(writer['namespace']==previous.NAMESPACE and writer['version']==previous.VERSION and
        [(x['phase'],x['kind']) for x in record['files']]==[(p,k) for p in (1,2) for k in ('early','runtime')]+[(2,'cron')],
        'P461 expected file selection differs')
    rows=[]
    for row in record['files']:
        expected=previous.path(writer['run_id']) if row['kind']=='cron' else previous.previous.previous.reboot.paths(writer['run_id'],row['phase'])[row['kind']]
        data=verify(row['source'],maximum=16384).read_bytes()
        require(row['path']==expected and row['mode']==0o100600 and row['uid']==row['gid']==0 and row['nlink']==1 and
            row['size']==len(data) and row['sha256']==hashlib.sha256(data).hexdigest() and
            row['source_kind']=='AUTHENTICATED_FINAL_PRODUCER_SNAPSHOT' and row['post_android_retention_proved'] is False,
            'P461 expected bytes or metadata differs')
        rows.append({k:row[k] for k in ('path','mode','uid','gid','nlink','size','sha256','source')})
    return rows
