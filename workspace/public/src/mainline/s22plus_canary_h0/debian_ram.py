"""Fixed Debian SysVinit RAM closure. H0 packaging and pure artifact checks only."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile

if __package__:
    from .prepare import ROOT, digest, require
else:
    from prepare import ROOT, digest, require

SCHEMA = 's22plus-mainline-debian-sysvinit-ram-v1'
OBSERVER = 'usr/libexec/g0q-ram-observer'
INITTAB = b'id:2:initdefault:\nr2:2:once:@/usr/libexec/g0q-ram-observer\n'
PACKAGES = {
    'libc6': ('2.41-12+deb13u4', '8784eda966b189c777a384dac5ce009e8fc9b52d006926c5a013e7fa8aa688cc'),
    'libpcre2-8-0': ('10.46-1~deb13u2', 'e7d2c997dac145c16457be0fed3d084c98cd030bec7633eec7e5bde6dbb97712'),
    'libselinux1': ('3.8.1-1', 'fc13da4c7783b8f4361d92ef1045931f298d1b0ac78ed1a85c2232615f49fc6f'),
    'sysvinit-core': ('3.14-4', '80200c6959e5a3022535e1b33497bfa3b8d7694366497566c7f3bae34f943362'),
}
# These are actual members of the signed packages above, not a host root copy.
MEMBERS = {
    'usr/sbin/init': ('sysvinit-core', '85c1d3dcd4d36b3ecfd44cb9dcce8ce068569b1a96b8a1024a6507807d7a48d5'),
    'usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1': ('libc6', '1b882eddacd494b060413a8aa4f0a4754ee3f84775e68cecbf8a86092b59cca6'),
    'usr/lib/aarch64-linux-gnu/libc.so.6': ('libc6', '70fa4c4cf57eabeb96097cce47582d02379c4cd1de3db3e98ade4dd7089a1b13'),
    'usr/lib/aarch64-linux-gnu/libselinux.so.1': ('libselinux1', '18a3d9b827b34c87c51cd5954868a8bf9aa206717b414987074b5fb11f74e952'),
    'usr/lib/aarch64-linux-gnu/libpcre2-8.so.0.14.0': ('libpcre2-8-0', '97b4e0f33829849a806c2d322f2febcd06c0cd5b22bff8c9422bf238ec265f75'),
}
DIRS = ('dev', 'proc', 'sys', 'config', 'run', 'var', 'var/log', 'etc',
        'usr', 'usr/lib', 'usr/lib/aarch64-linux-gnu', 'usr/libexec', 'usr/sbin')
LINKS = {'init': 'usr/sbin/init', 'lib': 'usr/lib', 'sbin': 'usr/sbin', 'var/run': '../run',
         'usr/lib/ld-linux-aarch64.so.1': 'aarch64-linux-gnu/ld-linux-aarch64.so.1',
         'usr/lib/aarch64-linux-gnu/libpcre2-8.so.0': 'libpcre2-8.so.0.14.0'}


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), size=path.stat().st_size, sha256=digest(path))


def package_inputs(folder):
    paths = []
    for name, (version, sha) in PACKAGES.items():
        path = folder/'debs'/f'{name}_{version}_arm64.deb'
        require(path.is_file() and digest(path) == sha, 'fixed Debian package differs: '+name)
        paths.append(path)
    return paths


def extract(folder, output):
    """Verify signatures into fresh output; never modify a retained package lock."""
    destination = output/'packages'; (destination/'debs').mkdir(parents=True)
    for path in package_inputs(folder):
        shutil.copyfile(path, destination/'debs'/path.name)
    shutil.copytree(folder/'apt-lists', destination/'apt-lists')
    (destination/'packages.tsv').write_text(''.join(f'{n}\t{v}\tarm64\n' for n,(v,_) in PACKAGES.items()))
    sys.path.insert(0, str(ROOT/'workspace/public/src/debian/s22plus_v1'))
    from verify_packages import verify
    verified = verify(destination)
    require(verified['count'] == 4, 'fixed package closure differs')
    files = {}
    for row in verified['packages']:
        raw = subprocess.check_output(['dpkg-deb','--fsys-tarfile', destination/'debs'/row['file']])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for member in archive:
                name = member.name.removeprefix('./')
                if name not in MEMBERS:
                    continue
                package, expected = MEMBERS[name]
                require(package == row['package'] and name not in files and member.isfile(), 'Debian member origin differs')
                data = archive.extractfile(member).read()
                require(hashlib.sha256(data).hexdigest() == expected, 'Debian member bytes differ')
                files[name] = data
    require(set(files) == set(MEMBERS), 'incomplete Debian ELF closure')
    return files, pin(destination/'package-lock.json')


def pack(files, vm):
    require(set(files) == set(MEMBERS)|{OBSERVER, 'etc/inittab'}, 'unexpected Debian RAM members')
    require(files['etc/inittab'] == INITTAB, 'fixed inittab differs')
    entries = [(name, stat.S_IFDIR|0o755, b'', 0, 0) for name in DIRS]
    entries += [(name, stat.S_IFLNK|0o777, target.encode(), 0, 0) for name,target in LINKS.items()]
    devices = [('dev/console',5,1), ('dev/null',1,3)]
    if vm:
        devices.append(('dev/ttyAMA0',204,64))
    entries += [(name, stat.S_IFCHR|0o600, b'', major, minor) for name,major,minor in devices]
    entries += [(name, stat.S_IFREG|(0o644 if name=='etc/inittab' else 0o755), data, 0, 0)
                for name,data in sorted(files.items())]
    result = bytearray()
    for inode,(name,mode,data,major,minor) in enumerate([*entries,('TRAILER!!!',0,b'',0,0)],1):
        encoded = name.encode()+b'\0'
        fields = [inode,mode,0,0,1,0,len(data),0,0,major,minor,len(encoded),0]
        result.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode())
        result.extend(encoded);result.extend(b'\0'*(-len(result)%4))
        result.extend(data);result.extend(b'\0'*(-len(result)%4))
    return bytes(result)


def populate(tree, files):
    for name in DIRS:
        (tree/name).mkdir(parents=True, exist_ok=True, mode=0o755)
    for name,data in files.items():
        path=tree/name;path.write_bytes(data);path.chmod(0o644 if name=='etc/inittab' else 0o755)
    for name,target in LINKS.items():
        (tree/name).symlink_to(target)
    # CPIO contains fixed character nodes; the host tree has no device nodes.


def declaration(files, observer, package_lock):
    return dict(schema=SCHEMA, package_lock=package_lock, observer=pin(observer),
                inittab_sha256=hashlib.sha256(INITTAB).hexdigest(),
                members={n:dict(package=MEMBERS[n][0],sha256=hashlib.sha256(files[n]).hexdigest(),size=len(files[n]))
                         for n in MEMBERS})


def validate(manifest):
    """Pure fixed-member/actual-CPIO check, including node types and symlinks."""
    value=manifest['debian_ram']
    require(set(value)=={'schema','package_lock','observer','inittab_sha256','members'} and
            value['schema']==SCHEMA and type(manifest['vm']) is bool, 'Debian RAM schema differs')
    require(value['inittab_sha256']==hashlib.sha256(INITTAB).hexdigest(), 'Debian inittab identity differs')
    require(set(value['members'])==set(MEMBERS), 'Debian member declaration differs')
    root=Path(manifest['init']['path']).parent.parent.parent
    files={}
    for name,(package,expected) in MEMBERS.items():
        data=(root/name).read_bytes()
        require(value['members'][name]==dict(package=package,sha256=expected,size=len(data)) and
                hashlib.sha256(data).hexdigest()==expected, 'fixed Debian runtime bytes differ')
        files[name]=data
    observer=value['observer']; path=Path(observer['path'])
    require(path==root/OBSERVER and pin(path)==observer and observer['size']<=4*1024*1024,
            'Debian observer identity differs')
    files[OBSERVER]=path.read_bytes();files['etc/inittab']=(root/'etc/inittab').read_bytes()
    require(manifest['init']['sha256']==MEMBERS['usr/sbin/init'][1], 'packaged PID1 identity differs')
    lock=value['package_lock'];require(pin(lock['path'])==lock, 'signed package receipt changed')
    packages=json.loads(Path(lock['path']).read_text())
    require(packages['verdict']=='PASS_SIGNED_PACKAGE_CLOSURE_H0' and packages['count']==4 and
            len(packages['packages'])==4 and
            {r['package']:(r['version'],r['sha256']) for r in packages['packages']}==PACKAGES and
            all(r['architecture']=='arm64' for r in packages['packages']), 'signed package closure differs')
    archive=Path(manifest['initramfs']['path'])
    require(archive.stat().st_size<=8*1024*1024 and pin(archive)==manifest['initramfs'], 'Debian archive changed')
    # Compare canonical bytes, rather than only data, to bind rdev, mode,
    # owner, symlinks, names and the absence of any extra archive member.
    require(archive.read_bytes()==gzip.compress(pack(files,manifest['vm']),mtime=0), 'Debian CPIO bytes differ')
    return value
