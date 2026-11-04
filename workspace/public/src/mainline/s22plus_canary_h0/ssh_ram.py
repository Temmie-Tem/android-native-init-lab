"""Fixed packaged OpenSSH in Debian RAM; pure closure, command and proof rules."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

if __package__:
    from . import debian_ram as base
else:
    import debian_ram as base

require=base.require
pin=base.pin
SCHEMA='s22plus-mainline-debian-ssh-ram-v1'
PACKAGES = {'dash': ('0.5.12-12', 'ce4c8688a1a3ea510186ba95aba74d4c49863094e47e1effc0b602839e840c04'),
 'libaudit1': ('1:4.0.2-2+deb13u1', '3472a1d77e36832ea0bb6509153c721ffc46a96aa0bc25073e7b95571df16196'),
 'libc6': ('2.41-12+deb13u4', '8784eda966b189c777a384dac5ce009e8fc9b52d006926c5a013e7fa8aa688cc'),
 'libcap-ng0': ('0.8.5-4+b1', 'eb6da83296e4710a8600c1426692ed9b9eadcab7ebd36dbabc2a562b5c1ab691'),
 'libcom-err2': ('1.47.2-3+b12', '1acba7e14a17a3f4b8008454e1a75840a5cdff4259d3c1d369092d82089ea0d8'),
 'libcrypt1': ('1:4.4.38-1', 'b9aaa808aa3812b3de3e54eb5dfb16762c1779db032604abef2354c02fdc29b8'),
 'libgssapi-krb5-2': ('1.21.3-5+deb13u1', '70803e8f5b9dd0a7167671bdd0b3cd05642384c1fc49e8270d340d85bf6c7d4c'),
 'libk5crypto3': ('1.21.3-5+deb13u1', '2453e8d4fa3b91b868d5bc10e84a15ad9c7bc4e4cb49379cb1f560bdce50db4a'),
 'libkeyutils1': ('1.6.3-6', '5e680f317a6613161986417fb3ed63007c9228343f5ac2348551b103cc7fd7b4'),
 'libkrb5-3': ('1.21.3-5+deb13u1', '1f5c46480abf894f662d894696c8a6c6510c2b20616cd453e88b27b11d3be25d'),
 'libkrb5support0': ('1.21.3-5+deb13u1', '6381bcb54e58854f9ebac2dfa580c3d6112d01b4ca3f725e7263b9374f79608e'),
 'libpam0g': ('1.7.0-5', '2dd0fdc9af8a8a48f0a54581f74005d4d8623baa8aea9ac3d201624c3217b6d3'),
 'libpcre2-8-0': ('10.46-1~deb13u2', 'e7d2c997dac145c16457be0fed3d084c98cd030bec7633eec7e5bde6dbb97712'),
 'libselinux1': ('3.8.1-1', 'fc13da4c7783b8f4361d92ef1045931f298d1b0ac78ed1a85c2232615f49fc6f'),
 'libsqlite3-0': ('3.46.1-7+deb13u2', '5b09efca71cb7a16d67f5453af3989ae1a84fe6b68c6dd3913de527cb0ca23aa'),
 'libssl3t64': ('3.5.7-1~deb13u2', 'ec131326aa9fa9ec934eca386bc7991f328fe383eaefd3e43bd8901a9199c5ae'),
 'libwrap0': ('7.6.q-36', 'fd2e54582a07fba9c8a6f78c68dcc6d3c8cf1c70632a68124394bde4dccf52ea'),
 'libwtmpdb0': ('0.73.0-3+deb13u1', '6c1e8bcf1192048b0c4d4fcff83debda41b609a0917017aa3faeb47401b1a62e'),
 'libzstd1': ('1.5.7+dfsg-1', '924540bd59fdbfa77a0604360efdaca54411a43daf11c7e002a3c64791b67448'),
 'openssh-server': ('1:10.0p1-7+deb13u4', '6da10564d3747e5f8fcca9595e154d863fdef786c3384ccd24e518c1fc45e41d'),
 'sysvinit-core': ('3.14-4', '80200c6959e5a3022535e1b33497bfa3b8d7694366497566c7f3bae34f943362'),
 'zlib1g': ('1:1.3.dfsg+really1.3.1-1+b1',
            '209aa5cf671e97b9eb0410844fa6df4cae2e75b0c72e7802ab6c8ece13e6ddef')}
MEMBERS = {'usr/bin/dash': ('dash', '367967c823a0c391e5049b15a67c6a0a629c88b9b6dcdca75ef13ac9d65334b1'),
 'usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1': ('libc6',
                                                     '1b882eddacd494b060413a8aa4f0a4754ee3f84775e68cecbf8a86092b59cca6'),
 'usr/lib/aarch64-linux-gnu/libaudit.so.1.0.0': ('libaudit1',
                                                 '56ed9de372c2734b56af41dfcf31c8a38494bb38317f4e4759b8014a4307a25b'),
 'usr/lib/aarch64-linux-gnu/libc.so.6': ('libc6',
                                         '70fa4c4cf57eabeb96097cce47582d02379c4cd1de3db3e98ade4dd7089a1b13'),
 'usr/lib/aarch64-linux-gnu/libcap-ng.so.0.0.0': ('libcap-ng0',
                                                  'dae52ebda1d10beeb0e49c18b6a986833808fcedce81d37639f3882297574422'),
 'usr/lib/aarch64-linux-gnu/libcom_err.so.2.1': ('libcom-err2',
                                                 '6a3258ad8e42f54f4333b8a5b6c671922a4482d261a89f75114b0de3ef565013'),
 'usr/lib/aarch64-linux-gnu/libcrypt.so.1.1.0': ('libcrypt1',
                                                 'fc0165e3cbff299baa266b5531ac9054fff35786bf3ffa46f6eae5650d9bd8c8'),
 'usr/lib/aarch64-linux-gnu/libcrypto.so.3': ('libssl3t64',
                                              'ad2d83bfb64c15110615fbee4161ee2cbe890abe0c924c459f63f89d4085940d'),
 'usr/lib/aarch64-linux-gnu/libgssapi_krb5.so.2.2': ('libgssapi-krb5-2',
                                                     '967b9c108b49481f6cc1358d675a6c1b16754254c84c421c43a5814010e2a215'),
 'usr/lib/aarch64-linux-gnu/libk5crypto.so.3.1': ('libk5crypto3',
                                                  '950c7c9c2da1d5ebaae583a6c4da6b9b41bbbee6a4a8f848a868c0e106fe9335'),
 'usr/lib/aarch64-linux-gnu/libkeyutils.so.1.10': ('libkeyutils1',
                                                   '729c2c3578b96763a2e7148ad5a26f0136958025dff0f309e4267f09b9f61a4a'),
 'usr/lib/aarch64-linux-gnu/libkrb5.so.3.3': ('libkrb5-3',
                                              'deb1db5877ee7535d8434003404b4a4e181ab660a9e5370ba66c4b8e759e1111'),
 'usr/lib/aarch64-linux-gnu/libkrb5support.so.0.1': ('libkrb5support0',
                                                     '265157c5541d3cc73f5bb5cf43e8a58e996a25211d716a9ab2ba65b1a787633a'),
 'usr/lib/aarch64-linux-gnu/libm.so.6': ('libc6',
                                         'a8afb2d1f4a0c5e14c0fc82f794ec839eafe29738907aa92895410f57630bbe2'),
 'usr/lib/aarch64-linux-gnu/libpam.so.0.85.1': ('libpam0g',
                                                '158c36c6c27ba44b04610bae1846602b9bf71f62010d54ad7fd447b23e3004a4'),
 'usr/lib/aarch64-linux-gnu/libpcre2-8.so.0.14.0': ('libpcre2-8-0',
                                                    '97b4e0f33829849a806c2d322f2febcd06c0cd5b22bff8c9422bf238ec265f75'),
 'usr/lib/aarch64-linux-gnu/libresolv.so.2': ('libc6',
                                              'cb9756963306434c0fbe3351ded4041a5cc6e6ce37efc175de1093e13b3747fc'),
 'usr/lib/aarch64-linux-gnu/libselinux.so.1': ('libselinux1',
                                               '18a3d9b827b34c87c51cd5954868a8bf9aa206717b414987074b5fb11f74e952'),
 'usr/lib/aarch64-linux-gnu/libsqlite3.so.0.8.6': ('libsqlite3-0',
                                                   '203e52aaa9cfa34eab0f4ea46b434e8a69031610a46d72c2f7886389990468a1'),
 'usr/lib/aarch64-linux-gnu/libwrap.so.0.7.6': ('libwrap0',
                                                '961f48b0d807ffdbdf8971b7e13f04409a4bc639cff3ea42defbd850b6ca739d'),
 'usr/lib/aarch64-linux-gnu/libwtmpdb.so.0.73.0': ('libwtmpdb0',
                                                   'a3e39d5725babc0e1aa3292901e2681925b718a3a674b39e98f83ae17762fb94'),
 'usr/lib/aarch64-linux-gnu/libz.so.1.3.1': ('zlib1g',
                                             '6fe00acadf8119ff245855e5dcc7f26c6c0ffaf4bfa2baa88feab58f23727d65'),
 'usr/lib/aarch64-linux-gnu/libzstd.so.1.5.7': ('libzstd1',
                                                '1279c4edfbfb08878b5b7fb40d392c1bdc9b30100d9b7a019d4aefaf10d2046c'),
 'usr/lib/openssh/sshd-auth': ('openssh-server',
                               'd3eb764862972211a3820b80c0898f41b27fff2710e6c4d14e776b5ae29a8394'),
 'usr/lib/openssh/sshd-session': ('openssh-server',
                                  '647ae62a77122195cc209503b7f835fea48ef50a72e76ac49241a801a1aea278'),
 'usr/sbin/init': ('sysvinit-core', '85c1d3dcd4d36b3ecfd44cb9dcce8ce068569b1a96b8a1024a6507807d7a48d5'),
 'usr/sbin/sshd': ('openssh-server', '92ab0b03133151a40e95fabd42059450ed00ba4de0e07e8f2b73ce320f2bb077')}
DIRS = ('.',
 'config',
 'dev',
 'etc',
 'etc/ssh',
 'home',
 'home/probe',
 'proc',
 'root',
 'run',
 'run/sshd',
 'sys',
 'usr',
 'usr/bin',
 'usr/lib',
 'usr/lib/aarch64-linux-gnu',
 'usr/lib/openssh',
 'usr/libexec',
 'usr/sbin',
 'var',
 'var/log')
LINKS = {'bin': 'usr/bin',
 'init': 'usr/sbin/init',
 'lib': 'usr/lib',
 'sbin': 'usr/sbin',
 'usr/lib/aarch64-linux-gnu/libaudit.so.1': 'libaudit.so.1.0.0',
 'usr/lib/aarch64-linux-gnu/libcap-ng.so.0': 'libcap-ng.so.0.0.0',
 'usr/lib/aarch64-linux-gnu/libcom_err.so.2': 'libcom_err.so.2.1',
 'usr/lib/aarch64-linux-gnu/libcrypt.so.1': 'libcrypt.so.1.1.0',
 'usr/lib/aarch64-linux-gnu/libgssapi_krb5.so.2': 'libgssapi_krb5.so.2.2',
 'usr/lib/aarch64-linux-gnu/libk5crypto.so.3': 'libk5crypto.so.3.1',
 'usr/lib/aarch64-linux-gnu/libkeyutils.so.1': 'libkeyutils.so.1.10',
 'usr/lib/aarch64-linux-gnu/libkrb5.so.3': 'libkrb5.so.3.3',
 'usr/lib/aarch64-linux-gnu/libkrb5support.so.0': 'libkrb5support.so.0.1',
 'usr/lib/aarch64-linux-gnu/libpam.so.0': 'libpam.so.0.85.1',
 'usr/lib/aarch64-linux-gnu/libpcre2-8.so.0': 'libpcre2-8.so.0.14.0',
 'usr/lib/aarch64-linux-gnu/libsqlite3.so.0': 'libsqlite3.so.0.8.6',
 'usr/lib/aarch64-linux-gnu/libwrap.so.0': 'libwrap.so.0.7.6',
 'usr/lib/aarch64-linux-gnu/libwtmpdb.so.0': 'libwtmpdb.so.0.73.0',
 'usr/lib/aarch64-linux-gnu/libz.so.1': 'libz.so.1.3.1',
 'usr/lib/aarch64-linux-gnu/libzstd.so.1': 'libzstd.so.1.5.7',
 'usr/lib/ld-linux-aarch64.so.1': 'aarch64-linux-gnu/ld-linux-aarch64.so.1',
 'var/run': '../run'}
FIXED = {'etc/group': b'root:x:0:\nnogroup:x:65534:\nprobe:x:1000:\n',
 'etc/inittab': b'id:2:initdefault:\nr2:2:once:@/usr/libexec/g0q-ram-observer\nsh:2:once:@/usr/sbin/sshd -D '
                b'-e -f /etc/ssh/sshd_config\n',
 'etc/nsswitch.conf': b'passwd: files\ngroup: files\nshadow: files\nhosts: files\n',
 'etc/passwd': b'root:x:0:0:root:/root:/usr/bin/dash\nsshd:x:101:65534:sshd:/run/sshd:/usr/sbin/nologin\npr'
               b'obe:x:1000:1000:probe:/home/probe:/usr/bin/dash\n',
 'etc/shadow': b'root:!:0:0:99999:7:::\nsshd:!:0:0:99999:7:::\nprobe:NP:0:0:99999:7:::\n',
 'etc/ssh/sshd_config': b'Port 22\nAddressFamily inet\nListenAddress 0.0.0.0\nHostKey /etc/ssh/ssh_host_ed255'
                        b'19_key\nPidFile /run/sshd.pid\nUsePAM no\nPermitRootLogin no\nAllowUsers probe\nP'
                        b'asswordAuthentication no\nKbdInteractiveAuthentication no\nGSSAPIAuthentication no'
                        b'\nHostbasedAuthentication no\nPubkeyAuthentication yes\nAuthenticationMethods publi'
                        b'ckey\nAuthorizedKeysFile /etc/ssh/authorized_keys\nStrictModes yes\nDisableForwardi'
                        b'ng yes\nPermitTTY no\nPermitTunnel no\nPermitUserRC no\nPermitUserEnvironment no'
                        b'\nX11Forwarding no\nMaxAuthTries 1\nMaxSessions 1\nMaxStartups 1\nLoginGraceTime '
                        b'15\nUseDNS no\nPrintMotd no\nPrintLastLog no\nLogLevel ERROR\nForceCommand /usr/l'
                        b'ibexec/g0q-ssh-probe\n',
 'usr/libexec/g0q-ssh-probe': b'#!/usr/bin/dash\nset -eu\nIFS= read -r boot </proc/sys/kernel/random/boot_'
                              b'id\nprintf \'G0Q_SSH_RAM_V1\\nboot_id=%s\\n\' "$boot"\nwhile IFS=\' \t\' read'
                              b' -r key value; do\n    case "$key" in\n        Uid:|Gid:|Groups:|CapEff:) '
                              b'printf \'%s %s\\n\' "$key" "$value" ;;\n    esac\ndone </proc/self/status\n'}
INITTAB=FIXED['etc/inittab']
KEY_NAMES=('host-key','host-key.pub','client-key','client-key.pub')
MODES={name:0o644 for name in FIXED}
MODES.update({'usr/libexec/g0q-ssh-probe':0o755,'etc/shadow':0o600,
              'etc/ssh/ssh_host_ed25519_key':0o600,'etc/ssh/authorized_keys':0o644})


def public_key(data):
    require(len(data)<=256 and data.endswith(b'\n'), 'SSH public key shape')
    fields=data.rstrip(b'\n').split(b' ')
    require(len(fields) in (2,3) and fields[0]==b'ssh-ed25519', 'SSH key algorithm')
    try:raw=base64.b64decode(fields[1],validate=True)
    except ValueError as error:raise ValueError('SSH public key encoding') from error
    require(len(raw)==51 and raw[:19]==b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' and
            base64.b64encode(raw)==fields[1], 'SSH Ed25519 public key bytes')
    return b' '.join(fields[:2])


def key_inputs(folder):
    paths=[Path(folder)/name for name in KEY_NAMES]
    for path in paths:
        require(path.is_file() and not path.is_symlink() and path.stat().st_size<=4096,
                'fixed private SSH key input missing')
    require(public_key(paths[1].read_bytes())!=public_key(paths[3].read_bytes()), 'SSH host/client keys must differ')
    return paths


def generate_keys(folder):
    folder=Path(folder).resolve()
    require(folder.is_relative_to(base.ROOT/'workspace/private'), 'private SSH keys required')
    folder.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name in ('host-key','client-key'):
        subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-C','g0q-ram-'+name,
                        '-f',str(folder/name)],check=True)
        generated=subprocess.check_output(['/usr/bin/ssh-keygen','-y','-f',str(folder/name)])
        require(public_key(generated)==public_key((folder/(name+'.pub')).read_bytes()), 'SSH key pair differs')
        (folder/name).chmod(0o400);(folder/(name+'.pub')).chmod(0o400)
    key_inputs(folder)


def specification():
    names=set(MEMBERS)|set(FIXED)|{'etc/ssh/ssh_host_ed25519_key','etc/ssh/authorized_keys'}
    return names,INITTAB,DIRS,LINKS,MODES


def files_with_keys(files,keys):
    files=dict(files);files.update(FIXED)
    files['etc/ssh/ssh_host_ed25519_key']=Path(keys['host-key']['path']).read_bytes()
    files['etc/ssh/authorized_keys']=b'restrict '+public_key(Path(keys['client-key.pub']['path']).read_bytes())+b'\n'
    return files


def declaration(files,observer,package_lock,folder):
    keys={p.name:pin(p) for p in key_inputs(folder)}
    return dict(schema=SCHEMA,package_lock=package_lock,observer=pin(observer),
        inittab_sha256=hashlib.sha256(INITTAB).hexdigest(),keys=keys,
        members={n:dict(package=MEMBERS[n][0],sha256=hashlib.sha256(files[n]).hexdigest(),size=len(files[n]))
                 for n in MEMBERS})


def validate(manifest):
    value=manifest['debian_ram']
    require(set(value)=={'schema','package_lock','observer','inittab_sha256','members','keys'} and
            value['schema']==SCHEMA and type(manifest['vm']) is bool, 'SSH RAM schema differs')
    require(value['inittab_sha256']==hashlib.sha256(INITTAB).hexdigest() and
            set(value['members'])==set(MEMBERS) and set(value['keys'])==set(KEY_NAMES), 'SSH RAM fixed declaration differs')
    for name,key in value['keys'].items():
        require(Path(key['path']).name==name and pin(key['path'])==key and key['size']<=4096,
                'SSH key identity differs')
    require(len({str(Path(key['path']).parent) for key in value['keys'].values()})==1, 'SSH key set is split')
    key_inputs(Path(value['keys']['host-key']['path']).parent)
    root=Path(manifest['init']['path']).parent.parent.parent;files={}
    for name,(package,expected) in MEMBERS.items():
        data=(root/name).read_bytes()
        require(value['members'][name]==dict(package=package,sha256=expected,size=len(data)) and
                hashlib.sha256(data).hexdigest()==expected, 'signed SSH RAM member differs')
        files[name]=data
    observer=value['observer'];path=Path(observer['path'])
    require(path==root/base.OBSERVER and pin(path)==observer and observer['size']<=4*1024*1024,
            'SSH RAM observer differs')
    files[base.OBSERVER]=path.read_bytes();files=files_with_keys(files,value['keys'])
    require(manifest['init']['sha256']==MEMBERS['usr/sbin/init'][1], 'packaged PID1 identity differs')
    lock=value['package_lock'];require(pin(lock['path'])==lock, 'SSH signed package receipt changed')
    packages=json.loads(Path(lock['path']).read_text())
    require(packages['verdict']=='PASS_SIGNED_PACKAGE_CLOSURE_H0' and packages['count']==len(PACKAGES) and
            len(packages['packages'])==len(PACKAGES) and
            {r['package']:(r['version'],r['sha256']) for r in packages['packages']}==PACKAGES and
            all(r['architecture']=='arm64' for r in packages['packages']), 'SSH signed package closure differs')
    archive=Path(manifest['initramfs']['path'])
    require(archive.stat().st_size<=16*1024*1024 and pin(archive)==manifest['initramfs'], 'SSH RAM archive changed')
    require(archive.read_bytes()==gzip.compress(base.pack(files,manifest['vm'],specification=specification()),mtime=0),
            'SSH RAM CPIO bytes, ownership, modes or membership differ')
    return value


def known_hosts(runtime):
    return b'g0q-ram-candidate '+public_key(Path(runtime['keys']['host-key.pub']['path']).read_bytes())+b'\n'


def command(runtime,ssh,known,host,*,port=22,source=None):
    argv=[str(ssh),'-F','/dev/null','-T','-n','-p',str(port),'-i',runtime['keys']['client-key']['path']]
    options=('HostKeyAlias=g0q-ram-candidate','BatchMode=yes','IdentitiesOnly=yes','IdentityAgent=none',
        'StrictHostKeyChecking=yes','UserKnownHostsFile='+str(known),'GlobalKnownHostsFile=/dev/null',
        'ConnectionAttempts=1','ConnectTimeout=5','ClearAllForwardings=yes','ControlMaster=no','ControlPath=none',
        'ProxyCommand=none','ProxyJump=none','RequestTTY=no','LogLevel=ERROR','PreferredAuthentications=publickey',
        'PasswordAuthentication=no','KbdInteractiveAuthentication=no','HostKeyAlgorithms=ssh-ed25519',
        'PubkeyAcceptedAlgorithms=ssh-ed25519','UpdateHostKeys=no','EscapeChar=none')
    for option in options:argv+=['-o',option]
    if source is not None:argv+=['-b',source]
    return argv+['probe@'+host,'g0q-ram-probe-v1']


def parse_stdout(data,boot_id):
    require(len(data)<=1024 and re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id),
            'SSH output/boot identity shape')
    wanted=(b'G0Q_SSH_RAM_V1\nboot_id='+boot_id.encode()+b'\n'+
            rb'Uid: 1000[ \t]+1000[ \t]+1000[ \t]+1000\n'+
            rb'Gid: 1000[ \t]+1000[ \t]+1000[ \t]+1000\n'+
            rb'Groups: 1000[ \t]*\nCapEff: 0000000000000000\n')
    require(re.fullmatch(wanted,data) is not None, 'SSH same-boot unprivileged proof differs')
    return dict(status='AUTHENTICATED_DEBIAN_SSH_RAM',boot_id=boot_id,uid=1000,gid=1000,
                supplementary_groups=[1000],effective_capabilities=0,general_commands=False)


VM_CASES=('positive','wrong-key','root','forced-command','pty','forwarding','sftp')


def vm_command(runtime,ssh,known,port,case,folder):
    """Pure H0 client perturbations, never selected by the physical owner."""
    require(case in VM_CASES,'unselected SSH VM case')
    argv=command(runtime,ssh,known,'127.0.0.1',port=port,source='127.0.0.1')
    if case=='wrong-key':argv[argv.index('-i')+1]=str(Path(folder)/'wrong-key')
    if case=='root':argv[-2]='root@127.0.0.1'
    if case=='forced-command':argv[-1]='printf FORBIDDEN_COMMAND_EXECUTED'
    if case=='pty':
        argv[argv.index('-T')]='-tt';argv[argv.index('RequestTTY=no')]='RequestTTY=force'
    if case=='forwarding':
        argv[argv.index('LogLevel=ERROR')]='LogLevel=VERBOSE'
        argv=argv[:-2]+['-W','127.0.0.1:22',argv[-2]]
    if case=='sftp':argv=argv[:-2]+['-s',argv[-2],'sftp']
    return argv


def vm_outcome(handle,boot_id,case):
    import device_action_raw_capture_v1 as raw
    require(case in VM_CASES and not handle.timed_out and not handle.output_exceeded and
            handle.producer_error_type is None,'incomplete SSH VM producer')
    stdout=raw.read_stdout(handle,maximum=1024);stderr=raw.read_stderr(handle,maximum=16384)
    if case in ('positive','forced-command'):
        raw.require_success(handle);require(not stderr,'VM SSH diagnostics')
        return parse_stdout(stdout,boot_id)
    expected={'wrong-key':b'Too many authentication failures','root':b'Too many authentication failures',
              'pty':b'PTY allocation request failed','forwarding':b'administratively prohibited',
              'sftp':b'subsystem request failed'}
    require(handle.returncode==255 and not stdout and expected[case] in stderr,'SSH negative case did not reject')
    return dict(status='PASS_H0_SSH_REJECTED',case=case)


def recheck_vm(folder,manifest,boot_id,*,case='positive'):
    """Reinterpret complete original SSH capture; never start a client."""
    import sys
    sys.path.insert(0,str(base.ROOT/'workspace/public/src/scripts/revalidation'))
    import device_action_raw_capture_v1 as raw
    folder=Path(folder);runtime=manifest['debian_ram']
    handle=raw.load_handle(folder/'ssh.capture.json')
    require((folder/'known-hosts').read_bytes()==known_hosts(runtime),'VM host key pin differs')
    saved=json.loads((folder/'ssh-command.json').read_text())
    qemu=json.loads((folder/'command.json').read_text())['command']
    forwards=re.findall(r',hostfwd=tcp:127\.0\.0\.1:([0-9]+)-:22(?:,|$)',qemu[qemu.index('-netdev')+1])
    require(len(forwards)==1 and 0<int(forwards[0])<65536,'VM SSH loopback forward differs')
    fields={'argv','executable','case'}|({'wrong_key'} if case=='wrong-key' else set())
    require(set(saved)==fields and saved['case']==case and saved['executable']['path']=='/usr/bin/ssh' and
            saved['argv']==vm_command(runtime,'/usr/bin/ssh',folder/'known-hosts',int(forwards[0]),case,folder),
            'VM SSH client command differs')
    if case=='wrong-key':require(saved['wrong_key']==pin(folder/'wrong-key'),'wrong-key fixture changed')
    return dict(proof=vm_outcome(handle,boot_id,case),
                executable=saved['executable'],ssh_capture=pin(handle.receipt_path))


def check_case(folder,manifest,manifest_pin,kernel,case):
    """Bind an SSH case to the same real CPIO/kernel and complete raw streams."""
    import sys
    sys.path.insert(0,str(base.ROOT/'workspace/public/src/scripts/revalidation'))
    import device_action_raw_capture_v1 as raw
    if __package__:
        from . import verify
    else:
        import verify
    folder=Path(folder);capture=json.loads((folder/'capture.json').read_text())
    result=json.loads((folder/'result.json').read_text())
    require(capture['schema']=='g0q-h0-vm-capture-v1' and capture['bad_key'] is False and
            capture['device_actions']==0 and capture['qemu_returncode'] in (0,-15,-9) and
            capture['inputs']['manifest']=={k:manifest_pin[k] for k in ('path','sha256')} and
            capture['inputs']['kernel']=={k:kernel[k] for k in ('path','sha256')}, 'SSH VM capture input differs')
    handle=raw.load_handle(folder/'ssh.capture.json')
    required={'command.json','nonce.bin','request.raw','response.raw','serial.log','qemu.stderr','known-hosts',
              'ssh-command.json',handle.receipt_path.name,handle.stdout_path.name,handle.stderr_path.name}
    require(set(capture['evidence'])==required,'SSH VM capture incomplete')
    for name,expected in capture['evidence'].items():
        require(Path(name).name==name and base.digest(folder/name)==expected,'SSH VM raw evidence changed')
    require({'vm.py','vm_evidence.py','ssh_ram.py','verify.py','device_action_raw_capture_v1.py'}<=set(capture['source']),
            'SSH VM producer source incomplete')
    for name,expected in capture['source'].items():
        require(Path(name).name==name and base.digest(folder/'source'/name)==expected,'SSH VM source changed')
    nonce=(folder/'nonce.bin').read_bytes();key=Path(manifest['key_path']).read_bytes()
    require((folder/'request.raw').read_bytes()==verify.request(key,bytes.fromhex(manifest['candidate_id']),nonce,manifest=manifest),
            'SSH VM base request differs')
    data=(folder/'response.raw').read_bytes();body=data[:352]
    import hmac,uuid
    require(len(data)>=384 and body[:8]==b'G0QSRS1\0' and body[8:40].hex()==manifest['candidate_id'] and
            body[40:72]==nonce and hmac.compare_digest(data[352:384],verify.tag(key,bytes.fromhex(manifest['candidate_id']),1,body,manifest=manifest)) and
            body[276:280]==b'\x01\x00\x00\x00','SSH VM base proof authentication/readiness differs')
    boot_id=str(uuid.UUID(bytes=body[72:88]))
    checked=recheck_vm(folder,manifest,boot_id,case=case)
    require(result['status']=='PASS_H0_VM_DEBIAN_SYSVINIT_RAM' and result['runtime_schema']==SCHEMA and
            result['ssh_case']==case and result['ssh_ready'] is True and result['ssh']==checked['proof'] and
            result['boot_id']==boot_id and result['kernel_sha256']==kernel['sha256'] and
            result['raw_sha256']==hashlib.sha256(data).hexdigest() and result['device_actions']==0,
            'SSH VM result differs from captured evidence')
    return dict(capture=pin(folder/'capture.json'),result=pin(folder/'result.json'),**checked)
