"""Actual native C and thermal workers across real host PTY hangup/replacement."""
from contextlib import contextmanager
import os
from pathlib import Path
import pty
import signal
import subprocess
import termios
import time
from types import SimpleNamespace
import unittest

import s22plus_native_baseline_v2_candidates as catalog
import s22plus_native_reconnect_source_v1 as source
import s22plus_native_resident_protocol_v1 as protocol
import s22plus_root_console_v1 as wire
import s22plus_resident_adoption_h0_support as support
import s22plus_native_reconnect_fixtures as fixtures
from test_s22plus_native_thermal_roundtrip_v3 import metrics_fixture

SELECTED=catalog.DECLARATIONS['p392']


class Reconnect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.compile_components(cls,SELECTED,render_source=source,
            metrics_transform=metrics_fixture,native_transform=fixtures.native_fixture)

    @contextmanager
    def running(self,case='normal'):
        folder=self.folder/str(time.monotonic_ns());folder.mkdir()
        master,slave=pty.openpty();os.set_blocking(master,False);os.set_blocking(slave,False)
        value=termios.tcgetattr(slave);value[6][termios.VMIN]=0;value[6][termios.VTIME]=0
        termios.tcsetattr(slave,termios.TCSANOW,value)
        name=os.ttyname(slave);(folder/'tty-route').write_text(name)
        proc=subprocess.Popen([self.binary,str(slave),'1'],pass_fds=(slave,),start_new_session=True,
            stderr=subprocess.PIPE,env=dict(os.environ,P364_CASE=case,P364_MARK=str(folder/'marks'),
                RC1_WORK=str(folder),HUD_RENDERER=str(self.renderer),METRICS_COLLECTOR=str(self.collector),LOCAL_CLOCK_RATE='1'))
        os.close(slave);ctx=SimpleNamespace(folder=folder,fd=master,proc=proc,held=[],name=name)
        try:yield ctx
        finally:
            if ctx.fd is not None:os.close(ctx.fd)
            for fd in ctx.held:os.close(fd)
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            _,err=proc.communicate(timeout=3)
            self.assertIn(proc.returncode,(-signal.SIGKILL,0),(err,self.marks(ctx)))

    @staticmethod
    def marks(ctx):
        path=ctx.folder/'marks'
        return path.read_text() if path.exists() else ''

    def until(self,predicate,timeout=6):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=predicate()
            if value:return value
            time.sleep(.01)
        self.fail('bounded fixture predicate did not complete')

    def observe(self,ctx,predicate=lambda row:True):
        def read():
            try:row={k:int(v) for field in (ctx.folder/'service.txt').read_text().split() for k,v in [field.split('=')]}
            except (OSError,ValueError):return None
            return row if len(row)==7 and predicate(row) else None
        return self.until(read)

    def disconnect(self,ctx):
        (ctx.folder/'tty-route').unlink(missing_ok=True)
        os.close(ctx.fd);ctx.fd=None

    def replacement(self,ctx):
        self.assertIsNone(ctx.fd)
        master,slave=pty.openpty();os.set_blocking(master,False)
        name=os.ttyname(slave);ctx.fd=master;ctx.held.append(slave)
        (ctx.folder/'tty-route-next').write_text(name)
        (ctx.folder/'tty-route-next').replace(ctx.folder/'tty-route')
        return slave

    def handshake(self,ctx):
        io=protocol.IO(self.codec,b'k'*32,SELECTED.IDENTITY,fd=ctx.fd,deadline=time.monotonic()+5,
            writer=SimpleNamespace(write_stdout=lambda data:None))
        io.handshake()
        session=protocol.Session(ctx.fd,b'k'*32,bytes.fromhex(SELECTED.IDENTITY.run_id_hex),io.audit.nonce,
            ctx.folder/str(time.monotonic_ns()),on_rx=io.capture,on_tx=io.audit.tx.extend)
        events=[]
        self.poll(session,events,lambda:session.ready is not None)
        return io,session,events

    def poll(self,session,events,predicate):
        def read():events.extend(session.poll());return predicate()
        return self.until(read)

    def clean(self,ctx):
        io,session,events=self.handshake(ctx)
        try:
            seq=session.send(wire.EXEC,wire.command(b'printf RECONNECT_OK',cwd=b'/s22-root-work',timeout_ms=1000))
            self.poll(session,events,lambda:seq in session.terminals)
            detach=session.send(protocol.DETACH)
            self.poll(session,events,lambda:any(k==protocol.DETACH_ACK and n==detach for k,n,_ in events))
            proof=protocol.replay_one(self.codec,SELECTED.IDENTITY,b'k'*32,bytes(io.audit.rx),bytes(io.audit.tx))
            return proof
        finally:session.close()

    def test_real_hangup_before_first_OPEN_and_after_DETACH_preserves_boot_and_sampling(self):
        with self.running('same-nonce') as ctx:
            first=self.observe(ctx,lambda r:r['system']>=1 and r['hardware']>=1)
            self.assertIn('tty-config 0',self.marks(ctx))
            self.assertNotIn('tty-close',self.marks(ctx))
            self.disconnect(ctx)
            self.until(lambda:'tty-close 0' in self.marks(ctx))
            waiting=self.observe(ctx,lambda r:r['system']>=first['system']+2 and r['hardware']>first['hardware'])
            self.assertFalse(waiting['terminal']);self.assertEqual(waiting['sessions'],0)
            slave=self.replacement(ctx);self.until(lambda:'tty-config 1' in self.marks(ctx))
            attrs=termios.tcgetattr(slave)
            self.assertEqual((attrs[6][termios.VMIN],attrs[6][termios.VTIME]),(1,0))
            p1=self.clean(ctx)
            self.disconnect(ctx);self.until(lambda:'tty-close 1' in self.marks(ctx))
            self.replacement(ctx);self.until(lambda:'tty-config 2' in self.marks(ctx))
            p2=self.clean(ctx);protocol.fresh_same_boot(p1,p2)
            self.assertEqual([p['resident_info']['authentication_ordinal'] for p in (p1,p2)],[1,2])
            self.assertEqual([p['resident_info']['preparation_cached'] for p in (p1,p2)],[False,True])
            after=self.observe(ctx,lambda r:r['system']>waiting['system'] and r['hardware']>waiting['hardware'])
            self.assertFalse(after['terminal']);self.assertGreater(after['seq'],first['seq'])
            marks=self.marks(ctx)
            self.assertEqual(marks.count('baseline-boot-prepare'),1)
            self.assertEqual(marks.count('metrics-child'),2);self.assertEqual(marks.count('hud-child'),1)
            self.assertEqual(marks.count('tty-close'),2)

    def test_empty_nonblocking_reads_and_idle_deadline_keep_the_healthy_fd(self):
        with self.running() as ctx:
            self.observe(ctx,lambda r:r['system']>=1)
            # The unchanged input deadline expires; this never consumes OPEN.
            support.Fixture.advance(SimpleNamespace(folder=ctx.folder,offset_ms=0),121000)
            self.observe(ctx,lambda r:r['system']>=3)
            self.assertNotIn('tty-close',self.marks(ctx));self.assertNotIn('tty-open-attempt',self.marks(ctx))
            proof=self.clean(ctx);self.assertEqual(proof['resident_info']['authentication_ordinal'],1)

    def test_link_loss_during_initial_or_reopen_configuration_can_reacquire(self):
        for case in ('tty-config-loss-initial','tty-config-loss-reopen'):
            with self.subTest(case=case),self.running(case) as ctx:
                generation=1
                if case.endswith('reopen'):
                    self.observe(ctx,lambda r:r['system']>=1)
                    self.disconnect(ctx);self.until(lambda:'tty-close 0' in self.marks(ctx))
                    self.replacement(ctx);generation=2
                self.until(lambda:f'tty-config {generation}' in self.marks(ctx))
                proof=self.clean(ctx)
                self.assertEqual(proof['resident_info']['authentication_ordinal'],1)
                self.assertFalse(self.observe(ctx)['terminal'])
                self.assertEqual(self.marks(ctx).count('tty-close'),generation)

    def test_configuration_and_close_failures_latch_without_reusing_or_double_closing_fd(self):
        for case in ('tty-config-initial','tty-config-reopen','tty-readback-reopen','tty-close-eintr'):
            with self.subTest(case=case),self.running(case) as ctx:
                if case!='tty-config-initial':
                    self.observe(ctx,lambda r:r['system']>=1)
                    self.disconnect(ctx);self.until(lambda:'tty-close 0' in self.marks(ctx))
                    self.replacement(ctx)
                row=self.observe(ctx,lambda r:r['terminal']==1 and r['system']>=1)
                expected=2 if case in ('tty-config-reopen','tty-readback-reopen') else 1
                self.assertEqual(self.marks(ctx).count('tty-close'),expected)
                attempts=self.marks(ctx).count('tty-open-attempt')
                self.observe(ctx,lambda r:r['system']>row['system'])
                self.assertEqual(self.marks(ctx).count('tty-open-attempt'),attempts)
                self.assertEqual(self.marks(ctx).count('tty-close'),expected)

    def test_partial_OPEN_AUTH_active_command_and_incomplete_ACK_never_reacquire(self):
        for case in ('partial-open','partial-auth','active-command','tty-detach-partial'):
            with self.subTest(case=case),self.running(case) as ctx:
                self.observe(ctx,lambda r:r['system']>=1)
                session=None
                if case=='partial-open':
                    os.write(ctx.fd,b'S328\x01');time.sleep(.1)
                elif case=='partial-auth':
                    frame=support.previous.baseline_test.local.frame(1,0,bytes.fromhex(SELECTED.IDENTITY.run_id_hex))
                    os.write(ctx.fd,frame)
                    self.until(lambda:bool(os.read(ctx.fd,4096)) if self.readable(ctx.fd) else False)
                    os.write(ctx.fd,b'S328\x01');time.sleep(.1)
                else:
                    _,session,events=self.handshake(ctx)
                    if case=='active-command':
                        seq=session.send(wire.EXEC,wire.command(b'printf once >> execution-count; sleep 20',cwd=b'/s22-root-work',timeout_ms=30000))
                        self.poll(session,events,lambda:any(k==wire.ACK and n==seq for k,n,_ in events))
                        self.until(lambda:(ctx.folder/'execution-count').exists())
                    else:
                        session.send(protocol.DETACH)
                        self.until(lambda:'tty-partial-ack' in self.marks(ctx))
                if session:session.close()
                self.disconnect(ctx)
                row=self.observe(ctx,lambda r:r['terminal']==1)
                self.replacement(ctx)
                after=self.observe(ctx,lambda r:r['system']>row['system'])
                self.assertEqual(after['sessions'],row['sessions']);self.assertFalse(after['stopped'])
                self.assertNotIn('tty-open-attempt',self.marks(ctx))
                if case=='active-command':self.assertEqual((ctx.folder/'execution-count').read_text(),'once')

    @staticmethod
    def readable(fd):
        import select
        return select.select([fd],[],[],0)[0]


if __name__=='__main__':unittest.main()
