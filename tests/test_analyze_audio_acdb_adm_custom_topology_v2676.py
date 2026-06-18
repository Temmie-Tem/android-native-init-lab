import unittest

from workspace.public.src.scripts.revalidation import analyze_audio_acdb_adm_custom_topology_v2676 as v2676


class AnalyzeAudioAcdbAdmCustomTopologyV2676Test(unittest.TestCase):
    def test_parse_lower_events_accepts_hex_value_lines(self):
        lines = "\n".join(
            [
                '{"event":"v2672_lower_hidden","stage":"acdb_ioctl_get_return","code":-12,"cal_type":10,"value":0x00000000,"pid":1,"tid":1}',
                '{"event":"v2672_lower_hidden","stage":"acdb_ioctl_get_return","code":0,"cal_type":14,"value":0x00000934,"pid":1,"tid":1}',
            ]
        )
        path = self.create_temp_file(lines)

        events = v2676.parse_lower_events(path)

        self.assertEqual([event.cal_type for event in events], [10, 14])
        self.assertEqual([event.code for event in events], [-12, 0])
        self.assertEqual(events[1].value, 0x934)

    def test_v2461_report_classifier_distinguishes_allocate_from_set(self):
        text = """
| 5 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 10 `ADM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 21 | 0 | `hash` |
| 28 | `AUDIO_SET_CALIBRATION` (`0xc00461cb`) | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 4916 | 37 | 0 | `hash` |
"""

        alloc_has_cal10, set_has_cal10, set_rows = v2676.analyze_v2461_report(text)

        self.assertTrue(alloc_has_cal10)
        self.assertFalse(set_has_cal10)
        self.assertEqual(set_rows, 1)

    def test_adm_geometry_requires_exact_8_byte_block_pair(self):
        text = """
    924a:       movs    r0, #10
    929e:       ldr     r1, [r0]
    92a0:       ldr     r0, [r0, #8]
    92a2:       strd    r1, r0, [sp, #56]
    92b6:       movs    r2, #8
    92ba:       movw    r0, #5012
    92c2:       movt    r0, #1
    92c6:       blx     #51112
"""

        geometry = v2676.analyze_adm_geometry(text)

        self.assertTrue(geometry.ok)
        self.assertTrue(geometry.has_exact_get_input_pair)
        self.assertTrue(geometry.has_cmd_0x11394)

    def create_temp_file(self, text):
        import tempfile
        from pathlib import Path

        handle = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        with handle:
            handle.write(text)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)


if __name__ == "__main__":
    unittest.main()
