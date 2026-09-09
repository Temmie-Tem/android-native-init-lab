"""Fresh status proof must join complete, bounded, same-run raw frames."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"workspace/public/src/scripts/revalidation"))
import unittest
import s22plus_fyg8_p379_research_shell_observer as observer


def log():
    return b'METRICS_START 122\nHUD_START 123\n'+b''.join((
        'HUD_FRAME run='+observer.RUN_ID_HEX+f' seq={i} uptime_ms={i*1000} state=1 metrics_seq={i} valid=227 age_ms=10 mem_total=8192000 mem_available=4000000 cpu_permille=200 battery_pct=0 charge=0 temp_deci=0 gauge_seq={i} gauge_age_ms=10 gauge_soc=500 voltage_uv=4000000 current_ua=-100000 event=matched visible=UNPROVED\n').encode() for i in range(1,4))


class StatusEvidence(unittest.TestCase):
    def test_fresh_memory_cpu_with_unavailable_battery(self):
        self.assertTrue(observer.hud_log_proof(log())['proved'])

    def test_partial_foreign_stale_invalid_or_duplicate_metrics(self):
        cases=[log()[:-1],log().replace(b'gauge_seq=3',b'gauge_seq=2'),log().replace(b'gauge_age_ms=10',b'gauge_age_ms=5001'),log().replace(b'current_ua=-100000',b'current_ua=-25600001'),log().replace(observer.RUN_ID_HEX.encode(),b'0'*32),
            log().replace(b'metrics_seq=3',b'metrics_seq=2'),log().replace(b'age_ms=10',b'age_ms=5001'),
            log().replace(b'valid=227',b'valid=1'),log().replace(b'valid=227',b'valid=35'),
            log().replace(b'mem_available=4000000',b'mem_available=9000000'),
            log().replace(b'cpu_permille=200',b'cpu_permille=1001'),
            log().replace(b'state=1',b'state=0'),log()+b'METRICS_EXIT 1792\n',
            log().replace(b'METRICS_START 122',b'METRICS_START 123'),
            log().replace(b'visible=UNPROVED',b'visible=PROVED')]
        for raw in cases:
            with self.subTest(raw=raw[-100:]):self.assertFalse(observer.hud_log_proof(raw)['proved'])


if __name__=='__main__':unittest.main()
