import importlib.util
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1a_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_bugreport(module, path: Path, section: bytes) -> None:
    main_name = "bugreport-FYG8-r4w1a.txt"
    report = (
        b"------ SYSTEM LOG ------\nordinary\n"
        + module.oracle.LAST_KMSG_HEADER
        + b"\n"
        + section
        + b"\n------ SYSTEM PROPERTIES ------\nproperty=value\n"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("version.txt", "2.0\n")
        archive.writestr("main_entry.txt", main_name + "\n")
        archive.writestr(main_name, report)


class S22PlusFyg8R4W1ALiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_candidate_oracle_and_rollback_pins(self):
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
            "a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133",
        )
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
            "cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895",
        )
        self.assertEqual(
            self.module.EXPECTED_ORACLE_SHA256,
            "bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462",
        )
        self.assertEqual(
            self.module.common.EXPECTED_MAGISK_AP_SHA256,
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(
            self.module.common.EXPECTED_STOCK_AP_SHA256,
            "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94",
        )

    def test_real_manifest_matches_live_contract(self):
        root = Path.cwd()
        manifest = self.module.verify_manifest(root / self.module.DEFAULT_MANIFEST)
        self.assertEqual(manifest["verdict"], "PASS_R4W1A_ARTIFACT_BUILT_HOST_ONLY")
        self.assertEqual(manifest["construction"]["r4w1_marker_count"], 1)
        self.assertEqual(
            manifest["construction"]["difference"]["outside_kernel_changed_byte_count"],
            0,
        )

    def test_timeline_has_only_canonical_events_shape(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.module.TIMELINE_NAMES:
                self.module.common.append_event(path, events, name)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"events"})
            self.assertEqual(
                [event["name"] for event in payload["events"]],
                list(self.module.TIMELINE_NAMES),
            )
            self.assertTrue(
                all(set(event) == {"name", "timestamp_utc"} for event in payload["events"])
            )

    def test_marker_absence_rejects_exact_foreign_and_boundary_partial(self):
        clean = self.module.classify_marker_absence(b"ordinary kernel log")
        self.assertTrue(clean["pass"])
        exact = self.module.classify_marker_absence(self.module.oracle.EXPECTED_MARKER)
        self.assertFalse(exact["pass"])
        foreign = self.module.classify_marker_absence(
            b"[[S22R4W9|id=foreign|phase=BAD|pid=2|path=/x]]"
        )
        self.assertFalse(foreign["pass"])
        partial = self.module.classify_marker_absence(
            b"prefix" + self.module.oracle.EXPECTED_MARKER[:50]
        )
        self.assertFalse(partial["pass"])

    def test_inventory_parser_requires_nul_and_safe_direct_paths(self):
        self.assertEqual(
            self.module.parse_inventory_paths(
                b"/bugreports/bugreport-a.zip\0/bugreports/dumpstate_log.txt\0"
            ),
            ["/bugreports/bugreport-a.zip", "/bugreports/dumpstate_log.txt"],
        )
        for payload in (
            b"/bugreports/no-terminator",
            b"/bugreports/../escape\0",
            b"/data/not-bugreport\0",
            b"/bugreports/a.zip\0/bugreports/a.zip\0",
        ):
            with self.subTest(payload=payload), self.assertRaises(self.module.GateError):
                self.module.parse_inventory_paths(payload)

    def test_inventory_delta_detects_preexisting_changes(self):
        original = {"/bugreports/old.zip": {"inode": 1, "size": 2}}
        clean_after = {
            **original,
            "/bugreports/new.zip": {"inode": 2, "size": 3},
        }
        clean = self.module.compare_inventories(original, clean_after)
        self.assertTrue(clean["preexisting_unchanged"])
        self.assertEqual(clean["added"], ["/bugreports/new.zip"])
        changed = self.module.compare_inventories(
            original, {"/bugreports/old.zip": {"inode": 1, "size": 99}}
        )
        self.assertFalse(changed["preexisting_unchanged"])
        self.assertEqual(changed["changed_preexisting"], ["/bugreports/old.zip"])

    def _capture_fakes(self, module, expectation: str, *, parser_marker: bytes):
        state = {"calls": 0, "identity": None, "sha": None}

        def fake_stream(_serial, output, stderr_path, _timeout):
            make_bugreport(module, output, parser_marker)
            stderr_path.write_bytes(b"")
            state["identity"] = {
                "device": 1,
                "inode": 22,
                "size": output.stat().st_size,
                "mtime": 33,
                "mode": "81a0",
            }
            state["sha"] = module.common.sha256_file(output)
            return {
                "returncode": 0,
                "bytes": output.stat().st_size,
                "sha256": state["sha"],
                "stderr_bytes": 0,
                "read_to_eof": True,
            }

        def fake_inventory(_serial):
            state["calls"] += 1
            if state["calls"] == 1 or state["calls"] == 3:
                return {}
            return {"/bugreports/bugreport-r4w1a.zip": state["identity"]}

        return state, fake_stream, fake_inventory

    def test_oracle_capture_parses_and_cleans_exact_created_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            state, fake_stream, fake_inventory = self._capture_fakes(
                self.module, "absent", parser_marker=b"ordinary retained log"
            )
            with mock.patch.object(
                self.module, "stream_bugreport", side_effect=fake_stream
            ), mock.patch.object(
                self.module, "remote_inventory", side_effect=fake_inventory
            ), mock.patch.object(
                self.module, "remote_file_sha256", side_effect=lambda *_: state["sha"]
            ), mock.patch.object(
                self.module, "cleanup_exact_remote_file"
            ) as cleanup:
                result = self.module.capture_oracle(
                    "serial", run_dir, expectation="absent", timeout=10
                )
            self.assertTrue(result["success"])
            self.assertTrue(result["cleanup_verified"])
            self.assertEqual(result["parser"]["marker"]["classification"], "MARKER_FAMILY_ABSENT")
            self.assertTrue(result["parser_stream_identity_match"])
            cleanup.assert_called_once()

    def test_oracle_capture_rejects_parser_input_not_bound_to_stream(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            state, fake_stream, fake_inventory = self._capture_fakes(
                self.module, "absent", parser_marker=b"ordinary retained log"
            )

            def fake_swapped_stream(*args):
                stream = fake_stream(*args)
                stream["sha256"] = "f" * 64
                state["sha"] = stream["sha256"]
                return stream

            with mock.patch.object(
                self.module, "stream_bugreport", side_effect=fake_swapped_stream
            ), mock.patch.object(
                self.module, "remote_inventory", side_effect=fake_inventory
            ), mock.patch.object(
                self.module, "remote_file_sha256", side_effect=lambda *_: state["sha"]
            ), mock.patch.object(
                self.module, "cleanup_exact_remote_file"
            ) as cleanup:
                result = self.module.capture_oracle(
                    "serial", run_dir, expectation="absent", timeout=10
                )
            self.assertFalse(result["success"])
            self.assertFalse(result["parser_stream_identity_match"])
            self.assertTrue(
                any("parsed host ZIP identity" in item for item in result["errors"])
            )
            cleanup.assert_called_once()

    def test_oracle_parser_failure_still_executes_exact_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            state, fake_stream, fake_inventory = self._capture_fakes(
                self.module,
                "absent",
                parser_marker=self.module.oracle.EXPECTED_MARKER,
            )
            with mock.patch.object(
                self.module, "stream_bugreport", side_effect=fake_stream
            ), mock.patch.object(
                self.module, "remote_inventory", side_effect=fake_inventory
            ), mock.patch.object(
                self.module, "remote_file_sha256", side_effect=lambda *_: state["sha"]
            ), mock.patch.object(
                self.module, "cleanup_exact_remote_file"
            ) as cleanup:
                result = self.module.capture_oracle(
                    "serial", run_dir, expectation="absent", timeout=10
                )
            self.assertFalse(result["success"])
            self.assertTrue(result["cleanup_verified"])
            self.assertTrue(any("oracle parser failed" in item for item in result["errors"]))
            cleanup.assert_called_once()

    def test_multiple_created_files_fail_closed_without_deletion(self):
        after = {
            "/bugreports/a.zip": {"device": 1, "inode": 1, "size": 1, "mtime": 1, "mode": "81a0"},
            "/bugreports/b.zip": {"device": 1, "inode": 2, "size": 1, "mtime": 1, "mode": "81a0"},
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module,
            "stream_bugreport",
            side_effect=self.module.GateError("stream failed"),
        ), mock.patch.object(
            self.module, "remote_inventory", side_effect=[{}, after]
        ), mock.patch.object(
            self.module, "cleanup_exact_remote_file"
        ) as cleanup:
            result = self.module.capture_oracle(
                "serial", Path(temporary), expectation="absent", timeout=10
            )
        self.assertFalse(result["success"])
        self.assertTrue(any("exactly one" in item for item in result["errors"]))
        cleanup.assert_not_called()

    def test_host_remote_mismatch_fails_closed_without_deletion(self):
        identity = {
            "device": 1,
            "inode": 2,
            "size": 10,
            "mtime": 3,
            "mode": "81a0",
        }
        after = {"/bugreports/new.zip": identity}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module,
            "stream_bugreport",
            return_value={
                "returncode": 0,
                "bytes": 9,
                "sha256": "1" * 64,
                "stderr_bytes": 0,
                "read_to_eof": True,
            },
        ), mock.patch.object(
            self.module, "remote_inventory", side_effect=[{}, after]
        ), mock.patch.object(
            self.module, "remote_file_sha256", return_value="2" * 64
        ), mock.patch.object(
            self.module, "cleanup_exact_remote_file"
        ) as cleanup:
            result = self.module.capture_oracle(
                "serial", Path(temporary), expectation="absent", timeout=10
            )
        self.assertFalse(result["success"])
        self.assertFalse(result["cleanup_attempted"])
        self.assertTrue(any("not deleted" in item for item in result["errors"]))
        cleanup.assert_not_called()

    def test_offline_check_never_contacts_device_or_policy_state(self):
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module.common,
            "current_android",
            side_effect=AssertionError("device contact"),
        ), mock.patch.object(
            self.module, "active_policy", side_effect=AssertionError("policy state")
        ), mock.patch("builtins.print"):
            self.assertEqual(self.module.main(["--offline-check"]), 0)

    def test_inactive_policies_block_write_and_flash_modes_before_device_contact(self):
        cases = (
            ("--oracle-dry-run", self.module.ORACLE_ACK_TOKEN),
            ("--live", self.module.LIVE_ACK_TOKEN),
            ("--rollback-from-download", self.module.ROLLBACK_ACK_TOKEN),
        )
        for mode, token in cases:
            with self.subTest(mode=mode), mock.patch.object(
                self.module, "verify_artifacts", return_value={"candidate": "pinned"}
            ), mock.patch.object(
                self.module, "verify_policy_draft", return_value={"active": False}
            ), mock.patch.object(
                self.module, "active_policy", return_value=False
            ), mock.patch.object(
                self.module.common,
                "current_android",
                side_effect=AssertionError("device contact"),
            ), mock.patch.object(
                self.module.common,
                "odin_devices",
                side_effect=AssertionError("device contact"),
            ), mock.patch("builtins.print"):
                self.assertEqual(self.module.main([mode, "--ack", token]), 2)

    def test_connected_dry_run_requires_fresh_ack_before_device_contact(self):
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module,
            "connected_preflight",
            side_effect=AssertionError("device contact"),
        ), mock.patch("builtins.print"):
            self.assertEqual(self.module.main(["--connected-dry-run"]), 2)

    def test_real_policy_draft_pins_current_helper_and_reports_exact_state(self):
        policy = self.module.verify_policy_draft(Path.cwd())
        self.assertEqual(
            policy["current_source_sha256"], self.module.helper_sha256(Path.cwd())
        )
        self.assertEqual(
            policy["oracle_policy_active"],
            self.module.active_policy(Path.cwd(), oracle_only=True),
        )
        self.assertEqual(
            policy["candidate_policy_active"],
            self.module.active_policy(Path.cwd(), oracle_only=False),
        )

    def test_oracle_policy_activation_requires_exact_connected_record_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, result_path = self._temporary_promotion_root(temporary)
            result = {
                "schema": self.module.SCHEMA,
                "mode": "connected-dry-run",
                "target": self.module.TARGET,
                "device_writes": False,
                "verdict": "PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY",
            }
            self.module.common.durable_write_json(result_path, result)
            record_sha = self.module.create_pass_record(
                root, "connected", result_path, result["verdict"]
            )
            required = (
                self.module.ORACLE_ACTIVE_SENTINEL,
                self.module.ORACLE_POLICY_MARKER,
                str(self.module.SCRIPT_RELATIVE),
                self.module.helper_sha256(root),
                self.module.ORACLE_ACK_TOKEN,
                self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
                self.module.EXPECTED_CANDIDATE_AP_SHA256,
                self.module.EXPECTED_ORACLE_SHA256,
                self.module.common.EXPECTED_MAGISK_AP_SHA256,
                str(self.module.CONNECTED_PASS_STATE),
                record_sha,
            )
            agents = root / "AGENTS.md"
            agents.write_text("\n".join(required) + "\n", encoding="utf-8")
            self.assertTrue(self.module.active_policy(root, oracle_only=True))
            self.assertFalse(self.module.active_policy(root, oracle_only=False))
            agents.write_text(
                "\n".join(item for item in required if item != record_sha) + "\n",
                encoding="utf-8",
            )
            self.assertFalse(self.module.active_policy(root, oracle_only=True))

    def test_candidate_policy_activation_requires_exact_oracle_record_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, connected_result = self._temporary_promotion_root(temporary)
            connected = {
                "schema": self.module.SCHEMA,
                "mode": "connected-dry-run",
                "target": self.module.TARGET,
                "device_writes": False,
                "verdict": "PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY",
            }
            self.module.common.durable_write_json(connected_result, connected)
            connected_sha = self.module.create_pass_record(
                root, "connected", connected_result, connected["verdict"]
            )
            oracle_result = root / self.module.RUN_ROOT / "oracle-run/result.json"
            oracle_result.parent.mkdir(parents=True)
            oracle = {
                "schema": self.module.SCHEMA,
                "mode": "oracle-dry-run",
                "target": self.module.TARGET,
                "capture": {
                    "success": True,
                    "cleanup_verified": True,
                    "parser_stream_identity_match": True,
                    "parser": {
                        "marker": {"classification": "MARKER_FAMILY_ABSENT"}
                    },
                },
                "verdict": "PASS_R4W1A_ORACLE_DRY_RUN_EXACT_ZIP_AND_CLEANUP",
            }
            self.module.common.durable_write_json(oracle_result, oracle)
            self.module.consume_oracle_exception(root, oracle_result.parent)
            oracle_sha = self.module.create_pass_record(
                root, "oracle", oracle_result, oracle["verdict"]
            )
            required = (
                self.module.ACTIVE_SENTINEL,
                self.module.POLICY_MARKER,
                str(self.module.SCRIPT_RELATIVE),
                self.module.helper_sha256(root),
                self.module.LIVE_ACK_TOKEN,
                self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
                self.module.EXPECTED_CANDIDATE_AP_SHA256,
                self.module.EXPECTED_ORACLE_SHA256,
                self.module.common.EXPECTED_MAGISK_AP_SHA256,
                str(self.module.CONNECTED_PASS_STATE),
                connected_sha,
                self.module.ROLLBACK_ACK_TOKEN,
                self.module.common.EXPECTED_STOCK_AP_SHA256,
                str(self.module.ORACLE_PASS_STATE),
                oracle_sha,
            )
            agents = root / "AGENTS.md"
            agents.write_text("\n".join(required) + "\n", encoding="utf-8")
            self.assertTrue(self.module.active_policy(root, oracle_only=False))
            agents.write_text(
                "\n".join(item for item in required if item != oracle_sha) + "\n",
                encoding="utf-8",
            )
            self.assertFalse(self.module.active_policy(root, oracle_only=False))

    def test_one_shot_state_is_separate_and_durable(self):
        self.assertNotEqual(self.module.CONSUMED_STATE, self.module.common.CONSUMED_STATE)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)
            self.module.consume_exception(root, run_dir)
            state = json.loads(
                self.module.consumed_state_path(root).read_text(encoding="utf-8")
            )
            self.assertEqual(state["reason"], "candidate_flash_start")
            with self.assertRaises(self.module.GateError):
                self.module.consume_exception(root, run_dir)

    def _temporary_promotion_root(self, temporary: str) -> tuple[Path, Path]:
        root = Path(temporary)
        helper = root / self.module.SCRIPT_RELATIVE
        helper.parent.mkdir(parents=True)
        helper.write_bytes(SCRIPT.read_bytes())
        result = root / self.module.RUN_ROOT / "promotion-run/result.json"
        result.parent.mkdir(parents=True)
        return root, result

    def test_connected_pass_record_reopens_and_pins_exact_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, result_path = self._temporary_promotion_root(temporary)
            result = {
                "schema": self.module.SCHEMA,
                "mode": "connected-dry-run",
                "target": self.module.TARGET,
                "device_writes": False,
                "verdict": "PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY",
            }
            self.module.common.durable_write_json(result_path, result)
            record_sha = self.module.create_pass_record(
                root, "connected", result_path, result["verdict"]
            )
            self.assertEqual(
                record_sha, self.module.validate_pass_record(root, "connected")
            )
            result_path.write_text("{}\n", encoding="ascii")
            with self.assertRaises(self.module.GateError):
                self.module.validate_pass_record(root, "connected")

    def test_oracle_pass_record_requires_shape_cleanup_and_absent_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, result_path = self._temporary_promotion_root(temporary)
            result = {
                "schema": self.module.SCHEMA,
                "mode": "oracle-dry-run",
                "target": self.module.TARGET,
                "capture": {
                    "success": True,
                    "cleanup_verified": True,
                    "parser_stream_identity_match": True,
                    "parser": {
                        "marker": {"classification": "MARKER_FAMILY_ABSENT"}
                    },
                },
                "verdict": "PASS_R4W1A_ORACLE_DRY_RUN_EXACT_ZIP_AND_CLEANUP",
            }
            self.module.common.durable_write_json(result_path, result)
            self.module.consume_oracle_exception(root, result_path.parent)
            record_sha = self.module.create_pass_record(
                root, "oracle", result_path, result["verdict"]
            )
            self.assertEqual(record_sha, self.module.validate_pass_record(root, "oracle"))

    def test_oracle_capture_consumption_is_one_shot_and_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _ = self._temporary_promotion_root(temporary)
            run_dir = root / self.module.RUN_ROOT / "oracle-run"
            run_dir.mkdir(parents=True)
            self.module.consume_oracle_exception(root, run_dir)
            self.assertTrue((root / self.module.ORACLE_CONSUMED_STATE).is_file())
            self.assertFalse((root / self.module.CONSUMED_STATE).exists())
            with self.assertRaises(self.module.GateError):
                self.module.consume_oracle_exception(root, run_dir)

    def test_live_verdict_matrix(self):
        cases = (
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                True,
                [{"boot_completed": "1"}],
                True,
                "PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK",
                0,
            ),
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                True,
                [{"boot_completed": "1"}],
                False,
                "NO_PROOF_R4W1A_ANDROID_VIABLE_WITNESS_NOT_RECOVERED",
                41,
            ),
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                False,
                [],
                False,
                "NO_PROOF_R4W1A_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK",
                31,
            ),
            (
                "stock",
                "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED",
                30,
                True,
                [{"boot_completed": "1"}],
                True,
                "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED",
                30,
            ),
        )
        for target, rollback, rc, transfer, samples, marker, verdict, expected_rc in cases:
            with self.subTest(verdict=verdict):
                self.assertEqual(
                    self.module.classify_live_verdict(
                        target, rollback, rc, transfer, samples, marker
                    ),
                    (verdict, expected_rc),
                )

    def test_exact_cleanup_refuses_paths_outside_bugreports(self):
        with self.assertRaises(self.module.GateError), mock.patch.object(
            self.module, "remote_exec_out"
        ) as execute:
            self.module.cleanup_exact_remote_file(
                "serial",
                "/data/not-authorized.zip",
                {"device": 1, "inode": 2, "size": 3, "mtime": 4, "mode": "81a0"},
                "0" * 64,
            )
        execute.assert_not_called()

    def test_source_contains_no_nonboot_flash_or_debug_actions(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "--repartition",
            "fastboot",
            "/proc/sysrq-trigger",
            "PrEaMbLe",
            "DaTaXfEr",
            "vendor_boot.img",
            "recovery.img",
            "dtbo.img",
            "vbmeta.img",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("common.flash_exact", source)
        self.assertIn("common.flash_rollback", source)
        self.assertIn('["adb", "-s", serial, "exec-out", "bugreportz", "-s"]', source)


if __name__ == "__main__":
    unittest.main()
