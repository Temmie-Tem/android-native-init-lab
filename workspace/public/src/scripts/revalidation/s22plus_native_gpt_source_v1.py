"""Prospective sealed 32 GiB Android GPT commands over the admitted drain runtime.

H0 composition only. The live owner must authorize and journal each effect.
The original/proposed metadata are private inputs, never public C literals.
"""
from pathlib import Path

import s22plus_native_output_drain_source_v1 as previous
import s22plus_native_gpt_profile_v1 as gpt
from s22plus_native_records_v3 import read, read_bytes, require, verify

resident=previous.resident
ROOT,NATIVE,PROFILE=previous.ROOT,previous.NATIVE,previous.PROFILE
THERMAL_PROFILE,RECONNECT_PROFILE=previous.THERMAL_PROFILE,previous.RECONNECT_PROFILE
STORAGE_PROFILE,CONSOLE_PROFILE=previous.STORAGE_PROFILE,previous.CONSOLE_PROFILE
GPT_PROFILE='fyg8-native-android32-gpt-v1'
POLICY=ROOT/'docs/operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md'
CORE=NATIVE/'s22plus_native_gpt_core_v1.h'
ENDPOINT=NATIVE/'s22plus_native_gpt_io_v1.inc.c'
PROPOSAL=dict(path=str(ROOT/'workspace/private/outputs/s22plus-native-android32-gpt-proposal-h0-20260916-1/result.json'),
    size=3760,sha256='1acf0147026ca4dcc07008ba61f32660b65c9a455dc2ee640a554acde179362c')
SAMPLE_MAGIC,VIEW_MAGIC=previous.SAMPLE_MAGIC,previous.VIEW_MAGIC
helper_template,materialize_helper=previous.helper_template,previous.materialize_helper
provider_sources,provider_files=previous.provider_sources,previous.provider_files
core_source,sensor_map,wire_source=previous.core_source,previous.sensor_map,previous.wire_source


def proposal_inputs():
    value=read(verify(PROPOSAL))
    require(value['schema']=='s22plus-native-gpt-layout-construction-h0-v1'
        and value['status']=='PASS_H0_EXACT_LAYOUT_CONSTRUCTION' and value['device_effects']==0,
        'sealed GPT construction differs')
    sealed=gpt.vectors(dict(proposal=PROPOSAL,regions=value['regions'],layout=value['layout']))
    require(value['layout']['construction']=='resize-existing-native-32g-v1'
        and value['layout']['userdata_new_size_bytes']==32*1024**3
        and value['layout']['userdata_first_lba']==3726848
        and value['layout']['non_userdata_entries_preserved']==39,'sealed 32 GiB geometry differs')
    for key in ('source_close','source_proposal','source_terminal'):verify(value[key])
    return value,sealed


def runtime_input_receipt():
    value,_=proposal_inputs()
    return dict(proposal=PROPOSAL,regions=value['regions'],layout=value['layout'])


def render_commands(identity):
    _,vectors=proposal_inputs()
    raw=resident.common._read(CORE)+b'\n'
    for name,data in vectors.items():
        raw+=('static const uint8_t gpt1_'+name+'[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)))={\n'
            +','.join(str(byte) for byte in data)+'\n};\n').encode()
    raw+=('static const char gpt1_target_run_id[]="'+identity.run_id_hex+'";\n').encode()
    raw+=resident.replace(resident.common._read(ENDPOINT),
        b'#include "s22plus_native_gpt_core_v1.h"',b'/* The sealed core is embedded above. */')
    return raw


def render_display(identity,modules):
    raw=previous.render_display(identity,modules)
    main=b'int main(int argc,char **argv) {'
    dispatch=b'''
    if(argc==3 && !strcmp(argv[1],"--gpt-observe"))return gpt1_entry(GPT1_OBSERVE,argv[2]);
    if(argc==3 && !strcmp(argv[1],"--gpt-apply"))return gpt1_entry(GPT1_APPLY,argv[2]);
    if(argc==3 && !strcmp(argv[1],"--gpt-restore"))return gpt1_entry(GPT1_RESTORE,argv[2]);
    if(argc==3 && !strcmp(argv[1],"--gpt-after-reset"))return gpt1_entry_full(GPT1_OBSERVE,argv[2],1);
    if(argc==3 && !strcmp(argv[1],"--gpt-after-original-reset"))return gpt1_entry_full(GPT1_OBSERVE,argv[2],2);
    if(argc>1 && !strncmp(argv[1],"--gpt-",6))return 100;
'''
    return resident.replace(raw,main,render_commands(identity)+b'\n'+main+dispatch)


def profile_contract():
    value,_=proposal_inputs()
    return dict(previous.profile_contract(),gpt_profile=GPT_PROFILE,
        gpt_proposal_sha256=PROPOSAL['sha256'],gpt_native_size_bytes=value['layout']['native_size_bytes'],
        gpt_commands=['observe','apply','restore','after-reset','after-original-reset'],gpt_caller_payload=False,
        gpt_reset_geometry_read_bytes=8192,gpt_reset_geometry_export_bytes=216,
        gpt_changed_lbas=[62305272,62305279,3,1],gpt_write_retry=False,
        gpt_authority='separate reviewed owner and finite grant required')


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__),Path(gpt.__file__),CORE,ENDPOINT,POLICY}))
