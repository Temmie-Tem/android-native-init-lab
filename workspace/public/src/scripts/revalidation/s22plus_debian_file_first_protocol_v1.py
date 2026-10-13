"""Version-2 storage-first history; never a USB or unmount-return proof."""
from s22plus_debian_file_first_plan_v1 import DOMAIN,CLIENTS,STORAGE_COUNT
from s22plus_native_records_v3 import require
import s22plus_debian_integrated_protocol_v1 as preparation
import s22plus_debian_file_protocol_v1 as retained

HEADER,RECORD,MAXIMUM=retained.HEADER,retained.RECORD,retained.MAXIMUM


def parse_log(raw,run,module_names,boot):
    require(len(module_names)==STORAGE_COUNT+len(CLIENTS) and
        tuple(module_names[STORAGE_COUNT:])==CLIENTS and module_names[0]=='sec_log_buf',
        'storage-first module declaration differs')
    rows=preparation.events(raw,run,boot,start=1);expected=rows[:1]+[b'TARGET_GUARD_OK']
    for ordinal,name in enumerate(module_names[:STORAGE_COUNT],1):
        expected.append(f'MODULE_BEGIN ordinal={ordinal} name={name}'.encode())
        if name=='sec_log_buf':expected.append(b'LOGGER_BIND phase=0 error=0')
        expected.append(f'MODULE_DONE ordinal={ordinal} name={name}'.encode())
        if name=='qcom_spmi_pmic':expected.extend((b'PROVIDERS_BEGIN',b'PROVIDERS_READY mask=7'))
    expected.append(b'TERMINAL result=STORAGE_READY error=0')
    require(rows==expected,'storage-first preparation is incomplete')
    return dict(module_completions=STORAGE_COUNT)


def decode(data,**kwargs):return retained.decode(data,**kwargs,storage_first=True)
