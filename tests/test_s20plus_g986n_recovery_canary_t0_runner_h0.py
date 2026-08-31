from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_recovery_canary_t0_runner_h0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_recovery_canary_t0_runner_h0_tested", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

EXPECTED_SCRIPT_SHA256 = (
    "3eb7cd148477c4e28d8bf1102a22f4eeb2f7a92bc99199fdd084af1dde5cd7df"
)
BOOT_ID = "12345678-1234-4234-9234-123456789abc"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_recovery_output(**changes: str) -> bytes:
    values = {
        **RUNNER.EXPECTED_RECOVERY_FIXED_OUTPUT,
        "boot_id": BOOT_ID,
    }
    values.update(changes)
    return "".join(
        f"{key}={values[key]}\n" for key in RUNNER.RECOVERY_OUTPUT_KEYS
    ).encode()


def build_test_ap(
    path: Path,
    *,
    name: str = RUNNER.AP_MEMBER_NAME,
    payload: bytes = b"fixed-recovery-lz4",
    extra: bool = False,
) -> tuple[int, str, int, str, str]:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:", format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        member.mode = 0o644
        member.uid = 0
        member.gid = 0
        member.mtime = 0
        archive.addfile(member, io.BytesIO(payload))
        if extra:
            second = tarfile.TarInfo("extra.bin")
            second.size = 1
            second.mode = 0o644
            second.uid = 0
            second.gid = 0
            second.mtime = 0
            archive.addfile(second, io.BytesIO(b"x"))
    tar_payload = tar_buffer.getvalue()
    tar_md5 = hashlib.md5(tar_payload).hexdigest()
    complete = tar_payload + f"{tar_md5}  AP.tar\n".encode()
    path.write_bytes(complete)
    path.chmod(0o400)
    return len(complete), sha256(complete), len(payload), sha256(payload), tar_md5


class S20PlusG986NRecoveryCanaryT0RunnerH0Tests(unittest.TestCase):
    def test_runner_source_is_frozen(self) -> None:
        self.assertEqual(sha256(SCRIPT.read_bytes()), EXPECTED_SCRIPT_SHA256)

    def test_exact_private_host_closure_validates(self) -> None:
        result = RUNNER.validate_host_closure()
        self.assertEqual(result["schema"], RUNNER.HOST_RESULT_SCHEMA)
        self.assertEqual(result["verdict"], RUNNER.HOST_PASS_VERDICT)
        self.assertEqual(result["tier"], "H0")
        self.assertFalse(result["live_authorized"])
        self.assertEqual(result["target"], RUNNER.EXPECTED_TARGET)
        self.assertEqual(
            result["closure"]["candidate"]["members"],
            [
                {
                    "name": "recovery.img.lz4",
                    "type": "regular",
                    "size": RUNNER.CANDIDATE_MEMBER_SIZE,
                    "sha256": RUNNER.CANDIDATE_MEMBER_SHA256,
                    "mode": "0644",
                    "uid": 0,
                    "gid": 0,
                    "mtime": 0,
                }
            ],
        )
        self.assertTrue(result["closure"]["candidate"]["recovery_only"])
        self.assertFalse(result["closure"]["candidate"]["vbmeta_member"])
        self.assertTrue(result["closure"]["rollback"]["recovery_only"])
        self.assertTrue(result["closure"]["manifest"]["semantic_validation"])

    def test_small_recovery_only_ap_and_md5_are_fully_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "AP.tar.md5"
            size, digest, member_size, member_digest, tar_md5 = build_test_ap(path)
            receipt = RUNNER.validate_recovery_only_ap(
                path,
                label="test AP",
                expected_size=size,
                expected_sha256=digest,
                expected_member_size=member_size,
                expected_member_sha256=member_digest,
                expected_tar_md5=tar_md5,
            )
        self.assertEqual(receipt["members"][0]["name"], RUNNER.AP_MEMBER_NAME)
        self.assertEqual(receipt["tar_md5"], tar_md5)
        self.assertTrue(receipt["recovery_only"])

    def test_archive_extra_member_wrong_name_and_trailer_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for label, options in (
                ("extra", {"extra": True}),
                ("wrong-name", {"name": "boot.img.lz4"}),
            ):
                path = root / f"{label}.tar.md5"
                values = build_test_ap(path, **options)
                with self.subTest(label=label):
                    with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                        RUNNER.validate_recovery_only_ap(
                            path,
                            label=label,
                            expected_size=values[0],
                            expected_sha256=values[1],
                            expected_member_size=values[2],
                            expected_member_sha256=values[3],
                            expected_tar_md5=values[4],
                        )
            trailer = root / "trailer.tar.md5"
            values = build_test_ap(trailer)
            payload = trailer.read_bytes()
            trailer.chmod(0o600)
            trailer.write_bytes(payload[:-1] + b"X")
            trailer.chmod(0o400)
            with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                RUNNER.validate_recovery_only_ap(
                    trailer,
                    label="trailer",
                    expected_size=values[0],
                    expected_sha256=sha256(trailer.read_bytes()),
                    expected_member_size=values[2],
                    expected_member_sha256=values[3],
                    expected_tar_md5=values[4],
                )

    def test_pinner_rejects_symlink_hardlink_writable_and_wrong_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "artifact"
            original.write_bytes(b"artifact")
            original.chmod(0o400)
            link = root / "link"
            link.symlink_to(original)
            hard = root / "hard"
            os.link(original, hard)
            for label, path in (
                ("symlink", link),
                ("hardlink", original),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                        with RUNNER.pin_regular_file(
                            path,
                            label=label,
                            expected_size=8,
                            expected_sha256=sha256(b"artifact"),
                        ):
                            pass
            hard.unlink()
            with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                with RUNNER.pin_regular_file(
                    original,
                    label="wrong-digest",
                    expected_size=8,
                    expected_sha256="0" * 64,
                ):
                    pass
            original.chmod(0o600)
            with RUNNER.pin_regular_file(
                original,
                label="owner-writable",
                expected_size=8,
                expected_sha256=sha256(b"artifact"),
            ) as (_descriptor, receipt):
                self.assertFalse(receipt["group_or_world_writable"])
            original.chmod(0o620)
            with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                with RUNNER.pin_regular_file(
                    original,
                    label="group-writable",
                    expected_size=8,
                    expected_sha256=sha256(b"artifact"),
                ):
                    pass

    def test_manifest_json_rejects_duplicate_keys_and_nonobject(self) -> None:
        with self.assertRaisesRegex(RUNNER.RecoveryCanaryT0Error, "duplicate"):
            RUNNER._strict_json(b'{"a":1,"a":2}', "test")
        with self.assertRaisesRegex(RUNNER.RecoveryCanaryT0Error, "not an object"):
            RUNNER._strict_json(b"[]", "test")

    def test_exact_recovery_canary_observation_is_accepted(self) -> None:
        parsed = RUNNER.parse_recovery_observation(
            (0, canonical_recovery_output(), b"")
        )
        self.assertEqual(parsed["boot_id"], BOOT_ID)
        self.assertEqual(parsed["marker_sha256"], RUNNER.MARKER_SHA256)
        self.assertEqual(parsed["incremental"], "G986NKSS8IYC2")

    def test_recovery_observer_rejects_each_fixed_field_and_bad_boot_id(self) -> None:
        for key in RUNNER.EXPECTED_RECOVERY_FIXED_OUTPUT:
            with self.subTest(key=key):
                with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                    RUNNER.parse_recovery_observation(
                        (0, canonical_recovery_output(**{key: "changed"}), b"")
                    )
        for boot_id in ("", "not-a-uuid", "12345678-1234-0234-1234-123456789abc"):
            with self.subTest(boot_id=boot_id):
                with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                    RUNNER.parse_recovery_observation(
                        (0, canonical_recovery_output(boot_id=boot_id), b"")
                    )

    def test_recovery_observer_envelope_and_framing_are_strict(self) -> None:
        canonical = canonical_recovery_output()
        cases = (
            (1, canonical, b""),
            (0, canonical, b"stderr"),
            (0, canonical[:-1], b""),
            (0, canonical.replace(b"\n", b"\r\n"), b""),
            (0, canonical + b"extra=1\n", b""),
            (0, b"x" * (RUNNER.MAX_RECOVERY_OBSERVER_BYTES + 1), b""),
            (True, canonical, b""),
        )
        for result in cases:
            with self.subTest(shape=(result[0], len(result[1]), len(result[2]))):
                with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                    RUNNER.parse_recovery_observation(result)  # type: ignore[arg-type]

    def test_observer_script_is_fixed_read_only_and_marker_bound(self) -> None:
        script = RUNNER.RECOVERY_OBSERVER_SCRIPT
        self.assertIn(f"marker_path={RUNNER.MARKER_PATH}", script)
        self.assertIn(RUNNER.MARKER_SHA256, script)
        self.assertIn("[ ! -L", script)
        for forbidden in (
            " dd ",
            "of=",
            "mount",
            "reboot",
            "setprop",
            "chmod",
            "chown",
            " rm ",
            " mv ",
            " cp ",
            " tee ",
            ">",
            "/dev/block/",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script.lower())

    def test_candidate_and_rollback_command_shapes_are_distinct_and_fixed(self) -> None:
        endpoint = "/dev/bus/usb/003/007"
        candidate = RUNNER.candidate_transfer_argv(endpoint)
        rollback = RUNNER.rollback_transfer_argv(endpoint)
        self.assertEqual(
            candidate,
            [str(RUNNER.ODIN), "-a", str(RUNNER.CANDIDATE_AP), "-d", endpoint],
        )
        self.assertNotIn("--reboot", candidate)
        self.assertEqual(
            rollback,
            [
                str(RUNNER.ODIN),
                "--reboot",
                "-a",
                str(RUNNER.ROLLBACK_AP),
                "-d",
                endpoint,
            ],
        )
        for endpoint_value in (
            "",
            "/dev/bus/usb/3/7",
            "/dev/bus/usb/003/007;id",
            "/dev/sda",
            True,
        ):
            with self.subTest(endpoint=endpoint_value):
                with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                    RUNNER.candidate_transfer_argv(endpoint_value)  # type: ignore[arg-type]
                with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                    RUNNER.rollback_transfer_argv(endpoint_value)  # type: ignore[arg-type]

    def test_every_required_journal_prefix_is_valid(self) -> None:
        for length in range(len(RUNNER.REQUIRED_JOURNAL_ORDER) + 1):
            nodes = set(RUNNER.REQUIRED_JOURNAL_ORDER[:length])
            with self.subTest(length=length):
                self.assertEqual(RUNNER.validate_journal_nodes(nodes), frozenset(nodes))
        success_prefix = set(RUNNER.REQUIRED_JOURNAL_ORDER[:6])
        success_prefix.add("recovery-boot-intent.json")
        self.assertEqual(
            RUNNER.validate_journal_nodes(success_prefix), frozenset(success_prefix)
        )

    def test_journal_gap_unknown_node_and_early_recovery_intent_stop(self) -> None:
        cases = (
            {"approval.json"},
            {"prepared.json", "candidate-intent.json"},
            {"prepared.json", "unknown.json"},
            {"prepared.json", "recovery-boot-intent.json"},
            {
                *RUNNER.REQUIRED_JOURNAL_ORDER[:6],
                "recovery-boot-intent.json",
                "rollback-download-intent.json",
            },
        )
        for nodes in cases:
            with self.subTest(nodes=sorted(nodes)):
                with self.assertRaises(RUNNER.RecoveryCanaryT0Error):
                    RUNNER.validate_journal_nodes(nodes)

    def test_candidate_and_rollback_intents_irrevocably_disable_replay(self) -> None:
        candidate_ready = set(RUNNER.REQUIRED_JOURNAL_ORDER[:4])
        before_candidate = RUNNER.replay_policy(candidate_ready)
        self.assertTrue(before_candidate["candidate_transfer_permitted"])
        self.assertIsNone(before_candidate["candidate_replay_permitted"])
        candidate_consumed = set(RUNNER.REQUIRED_JOURNAL_ORDER[:5])
        after_candidate = RUNNER.replay_policy(candidate_consumed)
        self.assertFalse(after_candidate["candidate_transfer_permitted"])
        self.assertFalse(after_candidate["candidate_replay_permitted"])

        rollback_ready = set(RUNNER.REQUIRED_JOURNAL_ORDER[:9])
        before_rollback = RUNNER.replay_policy(rollback_ready)
        self.assertTrue(before_rollback["rollback_transfer_permitted"])
        self.assertIsNone(before_rollback["rollback_replay_permitted"])
        rollback_consumed = set(RUNNER.REQUIRED_JOURNAL_ORDER[:10])
        after_rollback = RUNNER.replay_policy(rollback_consumed)
        self.assertFalse(after_rollback["rollback_transfer_permitted"])
        self.assertFalse(after_rollback["rollback_replay_permitted"])

    def test_intent_only_cuts_route_to_finalization_not_replay(self) -> None:
        candidate_intent = set(RUNNER.REQUIRED_JOURNAL_ORDER[:5])
        self.assertEqual(
            RUNNER.next_reviewed_action(candidate_intent),
            "finalize-candidate-result-without-replay",
        )
        rollback_intent = set(RUNNER.REQUIRED_JOURNAL_ORDER[:10])
        self.assertEqual(
            RUNNER.next_reviewed_action(rollback_intent),
            "finalize-stock-rollback-result-without-replay",
        )
        closed = set(RUNNER.REQUIRED_JOURNAL_ORDER)
        self.assertEqual(
            RUNNER.next_reviewed_action(closed), "closed-no-more-device-action"
        )

    def test_plan_keeps_t0_dormant_and_all_other_partitions_closed(self) -> None:
        plan = RUNNER.render_plan()
        self.assertFalse(RUNNER.RECOVERY_CANARY_T0_ACTIVE)
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authorized"])
        self.assertFalse(plan["t1_authorized"])
        self.assertEqual(plan["tier"], "H0")
        self.assertEqual(plan["experiment"], "T0_RECOVERY_ADB_CANARY_ONLY")
        effects = plan["maximum_effects"]
        self.assertEqual(effects["candidate_recovery_partition_transfer"], 1)
        self.assertEqual(effects["stock_recovery_partition_transfer"], 1)
        self.assertEqual(effects["all_other_partition_transfers"], 0)
        self.assertEqual(effects["vbmeta_transfers"], 0)
        self.assertEqual(effects["data_formats"], 0)
        self.assertEqual(effects["misc_writes"], 0)
        self.assertFalse(
            plan["proposed_command_shapes"]["candidate_auto_reboot"]
        )
        self.assertTrue(plan["artifacts"]["rollback"]["mandatory"])
        self.assertFalse(
            plan["artifacts"]["rollback"]["demonstrated_live_path"]
        )

    def test_connected_mode_stops_before_host_validation_or_source_read(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(RUNNER, "validate_host_closure", side_effect=AssertionError),
            mock.patch.object(RUNNER, "render_plan", side_effect=AssertionError),
            mock.patch.object(Path, "read_bytes", side_effect=AssertionError),
            contextlib.redirect_stdout(output),
        ):
            status = RUNNER.main(["--connected"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue().strip(), RUNNER.DORMANT_VERDICT)

    def test_cli_surface_is_closed_and_host_mode_returns_json(self) -> None:
        options = RUNNER.build_parser()._option_string_actions
        self.assertEqual(
            set(options),
            {"-h", "--help", "--render-plan", "--validate-host", "--connected"},
        )
        expected = {"verdict": "fake", "live_authorized": False}
        output = io.StringIO()
        with (
            mock.patch.object(RUNNER, "validate_host_closure", return_value=expected),
            contextlib.redirect_stdout(output),
        ):
            status = RUNNER.main(["--validate-host"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_module_has_no_device_execution_backend(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "subprocess.",
            "Popen(",
            "os.system",
            "/usr/bin/adb",
            "adb devices",
            "adb shell",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
