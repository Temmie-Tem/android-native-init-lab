"""Real target BusyBox shell/applets and optional diagnostic stream behavior."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_s22plus_fyg8_p380_hud_evidence as evidence

ROOT=Path(__file__).resolve().parents[1]
BB=ROOT/'workspace/private/inputs/s22plus_fyg8_p326/busybox/src/busybox-1.36.1/busybox'
observer=evidence.observer


class MemoryCommand(unittest.TestCase):
    def test_actual_arm64_busybox_and_two_separated_streams(self):
        # Only the executable launcher changes for host execution. Shell syntax,
        # applet options, byte caps, wait and stream routing remain exact.
        command=observer.HUD_COMMAND.decode().replace('/bin/busybox ',f'qemu-aarch64 {BB} ')
        with tempfile.TemporaryDirectory() as folder:
            log=evidence.log()
            (Path(folder)/'hud.log').write_bytes(log)
            run=subprocess.run(['qemu-aarch64',BB,'sh','-c',command],cwd=folder,
                               capture_output=True,timeout=20)
        self.assertEqual(run.returncode,0)
        self.assertEqual(run.stdout,log)
        self.assertEqual(run.stderr.count(b'MEM_SNAPSHOT '),2)
        self.assertEqual(run.stderr.count(b'MEM_END\n'),2)
        self.assertLess(len(run.stderr),85000)
        times=[]
        for phase in (b'early',b'late'):
            block=run.stderr.split(b'MEM_SNAPSHOT '+phase+b'\n',1)[1].split(b'MEM_END\n',1)[0]
            self.assertIn(b'MemTotal:',block)
            self.assertIn(b'MemAvailable:',block)
            ps=block.split(b'MEM_PS\n',1)[1]
            self.assertIn(b'RSS',ps.splitlines()[0])
            self.assertNotIn(b'bad -o argument',ps)
            times.append(float(block.split(b'MEM_FILE uptime\n',1)[1].split()[0]))
        self.assertGreaterEqual(times[1]-times[0],2)
        self.assertTrue(observer.hud_log_proof(run.stdout)['proved'])
        self.assertLessEqual(len(observer.HUD_COMMAND),1023)

    def test_optional_stderr_does_not_change_functional_qualification(self):
        step=observer.QUALIFICATION_COMMANDS[5]
        raw=evidence.log()
        row=dict(accepted=True,rejected=False,command=observer.identity(observer.HUD_COMMAND),
                 cwd=observer.identity(b'/s22-root-work'),timeout_ms=15000,
                 stdout=observer.identity(raw),terminal=[0]*6,hud=observer.hud_log_proof(raw))
        for diagnostic in (b'',b'MEM_SNAPSHOT early\nread failed\n',b'incomplete snapshot'):
            row['stderr']=observer.identity(diagnostic)
            original=dict(row)
            self.assertTrue(observer._qualified_step(row,step,[]))
            self.assertEqual(row,original)
        row['hud']=dict(row['hud'],proved=False)
        self.assertFalse(observer._qualified_step(row,step,[]))


if __name__=='__main__':unittest.main()
