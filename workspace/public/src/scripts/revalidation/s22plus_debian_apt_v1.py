"""Fixed USB HTTPS APT transaction and one per-boot RAM clock handoff; no authority."""
import hashlib
import json
import ipaddress
from pathlib import Path

import s22plus_debian_package_v1 as previous
from s22plus_native_records_v3 import read,require,verify

ROOT=previous.ROOT
NAMESPACE='p463'
VERSION='v0.24.0-rc.0'
POLICY='docs/operations/S22PLUS_DEBIAN_APT_V1.md'
HISTORY_SELECTION='post-autoboot-p462-apt-v1'
DURABLE_DOMAIN=b'S22PLUS-FYG8-DEBIAN-APT-DURABLE-v1'
DURABLE_REVISION=11
EXPECTED_MOUNT_COUNT=38
FILES=Path(__file__).with_name('s22plus_debian_apt_files_v1.json')
SIZE,IDLE=previous.SIZE,previous.IDLE
config_path,path,schedule=previous.config_path,previous.path,previous.schedule
programs,seal,decode=previous.programs,previous.seal,previous.decode
APT_FAULTS={'apt-clock-missing':1,'apt-clock-wrong-boot':2,'apt-metadata-changed':3,
    'apt-download-changed':4,'apt-plan-extra-package':5,'apt-install-failed':6,'apt-orphan-child':7}
RUNTIME_FAULTS=dict(previous.previous.RUNTIME_FAULTS,**APT_FAULTS)
APT_ROOT_CASES=('apt-first-retained-hello-changed','apt-second-retained-hello-missing')
ROOT_CASES=previous.ROOT_CASES+APT_ROOT_CASES
FIRST_PHASE_FAULTS=previous.previous.FIRST_PHASE_FAULTS+tuple(APT_FAULTS)
PRIOR=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-apt-p463-h0-20261027-1/p462-expectations.json'),
    size=4510,sha256='3ba5060be41f063f8c52ca1fb127054db212f1335d53fda750bea55b46151bd7')
REPO='https://deb.debian.org/debian'
APT_HOME='/run/s22-apt'
FUNCTION_OUTPUT='/run/s22-apt/function\n`-- branch\n    `-- leaf\n'
PLAN=('Reading package lists...\nBuilding dependency tree...\nThe following NEW packages will be installed:\n'
    '  tree\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n'
    'Inst tree (2.2.1-1 Debian:13.7/stable [arm64])\nConf tree (2.2.1-1 Debian:13.7/stable [arm64])\n')


def declaration(run):
    return dict(previous.declaration(run),initial_mount_count=EXPECTED_MOUNT_COUNT,durable_revision=DURABLE_REVISION)


def package_declaration():
    data=read(FILES)
    require(data['schema']=='s22plus-debian-apt-files-v1' and
        (data['package'],data['version'],data['architecture'])==('tree','2.2.1-1','arm64') and
        len(data['rows'])==64 and sum(r['existing'] for r in data['rows'])==54,'fixed APT effects differ')
    return dict(schema='s22plus-debian-apt-v1',package='tree',version='2.2.1-1',architecture='arm64',
        archive_path=APT_HOME+'/cache/archives/tree_2.2.1-1_arm64.deb',archive=data['repository']['payload'],
        effects_sha256=hashlib.sha256(FILES.read_bytes()).hexdigest(),repository=data['repository'],
        added_entries=10,retained_entries=52,replaced_files=2,install_phase=1,verify_phase=2,
        maximum_installations=1,workload_budget_ms=90000,function_output=FUNCTION_OUTPUT,
        success_retains_package=True,failure_may_retain_partial_state=True,automatic_package_repair=False,
        network=True,maintainer_scripts=False,activated_triggers=False,
        acquisition_uid=42,acquisition_gid=65534,root_acquisition_fallback=False,
        apt_use_pty=False,clock_realtime_only=True,maximum_clock_handoffs_per_boot=1,
        host_network_method='shared',host_network_persistent=False)


def apt_config():
    # APT_CONFIG is read before Parts/main; no installed APT hook is inherited.
    return b'''Dir::Etc "/run/s22-apt/etc";
Dir::Etc::Parts "/run/s22-apt/etc/empty";
Dir::Etc::main "/run/s22-apt/etc/empty-main";
Dir::Etc::sourcelist "/run/s22-apt/etc/sources.list";
Dir::Etc::sourceparts "/run/s22-apt/etc/empty";
Dir::Etc::preferences "/run/s22-apt/etc/empty-main";
Dir::Etc::preferencesparts "/run/s22-apt/etc/empty";
Dir::Etc::Trusted "/usr/share/keyrings/debian-archive-keyring.gpg";
Dir::Etc::TrustedParts "/run/s22-apt/etc/empty";
Dir::State "/run/s22-apt/state";
Dir::State::status "/var/lib/dpkg/status";
Dir::State::extended_states "/run/s22-apt/state/extended_states";
Dir::State::lists "/run/s22-apt/lists";
Dir::Cache "/run/s22-apt/cache";
Dir::Cache::archives "/run/s22-apt/cache/archives";
Dir::Cache::pkgcache "";
Dir::Cache::srcpkgcache "";
Dir::Log "/run/s22-apt/log";
DPkg::Options { "--log=/run/s22-debian/package-dpkg.log"; };
Dpkg::Use-Pty "false";
APT::Architecture "arm64";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::Assume-Yes "true";
Acquire::Retries "0";
Acquire::Languages "none";
Acquire::PDiffs "false";
Acquire::By-Hash "false";
Acquire::GzipIndexes "true";
Acquire::CompressionTypes::Order { "xz"; };
Acquire::ForceIPv4 "true";
Acquire::Check-Date "true";
Acquire::Check-Valid-Until "true";
Acquire::https::Verify-Peer "true";
Acquire::https::Verify-Host "true";
Acquire::https::Timeout "10";
Acquire::IndexTargets::deb::DEP-11::DefaultEnabled "false";
'''


def header():
    package_declaration();data=read(FILES)
    programs=('usr/bin/dpkg','usr/bin/dpkg-deb','usr/bin/dpkg-split','usr/bin/apt-get',
        'usr/lib/apt/methods/http','usr/bin/sqv','usr/share/keyrings/debian-archive-keyring.pgp','usr/bin/ip')
    return previous.effect_header(data,program_paths=programs,function_path='usr/bin/tree',added=10,
        base_added=52,budget=90000)


def runtime_header(*,virt=False):
    data=read(FILES);repo=data['repository']
    from s22plus_native_root_inspect_profile_v1 import prior_inputs
    link=prior_inputs()[2]['link'];gateway=ipaddress.ip_interface(link['host_address']).ip
    network=ipaddress.ip_interface(link['device_address']).network
    if network.prefixlen>24:network=network.supernet(new_prefix=24)
    resolver=network.network_address+254 if virt else gateway
    def pin(name,row):
        return ('static const uint64_t '+name+'_size='+str(row['size'])+'ULL;\n'+
            'static const uint8_t '+name+'_sha[]={'+','.join(map(str,bytes.fromhex(row['sha256'])))+'};\n')
    return ('#ifndef S22PLUS_DEBIAN_APT_SEAL_V1_H\n#define S22PLUS_DEBIAN_APT_SEAL_V1_H\n'+
        'static const char ap_config[]='+json.dumps(apt_config().decode())+';\n'+
        'static const char ap_sources[]='+json.dumps('deb [arch=arm64 signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] '+REPO+' trixie main\n')+';\n'+
        'static const char ap_plan[]='+json.dumps(PLAN)+';\n'+
        'static const char ap_function_output[]='+json.dumps(FUNCTION_OUTPUT)+';\n'+
        'static const char ap_gateway[]='+json.dumps(str(gateway))+';\n'+
        'static const char ap_interface[]="usb0";\n'+
        'static const char ap_resolver[]='+json.dumps('nameserver '+str(resolver)+'\n')+';\n'+
        pin('ap_release',repo['release'])+pin('ap_index',repo['acquired_index'])+pin('ap_archive',repo['payload'])+
        '#endif\n').encode()


def assets(assets):
    assets=dict(assets);script=assets['qualify'];needle=b' health)\n'
    require(script.count(needle)==1,'APT forced-command insertion differs')
    commands=br''' apt-time-status)
  exec /run/s22-debian/hook apt-time-status
  ;;
 apt-time\ *)
  set -f
  IFS=' '
  set -- $SSH_ORIGINAL_COMMAND
  test "$#" = 5
  exec /run/s22-debian/hook "$@"
  ;;
'''
    assets['qualify']=script.replace(needle,commands+needle)
    return assets


def history():
    record=read(verify(PRIOR));closed=read(verify(record['closed']));terminal=read(verify(record['terminal']))
    require(record['schema']=='s22plus-p462-final-producer-expectations-v1' and record['device_actions']==0 and
        record['post_android_retention_proved'] is False and record['current_clean_state_proved'] is False and
        record['expected_post_shutdown_mount_count']==record['source_mount_count']+4==EXPECTED_MOUNT_COUNT and
        closed['terminal_state']==terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        closed['current_android_terminal']==record['terminal'] and
        terminal['debian_autoboot']['automatic_download_return_proved'] is True and
        terminal['debian_autoboot']['cron_configuration_retired'] is True and
        all(terminal['debian_autoboot'][k] is True for k in ('package_installation_proved',
            'package_function_proved','package_exact_reboot_retention_proved')),
        'P462 final producer/package/return basis differs')
    writer=read(verify(record['writer_build']));verify(record['source']);verify(record['operation']);verify(record['source_snapshot'])
    require(writer['namespace']==previous.NAMESPACE and writer['version']==previous.VERSION and
        [(x['phase'],x['kind']) for x in record['files']]==[(p,k) for p in (1,2) for k in ('early','runtime')]+[(2,'cron')],
        'P462 expected file selection differs')
    from s22plus_debian_reboot_v1 import paths
    rows=[]
    for row in record['files']:
        expected=previous.path(writer['run_id']) if row['kind']=='cron' else paths(writer['run_id'],row['phase'])[row['kind']]
        data=verify(row['source'],maximum=16384).read_bytes()
        require(row['path']==expected and row['mode']==0o100600 and row['uid']==row['gid']==0 and row['nlink']==1 and
            row['size']==len(data) and row['sha256']==hashlib.sha256(data).hexdigest() and
            row['source_kind']=='AUTHENTICATED_FINAL_PRODUCER_SNAPSHOT' and row['post_android_retention_proved'] is False,
            'P462 expected bytes or metadata differs')
        rows.append({k:row[k] for k in ('path','mode','uid','gid','nlink','size','sha256','source')})
    return rows
