from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p327_framed_exec_runtime as p327  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


class P330AuthExecRuntimeTests(unittest.TestCase):
    @staticmethod
    def predecessor() -> bytes:
        return (
            p327.P327_HELPER
            + p327.PUBLISHER
            + p327.P327_ENTRY
            + b"s22plus_max77705_p319_stock_encode"
        )

    def test_transform_keeps_auth_contract_and_adds_only_bounded_diagnostics(self) -> None:
        before = self.predecessor()
        after = runtime.transform_runtime_include(before, auth_key=TEST_KEY)
        result = runtime.validate_p330_runtime(
            after, auth_key_sha256=runtime.auth_key_sha256(TEST_KEY)
        )
        self.assertEqual(result["run_id_hex"], runtime.P330_RUN_ID_HEX)
        self.assertEqual(result["wire_magic"], "S328")
        self.assertEqual(result["max_commands"], 16)
        self.assertEqual(result["command_timeout_sec"], 15)
        self.assertEqual(result["max_output_bytes"], 128 * 1024)
        self.assertEqual(result["preauth_diagnostic_frame"], 0x86)
        self.assertEqual(result["rng_eagain_retry_limit"], 64)
        self.assertFalse(result["non_eagain_retry"])
        self.assertFalse(result["interactive_pty"])

    def test_open_rng_challenge_order_and_eagain_only_retry_are_fixed(self) -> None:
        helper = runtime.materialize_helper(TEST_KEY)
        opened = helper.index(b"p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0)")
        retry = helper.index(b"for (;;) {", opened)
        rng = helper.index(b"P330_DIAG_RNG, (int32_t)rng_retries", retry)
        challenge = helper.index(b"P328_FRAME_CHALLENGE", rng)
        self.assertLess(opened, retry)
        self.assertLess(retry, rng)
        self.assertLess(rng, challenge)
        self.assertIn(
            b"rc != -EAGAIN || rng_retries == P330_RNG_EAGAIN_RETRY_LIMIT",
            helper,
        )
        self.assertEqual(helper.count(b"++rng_retries;"), 1)
        self.assertNotIn(b"ash -i", helper)

    def test_fresh_identity_and_public_source_contain_no_key(self) -> None:
        self.assertEqual(
            runtime.P330_RUN_ID_HEX,
            "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b",
        )
        self.assertNotEqual(
            runtime.P330_RUN_ID_HEX, runtime.P329_PREDECESSOR_RUN_ID_HEX
        )
        self.assertIn(runtime.P330_RUN_ID_HEX.encode(), runtime.DEVICE_BANNER)
        self.assertNotIn(
            runtime.P329_PREDECESSOR_RUN_ID_HEX.encode(), runtime.DEVICE_BANNER
        )
        source = Path(runtime.__file__).read_bytes()
        self.assertNotIn(TEST_KEY.hex().encode(), source)
        self.assertIn(
            runtime.AUTH_KEY_PLACEHOLDER.encode(), runtime.P330_HELPER_TEMPLATE
        )


if __name__ == "__main__":
    unittest.main()
