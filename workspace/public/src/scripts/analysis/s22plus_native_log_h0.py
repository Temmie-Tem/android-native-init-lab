"""Reproducible fixed logger helper; host work only, no device discovery."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_ext4_h0 as compiler
import s22plus_native_output_drain_build_v1 as carrier
import s22plus_memory_manifest_v1 as memory
import s22plus_debian_early_profile_v1 as early
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

NATIVE=ROOT/'workspace/public/src/native-init'
PROTOCOL=ROOT/'workspace/public/src/debian/s22plus_initramfs_h0/early-protocol.h'
LOGGER=early.LOGGER
RELEASE='5.10.226-android12-9-30958166-abS906NKSS7FYG8'
MODEL='Samsung G0Q PROJECT (board-id,12)'
SOURCE_FILES=(Path(__file__),NATIVE/'s22plus_native_log_calibration_v1.c',
    NATIVE/'s22plus_fyg8_max77705_result_parser.inc.c',
    NATIVE/'s22plus_fyg8_logger_binding_v1.h',PROTOCOL)
FLAGS=('-std=c11','-static','-Os','-fno-ident','-ffunction-sections','-fdata-sections',
    '-Wl,--gc-sections','-Wl,--build-id=none','-Wall','-Wextra','-Werror',
    '-Wno-unused-function','-Wno-unused-const-variable')


def native_key(expected):
    _,sources=carrier.shared.reference_inputs()
    matches=re.findall(rb'static const uint8_t p328_auth_key\[P328_AUTH_KEY_SIZE\] = \{ ([^}]+) \};',
        sources[carrier.shared.packager.RUNTIME_INCLUDE_NAME])
    require(len(matches)==1,'fixed native key declaration differs')
    value=bytes(int(x.strip().removesuffix(b'U'),16) for x in matches[0].split(b','))
    require(carrier.packaging.identity(value)==expected,'fixed native key identity differs')
    return value


def module():
    v=memory.vendor
    raw=memory.base.stable(ROOT/v.DEFAULT_VENDOR_RAMDISK,
        dict(size=v.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=v.EXPECTED_VENDOR_RAMDISK_SHA256))
    raw=memory.boot_verify.decompress_lz4_stream_python(raw,maximum=128*1024**2)
    require(len(raw)==v.EXPECTED_VENDOR_NEWC_SIZE,'vendor archive size differs')
    entries=memory.boot_verify.parse_newc(raw)
    require(len({e.name for e in entries})==len(entries),'duplicate vendor member')
    selected=[e for e in entries if e.name=='lib/modules/'+LOGGER['name']]
    require(len(selected)==1,'stock logger is absent')
    entry=selected[0]
    require((entry.mode,entry.uid,entry.gid,entry.nlink)==(0o100644,0,0,1) and
        len(entry.data)==LOGGER['size'] and hashlib.sha256(entry.data).hexdigest()==LOGGER['sha256'],
        'stock logger bytes or metadata differ')
    return entry.data


def seal(run,key):
    require(re.fullmatch('[0-9a-f]{32}',run) and len(key)==32,'helper run/key identity differs')
    def array(name,data):return 'static const uint8_t '+name+'['+str(len(data))+']={'+','.join(str(x) for x in data)+'};\n'
    return (array('early_key',key)+array('early_run',bytes.fromhex(run))+
        array('lc_module_hash',bytes.fromhex(LOGGER['sha256']))+
        'static const char lc_run[]='+json.dumps(run)+';\n'+
        'static const char lc_release[]='+json.dumps(RELEASE)+';\n'+
        'static const char lc_model[]='+json.dumps(MODEL)+';\n'+
        '#define LC_MODULE_SIZE '+str(LOGGER['size'])+'ULL\n').encode()


def sources():return {str(p.relative_to(ROOT)):pin(p) for p in SOURCE_FILES}


def build(out,run,key,*,virt=False):
    out=private_path(ROOT,out,exists=False);require(not out.exists(),'fresh helper build required')
    out.mkdir(mode=0o700,parents=True)
    before=sources()
    for name,raw in (('key',key),('log-calibration-seal.h',seal(run,key)),('s22-log-module.ko',module())):
        path=out/name;path.write_bytes(raw);path.chmod(0o400)
    cc=shutil.which('aarch64-linux-gnu-gcc');require(cc is not None,'ARM64 compiler absent')
    tool=compiler.compiler_identity(cc)
    commands=[]
    for side in ('a','b'):
        command=[cc,*FLAGS,*(['-DLC_VM'] if virt else []),'-I',out,'-I',NATIVE,'-I',PROTOCOL.parent,
            NATIVE/'s22plus_native_log_calibration_v1.c','-o',out/('helper-'+side)]
        commands.append([str(x) for x in command])
        compiler.run(command,cwd=out,stdout=out/('compile-'+side+'.log'))
    require(before==sources() and tool==compiler.compiler_identity(cc),'helper source/compiler changed')
    value=dict(schema='s22plus-native-log-helper-h0-v1',run_id_hex=run,virt=virt,key=pin(out/'key',maximum=32),
        header=pin(out/'log-calibration-seal.h'),module=pin(out/'s22-log-module.ko'),sources=before,
        compiler=tool,commands=commands,helper=compiler.tool_identity(out/'helper-a'),
        second=compiler.tool_identity(out/'helper-b'),ab_identical=True,device_actions=0)
    require(verify(value['helper']).read_bytes()==verify(value['second']).read_bytes(),'helper A/B bytes differ')
    publish(out/'result.json',value)
    return audit(out,run,key,virt=virt)


def audit(out,run,key,*,virt=False):
    out=private_path(ROOT,out);value=read(out/'result.json')
    require(value['schema']=='s22plus-native-log-helper-h0-v1' and value['run_id_hex']==run and
        value['virt'] is virt and value['ab_identical'] is True and value['device_actions']==0 and
        value['sources']==sources(),'helper construction identity differs')
    require(verify(value['header']).read_bytes()==seal(run,key) and verify(value['key'],maximum=32).read_bytes()==key and
        value['module']['size']==LOGGER['size'] and value['module']['sha256']==LOGGER['sha256'],
        'helper seal/logger input differs')
    verify(value['module'])
    binary=verify(value['helper']).read_bytes()
    require(binary==verify(value['second']).read_bytes() and compiler.tool_identity(value['helper']['path'])==value['helper'],
        'helper A/B or ELF identity differs')
    symbols=subprocess.check_output(['aarch64-linux-gnu-nm',value['helper']['path']])
    require(not any(re.search(rb'\b'+name+rb'$',symbols,re.M) for name in
        (b'mount',b'umount',b'ioctl',b'execve',b'reboot',b'fs1_open_block',b'system',b'fork')),
        'helper contains an excluded control or storage path')
    require(not any(path in binary for path in (b'/dev/block',b'/dev/mem',b'/s22-root/',b'/sys/power')),
        'helper contains an excluded data path')
    require((b'/lab/fault' in binary)==virt,'virtual helper identity differs')
    return value


def binding(out,run,key):
    value=audit(out,run,key)
    return dict(helper=value['helper'],module=value['module'],build=pin(Path(out)/'result.json'),
        logger=LOGGER,backend_maximum=4*1024**2,retained_ram_only=True,persistent_data_writes=False)
