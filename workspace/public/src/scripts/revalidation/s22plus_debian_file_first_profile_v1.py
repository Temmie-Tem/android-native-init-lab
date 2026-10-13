"""Storage-first sibling of the fixed file owner, with separate review identity."""
from pathlib import Path
import hashlib
import zlib
import s22plus_boot_verify as boot
import s22plus_debian_file_first_plan_v1 as plan
import s22plus_debian_file_profile_v1 as retained
from s22plus_native_records_v3 import require,read_bytes,read,verify

PROFILE=plan.PROFILE
SCHEMA='s22plus-debian-file-first-v1'
POLICY='docs/operations/S22PLUS_DEBIAN_FILE_FIRST_V1.md'
WINDOW_SECONDS,TRANSFER_SECONDS,RETURN_SECONDS=retained.WINDOW_SECONDS,retained.TRANSFER_SECONDS,retained.RETURN_SECONDS
PENDING=retained.PENDING
CASES=retained.CASES+('readback-error','module-error')
PARTIAL_WRITES=retained.PARTIAL_WRITES+('readback-error',)
before_transfer=retained.before_transfer


def validate_adoption(root,details):
    name=Path(POLICY).name.encode()
    require(name in details and name in read_bytes(Path(root)/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md') and
        b'Status: **REVIEW_GATED_CAPABILITY**' in read_bytes(Path(root)/POLICY),'storage-first adoption absent')


def virtual_artifact(row,built,sources,*,diagnostic=False):
    selected=PROFILE
    if diagnostic:
        import s22plus_debian_failure_profile_v1 as variant
        selected=variant.PROFILE
    helper=read(verify(row['helper_request']));construction=helper['construction']
    require(all(row['expected'][key]==built['measured'][key] for key in ('shell_sha256','init_sha256')),
        'virtual shell or initial owner differs from physical candidate')
    require(helper['virtual'] is True and helper['profile']==selected and helper['run_id']==built['run_id'] and
        helper['modules']==built['modules'] and helper['measured']==row['expected'] and
        helper['fault']==(row['case'] if row['case'] in ('short-write','file-sync-error','parent-sync-error',
            'unmount-error','late-ro-clear','checker-timeout','readback-error') else None) and
        helper['measured']['helper_sha256']==construction['helper']['sha256'],
        'virtual file helper identity differs')
    if diagnostic:
        require(helper.get('diagnostic') is True and helper.get('diagnostic_fault')==(row['case'] if row['case'] in variant.FAULT_CASES else None),'virtual diagnostic selection differs')
        for receipt in construction.get('fault_sources',[]):verify(receipt)
    physical={r['path']:r['sha256'] for r in built['source_inputs']}
    virtual={r['path']:r['sha256'] for r in construction['source_inputs']}
    require(all(virtual.get(name)==digest==sources.get(name) for name,digest in physical.items()) and
        all(sources.get(name)==digest for name,digest in virtual.items()),'virtual helper source closure differs')
    for value in construction['headers'].values():verify(value)
    compressed=verify(row['initramfs'],maximum=32*1024**2).read_bytes();members=[]
    while compressed:
        decoder=zlib.decompressobj(31);member=decoder.decompress(compressed,128*1024**2+1)
        require(decoder.eof and len(member)<=128*1024**2 and len(members)<2,'virtual gzip member differs')
        members.append(member);compressed=decoder.unused_data
    require(len(members)==2,'virtual vendor/owner archive count differs')
    parsed=boot.parse_newc(members[1]);entries={e.name:e for e in parsed}
    require(len(parsed)==len(entries),'virtual archive has duplicate members')
    for name,key in (('usr/sbin/fyg8-prepare','helper'),('usr/sbin/file-log','writer')):
        require(entries[name].data==verify(construction[key],maximum=4*1024**2).read_bytes(),
            'VM archive does not contain its exact compiled helper')
    require(hashlib.sha256(entries['init'].data).hexdigest()==built['measured']['init_sha256'],
        'VM changed Debian initial owner')
    shell=entries['usr/bin/sh'];bodies=[e.data for e in parsed if e.inode==shell.inode and e.file_type=='regular' and e.data]
    require(len(bodies)==1 and hashlib.sha256(bodies[0]).hexdigest()==built['measured']['shell_sha256'],
        'VM changed Debian shell')
    expected={'lab/modules/'+m['name']:m for m in built['modules']}
    require({n for n in entries if n.startswith('lab/modules/')}==set(expected),'virtual module set differs')
    for name,m in expected.items():
        require(len(entries[name].data)==m['size'] and hashlib.sha256(entries[name].data).hexdigest()==m['sha256'],
            'virtual module bytes differ')


def vm_results(tested,built):
    return retained.vm_results(tested,built,storage_first=True)
def image_binding(image):return retained.image_binding(image,storage_first=True)
