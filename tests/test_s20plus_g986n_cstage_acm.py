"""Host-only checks for the exact C-stage gadget, socket handoff and bounded banner."""
from array import array
from contextlib import ExitStack
from datetime import datetime, timezone
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'workspace/public/src/scripts/revalidation'
sys.path.insert(0, str(SCRIPTS))
HAS_FIXTURE = (ROOT / 'workspace/private/analysis/s20plus-y2q-cstage-serial-20261127/packaged/pair.json').is_file()


@unittest.skipUnless(HAS_FIXTURE, 'private y2q source fixture required')
class ACM(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_cstage_acm as m
        self.m = m
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.usb, self.tty = self.root/'usb', self.root/'tty'
        self.node = '1-5.1'
        self.device = self.usb / self.node
        self.device.mkdir(parents=True)
        self.tty.mkdir()
        self.serial, self.banner = m.witness()
        for key,value in dict(product='S20+ y2q mainline witness',serial=self.serial,
                              idVendor='1d6b',idProduct='0104',busnum='1',devnum='7').items():
            (self.device/key).write_text(value+'\n')
        self.port = m.sha(('usb:'+self.node).encode())
        self.interface = self.device/(self.node+':1.0')
        self.interface.mkdir()
        (self.interface/'bInterfaceNumber').write_text('00\n')
        for key,value in [('bInterfaceClass','02'),('bInterfaceSubClass','02'),('bInterfaceProtocol','00')]:
            (self.interface/key).write_text(value)
        driver=self.root/'cdc_acm'
        driver.mkdir()
        (self.interface/'driver').symlink_to(driver, target_is_directory=True)
        endpoint = self.tty/'ttyACM9'
        endpoint.mkdir()
        (endpoint/'dev').write_text('166:9\n')
        (endpoint/'device').symlink_to(self.interface,target_is_directory=True)

    def lookup(self):
        return self.m.lookup(self.port,self.serial,self.usb,self.tty)

    def test_exact_gadget_and_usb_session(self):
        m = self.m
        old = self.lookup()
        self.assertEqual(old[0].tty_name, 'ttyACM9')
        self.assertIsNone(m.lookup('0'*64,self.serial,self.usb,self.tty))
        for key,value in [('product','other'),('serial','stale'),('idProduct','ffff')]:
            with self.subTest(key=key):
                p=self.device/key
                before=p.read_bytes()
                p.write_text(value)
                self.assertIsNone(self.lookup())
                p.write_bytes(before)
        (self.device/'devnum').write_text('8')
        self.assertNotEqual(self.lookup()[1],old[1])
        (self.interface/'bInterfaceProtocol').write_text('01')
        self.assertIsNone(self.lookup())
        (self.interface/'bInterfaceProtocol').write_text('00')
        (self.interface/'bInterfaceNumber').write_text('01')
        self.assertIsNone(self.lookup())

    def test_host_filter_override_rejected(self):
        m = self.m
        response = ('ActiveState=inactive\nMainPID=0\nFragmentPath=/usr/lib/systemd/system/ModemManager.service\n'
                    'DropInPaths=\nEnvironment=\nPassEnvironment=\nUnsetEnvironment=\n'
                    'ExecStart={ path=/usr/sbin/ModemManager ; argv[]=/usr/sbin/ModemManager ; ignore_errors=no }\n')
        with patch.object(subprocess, 'check_output', side_effect=[response, b'MM_FILTER_RULE_TTY=0\n']):
            with self.assertRaises(m.base.OWNER.Stop):
                m.host_serial_policy()
        with patch.object(subprocess, 'check_output', side_effect=[response, b'']):
            m.host_serial_policy()

    def test_raw_requires_real_distinct_session_bracket_and_exact_line(self):
        m = self.m
        intent=dict(binding_sha256='b'*64,topology_sha256=self.port,transfer_sha256='c'*64,start_us=1_000_000)
        for payload,after,state,ok in [
            (self.banner,'a'*64,'pid1_exact',True),
            (self.banner[:-1],'a'*64,'pid1_exact',False),
            (self.banner.replace(b'pid=1',b'pid=2'),'a'*64,'pid1_exact',False),
            (self.banner,'d'*64,'pid1_exact',False),
            (self.banner,'d'*64,'unproved',True),
            (b'X'*513,'a'*64,'unproved',False),
        ]:
            raw=dict(**intent,endpoint_before='a'*64,endpoint_after=after,state=state,verified_us=1_000_001,
                     stream_hex=payload.hex(),size=len(payload),stream_sha256=m.sha(payload))
            if ok:
                self.assertEqual(m.derive(raw,intent)['state'],state)
            else:
                with self.assertRaises(m.base.OWNER.Stop):
                    m.derive(raw,intent)

    def test_expired_setup_and_late_bracket_are_rejected(self):
        m = self.m
        with patch('fcntl.ioctl') as setup:
            with self.assertRaises(m.base.OWNER.Stop):
                m.bounded_read(-1,self.banner,0)
            setup.assert_not_called()
        intent = dict(binding_sha256='b'*64, topology_sha256=self.port, transfer_sha256='c'*64, start_us=1)
        raw = dict(**intent, endpoint_before='a'*64, endpoint_after='a'*64, state='pid1_exact',
                   verified_us=1+m.WINDOW*1_000_000, stream_hex=self.banner.hex(),
                   size=len(self.banner), stream_sha256=m.sha(self.banner))
        with self.assertRaises(m.base.OWNER.Stop):
            m.derive(raw,intent)

    def test_actual_hidden_child_receives_readonly_tty(self):
        m = self.m
        key, identity='b'*64,'a'*64
        master,slave=os.openpty()
        slave_path = os.ttyname(slave)
        os.close(slave)
        def close(fd):
            try: os.close(fd)
            except OSError: pass
        self.addCleanup(close,master)
        # A host PTY is a stand-in for the newly created devtmpfs ttyACM.
        ro=os.open(slave_path,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
        self.addCleanup(close,ro)
        host,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        py="""import os,sys,fcntl,time
import s20plus_g986n_cstage_acm as m
assert not os.path.exists('/dev/bus/usb')
fd=m.get_descriptor('b'*64,'a'*64)
assert fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDONLY
import tty
tty.setraw(fd)
print('ready',flush=True)
b=m.witness()[1]
assert b in m.bounded_read(fd,b,time.monotonic()+4)
os.close(fd)
"""
        cmd=m.base.view.command(observe=False)
        cmd.insert(1,'--unshare-net')
        cmd[-1]=py
        with host, child, subprocess.Popen(cmd,stdin=child,stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,env=m.base.view.clean_environment()) as proc:
            child.close()
            host.settimeout(5)
            self.assertEqual(host.recv(100),(key+':open').encode())
            host.sendmsg([identity.encode()],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array('i',[ro]))])
            self.assertEqual(proc.stdout.readline(),b'ready\n')
            os.write(master,b'short\n'+self.banner)
            stdout,stderr=proc.communicate(timeout=6)
            self.assertEqual(proc.returncode,0,stderr)

    def test_open_fails_before_access_to_device(self):
        m=self.m
        r=self.root/'run-1111111111111111111'
        t=self.root/'ticket-1111111111111111111'
        r.mkdir()
        t.mkdir()
        outer=dict(issued=1,expires=1000)
        grant=m.sha(m.canonical(outer))
        approval=m.base.PREFIX+grant
        intent=dict(binding_sha256='c'*64,topology_sha256=self.port,transfer_sha256='d'*64,start_us=1_000_000)
        def write(path,obj):
            path.write_bytes(m.canonical(obj))
            path.chmod(0o400)
        write(r/'prepared.json',{})
        write(t/'prepared.json',outer)
        write(t/'accepted.json',dict(grant_sha256=grant,approved_at=5,approval_sha256=m.sha(approval.encode())))
        write(t/'acm-intent.json',intent)
        write(r/'candidate-observation-intent.json',dict(binding_sha256=intent['binding_sha256'],
             at=datetime.fromtimestamp(1,tz=timezone.utc).isoformat()))
        sock=Mock()
        sock.recv.return_value=(intent['binding_sha256']+':open').encode()
        with patch.object(m,'ticket',return_value=t), patch.object(m,'intent_for',return_value=intent), \
             patch.object(m,'live_guard'), patch.object(m,'lookup',return_value=self.lookup()), \
             patch.object(os,'open',wraps=os.open) as opened:
            for token in ('wrong',approval):
                with self.assertRaises(m.base.OWNER.Stop):
                    m.open_for_child(sock,r,token)
            self.assertFalse(any(str(call.args[0]).startswith('/dev/') for call in opened.call_args_list))
            sock.sendmsg.assert_not_called()
