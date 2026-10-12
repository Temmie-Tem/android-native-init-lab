"""One fixed root-child log calibration on the proved native drain carrier."""
import hashlib
import re

import s22plus_root_console_v1 as wire
import s22plus_debian_early_profile_v1 as early
import s22plus_native_log_protocol_v1 as protocol
from s22plus_native_records_v3 import read,require,verify

ROOT=early.ROOT
prior_inputs=early.prior_inputs
PROFILE='thermal-v3-reconnect-ufs-drain-log-calibration-v1'
SCHEMA='s22plus-native-log-calibration-v1'
OPERATION='log-calibrate'
SELECTION='log-calibration'
POLICY='docs/operations/S22PLUS_NATIVE_LOG_CALIBRATION_V1.md'
LOGGER=early.LOGGER
CASES={'normal':(7,1),'insert-error':(3,1),'binding-missing':(4,1),'logger-off':(2,0),
    'backend-absent':(6,1),'backend-missing':(6,1),'existing':(1,0),'bad-module':(1,0),'alias-exists':(1,0)}


def vm_results(receipt,binding,run,key):
    vm=read(verify(receipt));physical=read(verify(vm['physical_build']));virtual=read(verify(vm['virtual_build']))
    require(vm['schema']=='s22plus-native-log-vm-h0-v1' and vm['status']=='PASS' and vm['device_actions']==0 and
        physical['virt'] is False and virtual['virt'] is True and physical['ab_identical'] is True and
        virtual['ab_identical'] is True and physical['run_id_hex']==virtual['run_id_hex']==run and
        physical['sources']==virtual['sources'],'VM helper provenance differs')
    for field in ('helper','module'):
        require(all(physical[field][k]==binding[field][k] for k in ('size','sha256')),'VM physical input differs')
        verify(physical[field]);verify(virtual[field])
    require(all(physical['key'][k]==virtual['key'][k]==key[k] for k in ('size','sha256')) and
        physical['header']['sha256']==virtual['header']['sha256'] and
        physical['module']['sha256']==virtual['module']['sha256'],'VM seal/key/module differs')
    for row in (physical,virtual):
        for field in ('key','header','second'):verify(row[field])
        require(verify(row['helper']).read_bytes()==verify(row['second']).read_bytes(),'VM A/B helper differs')
        for receipt in row['sources'].values():verify(receipt)
    verify(vm['source'])
    for receipt in vm['tools'].values():verify(receipt,maximum=128*1024**2)
    require(len(vm['cases'])==len(CASES) and {c['case'] for c in vm['cases']}==set(CASES),'VM case set differs')
    for value in vm['cases']:
        name=value['case'];stage,attempts=CASES[name]
        serial=verify(value['serial']).read_bytes().replace(b'\r\n',b'\n')
        stdout=verify(value['stdout']).read_bytes()
        require(stdout==b'\n'.join(line for line in serial.splitlines() if line.startswith(b'LC1_'))+b'\n' and
            serial.count(b'LC_VM_BEGIN\n')==serial.count(b'LC_VM_EXIT status=0\n')==1 and
            b'reboot: Power down' in serial,'VM producer transcript differs')
        decoded=protocol.decode(stdout,b'',key=verify(key,maximum=32).read_bytes(),
            run=bytes.fromhex(run),helper=virtual['helper']['sha256'])
        require(value['status']=='PASS' and value['proof']==decoded and value['helper']==virtual['helper'] and
            value['run_id_hex']==run and value['device_actions']==0 and value['disk_unchanged'] is True and
            value['disk_before']==value['disk_after'] and decoded['live_pair_proved']==(name=='normal') and
            decoded['measurements']['stage']==stage and
            decoded['measurements']['attempted']==decoded['measurements']['returned']==attempts,
            'VM result does not rederive from actual helper bytes')
        require((b'LC_VM_ALIAS preserved=sentinel\n' if name=='alias-exists' else b'LC_VM_ALIAS absent=1\n') in serial,
            'VM alias ownership differs')
        if name=='logger-off':require(b'LC_VM_LOGGER_MODE=off\n' in serial,'VM ring-disable fault absent')
    return vm


def image_binding(image):
    value=image['log_calibration']
    require(image['profile']==PROFILE and re.fullmatch('[0-9a-f]{32}',image['run_id_hex']) and
        set(value)=={'helper','module','build','logger','backend_maximum','retained_ram_only','persistent_data_writes'} and
        value['logger']==LOGGER and value['backend_maximum']==protocol.MAXIMUM and
        value['retained_ram_only'] is True and value['persistent_data_writes'] is False,
        'log calibration binding differs')
    require(value['module']['size']==LOGGER['size'] and value['module']['sha256']==LOGGER['sha256'],
        'stock logger identity differs')
    for field in ('helper','module'):verify(value[field],maximum=4*1024**2)
    built=read(verify(value['build']))
    require(built['schema']=='s22plus-native-log-helper-h0-v1' and built['virt'] is False and
        built['run_id_hex']==image['run_id_hex'] and built['helper']==value['helper'] and built['module']==value['module'] and
        built['ab_identical'] is True and built['device_actions']==0 and
        all(built['key'][k]==image['key'][k] for k in ('size','sha256')) and image['key']['size']==32,
        'physical helper does not join the selected artifact')
    qualified=read(verify(image['qualification']))
    require(qualified['image']=={k:v for k,v in image.items() if k!='qualification'},'calibration qualification differs')
    abi=qualified['logger_abi'];kernel=read(verify(qualified['builder_result']))['image']
    require(set(abi)=={'kernel','module','imports','providers','matched'} and abi['module']==value['module'] and
        {k:abi['kernel'][k] for k in ('size','sha256')}==kernel and abi['matched'] is True,
        'logger/kernel ABI proof differs')
    verify(abi['kernel'],maximum=128*1024**2)
    imports=[line.split() for line in verify(abi['imports'],maximum=65536).read_text().splitlines()]
    require(len(imports)==71 and all(len(row)==2 for row in imports) and len({row[1] for row in imports})==71,
        'logger imports are incomplete or duplicated')
    required={symbol:(crc.lower().removeprefix('0x').lstrip('0') or '0') for crc,symbol in imports}
    require(required==abi['providers'],'logger import/provider CRCs differ')
    vm_results(qualified['vm'],value,image['run_id_hex'],image['key'])
    return value


class Profile:
    RESULT_KEY='log_calibration'
    MUTATES=True  # One module insertion and bounded retained-RAM marker writes.
    SETTLE_SECONDS=0
    OBSERVATION_SECONDS=60
    ADMISSION_SECONDS=25

    def __init__(self,image):
        self.binding=image_binding(image)
        self.key=verify(image['key'],maximum=32).read_bytes();self.run=bytes.fromhex(image['run_id_hex'])
        self.BODY=wire.command(('exec /s22-log-calibration calibrate '+image['run_id_hex']).encode(),
            cwd=b'/s22-root-work',timeout_ms=20000)

    def project(self,stdout,stderr,terminal,*,requested):
        result=dict(schema=SCHEMA,status='NO_PROOF',requested=requested,
            stdout=dict(size=len(stdout),sha256=hashlib.sha256(stdout).hexdigest()),
            stderr=dict(size=len(stderr),sha256=hashlib.sha256(stderr).hexdigest()))
        if not requested:return dict(result,reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        if terminal is None or terminal[:4]!=(5,0,0,0) or terminal[4]!=len(stdout)+len(stderr) or terminal[5]!=0:
            return dict(result,reason='CALIBRATION_COMMAND_INCOMPLETE')
        try:
            value=protocol.decode(stdout,stderr,key=self.key,run=self.run,helper=self.binding['helper']['sha256'])
        except (ValueError,UnicodeError,IndexError) as error:return dict(result,reason=str(error))
        return dict(result,**value)
