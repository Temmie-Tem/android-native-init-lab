import importlib.util
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1a_stream_candidate_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_r4w1a_stream_candidate_live_gate", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_bugreport(module, path: Path, section: bytes) -> None:
    main_name = "bugreport-FYG8-r4w1a-stream.txt"
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


class S22PlusFyg8R4W1AStreamCandidateLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_artifact_a4_and_rollback_pins(self):
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
            "a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133",
        )
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
            "cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895",
        )
        self.assertEqual(
            self.module.QUALIFICATION_RESULT_SHA256,
            "077885c4f785760720463763905e4db3453c6e262021524e6fff97700bf6b12a",
        )
        self.assertEqual(
            self.module.EXPECTED_MAGISK_ROLLBACK_AP_SHA256,
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

    def test_real_a4_qualification_reopens_every_pinned_input(self):
        result = self.module.verify_a4_qualification(Path.cwd())
        self.assertEqual(result["verdict"], self.module.QUALIFICATION_VERDICT)
        self.assertFalse(result["second_live_baseline_required"])

    def test_a4_fresh_result_must_equal_pinned_result(self):
        pinned = json.loads(
            (Path.cwd() / self.module.QUALIFICATION_RESULT_RELATIVE).read_text(
                encoding="utf-8"
            )
        )
        changed = json.loads(json.dumps(pinned))
        changed["decision"]["candidate_clause_design_ready"] = False
        with mock.patch.object(
            self.module.qualification, "qualify", return_value=changed
        ), self.assertRaises(self.module.GateError):
            self.module.verify_a4_qualification(Path.cwd())

    def _stream(self, module, section: bytes):
        def fake(_serial, output, stderr_path, _timeout):
            make_bugreport(module, output, section)
            stderr_path.write_bytes(b"")
            return {
                "argv": [
                    "adb",
                    "-s",
                    "<S22_SERIAL_REDACTED>",
                    "exec-out",
                    "bugreportz",
                    "-s",
                ],
                "returncode": 0,
                "bytes": output.stat().st_size,
                "sha256": module.common.sha256_file(output),
                "stderr_bytes": 0,
                "read_to_eof": True,
            }

        return fake

    def _args(self, root: Path) -> SimpleNamespace:
        return SimpleNamespace(
            ack=self.module.LIVE_ACK_TOKEN,
            odin=Path("odin4"),
            run_dir=root / self.module.RUN_ROOT / "synthetic-live",
            candidate_ap=Path("candidate.AP.tar.md5"),
            download_wait_sec=1,
            disconnect_wait_sec=1,
            candidate_wait_sec=1,
            manual_wait_sec=1,
            android_wait_sec=1,
            bugreport_wait_sec=1,
            sample_count=3,
            sample_interval_sec=0.01,
        )

    def _write_live_result(self, run_dir: Path) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        self.module.common.durable_write_json(
            run_dir / "result.json",
            {
                "schema": self.module.SCHEMA,
                "mode": "live",
                "target": self.module.TARGET,
                "verdict": "INCOMPLETE",
            },
        )

    def test_exact_marker_stream_with_unchanged_inventory_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                self.module.historical,
                "stream_bugreport",
                side_effect=self._stream(self.module, self.module.oracle.EXPECTED_MARKER),
            ), mock.patch.object(
                self.module.historical, "remote_inventory", side_effect=[{}, {}]
            ):
                result = self.module.capture_stream_oracle(
                    "SERIAL", run_dir, expectation="exact", timeout=30
                )
        self.assertTrue(result["success"])
        self.assertTrue(result["inventory_unchanged"])
        self.assertTrue(result["parser_stream_identity_match"])
        self.assertFalse(result["remote_cleanup_allowed"])
        self.assertFalse(result["cleanup_attempted"])
        self.assertEqual(
            result["parser"]["marker"]["classification"],
            "EXACT_MARKER_ONCE_IN_LAST_KMSG",
        )

    def test_marker_absent_candidate_stream_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                self.module.historical,
                "stream_bugreport",
                side_effect=self._stream(self.module, b"ordinary retained log"),
            ), mock.patch.object(
                self.module.historical, "remote_inventory", side_effect=[{}, {}]
            ):
                result = self.module.capture_stream_oracle(
                    "SERIAL", run_dir, expectation="exact", timeout=30
                )
        self.assertFalse(result["success"])
        self.assertIn("oracle parser failed", result["errors"][0])

    def test_added_remote_file_fails_without_cleanup(self):
        added = {
            "/bugreports/new.zip": {
                "device": 1,
                "inode": 2,
                "size": 3,
                "mtime": 4,
                "mode": "81a0",
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                self.module.historical,
                "stream_bugreport",
                side_effect=self._stream(self.module, self.module.oracle.EXPECTED_MARKER),
            ), mock.patch.object(
                self.module.historical, "remote_inventory", side_effect=[{}, added]
            ):
                result = self.module.capture_stream_oracle(
                    "SERIAL", run_dir, expectation="exact", timeout=30
                )
        self.assertFalse(result["success"])
        self.assertFalse(result["inventory_unchanged"])
        self.assertFalse(result["cleanup_attempted"])
        self.assertIn("remote cleanup is forbidden", result["errors"][0])

    def test_changed_preexisting_remote_file_fails_closed(self):
        before = {"/bugreports/old.zip": {"inode": 1, "size": 2}}
        after = {"/bugreports/old.zip": {"inode": 1, "size": 3}}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                self.module.historical,
                "stream_bugreport",
                side_effect=self._stream(self.module, self.module.oracle.EXPECTED_MARKER),
            ), mock.patch.object(
                self.module.historical,
                "remote_inventory",
                side_effect=[before, after],
            ):
                result = self.module.capture_stream_oracle(
                    "SERIAL", run_dir, expectation="exact", timeout=30
                )
        self.assertFalse(result["success"])
        self.assertFalse(result["cleanup_attempted"])

    def test_parser_must_match_stream_size_hash_and_same_fd_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            fake_parse = {
                "input": {
                    "size": 1,
                    "sha256": "0" * 64,
                    "same_fd_pre_post_sha256": False,
                },
                "marker": {"classification": "EXACT_MARKER_ONCE_IN_LAST_KMSG"},
            }
            with mock.patch.object(
                self.module.historical,
                "stream_bugreport",
                side_effect=self._stream(self.module, self.module.oracle.EXPECTED_MARKER),
            ), mock.patch.object(
                self.module.historical, "remote_inventory", side_effect=[{}, {}]
            ), mock.patch.object(
                self.module.oracle, "parse_bugreport", return_value=fake_parse
            ):
                result = self.module.capture_stream_oracle(
                    "SERIAL", run_dir, expectation="exact", timeout=30
                )
        self.assertFalse(result["success"])
        self.assertFalse(result["parser_stream_identity_match"])

    def test_stream_failure_is_durable_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                self.module.historical,
                "stream_bugreport",
                side_effect=self.module.GateError("synthetic stream failure"),
            ), mock.patch.object(
                self.module.historical, "remote_inventory", side_effect=[{}, {}]
            ):
                result = self.module.capture_stream_oracle(
                    "SERIAL", run_dir, expectation="exact", timeout=30
                )
            durable = json.loads(
                (run_dir / "oracle_capture.json").read_text(encoding="utf-8")
            )
        self.assertFalse(result["success"])
        self.assertIsNone(result["stream"])
        self.assertFalse(result["cleanup_attempted"])
        self.assertIn("synthetic stream failure", result["errors"])
        self.assertEqual(durable, result)

    def test_candidate_consumption_is_exclusive_and_rollback_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            self._write_live_result(run_dir)
            with mock.patch.object(
                self.module, "helper_sha256", return_value="a" * 64
            ):
                self.module.consume_exception(root, run_dir)
                state = self.module.require_consumed_for_rollback(root)
                self.assertEqual(
                    state["schema"],
                    "s22plus_fyg8_r4w1a_stream_candidate_consumed_v2",
                )
                with self.assertRaises(self.module.GateError):
                    self.module.consume_exception(root, run_dir)

    def test_rollback_rejects_unbound_consumed_timestamp_run_dir_and_result(self):
        mutations = {
            "missing timestamp": lambda state: state.pop("consumed_at_utc"),
            "malformed timestamp": lambda state: state.__setitem__(
                "consumed_at_utc", "not-a-timestamp"
            ),
            "unsafe run directory": lambda state: state.__setitem__(
                "run_dir", "../outside"
            ),
            "missing run directory": lambda state: state.pop("run_dir"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir = root / "workspace/private/runs/run"
                self._write_live_result(run_dir)
                with mock.patch.object(
                    self.module, "helper_sha256", return_value="a" * 64
                ):
                    self.module.consume_exception(root, run_dir)
                    path = root / self.module.CONSUMED_STATE
                    state = json.loads(path.read_text(encoding="utf-8"))
                    mutate(state)
                    path.write_text(json.dumps(state), encoding="utf-8")
                    with self.assertRaises(self.module.GateError):
                        self.module.require_consumed_for_rollback(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            self._write_live_result(run_dir)
            with mock.patch.object(
                self.module, "helper_sha256", return_value="a" * 64
            ):
                self.module.consume_exception(root, run_dir)
                result_path = run_dir / "result.json"
                result = json.loads(result_path.read_text(encoding="utf-8"))
                result["target"] = "wrong-target"
                result_path.write_text(json.dumps(result), encoding="utf-8")
                with self.assertRaises(self.module.GateError):
                    self.module.require_consumed_for_rollback(root)

    def test_rollback_refuses_historical_or_malformed_consumed_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / self.module.CONSUMED_STATE
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({"schema": "s22plus_fyg8_r4w1a_consumed_state_v1"}),
                encoding="utf-8",
            )
            with mock.patch.object(
                self.module, "helper_sha256", return_value="a" * 64
            ), self.assertRaises(self.module.GateError):
                self.module.require_consumed_for_rollback(root)

    def test_policy_requires_exact_active_line_and_every_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = (
                self.module.POLICY_MARKER,
                str(self.module.SCRIPT_RELATIVE),
                "a" * 64,
                "b" * 64,
                self.module.LIVE_ACK_TOKEN,
                self.module.ROLLBACK_ACK_TOKEN,
                self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
                self.module.EXPECTED_CANDIDATE_AP_SHA256,
                self.module.EXPECTED_MARKER_ORACLE_SHA256,
                self.module.EXPECTED_MAGISK_ROLLBACK_AP_SHA256,
                self.module.EXPECTED_STOCK_CLEANUP_AP_SHA256,
                self.module.QUALIFICATION_SHA256,
                self.module.QUALIFICATION_TEST_SHA256,
                self.module.QUALIFICATION_RESULT_SHA256,
                self.module.QUALIFICATION_VERDICT,
            )
            agents = root / "AGENTS.md"
            draft = root / self.module.POLICY_DRAFT
            draft.parent.mkdir(parents=True)
            draft.write_text(
                "DRAFT_INACTIVE\n"
                + self.module.ACTIVE_SENTINEL
                + "\n"
                + "\n".join(values),
                encoding="utf-8",
            )
            agents.write_text(
                "this prose mentions " + self.module.ACTIVE_SENTINEL + "\n" + "\n".join(values),
                encoding="utf-8",
            )
            with mock.patch.object(
                self.module, "helper_sha256", return_value="a" * 64
            ), mock.patch.object(
                self.module, "test_sha256", return_value="b" * 64
            ):
                self.assertFalse(self.module.policy_active(root))
                agents.write_text(
                    self.module.ACTIVE_SENTINEL + "\n" + "\n".join(values),
                    encoding="utf-8",
                )
                self.assertTrue(self.module.policy_active(root))
                self.assertTrue(self.module.verify_policy_draft(root)["active"])
                agents.write_text(
                    self.module.ACTIVE_SENTINEL + "\n" + "\n".join(values[:-1]),
                    encoding="utf-8",
                )
                self.assertFalse(self.module.policy_active(root))
                self.assertFalse(self.module.verify_policy_draft(root)["active"])

    def test_real_policy_state_and_draft_are_self_consistent(self):
        root = Path.cwd()
        agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
        exact_active_line = bool(
            re.search(
                rf"(?m)^\s*`?{re.escape(self.module.ACTIVE_SENTINEL)}`?\s*$",
                agents_text,
            )
        )
        required_pins = (
            self.module.POLICY_MARKER,
            str(self.module.SCRIPT_RELATIVE),
            self.module.helper_sha256(root),
            self.module.test_sha256(root),
            self.module.LIVE_ACK_TOKEN,
            self.module.ROLLBACK_ACK_TOKEN,
            self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
            self.module.EXPECTED_MARKER_ORACLE_SHA256,
            self.module.EXPECTED_MAGISK_ROLLBACK_AP_SHA256,
            self.module.EXPECTED_STOCK_CLEANUP_AP_SHA256,
            self.module.QUALIFICATION_SHA256,
            self.module.QUALIFICATION_TEST_SHA256,
            self.module.QUALIFICATION_RESULT_SHA256,
            self.module.QUALIFICATION_VERDICT,
        )
        expected_active = exact_active_line and all(
            value in agents_text for value in required_pins
        )
        self.assertEqual(self.module.policy_active(root), expected_active)
        draft = self.module.verify_policy_draft(root)
        self.assertEqual(draft["state"], "DRAFT_INACTIVE")
        self.assertEqual(draft["active"], expected_active)

    def test_policy_draft_missing_pin_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft_path = root / self.module.POLICY_DRAFT
            draft_path.parent.mkdir(parents=True)
            draft = (Path.cwd() / self.module.POLICY_DRAFT).read_text(
                encoding="utf-8"
            )
            draft_path.write_text(
                draft.replace(self.module.QUALIFICATION_VERDICT, "", 1),
                encoding="utf-8",
            )
            with mock.patch.object(
                self.module,
                "helper_sha256",
                return_value=self.module.common.sha256_file(Path.cwd() / SCRIPT),
            ), mock.patch.object(
                self.module,
                "test_sha256",
                return_value=self.module.common.sha256_file(Path(__file__)),
            ), self.assertRaises(self.module.GateError):
                self.module.verify_policy_draft(root)

    def test_verdict_requires_magisk_android_and_exact_stream_marker(self):
        pass_case = self.module.classify_live_verdict(
            "magisk", "ignored", 0, True, [{}, {}, {}], True
        )
        self.assertEqual(
            pass_case,
            ("PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK", 0),
        )
        no_marker = self.module.classify_live_verdict(
            "magisk", "ignored", 0, True, [{}, {}, {}], False
        )
        self.assertEqual(no_marker[1], 41)
        self.assertNotIn("PASS_", no_marker[0])
        stock = self.module.classify_live_verdict(
            "stock", "CLEANUP_ONLY", 51, True, [{}, {}, {}], True
        )
        self.assertEqual(stock, ("CLEANUP_ONLY", 51))
        for transfer_ok, samples in ((True, [{}]), (False, [{}, {}, {}])):
            with self.subTest(transfer_ok=transfer_ok, samples=len(samples)):
                verdict = self.module.classify_live_verdict(
                    "magisk", "ignored", 0, transfer_ok, samples, True
                )
                self.assertNotIn("PASS_", verdict[0])

    def test_cli_requires_exact_three_samples_and_300_second_candidate_bound(self):
        parser = self.module.build_parser()
        valid = parser.parse_args(["--offline-check"])
        self.module.validate_runtime_args(valid)
        for argv in (
            ["--offline-check", "--sample-count", "1"],
            ["--offline-check", "--sample-count", "4"],
            ["--offline-check", "--candidate-wait-sec", "301"],
        ):
            with self.subTest(argv=argv), self.assertRaises(self.module.GateError):
                self.module.validate_runtime_args(parser.parse_args(argv))

    def test_preconsumption_failure_finishes_canonical_timeline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / self.module.RUN_ROOT / "synthetic-live"
            args = self._args(root)
            with mock.patch.object(
                self.module, "policy_active", return_value=True
            ), mock.patch.object(
                self.module.historical,
                "connected_preflight",
                side_effect=self.module.GateError("synthetic preflight failure"),
            ):
                rc = self.module.live_run(root, args, {})
            timeline = json.loads(
                (run_dir / "timeline.json").read_text(encoding="utf-8")
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 20)
        self.assertEqual(
            [event["name"] for event in timeline["events"]],
            list(self.module.TIMELINE_NAMES),
        )
        self.assertEqual(
            result["verdict"], "FAIL_R4W1A_PRECONSUMPTION_NO_CANDIDATE_FLASH"
        )

    def test_postconsumption_oserror_enters_mandatory_rollback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / self.module.RUN_ROOT / "synthetic-live"
            args = self._args(root)
            with mock.patch.object(
                self.module, "policy_active", return_value=True
            ), mock.patch.object(
                self.module, "helper_sha256", return_value="a" * 64
            ), mock.patch.object(
                self.module.historical,
                "connected_preflight",
                return_value=("SERIAL", {"baseline": True}),
            ), mock.patch.object(
                self.module.historical,
                "pstore_console_absent",
                return_value={"pstore": True},
            ), mock.patch.object(
                self.module.common,
                "run",
                return_value=SimpleNamespace(returncode=0),
            ), mock.patch.object(
                self.module.common, "wait_for_odin", return_value="ODIN"
            ), mock.patch.object(
                self.module.common,
                "flash_exact",
                side_effect=OSError("synthetic transfer transport failure"),
            ), mock.patch.object(
                self.module.common, "odin_devices", return_value=["ODIN"]
            ), mock.patch.object(
                self.module.common, "flash_rollback", return_value="magisk"
            ) as rollback, mock.patch.object(
                self.module.common,
                "wait_final_android",
                return_value=({"android": "healthy"}, "PASS_MAGISK_ROLLBACK", 0),
            ), mock.patch.object(
                self.module,
                "collect_rollback_corroboration",
                return_value={"load_bearing": False},
            ), mock.patch.object(
                self.module.common, "adb_serial", return_value="SERIAL"
            ):
                rc = self.module.live_run(root, args, {})
            timeline = json.loads(
                (run_dir / "timeline.json").read_text(encoding="utf-8")
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        rollback.assert_called_once()
        self.assertEqual(rc, 31)
        self.assertEqual(
            result["verdict"],
            "NO_PROOF_R4W1A_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK",
        )
        self.assertEqual(
            [event["name"] for event in timeline["events"]],
            list(self.module.TIMELINE_NAMES),
        )

    def test_recovery_target_failure_finishes_canonical_timeline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original_run = root / self.module.RUN_ROOT / "original-live"
            self._write_live_result(original_run)
            args = self._args(root)
            args.ack = self.module.ROLLBACK_ACK_TOKEN
            args.run_dir = root / self.module.RUN_ROOT / "synthetic-rollback"
            with mock.patch.object(
                self.module, "helper_sha256", return_value="a" * 64
            ):
                self.module.consume_exception(root, original_run)
                with mock.patch.object(
                    self.module, "policy_active", return_value=True
                ), mock.patch.object(self.module.common, "odin_devices", return_value=[]):
                    rc = self.module.rollback_from_download(root, args)
            timeline = json.loads(
                (args.run_dir / "timeline.json").read_text(encoding="utf-8")
            )
            result = json.loads(
                (args.run_dir / "result.json").read_text(encoding="utf-8")
            )
        self.assertEqual(rc, 20)
        self.assertEqual(
            [event["name"] for event in timeline["events"]],
            list(self.module.TIMELINE_NAMES),
        )
        self.assertEqual(
            result["verdict"], "FAIL_R4W1A_ROLLBACK_TARGET_RECOVERY_REQUIRED"
        )

    def test_source_has_no_remote_delete_or_old_oracle_promotion(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("cleanup_exact_remote_file", source)
        self.assertNotIn("ORACLE_PASS_STATE =", source)
        self.assertNotIn("create_pass_record", source)
        self.assertIn('expectation="exact"', source)
        self.assertIn("remote_cleanup_allowed\": False", source)
        self.assertIn('result["baseline_pstore_console_absent"]', source)
        self.assertIn("historical.pstore_console_absent(", source)
        self.assertIn(
            '"multiple Odin endpoints observed; no rollback flash started"',
            source,
        )

    def test_cli_exposes_no_second_baseline_oracle_mode(self):
        parser = self.module.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--oracle-dry-run"])
        args = parser.parse_args(["--offline-check"])
        self.assertTrue(args.offline_check)


if __name__ == "__main__":
    unittest.main()
