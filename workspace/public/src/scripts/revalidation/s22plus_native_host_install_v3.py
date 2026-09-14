#!/usr/bin/python3 -I
"""Installation of reviewed fixed host files, outside a live grant.

Invoke through attended PC authorization with the prepared manifest and its
reviewed SHA-256. This installer is not covered by the census polkit exception.
Only byte-exact files from an explicitly supplied prior installation can be
replaced. Unknown different destination content is never replaced.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import uuid

DESTINATIONS={
    '/usr/local/libexec/s22plus-native-tty-census':0o755,
    '/etc/android-native-init-lab/s22plus-native-host.json':0o644,
    '/etc/polkit-1/rules.d/49-s22plus-native-census.rules':0o644,
    '/etc/udev/rules.d/79-s22plus-native-mm-ignore.rules':0o644,
    '/usr/share/polkit-1/actions/org.androidnativeinit.s22plus.tty-census.policy':0o644,
}
ACTION='/usr/share/polkit-1/actions/org.androidnativeinit.s22plus.tty-census.policy'


def require(value, message):
    if not value: raise ValueError(message)


def stable(path, maximum=65536):
    path=Path(path); require(path.is_absolute() and path.resolve(strict=True)==path,'indirect host installation input')
    before=path.stat(); require(stat.S_ISREG(before.st_mode) and before.st_nlink==1
        and 0<before.st_size<=maximum,'host installation input is not bounded and regular')
    data=path.read_bytes(); after=path.stat()
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
        ==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
        and len(data)==before.st_size,'host installation input changed')
    return data


def trusted_parent(path):
    for parent in (path.parent,*path.parent.parents):
        info=parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022,
            'host installation parent is not root-controlled')


def prepared(manifest, expected_sha256, caller, *, previous=False):
    data=stable(manifest)
    require(hashlib.sha256(data).hexdigest()==expected_sha256,'installation manifest differs from reviewed digest')
    value=json.loads(data)
    require(set(value)=={'schema','uid','account','topology','files'}
        and value['schema']=='s22plus-native-host-installation-v3' and value['uid']==caller
        and pwd.getpwuid(caller).pw_name==value['account'] and value['topology']=='3-1.3',
        'host installation caller or native port differs')
    names={row['destination'] for row in value['files']}
    require(len(value['files'])==len(names) and (names==set(DESTINATIONS)
        or previous and names==set(DESTINATIONS)-{ACTION}),
        'host installation destination set differs')
    result=[]
    for row in value['files']:
        require(set(row)=={'destination','mode','source'} and row['mode']==DESTINATIONS[row['destination']],
            'host installation file mode differs')
        receipt=row['source']; source=Path(receipt['path'])
        require(source.parent==Path(manifest).parent and set(receipt)=={'path','size','sha256'},
            'host installation source is outside its prepared directory')
        body=stable(source)
        require(len(body)==receipt['size'] and hashlib.sha256(body).hexdigest()==receipt['sha256'],
            'prepared host file changed')
        result.append((Path(row['destination']),body,row['mode']))
    return result


def install(manifest, expected_sha256, caller, *, prior=None):
    require(os.geteuid()==0,'host installation requires explicit PC administrator authorization')
    rows=prepared(manifest,expected_sha256,caller)
    previous={path:(data,mode) for path,data,mode in prepared(*prior,caller,previous=True)} if prior else {}
    new_directory=Path('/etc/android-native-init-lab')
    existing={}
    # Validate every existing destination before the first installation write.
    for path,data,mode in rows:
        if path.parent==new_directory and not new_directory.exists(): trusted_parent(new_directory)
        else: trusted_parent(path)
        if path.exists() or path.is_symlink():
            info=path.lstat()
            actual=stable(path)
            require(info.st_uid==0 and stat.S_IMODE(info.st_mode)==mode
                and (actual==data or previous.get(path)==(actual,mode)),
                'existing host destination has different bytes or ownership')
            existing[path]=actual
        else: existing[path]=None
    if not new_directory.exists():
        new_directory.mkdir(mode=0o755)
        descriptor=os.open(new_directory.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
    for path,data,mode in rows:
        trusted_parent(path)
        if existing[path]==data: continue
        temporary=path.parent/('.s22plus-native-install-'+uuid.uuid4().hex+'.tmp')
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
        try:
            try:
                offset=0
                while offset<len(data):
                    count=os.write(descriptor,data[offset:]); require(count>0,'host installation made no write progress'); offset+=count
                os.fchmod(descriptor,mode); os.fsync(descriptor)
            finally: os.close(descriptor)
            if existing[path] is None:
                os.link(temporary,path)
            else:
                info=path.lstat()
                require(stable(path)==existing[path] and info.st_uid==0 and stat.S_IMODE(info.st_mode)==mode,
                    'owned prior host file changed before replacement')
                os.replace(temporary,path)
        finally:
            if temporary.exists():temporary.unlink()
        descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
    for path,data,mode in rows:
        require(stable(path)==data and path.stat().st_uid==0 and stat.S_IMODE(path.stat().st_mode)==mode,
            'installed host file did not read back')
    subprocess.run(['/usr/bin/udevadm','control','--reload-rules'],check=True,timeout=10,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('HOST_FILES_INSTALLED_AND_RULES_RELOADED')


def main():
    require(len(sys.argv) in (3,5),'expected prepared manifest/digest and optional exact prior manifest/digest')
    caller=os.environ.get('PKEXEC_UID','')
    require(caller.isdecimal() and int(caller)>0,'exact non-root invoking account is unavailable')
    install(Path(sys.argv[1]),sys.argv[2],int(caller),
        prior=(Path(sys.argv[3]),sys.argv[4]) if len(sys.argv)==5 else None)


if __name__=='__main__': main()
