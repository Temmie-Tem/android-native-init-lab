"""Exact signed Debian rc2/rc6 SSH service cycle; no acquisition or execution entry."""
import hashlib
import hmac
import struct
import uuid

if __package__:
    from . import ssh_ram, download_ram
else:
    import ssh_ram, download_ram

SCHEMA='s22plus-mainline-debian-rc-ssh-ram-v1'
DOMAIN=b'G0Q-DEBIAN-RC-SSH-RAM-v1'
CONTROL_MAGIC=b'G0QRCQ1\0'
ACK_MAGIC=b'G0QRCA1\0'
CONTROL_SIZE=88
ACK_FIELDS=struct.Struct('<8I2Q')
ACK_SIZE=120+ACK_FIELDS.size
require=ssh_ram.require
PACKAGES=ssh_ram.PACKAGES|{'coreutils': ('9.7-3', '99b2531e8d16e4f2d3f239ae3cb57913ec1f43764d2d6cd5c69154cbb1e57f3e'),
 'debianutils': ('5.23.2', '662d59d9cd0d46f0250ddcd997353be915fbc6be692d7c676c73dc33c90715e8'),
 'dpkg': ('1.22.22', '1142468e57f69e13d174f517dff739508c61ee97d81c182c120cd6b281d8cdfa'),
 'grep': ('3.11-4+b1', '6f7257fbec0197bd54b2347861ff01e2c4e8411790b0df20242483615324fe66'),
 'sysv-rc': ('3.14-4', '05bae4fc83f9063940778429a60f30e844a862822f0cd2a15c51a11fe9841dce'),
 'sysvinit-utils': ('3.14-4', '1366e87a382a6b95a0a7c507b8f1be9b193f772f3428f9f7e0271a217915cfae')}
ARCHES={'sysv-rc': 'all'}
MEMBERS=ssh_ram.MEMBERS|{'etc/init.d/ssh': ('openssh-server', 'aa7a68603ff32afc694615fea4fc2781487acd88971dfd750d0f39b8c5cc1295'),
 'usr/bin/grep': ('grep', '4c00d38d6c66bd4e66aeffcf92a87ff40a981ef5e58bacc4a7677ea05c664804'),
 'usr/bin/run-parts': ('debianutils', '18ce6259e35cd89bcb0e766bfca82adcf71882d962b5080919c05217b5a2297b'),
 'usr/bin/stty': ('coreutils', '632b8bf557b2b2dfde99c3f5909ea3038dbd41bcd8eb133c230ae5ac02df2dc7'),
 'usr/lib/init/rc': ('sysv-rc', '4d635aada7b8bc96bf84a7d9c7799b98125556d8919a9b32a3e8ab22ccb2b035'),
 'usr/lib/lsb/init-functions': ('sysvinit-utils',
                                'f58bfadf2419d6036a2c7440e574c3c3e7a35aea380375f6ab1b590d64e5e952'),
 'usr/sbin/start-stop-daemon': ('dpkg', '6a6a2ca41d3c2c1f0cc91dfcd87bc5da0fdd10c25d9710c527a014223cc04f53')}
INITTAB=(b'id:2:initdefault:\nm2:2:wait:@/usr/libexec/g0q-ram-observer mounts\n'
         b'l2:2:wait:@/usr/libexec/g0q-ram-observer rc 2\n'
         b'ob:26:once:@/usr/libexec/g0q-ram-observer\n'
         b'l6:6:wait:@/usr/libexec/g0q-ram-observer rc 6\n')
WRAPPER='etc/init.d/g0q-ssh-cycle'
FIXED=ssh_ram.FIXED|{'etc/inittab':INITTAB,
    WRAPPER:b'#!/usr/bin/dash\nexec /usr/libexec/g0q-ram-observer service "$@"\n'}
LINKS=ssh_ram.LINKS|{'usr/bin/sh':'dash','etc/rc2.d/S01ssh':'../init.d/g0q-ssh-cycle',
    'etc/rc6.d/K01ssh':'../init.d/g0q-ssh-cycle'}
DIRS=tuple(sorted(set(ssh_ram.DIRS)|{'etc/init.d','etc/rc2.d','etc/rc6.d','usr/lib/init','usr/lib/lsb','usr/lib/lsb/init-functions.d'}))
MODES=ssh_ram.MODES|{WRAPPER:0o755,'usr/lib/lsb/init-functions':0o644}


def specification():
    return set(MEMBERS)|set(FIXED)|{'etc/ssh/ssh_host_ed25519_key','etc/ssh/authorized_keys'},INITTAB,DIRS,LINKS,MODES


def scope():
    return dict(schema=SCHEMA,service='ssh',runlevels=[2,6],ssh_sessions=1,control_requests=1,
        init6_invocations=1,restart2_calls=1,normal_download=True,full_system_shutdown=False,
        automatic_failure_recovery=False,linux_storage=False,observer_deadline_ms=120000)


def tag(key,identity,kind,payload):
    require(len(key)==len(identity)==32,'service authentication identity')
    return hmac.new(key,DOMAIN+identity+bytes([kind])+payload,hashlib.sha256).digest()


def control(key,identity,nonce,boot_id):
    require(len(nonce)==32 and uuid.UUID(boot_id).int!=0,'service command binding')
    head=CONTROL_MAGIC+nonce+uuid.UUID(boot_id).bytes
    return head+tag(key,identity,2,head)


def verify_ack(data,key,identity,nonce,boot_id,*,proof):
    require(len(data)==ACK_SIZE,'service receipt length')
    body,auth=data[:-32],data[-32:]
    require(body[:88]==ACK_MAGIC+identity+nonce+uuid.UUID(boot_id).bytes and
            hmac.compare_digest(auth,tag(key,identity,3,body)),'service receipt authentication')
    master,ticks,previous,level,script_rc,rc_rc,remaining,observer,stop_ms,end_ms=ACK_FIELDS.unpack(body[88:])
    require(master==proof['master_pid']>1 and ticks==proof['master_start_ticks']>0 and
            previous==2 and level==6 and script_rc==rc_rc==remaining==0 and observer==proof['responder_pid'] and
            proof['uptime_ms']<=stop_ms<=end_ms<120000,'service stop evidence differs')
    return dict(status='AUTHENTICATED_RC6_SSH_STOP',boot_id=boot_id,master_pid=master,master_start_ticks=ticks,
        previous_runlevel=previous,runlevel=level,stop_script_rc=script_rc,rc6_rc=rc_rc,remaining_ssh_processes=remaining,
        responder_pid=observer,stop_finished_ms=stop_ms,rc6_finished_ms=end_ms,restart_completed=False,download_arrival_proved=False)

frame_size=download_ram.frame_size
