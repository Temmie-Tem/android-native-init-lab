"""HUD records cannot promote stale, foreign or incomplete raw output."""
import copy
import unittest
import s22plus_fyg8_p376_research_shell_observer as observer
import s22plus_fyg8_p376_stock_process_v2_adapter as adapter


def log():
    return b'HUD_START 123\n'+b''.join(('HUD_FRAME run='+observer.RUN_ID_HEX+f' seq={i} uptime_ms={i*1000} state=1 event=matched visible=UNPROVED\n').encode() for i in range(1,4))

class HudEvidence(unittest.TestCase):
    def test_three_fresh_frames_with_busy_console(self):
        value=observer.hud_log_proof(log());self.assertTrue(value['proved']);self.assertEqual(value['frame_count'],3)
        self.assertEqual(adapter.acceptance_fixture()['qualification_commands'][-1]['ordinal'],6)
        self.assertEqual(adapter.audit()['total_commands'],6)

    def test_partial_foreign_stale_and_failure_records_are_unproved(self):
        cases=[log()[:-1],log().replace(observer.RUN_ID_HEX.encode(),b'0'*32),
            log().replace(b'seq=3',b'seq=2'),log().replace(b'uptime_ms=3000',b'uptime_ms=2000'),
            log().replace(b'state=1',b'state=0'),log()+b'HUD_EXIT 1792\n',
            log()+b'HUD_WAIT_ERROR 10\n',log().replace(b'event=matched',b'event=submitted'),
            log().replace(b'visible=UNPROVED',b'visible=PROVED'),b'HUD_START 123\n'+log()]
        for raw in cases:
            with self.subTest(raw=raw[-60:]):self.assertFalse(observer.hud_log_proof(raw)['proved'])

    def test_child_pid_and_log_bounds(self):
        self.assertFalse(observer.hud_log_proof(log().replace(b'HUD_START 123',b'HUD_START 1'))['proved'])
        self.assertFalse(observer.hud_log_proof(log()+b'x'*131072+b'\n')['proved'])

if __name__=='__main__':unittest.main()
