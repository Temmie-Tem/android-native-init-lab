"""P365 real generated console/observer on local sockets; platform calls are fixtures."""
from pathlib import Path
import os,signal,socket,subprocess,time
from unittest import mock
import test_s22plus_fyg8_p364_diagnostics as predecessor
import s22plus_fyg8_p365_research_shell_runtime as runtime
import s22plus_fyg8_p365_research_shell_observer as observer
import device_action_f1_live_v2 as live
KEY=predecessor.KEY

def console_source():
    with mock.patch.object(predecessor,'runtime',runtime):
        value=predecessor.source()
    # The retained fixture's C declarations name its original namespace.
    # Keep its P364_CASE environment vocabulary; only generated C symbols differ.
    value=value.replace('p364','p365')
    return value.replace('const unsigned char*b=p;', 'const unsigned char*b=p;\n if(n==52&&b[5]==0x8a&&fx_case("ack-zero"))return 0;',1)

class ConsolePeer:
    def __init__(self,root):
        self.root=Path(root);self.binary=self.root/'console-peer'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(self.binary)],input=console_source(),text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
    def run(self,case,writer,before_control):
        mark=self.root/('marks-'+str(time.monotonic_ns()))
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        p=subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],env=dict(os.environ,P364_CASE=case,P364_MARK=str(mark)),pass_fds=(peer.fileno(),),stderr=subprocess.PIPE,start_new_session=True);peer.close()
        codec=live._open_header_initial_observer_module(runtime,observer,'p365-real-console')
        result=error=None
        try:
            try:result=observer.qualify(codec,host.fileno(),KEY,None,set(),writer,deadline=time.monotonic()+4,before_control=before_control)
            except observer.QualificationError as exc:error=exc
            audit=result.sessions[0].session.audit if result is not None else error.audit
            host.close();code=p.wait(timeout=4);stderr=p.stderr.read().decode()
            if code:raise AssertionError(stderr)
            projection=observer.progress_projection(audit)
            if observer.replay_progress(codec,bytes(audit.rx),bytes(audit.tx),KEY)!=projection:raise AssertionError('raw progress differs')
            self.last_marks=mark.read_text().splitlines() if mark.exists() else []
            return result,error,audit,projection
        finally:
            host.close()
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
            p.communicate(timeout=3)
