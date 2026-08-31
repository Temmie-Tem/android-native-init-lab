from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_recovery_digest_profile_h0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_recovery_digest_profile_h0_tested", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)

EXPECTED_SCRIPT_SHA256 = (
    "9377e58d3717e0fa96826210815b09df20bf2ba62a70c85c896f5a6fdf68fded"
)


class S20PlusG986NRecoveryDigestProfileH0Tests(unittest.TestCase):
    def test_profile_source_is_frozen(self) -> None:
        self.assertEqual(
            hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), EXPECTED_SCRIPT_SHA256
        )

    def test_plan_is_h0_dormant_and_exact_target_bound(self) -> None:
        plan = PROFILE.render_plan()
        self.assertFalse(PROFILE.RECOVERY_DIGEST_PROFILE_ACTIVE)
        self.assertFalse(plan["profile_active"])
        self.assertFalse(plan["live_authorized"])
        self.assertEqual(plan["tier"], "H0")
        self.assertEqual(plan["target"], PROFILE.EXPECTED_TARGET)
        self.assertEqual(
            plan["current_contract_status"],
            "FORBIDDEN_UNTIL_COMMON_BOUNDARY_AND_S20PLUS_TARGET_ACTIVATION",
        )
        self.assertEqual(
            plan["fixed_surface"]["recovery_link"],
            "/dev/block/by-name/recovery",
        )
        self.assertEqual(
            plan["fixed_surface"]["required_resolved_node"], "/dev/block/sda24"
        )
        self.assertFalse(plan["fixed_surface"]["node_live_confirmed"])
        self.assertEqual(
            plan["fixed_surface"]["node_h0_derivation"]["identifier"], 24
        )
        self.assertEqual(
            plan["fixed_surface"]["node_h0_derivation"][
                "block_count_times_block_bytes"
            ],
            PROFILE.EXPECTED_RECOVERY_SIZE,
        )
        self.assertEqual(
            plan["fixed_surface"]["expected_size"], PROFILE.EXPECTED_RECOVERY_SIZE
        )
        self.assertEqual(
            plan["fixed_surface"]["expected_sha256"],
            PROFILE.EXPECTED_RECOVERY_SHA256,
        )
        self.assertFalse(plan["fixed_surface"]["caller_supplied_path"])
        self.assertFalse(plan["fixed_surface"]["returned_block_path"])

    def test_connected_mode_stops_without_render_or_io(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(PROFILE, "render_plan", side_effect=AssertionError),
            mock.patch.object(Path, "read_bytes", side_effect=AssertionError),
            contextlib.redirect_stdout(output),
        ):
            status = PROFILE.main(["--connected"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue().strip(), PROFILE.DORMANT_VERDICT)

    def test_exact_canonical_root_transcript_is_accepted(self) -> None:
        parsed = PROFILE.parse_root_result((0, PROFILE.EXPECTED_ROOT_STDOUT, b""))
        self.assertEqual(parsed, PROFILE.EXPECTED_ROOT_OUTPUT)
        self.assertIsNot(parsed, PROFILE.EXPECTED_ROOT_OUTPUT)

    def test_result_envelope_types_are_strict(self) -> None:
        malformed = (
            [0, PROFILE.EXPECTED_ROOT_STDOUT, b""],
            (True, PROFILE.EXPECTED_ROOT_STDOUT, b""),
            (0, bytearray(PROFILE.EXPECTED_ROOT_STDOUT), b""),
            (0, PROFILE.EXPECTED_ROOT_STDOUT, ""),
            (0, PROFILE.EXPECTED_ROOT_STDOUT),
        )
        for value in malformed:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(PROFILE.RecoveryDigestProfileError):
                    PROFILE.parse_root_result(value)  # type: ignore[arg-type]

    def test_nonzero_stderr_and_oversized_results_stop(self) -> None:
        cases = (
            (1, PROFILE.EXPECTED_ROOT_STDOUT, b""),
            (0, PROFILE.EXPECTED_ROOT_STDOUT, b"unexpected"),
            (0, b"x" * (PROFILE.MAX_ROOT_STDOUT_BYTES + 1), b""),
            (0, b"", b"x" * (PROFILE.MAX_ROOT_STDERR_BYTES + 1)),
        )
        for result in cases:
            with self.subTest(result=(result[0], len(result[1]), len(result[2]))):
                with self.assertRaises(PROFILE.RecoveryDigestProfileError):
                    PROFILE.parse_root_result(result)

    def test_every_root_field_is_exact(self) -> None:
        for key in PROFILE.ROOT_OUTPUT_KEYS:
            changed = copy.deepcopy(PROFILE.EXPECTED_ROOT_OUTPUT)
            changed[key] += "x"
            payload = "".join(
                f"{name}={changed[name]}\n" for name in PROFILE.ROOT_OUTPUT_KEYS
            ).encode()
            with self.subTest(key=key):
                with self.assertRaises(PROFILE.RecoveryDigestProfileError):
                    PROFILE.parse_root_result((0, payload, b""))

    def test_transcript_format_drift_stops(self) -> None:
        canonical = PROFILE.EXPECTED_ROOT_STDOUT
        cases = (
            canonical + b"extra=1\n",
            canonical[:-1],
            canonical.replace(b"\n", b"\r\n"),
            canonical.replace(b"uid=0\n", b"gid=0\nuid=0\n", 1),
            canonical.replace(b"uid=0", b"uid=00", 1),
            canonical.replace(b"recovery_size=82694144", b"recovery_size=82694145"),
            canonical.replace(
                PROFILE.EXPECTED_RECOVERY_SHA256.encode(), b"0" * 64
            ),
        )
        for payload in cases:
            with self.subTest(length=len(payload)):
                with self.assertRaises(PROFILE.RecoveryDigestProfileError):
                    PROFILE.parse_root_result((0, payload, b""))

    def test_root_script_has_only_fixed_read_surface(self) -> None:
        script = PROFILE.ROOT_READ_SCRIPT
        self.assertIn("recovery_link=/dev/block/by-name/recovery", script)
        self.assertIn(
            '[ "$recovery_node" = "/dev/block/sda24" ] || exit 91', script
        )
        self.assertNotIn("sd[a-z]", script)
        self.assertIn(str(PROFILE.EXPECTED_RECOVERY_SIZE), script)
        self.assertIn(PROFILE.EXPECTED_RECOVERY_SHA256, script)
        self.assertNotIn("$1", script.split("recovery_sha256=$1", 1)[0])
        self.assertNotIn("${", script)
        self.assertNotIn("getopts", script)
        self.assertNotIn("read ", script)

    def test_root_script_uses_only_the_reviewed_executables(self) -> None:
        system_executables = set(re.findall(r"/system/bin/[a-z0-9._-]+", PROFILE.ROOT_READ_SCRIPT))
        self.assertEqual(
            system_executables,
            {
                "/system/bin/blockdev",
                "/system/bin/cat",
                "/system/bin/getenforce",
                "/system/bin/id",
                "/system/bin/readlink",
                "/system/bin/sha256sum",
            },
        )
        data_executables = set(
            re.findall(r"/data/adb/[a-z0-9/._-]+", PROFILE.ROOT_READ_SCRIPT)
        )
        self.assertEqual(data_executables, {"/data/adb/magisk/magisk"})

    def test_root_script_has_no_write_or_control_primitive(self) -> None:
        lowered = PROFILE.ROOT_READ_SCRIPT.lower()
        for forbidden in (
            " dd ",
            "of=",
            "mount",
            "remount",
            "reboot",
            "setprop",
            "chmod",
            "chown",
            " rm ",
            " mv ",
            " cp ",
            " tee ",
            ">",
            "vendor_boot",
            "vbmeta",
            "/efs",
            "/persist",
            "/misc",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)

    def test_node_size_and_digest_checks_precede_output(self) -> None:
        script = PROFILE.ROOT_READ_SCRIPT
        self.assertLess(script.index("readlink -f"), script.index("[ -b"))
        self.assertLess(script.index("[ -b"), script.index("blockdev --getsize64"))
        self.assertLess(script.index("blockdev --getsize64"), script.index("sha256sum"))
        self.assertLess(script.index("exit 96"), script.index("printf '%s\\n'"))

    def test_shell_argument_and_plan_receipts_are_exact(self) -> None:
        self.assertEqual(PROFILE.ROOT_SHELL_ARGUMENT, PROFILE.shlex.quote(PROFILE.ROOT_READ_SCRIPT))
        plan = PROFILE.render_plan()
        script = PROFILE.ROOT_READ_SCRIPT.encode()
        argument = PROFILE.ROOT_SHELL_ARGUMENT.encode()
        stdout = PROFILE.EXPECTED_ROOT_STDOUT
        self.assertEqual(plan["root_command"]["script_size"], len(script))
        self.assertEqual(
            plan["root_command"]["script_sha256"], hashlib.sha256(script).hexdigest()
        )
        self.assertEqual(plan["root_command"]["shell_argument_size"], len(argument))
        self.assertEqual(
            plan["root_command"]["shell_argument_sha256"],
            hashlib.sha256(argument).hexdigest(),
        )
        self.assertEqual(plan["root_command"]["expected_stdout_size"], len(stdout))
        self.assertEqual(
            plan["root_command"]["expected_stdout_sha256"],
            hashlib.sha256(stdout).hexdigest(),
        )

    def test_plan_counts_report_no_execution_or_mutation(self) -> None:
        counts = PROFILE.render_plan()["planned_counts"]
        self.assertEqual(counts["root_command_count"], 1)
        self.assertEqual(counts["partition_read_count"], 1)
        for key in (
            "partition_write_count",
            "partition_transfer_count",
            "device_effect_count",
            "reboot_count",
            "adb_command_count_in_this_h0_module",
            "su_command_count_in_this_h0_module",
        ):
            self.assertEqual(counts[key], 0, key)

    def test_cli_surface_is_closed_and_plan_is_json(self) -> None:
        options = PROFILE.build_parser()._option_string_actions
        self.assertEqual(set(options), {"-h", "--help", "--render-plan", "--connected"})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = PROFILE.main(["--render-plan"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), PROFILE.render_plan())

    def test_module_has_no_device_execution_backend(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "subprocess.",
            "os.system",
            "Popen(",
            "/usr/bin/adb",
            "/usr/bin/odin4",
            "/dev/bus/usb",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
