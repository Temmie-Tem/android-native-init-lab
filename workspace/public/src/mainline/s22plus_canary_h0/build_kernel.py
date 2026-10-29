#!/usr/bin/env python3
"""Build the already prepared H0 kernel using private extracted build deps."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from prepare import digest, require, run

def marker_provenance(prepared_dir,kernel):
    import retained_marker as marker
    from prepare_marked import instrumented_head
    path=prepared_dir/'marker-source.json';text=(kernel/'arch/arm64/kernel/head.S').read_text()
    require(('s22_retained_' in text)==path.exists(),'partial marker source publication')
    if not path.exists():return None
    value=json.loads(path.read_text())
    for key in ('config','original_head','instrumented_head','init_manifest'):
        row=value[key];p=Path(row['path'])
        require(p.stat().st_size==row['size'] and digest(p)==row['sha256'],'marker source input changed: '+key)
    require(Path(value['instrumented_head']['path'])==kernel/'arch/arm64/kernel/head.S','marker head path differs')
    cfg=json.loads(Path(value['config']['path']).read_text());ir=json.loads(Path(value['init_manifest']['path']).read_text())
    marker.validate(cfg,ir['candidate_id'],Path(ir['key_path']).read_bytes())
    require(text==instrumented_head(Path(value['original_head']['path']).read_text(),cfg),'complete marker source differs')
    return value


def build(prepared_dir, deps, label, jobs):
    prepared_dir, deps = prepared_dir.resolve(), deps.resolve()
    require(bool(label) and all(c.isalnum() or c=='-' for c in label), 'build label')
    require(1 <= jobs <= 16, 'parallel job bound')
    data = json.loads((prepared_dir/'prepared.json').read_text())
    output = Path(data['kernel_build']); kernel = Path(data['kernel'])
    require(digest(output/'.config') == data['config_sha256'], 'prepared config changed')
    marker_source=prepared_dir/'marker-source.json'
    marker_record=marker_provenance(prepared_dir,kernel)
    if marker_record:
        head=marker_record['instrumented_head']
        require(Path(head['path'])==kernel/'arch/arm64/kernel/head.S' and digest(head['path'])==head['sha256'],
                'instrumented kernel entry differs')
    cc = shutil.which('aarch64-linux-gnu-gcc');require(cc is not None,'ARM64 compiler absent')
    compiler = Path(cc).resolve()
    env = dict(os.environ)
    settings = {
        'SOURCE_DATE_EPOCH':'0', 'KBUILD_BUILD_TIMESTAMP':'1970-01-01 00:00:00 +0000',
        'KBUILD_BUILD_USER':'lab', 'KBUILD_BUILD_HOST':'h0', 'KBUILD_BUILD_VERSION':'1',
        'HOSTCFLAGS':f'-O2 -I{deps}/usr/include -I{deps}/usr/include/x86_64-linux-gnu',
        'HOSTLDFLAGS':f'-L{deps}/usr/lib/x86_64-linux-gnu',
        'LD_LIBRARY_PATH':str(deps/'usr/lib/x86_64-linux-gnu'),
        'PKG_CONFIG_LIBDIR':str(deps/'usr/lib/x86_64-linux-gnu/pkgconfig'),
        'PKG_CONFIG_SYSROOT_DIR':str(deps),
    }
    env.update(settings)
    command = ['make','-C',kernel,'O='+str(output),'ARCH=arm64',
               'CROSS_COMPILE=aarch64-linux-gnu-',f'-j{jobs}','Image']
    record = {'command':[str(x) for x in command], 'environment':settings,
              'compiler':{'path':str(compiler),'sha256':digest(compiler),
                          'version':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]},
              'prepared_sha256':digest(prepared_dir/'prepared.json')}
    with (prepared_dir/(label+'-command.json')).open('x') as stream:
        json.dump(record,stream,indent=2);stream.write('\n')
    run(command, prepared_dir/(label+'.log'), env=env)
    require(digest(output/'.config')==data['config_sha256'],'make changed the prepared config')
    image = output/'arch/arm64/boot/Image'
    header = image.read_bytes()[:64]
    require(len(header)==64 and header[56:60]==b'ARM\x64', 'ARM64 Image header')
    text_offset, runtime_size, flags = struct.unpack_from('<QQQ',header,8)
    require(runtime_size >= image.stat().st_size and text_offset == 0, 'Image geometry')
    result = {'status':'H0_KERNEL_BUILT_NOT_DEVICE_AUTHORITY','image':str(image),
              'sha256':digest(image),'file_size':image.stat().st_size,
              'runtime_size':runtime_size,'text_offset':text_offset,'flags':flags,
              'config_sha256':digest(output/'.config'), 'command':record,'device_actions':0}
    if marker_record:
        require(marker_provenance(prepared_dir,kernel)==marker_record,'kernel marker changed during build')
        result['retained_marker']=dict(path=str(marker_source),size=marker_source.stat().st_size,sha256=digest(marker_source))
    with (prepared_dir/(label+'-result.json')).open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['command','image']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--deps',type=Path,required=True)
    p.add_argument('--label',default='kernel-1')
    p.add_argument('--jobs',type=int,default=6)
    a=p.parse_args();build(a.prepared,a.deps,a.label,a.jobs)
