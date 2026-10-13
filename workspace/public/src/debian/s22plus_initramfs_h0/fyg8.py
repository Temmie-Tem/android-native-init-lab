#!/usr/bin/env python3
"""Host-only FYG8 preparation port; no device transport or live activation."""
import argparse
import difflib
import shutil
import gzip
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys

import h0

sys.path.extend([str(h0.ROOT / 'workspace/public/src/scripts/analysis'),
                 str(h0.ROOT / 'workspace/public/src/scripts/revalidation')])
import s22plus_boot_verify as boot
import s22plus_debian_profile_v1 as retained
import s22plus_native_ufs_source_v1 as ufs
import s22plus_memory_manifest_v1 as memory
import s22plus_fyg8_p319_stock_candidate_build as linkage
import s22plus_native_ext4_h0 as ext4
import s22plus_native_ext4_source_v1 as filesystem
from s22plus_native_records_v3 import verify

KERNEL_RELEASE = '5.10.226-android12-9-30958166-abS906NKSS7FYG8'
MODEL = 'Samsung G0Q PROJECT (board-id,12)'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def capture(argv, path):
    result = subprocess.run([str(x) for x in argv], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=30)
    path.write_bytes(result.stdout + result.stderr)
    h0.require(result.returncode == 0 and len(result.stdout) < 1024 * 1024,
               'static inspection failed; see ' + str(path))
    return result.stdout.decode().strip()


def inventory(out):
    out = h0.private(out, fresh=True)
    previous = json.loads(verify(retained.RETAINED_RESULT).read_text())
    image_file = h0.regular(retained.RETAINED / 'candidate-a/boot.img')
    raw = image_file.read_bytes()
    expected = previous['candidate']['a']['boot_img']
    h0.require(len(raw) == expected['size'] and digest(raw) == expected['sha256'],
               'retained boot input changed')
    parsed = boot.parse_boot_v4(raw)
    h0.require(digest(parsed.kernel) == previous['image']['sha256'], 'retained kernel changed')
    entries = boot.parse_newc(boot.decompress_lz4_stream_python(parsed.ramdisk, maximum=128*1024**2))
    old = {row.name: row for row in entries}
    h0.require(len(old) == len(entries), 'duplicate retained ramdisk entry')
    plan = verify(retained.PLATFORM_PLAN).read_text()
    block = plan.split('s22plus_o2_module_plan[] = {', 1)[1].split('};', 1)[0]
    rows = re.findall(r'\{"([A-Za-z0-9_.-]+\.ko)", "([A-Za-z0-9_]+)", "([^"\n]*)"\}', block)
    h0.require(rows and len(rows) == len({r[0] for r in rows}) and
               not re.sub(r'\{"[A-Za-z0-9_.-]+\.ko", "[A-Za-z0-9_]+", "[^"\n]*"\},?', '', block).strip(),
               'malformed retained module declaration')
    platform_count = len(rows)
    h0.require(not ({r[0] for r in rows} & {r[0] for r in ufs.MODULES}), 'duplicate UFS module')
    rows += [(name, runtime, '') for name, runtime, _, _ in ufs.MODULES]
    vendor = memory.vendor
    source = memory.base.stable(h0.ROOT / vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE, sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    vendor_entries = boot.parse_newc(boot.decompress_lz4_stream_python(source, maximum=128*1024**2))
    stock = {row.name: row for row in vendor_entries}
    h0.require(len(stock) == len(vendor_entries), 'duplicate stock member')
    module_dir = out / 'modules'; module_dir.mkdir()
    logs = out / 'inspection'; logs.mkdir()
    providers = linkage._image_provider_map(parsed.kernel, linkage.IMAGE_SECTION_LAYOUT)
    provider_names = {name: 'kernel' for name in providers}
    loaded = set()
    modules = []
    for index, (name, runtime, parameters) in enumerate(rows):
        member = 'lib/modules/' + name
        entry = old.get(member) or stock[member]
        if member in old:
            pinned = previous['candidate']['a']['inventory'][member]
            h0.require(len(entry.data) == pinned['size'] and digest(entry.data) == pinned['sha256'],
                       'retained module bytes changed')
            h0.require(all(getattr(entry, key) == pinned[key] for key in ('mode', 'uid', 'gid', 'nlink', 'mtime')),
                       'retained module metadata changed')
        else:
            h0.require((entry.mode, entry.uid, entry.gid, entry.nlink) == (stat.S_IFREG | 0o644, 0, 0, 1),
                       'stock module file metadata changed')
        h0.require(stat.S_ISREG(entry.mode) and not (entry.mode & 0o022) and
                   (entry.uid, entry.gid, entry.nlink) == (0, 0, 1), 'unsafe module metadata')
        if index >= platform_count:
            declaration = ufs.MODULES[index - platform_count]
            h0.require((len(entry.data), digest(entry.data)) == declaration[2:], 'UFS declaration differs')
        path = module_dir / name; path.write_bytes(entry.data); path.chmod(0o400)
        info = {}
        for field in ('name', 'depends', 'vermagic', 'firmware'):
            info[field] = capture(['modinfo', '-F', field, path], logs / (name + '.' + field))
        h0.require(info['name'] == runtime, 'runtime module name changed')
        h0.require(info['vermagic'].split(' ', 1)[-1] == 'SMP preempt mod_unload modversions aarch64',
                   'module vermagic attributes changed')
        depends = [n.replace('-', '_') for n in info['depends'].split(',') if n]
        h0.require(set(depends) <= loaded, 'module dependency not available earlier: ' + name)
        imports = {}
        for line in capture(['modprobe', '--dump-modversions', path], logs / (name + '.imports')).splitlines():
            crc, symbol = line.split()
            h0.require(symbol not in imports, 'duplicate module import')
            imports[symbol] = linkage._norm_crc(crc)
        h0.require(imports and all(providers.get(symbol) == crc for symbol, crc in imports.items()),
                   'actual Image/earlier-module CRC mismatch: ' + name)
        dependencies = sorted({provider_names[symbol] for symbol in imports if provider_names[symbol] != 'kernel'})
        exports = {}
        for line in capture(['aarch64-linux-gnu-nm', '-g', '--defined-only', path], logs / (name + '.exports')).splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[-1].startswith('__crc_'):
                symbol = fields[-1][6:]
                h0.require(symbol not in providers and symbol not in exports, 'duplicate export')
                exports[symbol] = linkage._norm_crc(fields[0])
        providers.update(exports); provider_names.update({key: name for key in exports}); loaded.add(runtime)
        firmware = info['firmware'].splitlines() if info['firmware'] else []
        firmware_calls = sorted(n for n in imports if 'firmware' in n)
        modules.append(dict(ordinal=index + 1, name=name, runtime_name=runtime, parameters=parameters,
            size=len(entry.data), sha256=digest(entry.data), origin='retained-ramdisk' if member in old else 'stock-vendor',
            declared_dependencies=depends, earlier_symbol_providers=dependencies,
            imports=len(imports), exports=len(exports), vermagic=info['vermagic'],
            declared_firmware=firmware, firmware_api_imports=firmware_calls))
    h0.require(parsed.kernel.count(b'IKCFG_ST') == 1 and parsed.kernel.count(b'IKCFG_ED') == 1,
               'ambiguous kernel config')
    config = gzip.decompress(parsed.kernel.split(b'IKCFG_ST',1)[1].split(b'IKCFG_ED',1)[0])
    (out / 'kernel.config').write_bytes(config)
    (out / 'fixed-Image').write_bytes(parsed.kernel)
    (out / 'platform-plan.h').write_text(plan)
    firmware_files = sorted(name for name in set(old) | set(stock) if name.startswith(('lib/firmware/','vendor/firmware/')))
    h0.publish(out / 'inventory.json', dict(scope='H0 static FYG8 preparation inventory', device_actions=0,
        kernel_release=KERNEL_RELEASE, model=MODEL, retained_result=retained.RETAINED_RESULT,
        retained_plan=retained.PLATFORM_PLAN, kernel_sha256=digest(parsed.kernel),
        config_sha256=digest(config), platform_count=platform_count, modules=modules,
        firmware_files_in_retained_ramdisks=firmware_files,
        firmware_limit='Declared names and imported APIs do not prove runtime requests or firmware readiness'))
    print(json.dumps(dict(modules=len(modules), imports=sum(m['imports'] for m in modules),
        firmware_modules=[m['name'] for m in modules if m['declared_firmware'] or m['firmware_api_imports']],
        retained_firmware_files=len(firmware_files)), indent=2))



def debian_entries(path):
    raw=gzip.decompress(h0.regular(path).read_bytes())
    # GNU cpio emits a leading root-directory record, which the Samsung parser
    # intentionally does not accept. Check and omit only that exact record.
    h0.require(raw[:6]==b'070701', 'not Debian newc')
    fields=[int(raw[6+i*8:14+i*8],16) for i in range(13)]
    end=(110+fields[11]+3)&~3
    h0.require(raw[110:110+fields[11]]==b'.\0' and fields[6]==0 and
        stat.S_ISDIR(fields[1]) and fields[2:4]==[0,0] and not any(raw[112:end]),
        'unexpected leading Debian archive record')
    return boot.parse_newc(raw[end:])


def verify_inventory(inputs):
    value=json.loads(h0.regular(inputs/'inventory.json').read_text())
    h0.require(value['device_actions']==0 and value['kernel_release']==KERNEL_RELEASE and
        value['model']==MODEL and value['retained_plan']==retained.PLATFORM_PLAN and
        value['retained_result']==retained.RETAINED_RESULT, 'wrong inventory parent')
    previous=json.loads(verify(retained.RETAINED_RESULT).read_text())
    h0.require(value['kernel_sha256']==previous['image']['sha256'] and
        h0.sha(h0.regular(inputs/'fixed-Image'))==value['kernel_sha256'] and
        h0.sha(h0.regular(inputs/'kernel.config'))==value['config_sha256'] and
        h0.sha(h0.regular(inputs/'platform-plan.h'))==retained.PLATFORM_PLAN['sha256'],
        'inventory inputs changed')
    plan=verify(retained.PLATFORM_PLAN).read_text().split('s22plus_o2_module_plan[] = {',1)[1].split('};',1)[0]
    expected_rows=re.findall(r'\{"([A-Za-z0-9_.-]+\.ko)", "([A-Za-z0-9_]+)", "([^"\n]*)"\}',plan)
    h0.require(value['platform_count']==len(expected_rows),'platform count differs')
    expected_rows += [(name,runtime,'') for name,runtime,_,_ in ufs.MODULES]
    vendor=memory.vendor
    raw=memory.base.stable(h0.ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
    stock={e.name:e for e in boot.parse_newc(boot.decompress_lz4_stream_python(raw,maximum=128*1024**2))}
    actual_config=gzip.decompress((inputs/'fixed-Image').read_bytes().split(b'IKCFG_ST',1)[1].split(b'IKCFG_ED',1)[0])
    h0.require((inputs/'kernel.config').read_bytes()==actual_config,'config differs from fixed kernel')
    h0.require([(m['name'],m['runtime_name'],m['parameters']) for m in value['modules']]==expected_rows,
        'module order/name/parameters differ from fixed declaration')
    h0.require({p.name for p in (inputs/'modules').iterdir()}=={row['name'] for row in value['modules']},
        'extra or missing module payload')
    for index,row in enumerate(value['modules']):
        member='lib/modules/'+row['name']
        expected=previous['candidate']['a']['inventory'].get(member)
        if expected is None:
            entry=stock[member];expected=dict(size=len(entry.data),sha256=digest(entry.data))
        h0.require((row['ordinal'],row['size'],row['sha256'])==(index+1,expected['size'],expected['sha256']),
            'module inventory differs from retained origin')
        h0.require(re.fullmatch(r'[A-Za-z0-9_.-]+\.ko',row['name']) is not None and
            re.fullmatch(r'[A-Za-z0-9_]+',row['runtime_name']) is not None and
            row['parameters']=='','unsupported module declaration')
        path=h0.regular(inputs/'modules'/row['name'])
        h0.require(path.stat().st_size==row['size'] and h0.sha(path)==row['sha256'],
            'inventory module changed')
    h0.require(len(value['modules'])==value['platform_count']+len(ufs.MODULES) and
        len({row['name'] for row in value['modules']})==len(value['modules']), 'invalid module set')
    return value


def compile_helper(out, inputs, *, virt=False, run_id=None):
    value=verify_inventory(inputs)
    # Fixed prospective construction identity; not a live session grant.
    run_id=run_id or hashlib.sha256((h0.sha(inputs/'inventory.json')+'fyg8-h0').encode()).hexdigest()[:32]
    h0.require(re.fullmatch('[0-9a-f]{32}',run_id) is not None,'invalid preparation run identity')
    (out/'s22plus_native_ext4_seal_v1.h').write_bytes(ext4.seal(filesystem.BINDING,run_id,initialize=False))
    rows=['struct fyg8_module {const char *path,*runtime,*parameters; uint64_t size; uint8_t hash[32];};',
          'static const char fyg8_release[]='+json.dumps(KERNEL_RELEASE)+';',
          'static const char fyg8_model[]='+json.dumps(MODEL)+';',
          'static const struct fyg8_module fyg8_modules[]={']
    for row in value['modules']:
        rows.append('{'+','.join(json.dumps(x) for x in
            ('/lab/modules/'+row['name'],row['runtime_name'],row['parameters']))+','+str(row['size'])+'ULL,{'+
            ','.join(map(str,bytes.fromhex(row['sha256'])))+'}},')
    (out/'fyg8-plan.h').write_text('\n'.join(rows+['};'])+'\n')
    h0.run(['aarch64-linux-gnu-gcc','-static','-Os','-Wall','-Wextra','-Werror',
        '-Wno-unused-function','-Wno-unused-const-variable','-ffunction-sections','-fdata-sections',
        '-Wl,--gc-sections','-fno-ident','-Wl,--build-id=none',
        *(['-DFYG8_VM_TEST'] if virt else []),'-I',out,'-I',ext4.NATIVE,
        h0.HERE/'fyg8-prepare.c','-o',out/'fyg8-prepare'],out/'compile.log')
    h0.run(['file',out/'fyg8-prepare'],out/'file.log')
    symbols=subprocess.check_output(['aarch64-linux-gnu-nm',out/'fyg8-prepare'])
    (out/'symbols.txt').write_bytes(symbols)
    h0.require(not any(re.search(rb'\b'+s+rb'$',symbols,re.M) for s in
        (b'fs1_tool',b'fs1_mount_root',b'execve',b'fexecve',b'mount',b'reboot')),
        'unexpected writer/handoff/reboot linkage')
    return dict(run_id=run_id,filesystem_binding=filesystem.BINDING)


def file_script():
    return '''[ "$fyg8_status" = 0 ] || fyg8_stop
mkdir -m 700 /s22-root-work || fyg8_stop
mount -t tmpfs -o nodev,nosuid,noexec,mode=0700 tmpfs /s22-root-work || fyg8_stop
umask 077
set -C
/sbin/file-log >/run/initramfs/file-admission 2>&1
file_status=$?
fyg8_stop
'''


def inside(out,packages,inputs,*,observed=False,file_pilot=False,storage_first=False):
    h0.require(not (observed and file_pilot),"select one early observer")
    h0.require(not storage_first or file_pilot,'storage-first requires fixed file writer')
    value=verify_inventory(inputs)
    tree=h0.builder_tree(out,packages)
    shutil.copyfile(out/'fyg8-prepare',tree/'usr/sbin/fyg8-prepare')
    (tree/'usr/sbin/fyg8-prepare').chmod(0o755)
    shutil.copytree(inputs/'modules',tree/'lab/modules')
    if storage_first:
        import usb_first
        target=tree/'lab/modules'/usb_first.LOGGER['name']
        target.write_bytes((out/usb_first.LOGGER['name']).read_bytes());target.chmod(0o400)
    if observed:
        shutil.copyfile(out/'early-observer',tree/'usr/sbin/early-observer')
        (tree/'usr/sbin/early-observer').chmod(0o755)
    if file_pilot:
        for source,target in (('file-log','usr/sbin/file-log'),('s22-fs-e2fsck','s22-fs-e2fsck'),('table.bin','s22-root-inspect.table')):
            shutil.copyfile(out/source,tree/target);(tree/target).chmod(0o400 if source=='table.bin' else 0o500)
    conf=tree/'etc/initramfs-tools'
    for directory in ('conf.d','hooks','scripts'):
        (conf/directory).mkdir(parents=True,exist_ok=True)
    (conf/'initramfs.conf').write_text('MODULES=list\nBUSYBOX=y\nCOMPRESS=gzip\nKEYMAP=n\nRESUME=none\n')
    (conf/'modules').write_text('')
    for source,target in [('fyg8-hook','hooks/fyg8'),('fyg8-dev','scripts/fyg8-dev')]:
        shutil.copyfile(h0.HERE/source,conf/target);(conf/target).chmod(0o755)
    if observed:
        source=(h0.HERE/'fyg8-dev').read_text()
        h0.require(source.endswith('fyg8_stop\n'),'early terminal hook changed')
        (conf/'scripts/fyg8-dev').write_text(source[:-len('fyg8_stop\n')]+
            '/sbin/early-observer "$fyg8_status"\nfyg8_stop\n')
        shutil.copyfile(h0.HERE/'early-hook',conf/'hooks/zzzz-early')
        (conf/'hooks/zzzz-early').chmod(0o755)
    if file_pilot:
        source=(h0.HERE/'fyg8-dev').read_text()
        h0.require(source.endswith('fyg8_stop\n'),'early terminal hook changed')
        if storage_first:
            anchor='mknod -m 666 /dev/null c 1 3 || fyg8_stop\n'
            h0.require(source.count(anchor)==1,'storage-first RAM device hook changed')
            source=source.replace(anchor,anchor+'mknod -m 600 /dev/kmsg c 1 11 || fyg8_stop\n')
        (conf/'scripts/fyg8-dev').write_text(source[:-len('fyg8_stop\n')]+file_script())
        shutil.copyfile(h0.HERE/'file-hook',conf/'hooks/zzzz-file')
        (conf/'hooks/zzzz-file').chmod(0o755)
    init=tree/'usr/share/initramfs-tools/init'
    original=init.read_text();needle='mount -t devtmpfs -o nosuid,mode=0755 udev /dev\n'
    h0.require(original.count(needle)==1,'Debian early init changed')
    adapted=original.replace(needle,'. /scripts/fyg8-dev\n')
    init.write_text(adapted)
    (out/'debian-init.original').write_text(original)
    (out/'debian-init.adapted').write_text(adapted)
    (out/'debian-init.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),
        adapted.splitlines(True),fromfile='Debian-0.148.4/init',tofile='FYG8-H0/init')))
    (tree/'boot').mkdir(exist_ok=True)
    shutil.copyfile(inputs/'kernel.config',tree/'boot'/('config-'+KERNEL_RELEASE))
    modules=tree/'usr/lib/modules'/KERNEL_RELEASE;modules.mkdir(parents=True,exist_ok=True)
    # Automatic modprobe is outside this prototype. Modules are carried in the
    # private fixed-plan directory, never a searchable modules.dep inventory.
    for name in ('modules.builtin','modules.builtin.modinfo','modules.order'):
        (modules/name).write_text('')
    h0.generate_archives(out,tree,KERNEL_RELEASE)


def build(out,packages,inputs):
    out=h0.private(out,fresh=True);packages=h0.private(packages);inputs=h0.private(inputs)
    value=verify_inventory(inputs)
    h0.verify_packages(packages,out)
    sources=snapshot(out)
    binding=compile_helper(out,inputs)
    h0.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork','--mount-proc',
        sys.executable,__file__,'inside','--output',out,'--packages',packages,'--inputs',inputs],
        out/'namespace-build.log',timeout=700)
    h0.require(h0.sha(out/'initramfs-a.cpio.gz')==h0.sha(out/'initramfs-b.cpio.gz'),'A/B archive mismatch')
    entries=debian_entries(out/'initramfs-a.cpio.gz')
    by_name={entry.name:entry for entry in entries}
    h0.require(len(by_name)==len(entries),'duplicate archive entry')
    h0.require(by_name['init'].data==(out/'debian-init.adapted').read_bytes(),'wrong PID1 init')
    h0.require({name for name in by_name if name.startswith('lab/modules/')}==
        {'lab/modules/'+row['name'] for row in value['modules']}, 'archive module set differs')
    for row in value['modules']:
        entry=by_name['lab/modules/'+row['name']]
        h0.require(digest(entry.data)==row['sha256'] and len(entry.data)==row['size'] and
            (entry.mode,entry.uid,entry.gid,entry.nlink)==(stat.S_IFREG|0o400,0,0,1),'embedded module differs')
    h0.require(not any(name.startswith(('s22-','lib/firmware/','usr/lib/firmware/')) for name in by_name),
        'unexpected legacy runtime or firmware payload')
    for row in sources:
        h0.require(h0.sha(h0.ROOT/row['path'])==row['sha256'],'source changed during build')
    verify_inventory(inputs)
    h0.publish(out/'archive.json',[dict(name=e.name,mode=e.mode,uid=e.uid,gid=e.gid,nlink=e.nlink,
        size=len(e.data),sha256=digest(e.data)) for e in entries])
    h0.publish(out/'build.json',dict(scope='H0 prospective FYG8 metadata-only initramfs',device_actions=0,
        active=False,kernel_sha256=value['kernel_sha256'],config_sha256=value['config_sha256'],
        input_inventory=dict(path=str(inputs/'inventory.json'),sha256=h0.sha(inputs/'inventory.json')),
        packages=dict(path=str(packages/'packages.json'),sha256=h0.sha(packages/'packages.json')),
        initramfs_sha256=h0.sha(out/'initramfs-a.cpio.gz'),helper_sha256=h0.sha(out/'fyg8-prepare'),
        ab_identical=True,source_inputs=sources,
        generated_headers={name:h0.sha(out/name) for name in ('fyg8-plan.h','s22plus_native_ext4_seal_v1.h')},**binding))
    print('PASS: FYG8 H0 initramfs A/B; no device qualification or activation')


def snapshot(out):
    paths={p for p in h0.HERE.iterdir() if p.is_file() and p.suffix in ('.py','.c')}
    paths.update(h0.HERE/name for name in ('fyg8-dev','fyg8-hook'))
    paths.update(h0.ROOT/'workspace/public/src/native-init'/name for name in
        ('s22plus_native_ext4_v1.c','s22plus_native_ext4_core_v1.h',
         's22plus_fyg8_max77705_result_parser.inc.c','s22plus_fyg8_logger_binding_v1.h'))
    paths.add(h0.HERE.parent/'s22plus_v1/device/virt-binding.inc.c')
    # Preserve the loaded static inventory/seal producer closure as well.
    for module in tuple(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path and Path(path).is_relative_to(h0.ROOT/'workspace/public/src'):
            paths.add(Path(path))
    records=[]
    for path in sorted(paths):
        destination=out/'source-snapshot'/path.relative_to(h0.ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(path.read_bytes())
        records.append(dict(path=str(path.relative_to(h0.ROOT)),sha256=h0.sha(destination)))
    h0.publish(out/'source-inputs.json',records)
    return records


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inventory','build','inside'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--packages',type=Path)
    parser.add_argument('--inputs',type=Path)
    args=parser.parse_args()
    if args.action=='inventory':inventory(args.output)
    elif args.action=='build':build(args.output,args.packages,args.inputs)
    else:inside(h0.private(args.output),h0.private(args.packages),h0.private(args.inputs))
