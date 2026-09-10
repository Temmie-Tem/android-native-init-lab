"""Derive the fixed metadata-only census from the sealed vendor and USB plan."""
from pathlib import Path
import hashlib
import json
import re
import stat
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'revalidation'))
import s22plus_boot_verify as boot_verify
import s22plus_fyg8_p241_e2_static_checker as vendor
import s22plus_fyg8_p350_stock_candidate_build as base

ROOT=Path(__file__).resolve().parents[5]
PLAN_NAME='s22plus_fyg8_p286_e3_plan.h'


def derive(entries,plan):
    anchor='static const struct s22plus_o2_module_plan_entry s22plus_o2_module_plan[] = {'
    if plan.count(anchor)!=1:raise ValueError('module plan declaration differs')
    body=plan.split(anchor,1)[1].split('};',1)[0]
    names=re.findall(r'\{"([A-Za-z0-9_.-]+\.ko)", "[A-Za-z0-9_]+", "[^"\n]*"\}',body)
    remainder=re.sub(r'\{"[A-Za-z0-9_.-]+\.ko", "[A-Za-z0-9_]+", "[^"\n]*"\},?', '',body)
    if not names or len(names)!=len(set(names)) or remainder.strip():
        raise ValueError('module plan rows malformed')
    selected={'lib/modules/'+n for n in names};seen=set();rows=[]
    for e in entries:
        if e.name in seen:raise ValueError('duplicate vendor entry')
        seen.add(e.name)
        if not e.name.startswith('lib/modules/') or not e.name.endswith('.ko'):continue
        name=e.name[len('lib/modules/'):]
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.ko',name) or name.startswith('.'):
            raise ValueError('non-flat module name')
        if not stat.S_ISREG(e.mode) or e.nlink!=1 or e.uid or e.gid:
            raise ValueError('vendor module metadata differs')
        if e.name not in selected:rows.append((name,len(e.data),e.mode&0o7777))
    if not rows:raise ValueError('empty unselected module census')
    return tuple(sorted(rows))


def manifest():
    receipt=json.loads(base.stable(base.BASE/'result.json',base.BASE_RESULT))
    plan=base.stable(base.BASE/'stock-sources'/PLAN_NAME,receipt['source_closure'][PLAN_NAME])
    compressed=base.stable(ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
        {'size':vendor.EXPECTED_VENDOR_RAMDISK_SIZE,'sha256':vendor.EXPECTED_VENDOR_RAMDISK_SHA256})
    lz4=(ROOT/vendor.DEFAULT_LZ4).resolve()
    # Reuse the vendor extractor's existing tool-byte check; this tool is a
    # retained hardlink, not a mutable candidate/source artifact.
    tool=vendor.stable_read(lz4,'pinned LZ4',1024*1024)
    if base.identity(tool)!={'size':vendor.base_static.LZ4_SIZE,'sha256':vendor.base_static.LZ4_SHA256}:
        raise ValueError('LZ4 identity differs')
    cpio=boot_verify.decompress_lz4(lz4,compressed)
    if len(cpio)!=vendor.EXPECTED_VENDOR_NEWC_SIZE:raise ValueError('vendor CPIO size differs')
    entries=boot_verify.parse_newc(cpio)
    # The retained initial plan is copied byte-for-byte by the current builder.
    # All additional display/return files are in /s22-display-modules, outside
    # this vendor /lib/modules census; they cannot enter its unselected set.
    return derive(entries,plan.decode())


def render():
    rows=manifest()
    lines=['/* Fixed metadata census; no file content is read by the device helper. */',
        '#define MS_MANIFEST_COUNT '+str(len(rows))+'U', '#define MS_MANIFEST_ROWS \\']
    lines += ['    {"%s", %dULL, 0%oU}%s'%(name,size,mode,', \\' if i+1<len(rows) else '')
              for i,(name,size,mode) in enumerate(rows)]
    return ('\n'.join(lines)+'\n').encode()


if __name__=='__main__':
    value=render();print(json.dumps({'rows':len(manifest()),'size':len(value),
        'sha256':hashlib.sha256(value).hexdigest()}))
