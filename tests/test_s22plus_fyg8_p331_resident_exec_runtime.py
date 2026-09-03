from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p327_framed_exec_runtime as p327  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as p330  # noqa: E402
import s22plus_fyg8_p331_resident_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


class P331ResidentRuntimeTests(unittest.TestCase):
    @staticmethod
    def p327_include() -> bytes:
        return (
            p327.P327_HELPER
            + p327.PUBLISHER
            + p327.P327_ENTRY
            + b"s22plus_max77705_p319_stock_encode"
        )

    def p330_include(self) -> bytes:
        return p330.transform_runtime_include(self.p327_include(), TEST_KEY)

    def test_transform_retains_p330_auth_diagnostics_and_adds_only_resident_loop(self) -> None:
        before = self.p330_include()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        result = runtime.validate_p331_runtime(
            after, auth_key_sha256=runtime.auth_key_sha256(TEST_KEY)
        )
        self.assertEqual(result["schema"], runtime.CONTRACT_ID)
        self.assertEqual(result["wire_magic"], "S328")
        self.assertEqual(result["session_cap"], 2)
        self.assertEqual(result["reconnect_cap"], 1)
        self.assertFalse(result["caller_selected_command"])
        self.assertFalse(result["interactive_pty"])
        self.assertFalse(result["arbitrary_file_transfer"])
        self.assertFalse(result["persistent_state"])
        self.assertIn(b"P330_FRAME_DIAGNOSTIC 0x86U", after)
        self.assertIn(b"p328_auth_domain_open", after)
        self.assertIn(b"p328_getrandom_nonce", after)
        self.assertEqual(
            after.count(b"s22plus_p318_banner_attempt(tty_fd);"), 1
        )
        self.assertNotIn(
            b"s22plus_p318_banner_attempt(tty_fd);", runtime.P331_ENTRY
        )
        self.assertEqual(
            after.count(runtime.P331_ENTRY), 1
        )

    def test_fixed_heartbeat_and_one_shot_caps_are_enforced_in_c(self) -> None:
        helper = runtime.materialize_helper(TEST_KEY)
        self.assertIn(b"p331_heartbeat_command", helper)
        self.assertIn(b"P331_COMMANDS_PER_SESSION 1U", helper)
        self.assertIn(b"P331_MAX_SESSIONS 2U", helper)
        self.assertIn(b"P331_MAX_RECONNECTS 1U", helper)
        self.assertIn(b"p331_resident_loop", helper)
        loop = helper[helper.index(b"static long p331_resident_loop"):]
        self.assertEqual(loop.count(b"s22plus_p318_banner_attempt(tty_fd);"), 1)
        self.assertIn(b"p331_banner.outcome != S22PLUS_P318_BANNER_WRITTEN", loop)
        self.assertNotIn(b"ash -i", helper)
        self.assertNotIn(b"sendfile", helper)
        self.assertNotIn(b"p331_write_file", helper)

    def test_materialized_key_and_predecessor_or_delta_mutations_fail_closed(self) -> None:
        before = self.p330_include()
        after = runtime.transform_runtime_include(before, TEST_KEY)
        with self.assertRaises(runtime.P331RuntimeError):
            runtime.validate_p331_runtime(after, auth_key_sha256="0" * 64)
        with self.assertRaises(runtime.P331RuntimeError):
            runtime.validate_transform(before, after + b"x")
        with self.assertRaises(runtime.P331RuntimeError):
            runtime.transform_runtime_include(before, bytearray(TEST_KEY))


if __name__ == "__main__":
    unittest.main()
