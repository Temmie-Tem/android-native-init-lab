from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p327_framed_exec_runtime as p327  # noqa: E402
import s22plus_fyg8_p328_auth_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))


class P328AuthExecRuntimeTests(unittest.TestCase):
    @staticmethod
    def predecessor() -> bytes:
        # Keep this test host-only and independent of private candidate
        # evidence while preserving the P327 validator's exact anchor order.
        return (
            p327.P327_HELPER
            + p327.PUBLISHER
            + p327.P327_ENTRY
            + b"s22plus_max77705_p319_stock_encode"
        )

    def test_key_shape_and_public_source_do_not_contain_test_secret(self) -> None:
        with self.assertRaises(runtime.AuthRuntimeError):
            runtime.materialize_helper(b"short")
        self.assertEqual(runtime.auth_key_sha256(TEST_KEY), runtime.auth_key_sha256(TEST_KEY))
        source = Path(runtime.__file__).read_bytes()
        self.assertNotIn(TEST_KEY.hex().encode("ascii"), source)
        self.assertIn(runtime.AUTH_KEY_PLACEHOLDER.encode("ascii"), source)

    def test_transform_changes_only_the_two_p327_console_anchors(self) -> None:
        before = self.predecessor()
        after = runtime.transform_runtime_include(before, auth_key=TEST_KEY)
        receipt = runtime.validate_transform(
            before,
            after,
            auth_key_sha256=runtime.auth_key_sha256(TEST_KEY),
        )
        self.assertEqual(
            receipt["changed_anchors"],
            ["p327_console_helper", "p319_stock_publish"],
        )
        self.assertEqual(receipt["wire_magic"], "S328")
        self.assertEqual(receipt["frame_version"], 1)
        self.assertEqual(receipt["max_commands"], 16)
        self.assertEqual(receipt["max_command_size"], 1023)
        self.assertEqual(receipt["max_frame_payload"], 1055)
        self.assertEqual(receipt["command_timeout_sec"], 15)
        self.assertEqual(receipt["max_output_bytes"], 128 * 1024)
        self.assertTrue(receipt["caller_selected_command"])
        self.assertTrue(receipt["per_session_random_nonce"])
        self.assertTrue(receipt["child_kill_and_reap"])
        self.assertTrue(receipt["descendant_group_cleanup"])
        self.assertFalse(receipt["interactive_pty"])
        self.assertTrue(receipt["stdin_dev_null"])
        self.assertNotIn(p327.P327_HELPER, after)
        self.assertNotIn(p327.P327_ENTRY, after)
        self.assertNotIn(b"ash -i", after)

    def test_runtime_contains_getrandom_and_constant_time_auth_anchors(self) -> None:
        helper = runtime.materialize_helper(TEST_KEY)
        for anchor in (
            b"#define P328_MAGIC_3 0x38U",
            b"P328_NR_GETRANDOM 278",
            b"P328_GRND_NONBLOCK 1U",
            b"syscall6(\n        P328_NR_GETRANDOM",
            b"amount != (long)P328_NONCE_SIZE",
            b"nonzero == 0U ? -EIO : 0",
            b"p328_constant_time_equal",
            b"p328_hmac_message",
            b"P328_FRAME_CHALLENGE 0x85U",
            b"P328_FRAME_AUTH 4U",
            b"P328_MAX_COMMANDS 16U",
            b"P328_COMMAND_TIMEOUT_SEC 15LL",
            b"P328_MAX_OUTPUT 131072U",
            b"sys_kill(-pid, SIGKILL)",
            b"/dev/null",
        ):
            self.assertIn(anchor, helper)
        self.assertNotIn(b"P327", helper)
        self.assertNotIn(b"p327", helper)

    def test_materialized_c_and_host_auth_domains_are_byte_identical(self) -> None:
        helper = runtime.materialize_helper(TEST_KEY)
        for name, domain in (
            (b"open", runtime.AUTH_DOMAIN_OPEN),
            (b"ready", runtime.AUTH_DOMAIN_READY),
            (b"exec", runtime.AUTH_DOMAIN_EXEC),
            (b"close", runtime.AUTH_DOMAIN_CLOSE),
        ):
            anchor = (
                b"static const char p328_auth_domain_"
                + name
                + b"[] = \""
                + domain
                + b"\";"
            )
            self.assertIn(anchor, helper)

    def test_materialized_key_is_exactly_private_helper_input(self) -> None:
        helper = runtime.materialize_helper(TEST_KEY)
        self.assertEqual(runtime._extract_materialized_key(helper), TEST_KEY)
        with self.assertRaises(runtime.AuthRuntimeError):
            runtime.validate_p328_runtime(
                helper + runtime.PUBLISHER + runtime.P328_ENTRY,
                auth_key_sha256=runtime.auth_key_sha256(b"X" * 32),
            )

    def test_artifact_mapping_changes_only_runtime_key(self) -> None:
        before = self.predecessor()
        source = {
            runtime.RUNTIME_KEY: before,
            "unchanged": b"fixture",
        }
        result = runtime.transform_artifacts(source, auth_key=TEST_KEY)
        self.assertEqual(set(result), set(source))
        self.assertEqual(result["unchanged"], source["unchanged"])
        self.assertNotEqual(result[runtime.RUNTIME_KEY], before)


if __name__ == "__main__":
    unittest.main()
