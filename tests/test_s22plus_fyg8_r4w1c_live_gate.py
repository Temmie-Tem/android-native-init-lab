import importlib.util
import contextlib
import io
import json
import os
import stat
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("r4w1c_live_gate_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1CLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def make_root(self, temporary: str) -> Path:
        module = self.module
        root = Path(temporary)
        for relative, payload in (
            (module.SCRIPT_RELATIVE, b"helper"),
            (module.TEST_RELATIVE, b"test"),
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        (root / module.CONSUMED_STATE.parent).mkdir(parents=True, exist_ok=True)
        template = root / module.POLICY_DRAFT
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_bytes((Path.cwd() / module.POLICY_DRAFT).read_bytes())
        return root

    def binding(self, module, **overrides):
        value = {
            "pass_path": str(module.connected.PASS_STATE),
            "created_at_utc": "2026-07-19T20:00:00.000000Z",
            "pass_size": 123,
            "pass_sha256": "a" * 64,
            "result_path": "workspace/private/runs/r4w1c-connected/result.json",
            "result_size": 456,
            "result_sha256": "b" * 64,
        }
        value.update(overrides)
        return value

    def binding_clause(self, module, **overrides):
        values = {
            "pass_path": str(module.connected.PASS_STATE),
            "created_at": "2026-07-19T20:00:00.000000Z",
            "pass_size": "123",
            "pass_sha": "a" * 64,
            "result_path": "workspace/private/runs/r4w1c-connected/result.json",
            "result_size": "456",
            "result_sha": "b" * 64,
        }
        values.update(overrides)
        return (
            "The load-bearing connected PASS record is\n"
            f"`{values['pass_path']}`, created at `{values['created_at']}`, size\n"
            f"`{values['pass_size']}`, SHA256\n"
            f"`{values['pass_sha']}`. It binds connected result\n"
            f"`{values['result_path']}`, size `{values['result_size']}`, SHA256\n"
            f"`{values['result_sha']}`.\n"
        )

    def test_parser_has_only_offline_live_and_recovery_modes(self):
        options = {action.dest for action in self.module.build_parser()._actions}
        self.assertIn("offline_check", options)
        self.assertIn("live", options)
        self.assertIn("rollback_from_download", options)
        self.assertNotIn("connected_read_only_dry_run", options)

    def test_exact_frozen_connected_and_core_pins(self):
        module = self.module
        self.assertEqual(
            module.CONNECTED_HELPER_SHA256,
            "fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9",
        )
        self.assertEqual(
            module.CONNECTED_TEST_SHA256,
            "98938da61fc6a3f95389a31f019950fa00b3e6575687aab8d1edf5d070240251",
        )
        self.assertEqual(
            module.CONNECTED_CLAUSE_SHA256,
            "35f1d2cf8b9a4b25bac108832fb3f9ec9fd37e05c1b03f9fa34eeb5367c17ffa",
        )
        self.assertEqual(module.LIVE_CORE_SHA256, module.connected.EXPECTED_LIVE_CORE_SHA256)
        self.assertEqual(module.ODIN_CORE_SHA256, module.connected.EXPECTED_ODIN_CORE_SHA256)

    def test_parse_connected_binding_accepts_exact_shape(self):
        value = self.module.parse_connected_binding(self.binding_clause(self.module))
        self.assertEqual(value["pass_size"], 123)
        self.assertEqual(value["result_size"], 456)
        self.assertEqual(value["result_path"], "workspace/private/runs/r4w1c-connected/result.json")

    def test_parse_connected_binding_rejects_traversal_and_duplicate(self):
        module = self.module
        bad = self.binding_clause(module, result_path="workspace/private/runs/../result.json")
        with self.assertRaises(module.GateError):
            module.parse_connected_binding(bad)
        exact = self.binding_clause(module)
        with self.assertRaises(module.GateError):
            module.parse_connected_binding(exact + exact)

    def test_policy_clause_is_scoped_and_requires_one_exact_sentinel(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            clause, _identity = module.render_policy_clause(
                root, self.binding(module)
            )
            (root / "AGENTS.md").write_text("outside active\n" + clause + "\noutside\n")
            self.assertIn(module.POLICY_BEGIN, module.policy_clause(root))
            (root / "AGENTS.md").write_text(
                clause.replace("at most two numbered recovery attempts", "at most nine numbered recovery attempts")
            )
            with self.assertRaises(module.GateError):
                module.policy_clause(root)

    def test_runtime_args_reject_nan_and_out_of_bounds(self):
        module = self.module
        args = module.build_parser().parse_args(["--offline-check"])
        args.park_wait_sec = float("nan")
        with self.assertRaises(module.GateError):
            module.validate_runtime_args(args)
        args.park_wait_sec = 181
        with self.assertRaises(module.GateError):
            module.validate_runtime_args(args)

    def test_observation_never_claims_watchdog_proof(self):
        module = self.module
        clock = iter([10.0, 130.0])
        with mock.patch.object(module.time, "sleep"), mock.patch.object(
            module.time, "monotonic", side_effect=lambda: next(clock)
        ):
            result = module.observe_candidate(120)
        self.assertTrue(result["full_window_completed"])
        self.assertFalse(result["watchdog_survival_directly_proven"])

    def test_classification_matrix(self):
        module = self.module
        clean_present = {"marker": {"integrity_issue": False, "acceptance_present": True}}
        clean_absent = {"marker": {"integrity_issue": False, "acceptance_present": False}}
        observation = {
            "bounded": True,
            "requested_sec": module.DEFAULT_PARK_WAIT_SEC,
            "elapsed_sec": module.DEFAULT_PARK_WAIT_SEC,
            "full_window_completed": True,
            "odin_disconnected": True,
            "candidate_transfer_ok": True,
        }
        self.assertEqual(
            module.classify_verdict(
                rollback_target="magisk",
                rollback_ok=True,
                candidate_transfer_ok=True,
                candidate_observation=observation,
                observer=clean_present,
            ),
            (module.PASS_VERDICT, 0),
        )
        self.assertEqual(
            module.classify_verdict(
                rollback_target="magisk",
                rollback_ok=True,
                candidate_transfer_ok=True,
                candidate_observation=observation,
                observer=clean_absent,
            ),
            (module.NO_PROOF_VERDICT, 32),
        )
        self.assertEqual(
            module.classify_verdict(
                rollback_target="stock",
                rollback_ok=True,
                candidate_transfer_ok=True,
                candidate_observation=observation,
                observer=clean_present,
            )[0],
            "FAIL_R4W1C_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
        )

    def test_classification_requires_complete_candidate_observation(self):
        module = self.module
        observer = {
            "marker": {"integrity_issue": False, "acceptance_present": True}
        }
        complete = {
            "bounded": True,
            "requested_sec": module.DEFAULT_PARK_WAIT_SEC,
            "elapsed_sec": module.DEFAULT_PARK_WAIT_SEC,
            "full_window_completed": True,
            "odin_disconnected": True,
            "candidate_transfer_ok": True,
        }
        incomplete_values = (
            None,
            {**complete, "elapsed_sec": module.DEFAULT_PARK_WAIT_SEC - 0.001},
            {**complete, "full_window_completed": False},
            {**complete, "odin_disconnected": False},
            {**complete, "candidate_transfer_ok": False},
        )
        for observation in incomplete_values:
            with self.subTest(observation=observation):
                self.assertEqual(
                    module.classify_verdict(
                        rollback_target="magisk",
                        rollback_ok=True,
                        candidate_transfer_ok=True,
                        candidate_observation=observation,
                        observer=observer,
                    ),
                    ("FAIL_R4W1C_CANDIDATE_OBSERVATION_REQUIRED", 25),
                )

    def test_consumed_state_is_exclusive_and_reopens_same_run(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            run_dir = root / module.RUN_ROOT / "live-run"
            run_dir.mkdir(parents=True)
            evidence = {"binding": self.binding(module)}
            artifacts = {"target": module.TARGET}
            baseline = {
                "android_serial": "serial",
                "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
            }
            with module.odin_core.transaction_session(run_dir) as lease:
                module.create_phase(
                    run_dir,
                    "prepared",
                    module.connected.expected_phase_payload(baseline),
                    lease=lease,
                )
            policy = module.verify_policy_draft(root)
            clause = "exact active clause"
            record = module.consume_exception(
                root,
                run_dir,
                artifacts,
                evidence,
                policy,
                clause,
                baseline,
                {"topology": "1-2", "serial_sha256": "e" * 64},
                "2026-07-20T00:00:00.000000Z",
            )
            with mock.patch.object(
                module, "reopen_connected_evidence", return_value=evidence
            ):
                reopened, reopened_run, reopened_evidence = module.require_consumed(
                    root, artifacts, policy, clause
                )
            self.assertEqual(record, reopened)
            self.assertEqual(reopened_run, run_dir)
            self.assertEqual(reopened_evidence, evidence)
            with self.assertRaises(module.GateError):
                module.consume_exception(
                    root,
                    run_dir,
                    artifacts,
                    evidence,
                    policy,
                    clause,
                    baseline,
                    {"topology": "1-2", "serial_sha256": "e" * 64},
                    "2026-07-20T00:00:00.000000Z",
                )

    def test_consumed_state_parent_symlink_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            real = root / "real-state"
            real.mkdir()
            state_parent = root / module.CONSUMED_STATE.parent
            state_parent.rmdir()
            state_parent.symlink_to(real, target_is_directory=True)
            with self.assertRaises(module.connected.GateError):
                module._direct_state_parent(root)

    def test_normalize_recovery_prefix_adds_only_missing_candidate_phases(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            with module.odin_core.transaction_session(run_dir) as lease:
                baseline = {
                    "android_serial": "serial",
                    "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
                }
                module.create_phase(
                    run_dir,
                    "prepared",
                    module.connected.expected_phase_payload(baseline),
                    lease=lease,
                )
                module.normalize_recovery_prefix(run_dir, lease=lease)
            self.assertEqual(
                module._phase_names(run_dir),
                list(module.odin_core.TRANSACTION_PHASES[:4]),
            )
            for phase in module.odin_core.TRANSACTION_PHASES[1:4]:
                self.assertTrue(
                    module.phase_payload(Path(temporary), run_dir, phase)["recovery_fill"]
                )

    def test_next_snapshot_sequence_rejects_gap(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                module.odin_core,
                "list_snapshot_receipts",
                return_value=[{"sequence": 0}, {"sequence": 2}],
            ):
                with self.assertRaises(module.GateError):
                    module.next_snapshot_sequence(run_dir)

    def test_fresh_confirmation_rejects_prebuffered_non_tty(self):
        module = self.module
        with mock.patch.object(module.sys.stdin, "fileno", return_value=9), mock.patch.object(
            module.os, "isatty", return_value=False
        ), mock.patch.object(module.select, "select", return_value=([9], [], [])):
            with self.assertRaises(module.GateError):
                module.prepare_fresh_confirmation_input()

    def test_read_confirmation_rejects_trailing_input(self):
        module = self.module
        with mock.patch.object(module.select, "select", return_value=([9], [], [])), mock.patch.object(
            module.os, "read", return_value=b"token\nextra"
        ):
            with self.assertRaises(module.GateError):
                module.read_fresh_confirmation(1.0, 9)

    def test_transaction_evidence_reopens_receipts_and_index(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            runner = lambda _argv, _timeout: SimpleNamespace(
                returncode=0, stdout="", stderr=""
            )
            with module.odin_core.transaction_session(run_dir) as lease:
                module.odin_core.wait_for_no_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=runner,
                    device_inventory=lambda: {},
                    device_identity=lambda _path: None,
                )
                module.create_phase(run_dir, "prepared", {"ok": True}, lease=lease)
            evidence = module.transaction_evidence(root, run_dir)
            self.assertEqual(len(evidence["snapshots"]), 1)
            self.assertEqual([value["phase"] for value in evidence["phases"]], ["prepared"])
            self.assertGreaterEqual(evidence["record_count"], 2)

    def test_finish_preserves_original_failure_when_no_receipts_exist(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)
            timeline = []
            timeline_path = run_dir / "timeline.json"
            rc = module._finish(
                root,
                run_dir,
                timeline_path,
                timeline,
                {"schema": module.SCHEMA},
                verdict="FAIL_TEST",
                rc=1,
                result_name="result-test.json",
                error="original",
            )
            self.assertEqual(rc, 1)
            result = json.loads((run_dir / "result-test.json").read_text())
            self.assertEqual(result["error"], "original")
            self.assertIsNone(result["transaction_evidence"])

    def test_reopen_connected_evidence_requires_clause_exact_hashes(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            pass_path = root / module.connected.PASS_STATE
            result_path = root / "workspace/private/runs/r4w1c-connected/result.json"
            result_path.parent.mkdir(parents=True)
            result_path.write_text("{}\n")
            record = {
                "created_at_utc": "2026-07-19T20:00:00.000000Z",
                "result_path": str(result_path.relative_to(root)),
                "helper_sha256": module.CONNECTED_HELPER_SHA256,
                "test_sha256": module.CONNECTED_TEST_SHA256,
                "policy_clause_sha256": module.CONNECTED_CLAUSE_SHA256,
            }
            pass_path.parent.mkdir(parents=True, exist_ok=True)
            pass_path.write_text(json.dumps(record))
            pass_identity = module.core.hash_stable_file(pass_path)
            result_identity = module.core.hash_stable_file(result_path)
            clause = self.binding_clause(
                module,
                pass_size=str(pass_identity["size"]),
                pass_sha=pass_identity["sha256"],
                result_size=str(result_identity["size"]),
                result_sha=result_identity["sha256"],
            )
            with mock.patch.object(
                module.connected, "validate_connected_pass", return_value=record
            ):
                reopened = module.reopen_connected_evidence(root, {}, clause)
            self.assertEqual(reopened["binding"]["pass_sha256"], pass_identity["sha256"])
            with self.assertRaises(module.GateError):
                module.reopen_connected_evidence(root, {}, clause.replace("a", "c", 1))

    def test_completed_rollback_receipt_does_not_invoke_flash(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            timeline = []
            timeline_path = run_dir / "recovery-attempt-01-timeline.json"
            for name in module.core.TIMELINE_NAMES[:4]:
                module.core.append_event(timeline_path, timeline, name)
            args = module.build_parser().parse_args(["--rollback-from-download"])
            with module.odin_core.transaction_session(run_dir) as lease:
                for phase, payload in zip(
                    module.odin_core.TRANSACTION_PHASES[:7],
                    [
                        {"ok": True},
                        {"ok": True},
                        {"ok": True},
                        {"ok": True},
                        {"ok": True},
                        {"ok": True},
                        {"target": "magisk", "revalidation": {}},
                    ],
                ):
                    module.create_phase(run_dir, phase, payload, lease=lease)
                with mock.patch.object(module, "wait_magisk_android", side_effect=module.GateError("stop")), mock.patch.object(
                    module, "flash_sealed_exact"
                ) as flash:
                    rc = module._rollback_sequence(
                        root,
                        args,
                        run_dir,
                        timeline_path,
                        timeline,
                        {
                            "candidate_transfer_ok": False,
                            "android_serial": "serial",
                            "usb_binding": {
                                "topology": "1-2",
                                "serial_sha256": "e" * 64,
                            },
                        },
                        Path("odin4"),
                        9,
                        sequence=0,
                        lease=lease,
                        attempt=1,
                        result_name="result-recovery-attempt-01.json",
                    )
            self.assertEqual(rc, 20)
            flash.assert_not_called()

    def test_recovery_rejects_inactive_policy_before_consumed_state(self):
        module = self.module
        args = module.build_parser().parse_args(
            ["--rollback-from-download", "--ack", module.ROLLBACK_ACK_TOKEN]
        )
        with mock.patch.object(module, "policy_active", return_value=False), mock.patch.object(
            module, "require_consumed"
        ) as require_consumed:
            with self.assertRaises(module.GateError):
                module.rollback_from_download(
                    Path("/repo"), args, {"target": module.TARGET}, {"active": False}
                )
        require_consumed.assert_not_called()

    def test_ticket_topology_rejects_different_physical_port(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/001/002",
            device_identity="identity",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        with mock.patch.object(
            module,
            "endpoint_usb_identity",
            return_value={
                "topology": "1-3",
                "vendor": "04e8",
                "product": module.DOWNLOAD_USB_PRODUCT,
                "serial_sha256": "e" * 64,
                "device_identity": ticket.device_identity,
            },
        ):
            with self.assertRaises(module.GateError):
                module.require_ticket_usb_binding(
                    ticket, {"topology": "1-2", "serial_sha256": "e" * 64}
                )

    def test_endpoint_usb_identity_restats_after_sysfs_reads(self):
        module = self.module
        metadata = SimpleNamespace(st_rdev=os.makedev(189, 2))
        sysfs_device = Path("/sys/devices/platform/usb1/1-2")
        fields = ["04e8\n", "685d\n", "1\n", "2\n", "SERIAL123\n"]

        with mock.patch.object(
            module,
            "endpoint_node_snapshot",
            side_effect=[
                (metadata, "1:2:3:4"),
                (metadata, "1:2:3:4"),
            ],
        ) as snapshot, mock.patch.object(
            Path, "resolve", return_value=sysfs_device
        ), mock.patch.object(Path, "read_text", side_effect=fields):
            identity = module.endpoint_usb_identity("/dev/bus/usb/001/002")
        self.assertEqual(identity["device_identity"], "1:2:3:4")
        self.assertEqual(snapshot.call_count, 2)

        with mock.patch.object(
            module,
            "endpoint_node_snapshot",
            side_effect=[
                (metadata, "1:2:3:4"),
                (metadata, "1:9:3:5"),
            ],
        ), mock.patch.object(
            Path, "resolve", return_value=sysfs_device
        ), mock.patch.object(Path, "read_text", side_effect=fields):
            with self.assertRaisesRegex(module.GateError, "changed while reading"):
                module.endpoint_usb_identity("/dev/bus/usb/001/002")

    def test_ticket_usb_binding_rejects_same_port_other_serial(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/001/002",
            device_identity="identity",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        with mock.patch.object(
            module,
            "endpoint_usb_identity",
            return_value={
                "topology": "1-2",
                "vendor": "04e8",
                "product": module.DOWNLOAD_USB_PRODUCT,
                "serial_sha256": "f" * 64,
                "device_identity": ticket.device_identity,
            },
        ):
            with self.assertRaises(module.GateError):
                module.require_ticket_usb_binding(
                    ticket, {"topology": "1-2", "serial_sha256": "e" * 64}
                )

    def test_ticket_usb_binding_requires_download_product(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/001/002",
            device_identity="identity",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        with mock.patch.object(
            module,
            "endpoint_usb_identity",
            return_value={
                "topology": "1-2",
                "vendor": "04e8",
                "product": "6860",
                "serial_sha256": "e" * 64,
                "device_identity": ticket.device_identity,
            },
        ):
            with self.assertRaisesRegex(module.GateError, "Download identity"):
                module.require_ticket_usb_binding(
                    ticket, {"topology": "1-2", "serial_sha256": "e" * 64}
                )

    def test_ticket_usb_binding_rejects_same_path_recreated_node(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/001/002",
            device_identity="1:2:3:4",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        with mock.patch.object(
            module,
            "endpoint_usb_identity",
            return_value={
                "topology": "1-2",
                "vendor": "04e8",
                "product": module.DOWNLOAD_USB_PRODUCT,
                "serial_sha256": "e" * 64,
                "device_identity": "1:9:3:5",
            },
        ):
            with self.assertRaisesRegex(module.GateError, "Download identity"):
                module.require_ticket_usb_binding(
                    ticket, {"topology": "1-2", "serial_sha256": "e" * 64}
                )

    def test_adb_usb_binding_requires_selected_and_sysfs_serial_agreement(self):
        module = self.module
        result = SimpleNamespace(returncode=0, stdout="SERIAL123\n", stderr=None)
        with mock.patch.object(
            module, "adb_usb_topology", return_value="1-2"
        ), mock.patch.object(
            module.transport, "run", return_value=result
        ), mock.patch.object(
            Path, "read_text", return_value="SERIAL123\n"
        ):
            binding = module.adb_usb_binding("SERIAL123")
        self.assertEqual(binding["topology"], "1-2")
        self.assertRegex(binding["serial_sha256"], r"^[0-9a-f]{64}$")

    def test_adb_usb_topology_requires_exact_get_devpath_shape(self):
        module = self.module
        good = SimpleNamespace(returncode=0, stdout="usb:1-2.3\n", stderr=None)
        bad = SimpleNamespace(returncode=0, stdout="usb:1-2 extra\n", stderr=None)
        with mock.patch.object(module.transport, "run", return_value=good):
            self.assertEqual(module.adb_usb_topology("serial"), "1-2.3")
        with mock.patch.object(module.transport, "run", return_value=bad):
            with self.assertRaises(module.GateError):
                module.adb_usb_topology("serial")

    def test_bound_download_sample_requires_expected_product_and_serial(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            sysfs = Path(temporary)
            device = sysfs / "2-1.3"
            device.mkdir()
            values = {
                "idVendor": "04e8\n",
                "idProduct": module.DOWNLOAD_USB_PRODUCT + "\n",
                "serial": "SERIAL123\n",
                "busnum": "2\n",
                "devnum": "14\n",
            }
            for name, value in values.items():
                (device / name).write_text(value)
            expected = {
                "topology": "2-1.3",
                "serial_sha256": module.core.sha256_bytes(b"SERIAL123"),
            }
            metadata = SimpleNamespace(
                st_mode=stat.S_IFCHR,
                st_dev=1,
                st_ino=2,
                st_rdev=3,
                st_ctime_ns=4,
            )
            with mock.patch.object(module.os, "stat", return_value=metadata):
                sample = module.bound_download_node_sample(
                    expected, sysfs_root=sysfs
                )
            self.assertEqual(sample["device"], "/dev/bus/usb/002/014")
            self.assertEqual(sample["node"]["st_ctime_ns"], 4)
            (device / "idProduct").write_text("6860\n")
            self.assertIsNone(
                module.bound_download_node_sample(expected, sysfs_root=sysfs)
            )
            (device / "idProduct").write_text(module.DOWNLOAD_USB_PRODUCT + "\n")
            (device / "serial").write_text("OTHER123\n")
            with self.assertRaisesRegex(module.GateError, "serial changed"):
                module.bound_download_node_sample(expected, sysfs_root=sysfs)
            (device / "serial").write_text("SERIAL123\n")
            (device / "idVendor").write_text("1234\n")
            with self.assertRaisesRegex(module.GateError, "no longer Samsung"):
                module.bound_download_node_sample(expected, sysfs_root=sysfs)
            (device / "idVendor").write_text("04e8\n")
            metadata.st_mode = stat.S_IFREG
            with mock.patch.object(module.os, "stat", return_value=metadata):
                with self.assertRaisesRegex(module.GateError, "character device"):
                    module.bound_download_node_sample(expected, sysfs_root=sysfs)

    def test_download_stabilization_accepts_ctime_settle_only(self):
        module = self.module
        clock = SimpleNamespace(now=0.0)

        def monotonic():
            return clock.now

        def sleep(seconds):
            clock.now += seconds

        def sample(ctime):
            return {
                "device": "/dev/bus/usb/002/014",
                "topology": "2-1.3",
                "serial_sha256": "e" * 64,
                "product": module.DOWNLOAD_USB_PRODUCT,
                "node": {
                    "st_dev": 1,
                    "st_ino": 2,
                    "st_rdev": 3,
                    "st_ctime_ns": ctime,
                },
            }

        samples = iter([None, sample(10), sample(11), sample(11), sample(11)])
        result = module.wait_for_stable_download_node(
            {"topology": "2-1.3", "serial_sha256": "e" * 64},
            5.0,
            sampler=lambda _expected: next(samples),
            monotonic=monotonic,
            sleep=sleep,
        )
        self.assertEqual(result["stable_samples"], 3)
        self.assertGreaterEqual(result["elapsed_sec"], 1.0)

    def test_download_stabilization_rejects_replacement_and_disappearance(self):
        module = self.module
        base = {
            "device": "/dev/bus/usb/002/014",
            "topology": "2-1.3",
            "serial_sha256": "e" * 64,
            "product": module.DOWNLOAD_USB_PRODUCT,
            "node": {"st_dev": 1, "st_ino": 2, "st_rdev": 3, "st_ctime_ns": 4},
        }

        class Clock:
            now = 0.0

            def monotonic(self):
                return self.now

            def sleep(self, seconds):
                self.now += seconds

        replacement = {**base, "node": {**base["node"], "st_ino": 9}}
        clock = Clock()
        samples = iter([base, replacement])
        with self.assertRaisesRegex(module.GateError, "replaced"):
            module.wait_for_stable_download_node(
                {"topology": "2-1.3", "serial_sha256": "e" * 64},
                5.0,
                sampler=lambda _expected: next(samples),
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
        clock = Clock()
        samples = iter([base, None])
        with self.assertRaisesRegex(module.GateError, "disappeared"):
            module.wait_for_stable_download_node(
                {"topology": "2-1.3", "serial_sha256": "e" * 64},
                5.0,
                sampler=lambda _expected: next(samples),
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

    def test_download_stabilization_rejects_sampler_binding_mismatch(self):
        module = self.module
        sample = {
            "device": "/dev/bus/usb/002/014",
            "topology": "2-1.3",
            "serial_sha256": "f" * 64,
            "product": module.DOWNLOAD_USB_PRODUCT,
            "node": {"st_dev": 1, "st_ino": 2, "st_rdev": 3, "st_ctime_ns": 4},
        }
        with self.assertRaisesRegex(module.GateError, "does not match binding"):
            module.wait_for_stable_download_node(
                {"topology": "2-1.3", "serial_sha256": "e" * 64},
                1.0,
                sampler=lambda _expected: sample,
                monotonic=lambda: 0.0,
                sleep=lambda _seconds: None,
            )

    def test_download_stabilization_times_out_without_endpoint(self):
        module = self.module
        clock = SimpleNamespace(now=0.0)

        def sleep(seconds):
            clock.now += seconds

        with self.assertRaisesRegex(module.GateError, "did not stabilize"):
            module.wait_for_stable_download_node(
                {"topology": "2-1.3", "serial_sha256": "e" * 64},
                0.5,
                sampler=lambda _expected: None,
                monotonic=lambda: clock.now,
                sleep=sleep,
            )

    def test_wait_for_endpoint_shares_deadline_and_binds_stable_node(self):
        module = self.module
        node = {"st_dev": 1, "st_ino": 2, "st_rdev": 3, "st_ctime_ns": 4}
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/002/014",
            device_identity="1:2:3:4",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        result = module.odin_core.WaitResult(
            ticket=ticket, next_sequence=1, timed_out=False
        )
        stable = {"device": ticket.device, "node": node}
        binding = {"topology": "2-1.3", "serial_sha256": "e" * 64}
        with mock.patch.object(
            module, "wait_for_stable_download_node", return_value=stable
        ) as stabilize, mock.patch.object(
            module.odin_core, "wait_for_single_live_endpoint", return_value=result
        ) as wait, mock.patch.object(
            module, "require_ticket_usb_binding", return_value={"product": "685d"}
        ) as usb_binding, mock.patch.object(
            module.time, "monotonic", side_effect=[10.0, 12.0]
        ):
            returned, sequence = module.wait_for_endpoint(
                Path("odin4"),
                Path("run"),
                timeout_sec=10.0,
                sequence=0,
                lease="lease",
                expected_usb_binding=binding,
            )
        self.assertEqual(returned, ticket)
        self.assertEqual(sequence, 1)
        stabilize.assert_called_once_with(binding, 10.0)
        self.assertEqual(wait.call_args.kwargs["timeout_sec"], 8.0)
        usb_binding.assert_called_once_with(ticket, binding)

    def test_wait_for_endpoint_rejects_different_ticketed_node(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/002/015",
            device_identity="identity",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        result = module.odin_core.WaitResult(
            ticket=ticket, next_sequence=1, timed_out=False
        )
        with mock.patch.object(
            module,
            "wait_for_stable_download_node",
            return_value={
                "device": "/dev/bus/usb/002/014",
                "node": {"st_dev": 1, "st_ino": 2, "st_rdev": 3, "st_ctime_ns": 4},
            },
        ), mock.patch.object(
            module.odin_core, "wait_for_single_live_endpoint", return_value=result
        ), mock.patch.object(module.time, "monotonic", side_effect=[0.0, 1.0]):
            with self.assertRaisesRegex(module.GateError, "differs"):
                module.wait_for_endpoint(
                    Path("odin4"),
                    Path("run"),
                    timeout_sec=10.0,
                    sequence=0,
                    lease="lease",
                    expected_usb_binding={
                        "topology": "2-1.3",
                        "serial_sha256": "e" * 64,
                    },
                )

    def test_wait_for_endpoint_rejects_same_path_replaced_identity(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/002/014",
            device_identity="1:9:3:4",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        result = module.odin_core.WaitResult(
            ticket=ticket, next_sequence=1, timed_out=False
        )
        with mock.patch.object(
            module,
            "wait_for_stable_download_node",
            return_value={
                "device": ticket.device,
                "node": {"st_dev": 1, "st_ino": 2, "st_rdev": 3, "st_ctime_ns": 4},
            },
        ), mock.patch.object(
            module.odin_core, "wait_for_single_live_endpoint", return_value=result
        ), mock.patch.object(
            module.time, "monotonic", side_effect=[0.0, 1.0]
        ), mock.patch.object(module, "require_ticket_usb_binding") as usb_binding:
            with self.assertRaisesRegex(module.GateError, "differs"):
                module.wait_for_endpoint(
                    Path("odin4"),
                    Path("run"),
                    timeout_sec=10.0,
                    sequence=0,
                    lease="lease",
                    expected_usb_binding={
                        "topology": "2-1.3",
                        "serial_sha256": "e" * 64,
                    },
                )
        usb_binding.assert_not_called()

    def test_sealed_memfd_rechecks_boot_only_bytes_and_write_seals(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "AP.tar.md5"
            with tarfile.open(path, "w") as archive:
                payload = b"boot"
                info = tarfile.TarInfo("boot.img.lz4")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            identity = module.core.hash_stable_file(path)
            with module.sealed_memfd(
                path,
                label="test AP",
                expected_size=identity["size"],
                expected_sha256=identity["sha256"],
                boot_only_ap=True,
            ) as descriptor:
                seals = module.fcntl.fcntl(descriptor, module.fcntl.F_GET_SEALS)
                self.assertTrue(seals & module.fcntl.F_SEAL_WRITE)
                with self.assertRaises(OSError):
                    os.write(descriptor, b"x")

    def test_pinned_odin_session_exposes_only_the_sealed_descriptor(self):
        module = self.module

        @contextlib.contextmanager
        def fake_sealed(*_args, **kwargs):
            self.assertEqual(kwargs["label"], "Odin4-session")
            self.assertTrue(kwargs["executable"])
            descriptor = os.memfd_create("sealed-odin-test")
            try:
                yield descriptor
            finally:
                os.close(descriptor)

        with mock.patch.object(module, "sealed_memfd", side_effect=fake_sealed):
            with module.pinned_odin_session(Path("mutable-odin")) as (
                descriptor,
                external_path,
            ):
                self.assertEqual(
                    external_path,
                    Path(f"/proc/{os.getpid()}/fd/{descriptor}"),
                )
                self.assertTrue(external_path.exists())

    def test_flash_sealed_revalidates_after_both_inputs_are_open(self):
        module = self.module
        order = []

        @contextlib.contextmanager
        def fake_sealed(*_args, **kwargs):
            order.append("sealed-" + kwargs["label"])
            descriptor = os.memfd_create("test")
            try:
                yield descriptor
            finally:
                os.close(descriptor)

        def revalidate():
            order.append("revalidate")
            return "/dev/bus/usb/001/002", {"ok": True}

        subprocess_call = {}

        def run(command, **kwargs):
            order.append("subprocess")
            subprocess_call["command"] = command
            subprocess_call["pass_fds"] = kwargs["pass_fds"]
            return SimpleNamespace(returncode=0, stdout=b"ok", stderr=b"")

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "sealed_memfd", side_effect=fake_sealed
        ), mock.patch.object(module.subprocess, "run", side_effect=run):
            transfer, validation = module.flash_sealed_exact(
                9,
                Path("ap"),
                ap_size=1,
                ap_sha256="a" * 64,
                label="candidate",
                log_path=Path(temporary) / "transfer.json",
                revalidate=revalidate,
            )
        self.assertEqual(
            order,
            ["sealed-candidate", "revalidate", "subprocess"],
        )
        self.assertTrue(transfer["sealed_inputs"])
        self.assertEqual(validation, {"ok": True})
        self.assertEqual(subprocess_call["command"][0], "/proc/self/fd/9")
        self.assertEqual(subprocess_call["pass_fds"][0], 9)

    def test_flash_sealed_does_not_launch_after_final_binding_node_change(self):
        module = self.module
        ticket = module.odin_core.EndpointTicket(
            device="/dev/bus/usb/001/002",
            device_identity="1:2:3:4",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="receipt",
            snapshot_receipt_sha256="a" * 64,
        )
        binding = {"topology": "1-2", "serial_sha256": "e" * 64}

        @contextlib.contextmanager
        def fake_sealed(*_args, **_kwargs):
            descriptor = os.memfd_create("test")
            try:
                yield descriptor
            finally:
                os.close(descriptor)

        def revalidate():
            module.require_ticket_usb_binding(ticket, binding)
            return ticket.device, {"ok": True}

        changed_identity = {
            "topology": "1-2",
            "vendor": "04e8",
            "product": module.DOWNLOAD_USB_PRODUCT,
            "serial_sha256": "e" * 64,
            "device_identity": "1:9:3:5",
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "sealed_memfd", side_effect=fake_sealed
        ), mock.patch.object(
            module, "endpoint_usb_identity", return_value=changed_identity
        ), mock.patch.object(module.subprocess, "run") as run:
            with self.assertRaisesRegex(module.GateError, "Download identity"):
                module.flash_sealed_exact(
                    9,
                    Path("ap"),
                    ap_size=1,
                    ap_sha256="a" * 64,
                    label="candidate",
                    log_path=Path(temporary) / "transfer.json",
                    revalidate=revalidate,
                )
        run.assert_not_called()

    def test_consumed_state_rejects_forged_connected_binding(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            run_dir = root / module.RUN_ROOT / "live-run"
            run_dir.mkdir(parents=True)
            baseline = {
                "android_serial": "serial",
                "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
            }
            with module.odin_core.transaction_session(run_dir) as lease:
                module.create_phase(
                    run_dir,
                    "prepared",
                    module.connected.expected_phase_payload(baseline),
                    lease=lease,
                )
            evidence = {"binding": self.binding(module)}
            policy = module.verify_policy_draft(root)
            module.consume_exception(
                root,
                run_dir,
                {"target": module.TARGET},
                evidence,
                policy,
                "clause",
                baseline,
                {"topology": "1-2", "serial_sha256": "e" * 64},
                "2026-07-20T00:00:00.000000Z",
            )
            state_path = root / module.CONSUMED_STATE
            state = json.loads(state_path.read_text())
            state["connected_binding"]["pass_sha256"] = "f" * 64
            state_path.write_text(json.dumps(state))
            with mock.patch.object(
                module, "reopen_connected_evidence", return_value=evidence
            ):
                with self.assertRaises(module.GateError):
                    module.require_consumed(
                        root, {"target": module.TARGET}, policy, "clause"
                    )

    def test_ambiguous_rollback_cannot_retransfer_without_fresh_ack(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            timeline_path = run_dir / "recovery-attempt-01-timeline.json"
            timeline = []
            for name in module.core.TIMELINE_NAMES[:4]:
                module.append_timeline_event(timeline_path, timeline, name)
            args = module.build_parser().parse_args(["--rollback-from-download"])
            with module.odin_core.transaction_session(run_dir) as lease:
                payloads = [
                    {"ok": True},
                    {"ok": True},
                    {"ok": True},
                    {"ok": True},
                    {"ok": True},
                    {"transfer_intent": "magisk"},
                ]
                for phase, payload in zip(module.odin_core.TRANSACTION_PHASES, payloads):
                    module.create_phase(run_dir, phase, payload, lease=lease)
                with mock.patch.object(
                    module, "wait_magisk_android", side_effect=module.GateError("absent")
                ), mock.patch.object(module, "wait_for_endpoint") as wait_endpoint:
                    rc = module._rollback_sequence(
                        root,
                        args,
                        run_dir,
                        timeline_path,
                        timeline,
                        {
                            "candidate_transfer_ok": True,
                            "android_serial": "serial",
                            "usb_binding": {
                                "topology": "1-2",
                                "serial_sha256": "e" * 64,
                            },
                        },
                        Path("odin4"),
                        9,
                        sequence=0,
                        lease=lease,
                        attempt=1,
                        result_name="result-recovery-attempt-01.json",
                    )
            self.assertEqual(rc, 20)
            wait_endpoint.assert_not_called()

    def test_recovery_attempts_are_numbered_and_stop_after_two(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)
            first, first_timeline, _ = module.next_recovery_attempt(root, run_dir)
            self.assertEqual(first, 1)
            module.core.durable_create_json(first_timeline, {"events": []})
            second, second_timeline, _ = module.next_recovery_attempt(root, run_dir)
            self.assertEqual(second, 2)
            module.core.durable_create_json(second_timeline, {"events": []})
            with self.assertRaises(module.GateError):
                module.next_recovery_attempt(root, run_dir)

    def test_observer_reopens_first_complete_capture_without_recapture(self):
        module = self.module
        payload = b"complete retained observer\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)

            def capture(_serial, _command, path, **_kwargs):
                path.write_bytes(payload)
                path.with_suffix(path.suffix + ".stderr").write_bytes(b"")
                return {
                    "path": str(path),
                    "bytes": len(payload),
                    "sha256": module.core.sha256_bytes(payload),
                    "returncode": 0,
                    "stderr_bytes": 0,
                    "read_to_eof": True,
                    "elapsed_sec": 0.1,
                }

            with mock.patch.object(module.core, "capture_adb_exec_out", side_effect=capture):
                observer = module.collect_rollback_observer(root, "serial", run_dir, 1)
            reopened = module.reopen_rollback_observer(
                root, run_dir, {"summary": observer["summary"]}
            )
            self.assertEqual(reopened["sha256"], observer["sha256"])

    def test_failure_timeline_does_not_synthesize_action_events(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)
            timeline_path = run_dir / "timeline-live.json"
            timeline = []
            module.append_timeline_event(timeline_path, timeline, "live_session_start")
            module._finish(
                root,
                run_dir,
                timeline_path,
                timeline,
                {"schema": module.SCHEMA},
                verdict="FAIL_TEST",
                rc=1,
                result_name="result.json",
            )
            names = [value["name"] for value in timeline]
            self.assertEqual(names, ["live_session_start", "live_session_end"])

    def test_pass_is_downgraded_when_timeline_is_incomplete(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)
            timeline_path = run_dir / "timeline-live.json"
            timeline = []
            module.append_timeline_event(
                timeline_path, timeline, "live_session_start"
            )
            rc = module._finish(
                root,
                run_dir,
                timeline_path,
                timeline,
                {"schema": module.SCHEMA},
                verdict=module.PASS_VERDICT,
                rc=0,
                result_name="result.json",
            )
            result = json.loads((run_dir / "result.json").read_text())
            self.assertEqual(rc, 26)
            self.assertEqual(
                result["verdict"], "FAIL_R4W1C_PASS_TIMELINE_INCOMPLETE"
            )

    def test_wait_magisk_android_rejects_other_serial_and_usb_binding(self):
        module = self.module
        expected_binding = {"topology": "1-2", "serial_sha256": "e" * 64}

        for returned_serial, returned_binding in (
            ("other", expected_binding),
            ("serial", {"topology": "1-3", "serial_sha256": "e" * 64}),
        ):
            with self.subTest(
                returned_serial=returned_serial,
                returned_binding=returned_binding,
            ), mock.patch.object(
                module.connected,
                "current_android_exact",
                return_value=(returned_serial, {"ok": "1"}),
            ), mock.patch.object(
                module, "adb_usb_binding", return_value=returned_binding
            ), mock.patch.object(
                module.time, "monotonic", side_effect=[0.0, 0.0, 2.0]
            ), mock.patch.object(module.time, "sleep"):
                with self.assertRaises(module.GateError):
                    module.wait_magisk_android(
                        1.0,
                        expected_serial="serial",
                        expected_usb_binding=expected_binding,
                    )

    def test_live_run_orders_topology_consumption_and_sealed_candidate(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            args = module.build_parser().parse_args(
                ["--live", "--ack", module.LIVE_ACK_TOKEN]
            )
            artifacts = {"target": module.TARGET}
            policy = {"active": True, "path": str(module.POLICY_DRAFT), "size": 1, "sha256": "a" * 64}
            evidence = {"binding": self.binding(module)}
            baseline = {
                "android_serial": "serial",
                "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
            }
            ticket = module.odin_core.EndpointTicket(
                device="/dev/bus/usb/001/002",
                device_identity="identity",
                generation=1,
                snapshot_sequence=0,
                snapshot_receipt="receipt",
                snapshot_receipt_sha256="a" * 64,
            )
            order = []
            original_consume = module.consume_exception

            def preflight(_root, run_dir, _odin, *, lease, **_kwargs):
                self.assertEqual(_odin, Path("sealed-odin"))
                module.create_phase(
                    run_dir,
                    "prepared",
                    module.connected.expected_phase_payload(baseline),
                    lease=lease,
                )
                return baseline

            def topology(_serial):
                order.append("topology")
                return {"topology": "1-2", "serial_sha256": "e" * 64}

            def reboot(*_args, **_kwargs):
                order.append("reboot")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def consume(*args_, **kwargs_):
                order.append("consume")
                return original_consume(*args_, **kwargs_)

            def sealed(*_args, **_kwargs):
                order.append("sealed-transfer")
                return {"sealed_inputs": True}, {"endpoint": True}

            with mock.patch.object(module, "policy_active", return_value=True), mock.patch.object(
                module, "policy_clause", return_value="exact-clause"
            ), mock.patch.object(
                module, "reopen_connected_evidence", return_value=evidence
            ), mock.patch.object(
                module, "verify_policy_draft", return_value=policy
            ), mock.patch.object(
                module.connected, "connected_preflight", side_effect=preflight
            ), mock.patch.object(
                module, "adb_usb_binding", side_effect=topology
            ), mock.patch.object(
                module.transport, "run", side_effect=reboot
            ), mock.patch.object(
                module, "wait_for_endpoint", return_value=(ticket, 1)
            ) as wait_endpoint, mock.patch.object(
                module, "require_ticket_usb_binding", return_value={"topology": "1-2"}
            ), mock.patch.object(
                module, "consume_exception", side_effect=consume
            ), mock.patch.object(
                module, "flash_sealed_exact", side_effect=sealed
            ), mock.patch.object(
                module.odin_core,
                "wait_for_no_live_endpoint",
                return_value=module.odin_core.AbsenceResult(
                    absent=True, next_sequence=2, timed_out=False
                ),
            ), mock.patch.object(
                module, "observe_candidate", return_value={
                    "full_window_completed": True,
                    "watchdog_survival_directly_proven": False,
                }
            ), mock.patch.object(
                module, "_rollback_sequence", return_value=0
            ) as rollback:
                rc = module._live_run_with_odin(
                    root, args, artifacts, policy, Path("sealed-odin"), 9
                )
            self.assertEqual(rc, 0)
            self.assertEqual(order[:3], ["topology", "reboot", "consume"])
            self.assertEqual(order[3], "sealed-transfer")
            self.assertEqual(
                wait_endpoint.call_args.kwargs["expected_usb_binding"],
                {"topology": "1-2", "serial_sha256": "e" * 64},
            )
            rollback.assert_called_once()

    def test_rollback_sequence_happy_path_uses_same_topology_and_first_observer(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            timeline_path = run_dir / "timeline-live.json"
            timeline = []
            for name in module.core.TIMELINE_NAMES[:4]:
                module.append_timeline_event(timeline_path, timeline, name)
            args = module.build_parser().parse_args(["--rollback-from-download"])
            ticket = module.odin_core.EndpointTicket(
                device="/dev/bus/usb/001/002",
                device_identity="identity",
                generation=1,
                snapshot_sequence=0,
                snapshot_receipt="receipt",
                snapshot_receipt_sha256="a" * 64,
            )
            observer = {
                "bytes": 10,
                "sha256": "c" * 64,
                "byte_identical": True,
                "marker": {"integrity_issue": False, "acceptance_present": True},
                "summary": {"path": "summary", "size": 1, "sha256": "d" * 64},
            }
            with module.odin_core.transaction_session(run_dir) as lease:
                for phase, payload in zip(
                    module.odin_core.TRANSACTION_PHASES[:4],
                    [{"ok": True}, {"ok": True}, {"ok": True}, {"ok": True}],
                ):
                    module.create_phase(run_dir, phase, payload, lease=lease)
                with mock.patch.object(
                    module, "wait_for_endpoint", return_value=(ticket, 1)
                ) as wait_endpoint, mock.patch.object(
                    module, "require_ticket_usb_binding", return_value={"topology": "1-2"}
                ) as topology, mock.patch.object(
                    module, "confirm_normal_download"
                ), mock.patch.object(
                    module,
                    "flash_sealed_exact",
                    return_value=({"sealed_inputs": True}, {"endpoint": True}),
                ), mock.patch.object(
                    module, "wait_magisk_android", return_value=("serial", {"ok": "1"})
                ), mock.patch.object(
                    module.odin_core,
                    "wait_for_no_live_endpoint",
                    return_value=module.odin_core.AbsenceResult(
                        absent=True, next_sequence=2, timed_out=False
                    ),
                ), mock.patch.object(
                    module, "find_completed_rollback_observer", return_value=None
                ), mock.patch.object(
                    module, "collect_rollback_observer", return_value=observer
                ):
                    rc = module._rollback_sequence(
                        root,
                        args,
                        run_dir,
                        timeline_path,
                        timeline,
                        {
                            "candidate_transfer_ok": True,
                            "android_serial": "serial",
                            "candidate_observation": {
                                "bounded": True,
                                "requested_sec": module.DEFAULT_PARK_WAIT_SEC,
                                "elapsed_sec": module.DEFAULT_PARK_WAIT_SEC,
                                "full_window_completed": True,
                                "odin_disconnected": True,
                                "candidate_transfer_ok": True,
                            },
                            "usb_binding": {
                                "topology": "1-2",
                                "serial_sha256": "e" * 64,
                            },
                        },
                        Path("odin4"),
                        9,
                        sequence=0,
                        lease=lease,
                        attempt=0,
                        result_name="result-live.json",
                    )
            self.assertEqual(rc, 0)
            self.assertEqual(
                wait_endpoint.call_args.kwargs["expected_usb_binding"],
                {"topology": "1-2", "serial_sha256": "e" * 64},
            )
            self.assertGreaterEqual(topology.call_count, 1)
            self.assertEqual(
                module.phase_payload(root, run_dir, "classified")["verdict"],
                module.PASS_VERDICT,
            )

    def test_stock_cleanup_is_not_attempted_for_prelaunch_magisk_error(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            timeline_path = run_dir / "timeline-live.json"
            timeline = []
            for name in module.core.TIMELINE_NAMES[:4]:
                module.append_timeline_event(timeline_path, timeline, name)
            args = module.build_parser().parse_args(["--rollback-from-download"])
            ticket = module.odin_core.EndpointTicket(
                device="/dev/bus/usb/001/002",
                device_identity="identity",
                generation=1,
                snapshot_sequence=0,
                snapshot_receipt="receipt",
                snapshot_receipt_sha256="a" * 64,
            )
            with module.odin_core.transaction_session(run_dir) as lease:
                for phase, payload in zip(
                    module.odin_core.TRANSACTION_PHASES[:4],
                    [{"ok": True}, {"ok": True}, {"ok": True}, {"ok": True}],
                ):
                    module.create_phase(run_dir, phase, payload, lease=lease)
                with mock.patch.object(
                    module, "wait_for_endpoint", return_value=(ticket, 1)
                ), mock.patch.object(
                    module, "require_ticket_usb_binding", return_value={"topology": "1-2"}
                ), mock.patch.object(
                    module, "confirm_normal_download"
                ), mock.patch.object(
                    module, "flash_sealed_exact", side_effect=module.GateError("prelaunch")
                ) as flash:
                    rc = module._rollback_sequence(
                        root,
                        args,
                        run_dir,
                        timeline_path,
                        timeline,
                        {
                            "candidate_transfer_ok": True,
                            "android_serial": "serial",
                            "usb_binding": {
                                "topology": "1-2",
                                "serial_sha256": "e" * 64,
                            },
                        },
                        Path("odin4"),
                        9,
                        sequence=0,
                        lease=lease,
                        attempt=0,
                        result_name="result-live.json",
                    )
            self.assertEqual(rc, 20)
            self.assertEqual(flash.call_count, 1)


if __name__ == "__main__":
    unittest.main()
