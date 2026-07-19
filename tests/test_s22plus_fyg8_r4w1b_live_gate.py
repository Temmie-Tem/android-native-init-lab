import importlib.util
import json
import os
import pty
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1b_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1b_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1BLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_candidate_and_rollback_pins(self):
        self.assertEqual(len(self.module.MARKER), 99)
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
            "69690e6832bab2a422979054b51ad279222c14cbc369517433b55a785ed3d44d",
        )
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
            "ae26340d69f7208ae3a8c0d135e3f65317b4d16b539d4e19c1613b7f15f0f2c5",
        )
        self.assertEqual(
            self.module.EXPECTED_STATIC_RESULT_SHA256,
            "969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47",
        )
        self.assertEqual(
            self.module.EXPECTED_MAGISK_AP_SHA256,
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

    def test_marker_classifier_accepts_repeated_exact_and_rejects_foreign(self):
        repeated = self.module.classify_marker(
            self.module.MARKER + self.module.MARKER
        )
        self.assertTrue(repeated["acceptance_present"])
        self.assertEqual(repeated["exact_count"], 2)
        foreign = self.module.classify_marker(
            b"\n[[S22R4W1B|id=foreign|phase=BAD|pid=2|path=/x]]\n"
        )
        self.assertTrue(foreign["integrity_issue"])

    def test_historical_family_is_disjoint_from_r4w1b(self):
        result = self.module.classify_marker(b"\n[[S22R4W1|id=historical]]\n")
        self.assertTrue(result["baseline_absent"])
        self.assertFalse(result["integrity_issue"])
        self.assertEqual(result["historical_family_count"], 1)

    def test_verdict_mapping(self):
        positive = {"marker": self.module.classify_marker(self.module.MARKER)}
        absent = {"marker": self.module.classify_marker(b"ordinary")}
        foreign = {
            "marker": self.module.classify_marker(
                b"\n[[S22R4W1B|id=foreign|phase=BAD]]\n"
            )
        }
        self.assertEqual(
            self.module.classify_verdict(
                rollback_target="magisk",
                rollback_ok=True,
                candidate_transfer_ok=True,
                observer=positive,
            ),
            ("PASS_R4W1B_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK", 0),
        )
        self.assertEqual(
            self.module.classify_verdict(
                rollback_target="magisk",
                rollback_ok=True,
                candidate_transfer_ok=True,
                observer=absent,
            )[0],
            "NO_PROOF_R4W1B_EXEC_OR_TRANSITION_UNRESOLVED",
        )
        self.assertEqual(
            self.module.classify_verdict(
                rollback_target="magisk",
                rollback_ok=True,
                candidate_transfer_ok=True,
                observer=foreign,
            )[0],
            "FAIL_R4W1B_MARKER_INTEGRITY",
        )
        self.assertEqual(
            self.module.classify_verdict(
                rollback_target="stock",
                rollback_ok=False,
                candidate_transfer_ok=True,
                observer=positive,
            )[0],
            "FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
        )

    def test_positive_marker_without_successful_transfer_is_integrity_failure(self):
        observer = {"marker": self.module.classify_marker(self.module.MARKER)}
        verdict, _ = self.module.classify_verdict(
            rollback_target="magisk",
            rollback_ok=True,
            candidate_transfer_ok=False,
            observer=observer,
        )
        self.assertEqual(verdict, "FAIL_R4W1B_MARKER_INTEGRITY")

    def test_absent_marker_after_failed_transfer_is_explicit_transfer_failure(self):
        observer = {"marker": self.module.classify_marker(b"ordinary")}
        verdict, _ = self.module.classify_verdict(
            rollback_target="magisk",
            rollback_ok=True,
            candidate_transfer_ok=False,
            observer=observer,
        )
        self.assertEqual(verdict, "FAIL_R4W1B_CANDIDATE_TRANSFER_AND_ROLLED_BACK")

    def test_consumed_state_is_exclusive_and_pinned(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / module.RUN_ROOT / "run"
            run_dir.mkdir(parents=True)
            (root / module.SCRIPT_RELATIVE).parent.mkdir(parents=True)
            (root / module.SCRIPT_RELATIVE).write_text("helper", encoding="ascii")
            with mock.patch.object(module, "helper_sha256", return_value="a" * 64):
                module.consume_exception(root, run_dir)
                with self.assertRaises(module.core.LiveCoreError):
                    module.consume_exception(root, run_dir)
            with mock.patch.object(module, "helper_sha256", return_value="b" * 64):
                state = module.require_consumed_for_rollback(root)
            self.assertEqual(state["helper_sha256"], "a" * 64)
            self.assertEqual(state["candidate_ap_sha256"], module.EXPECTED_CANDIDATE_AP_SHA256)
            self.assertEqual(state["static_result_sha256"], module.EXPECTED_STATIC_RESULT_SHA256)

    def test_normal_download_confirmation_is_temporal_input_gate(self):
        module = self.module
        def delayed_write(descriptor, payload):
            time.sleep(0.02)
            os.write(descriptor, payload)

        read_fd, write_fd = os.pipe()
        with os.fdopen(read_fd, "r", encoding="ascii") as stdin, mock.patch.object(
            module.sys, "stdin", stdin
        ):
            writer = threading.Thread(
                target=delayed_write,
                args=(write_fd, (module.NORMAL_DOWNLOAD_CONFIRMATION + "\n").encode("ascii")),
            )
            writer.start()
            module.confirm_normal_download(1)
            writer.join()
        os.close(write_fd)

        master_fd, slave_fd = pty.openpty()
        with os.fdopen(slave_fd, "r", encoding="ascii") as stdin, mock.patch.object(
            module.sys, "stdin", stdin
        ):
            writer = threading.Thread(
                target=delayed_write,
                args=(master_fd, (module.NORMAL_DOWNLOAD_CONFIRMATION + "\n").encode("ascii")),
            )
            writer.start()
            module.confirm_normal_download(1)
            writer.join()
        os.close(master_fd)

        master_fd, slave_fd = pty.openpty()
        prefix = module.NORMAL_DOWNLOAD_CONFIRMATION[:12].encode("ascii")
        suffix = module.NORMAL_DOWNLOAD_CONFIRMATION[12:].encode("ascii") + b"\n"
        os.write(master_fd, prefix)
        with os.fdopen(slave_fd, "r", encoding="ascii") as stdin, mock.patch.object(
            module.sys, "stdin", stdin
        ):
            writer = threading.Thread(target=delayed_write, args=(master_fd, suffix))
            writer.start()
            with self.assertRaises(module.GateError):
                module.confirm_normal_download(1)
            writer.join()
        os.close(master_fd)

        read_fd, write_fd = os.pipe()
        os.write(write_fd, (module.NORMAL_DOWNLOAD_CONFIRMATION + "\n").encode("ascii"))
        with os.fdopen(read_fd, "r", encoding="ascii") as stdin, mock.patch.object(
            module.sys, "stdin", stdin
        ), self.assertRaises(module.GateError):
            module.confirm_normal_download(1)
        os.close(write_fd)

        read_fd, write_fd = os.pipe()
        with os.fdopen(read_fd, "r", encoding="ascii") as stdin, mock.patch.object(
            module.sys, "stdin", stdin
        ):
            writer = threading.Thread(target=delayed_write, args=(write_fd, b"partial"))
            writer.start()
            with self.assertRaises(module.GateError):
                module.confirm_normal_download(0.05)
            writer.join()
        os.close(write_fd)

    def test_confirmation_revalidates_same_single_odin_endpoint(self):
        module = self.module
        with mock.patch.object(
            module, "strict_odin_devices", return_value=["expected"]
        ) as devices:
            observed = module.require_unchanged_odin_endpoint(
                Path("odin4"),
                Path("live.log"),
                "expected",
                label="revalidate",
            )
        self.assertEqual(observed, "expected")
        devices.assert_called_once()
        with mock.patch.object(
            module, "strict_odin_devices", return_value=["changed"]
        ), self.assertRaises(module.GateError):
            module.require_unchanged_odin_endpoint(
                Path("odin4"),
                Path("live.log"),
                "expected",
                label="revalidate",
            )

    def test_strict_odin_enumeration_rejects_nonzero_empty_result(self):
        module = self.module
        failed = mock.Mock(returncode=1, stdout="", stderr=None)
        with mock.patch.object(module.transport, "run", return_value=failed), mock.patch.object(
            module.transport, "append_log"
        ), self.assertRaises(module.GateError):
            module.strict_odin_devices(Path("odin4"), Path("live.log"), "strict")

    def test_runtime_bounds_fix_park_and_transition_maximums(self):
        parser = self.module.build_parser()
        valid = parser.parse_args(["--offline-check"])
        self.module.validate_runtime_args(valid)
        for argv in (
            ["--offline-check", "--park-wait-sec", "91"],
            ["--offline-check", "--transition-wait-sec", "121"],
            ["--offline-check", "--disconnect-wait-sec", "121"],
        ):
            with self.subTest(argv=argv), self.assertRaises(self.module.GateError):
                self.module.validate_runtime_args(parser.parse_args(argv))

    def connected_result(self):
        module = self.module
        marker = module.classify_marker(b"ordinary retained log")

        def observer(name, read_count):
            names = (
                ["baseline_ap_klog.bin"]
                if name == "ap_klog"
                else ["baseline_last_kmsg_1.bin", "baseline_last_kmsg_2.bin"]
            )
            receipts = [{
                "path": "/tmp/r4w1b/" + filename,
                "read_to_eof": True,
                "returncode": 0,
                "stderr_bytes": 0,
                "bytes": 1,
                "sha256": "a" * 64,
            } for filename in names]
            return {
                "read_to_eof": True,
                "stderr_bytes": 0,
                "bytes": 1,
                "sha256": "a" * 64,
                "reads": receipts,
                "read_count": read_count,
                "byte_identical": True,
                "marker": dict(marker),
            }

        return {
            "schema": module.SCHEMA,
            "mode": "connected-read-only-dry-run",
            "target": module.TARGET,
            "artifacts": {
                "target": module.TARGET,
                "identities": {
                    "candidate_boot": {"size": module.EXPECTED_CANDIDATE_BOOT_SIZE, "sha256": module.EXPECTED_CANDIDATE_BOOT_SHA256},
                    "candidate_lz4": {"size": module.EXPECTED_CANDIDATE_LZ4_SIZE, "sha256": module.EXPECTED_CANDIDATE_LZ4_SHA256},
                    "candidate_ap": {"size": module.EXPECTED_CANDIDATE_AP_SIZE, "sha256": module.EXPECTED_CANDIDATE_AP_SHA256},
                    "manifest": {"size": module.EXPECTED_MANIFEST_SIZE, "sha256": module.EXPECTED_MANIFEST_SHA256},
                    "static_result": {"size": module.EXPECTED_STATIC_RESULT_SIZE, "sha256": module.EXPECTED_STATIC_RESULT_SHA256},
                    "magisk_rollback_ap": {"size": module.EXPECTED_MAGISK_AP_SIZE, "sha256": module.EXPECTED_MAGISK_AP_SHA256},
                    "stock_cleanup_ap": {"size": module.EXPECTED_STOCK_AP_SIZE, "sha256": module.EXPECTED_STOCK_AP_SHA256},
                    "odin": {"size": module.EXPECTED_ODIN_SIZE, "sha256": module.EXPECTED_ODIN_SHA256},
                    "full_firmware": {"size": module.EXPECTED_FULL_FIRMWARE_SIZE, "sha256": module.EXPECTED_FULL_FIRMWARE_SHA256},
                },
                "source_pins": {
                    "static_checker": {"size": module.EXPECTED_STATIC_CHECKER_SIZE, "sha256": module.EXPECTED_STATIC_CHECKER_SHA256},
                    "static_checker_test": {"size": module.EXPECTED_STATIC_CHECKER_TEST_SIZE, "sha256": module.EXPECTED_STATIC_CHECKER_TEST_SHA256},
                    "builder": {"size": module.EXPECTED_BUILDER_SIZE, "sha256": module.EXPECTED_BUILDER_SHA256},
                    "build_primitive": {"size": module.EXPECTED_BUILD_PRIMITIVE_SIZE, "sha256": module.EXPECTED_BUILD_PRIMITIVE_SHA256},
                    "check_primitive": {"size": module.EXPECTED_CHECK_PRIMITIVE_SIZE, "sha256": module.EXPECTED_CHECK_PRIMITIVE_SHA256},
                    "transport": {"size": module.EXPECTED_TRANSPORT_SIZE, "sha256": module.EXPECTED_TRANSPORT_SHA256},
                },
                "fresh_static_checker": {
                    "size": module.EXPECTED_STATIC_RESULT_SIZE,
                    "sha256": module.EXPECTED_STATIC_RESULT_SHA256,
                    "schema": module.EXPECTED_STATIC_SCHEMA,
                    "verdict": module.EXPECTED_STATIC_VERDICT,
                },
                "ap_members": ["boot.img.lz4"],
            },
            "device_contact": True,
            "device_writes": False,
            "reboot": False,
            "download_transition": False,
            "odin_transfer": False,
            "flash": False,
            "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
            "baseline": {
                "target": module.TARGET,
                "android": {
                    "model": "SM-S906N",
                    "device": "g0q",
                    "bootloader": "S906NKSS7FYG8",
                    "incremental": "S906NKSS7FYG8",
                    "boot_completed": "1",
                    "bootanim": "stopped",
                    "verified_boot_state": "orange",
                    "root": "uid=0(root)",
                    "boot_sha256": module.EXPECTED_MAGISK_BOOT_SHA256,
                    "dtbo_sha256": module.EXPECTED_DTBO_SHA256,
                    "recovery_sha256": module.EXPECTED_RECOVERY_SHA256,
                    "vendor_boot_sha256": module.EXPECTED_VENDOR_BOOT_SHA256,
                },
                "device_writes": False,
                "one_shot_consumed": False,
                "no_odin_endpoint": True,
                "sec_log_buf_live": True,
                "bind": self.module.EXPECTED_BIND,
                "observers": {
                    "ap_klog": observer("ap_klog", 1),
                    "last_kmsg": observer("last_kmsg", 2),
                },
                "pstore_console_absent": {
                    path: True for path in self.module.PSTORE_PATHS
                },
            },
        }

    def test_connected_result_contract_reopens_load_bearing_semantics(self):
        result = self.connected_result()
        self.module.validate_connected_result_contract(result)
        result["baseline"]["observers"]["last_kmsg"]["read_to_eof"] = False
        with self.assertRaises(self.module.GateError):
            self.module.validate_connected_result_contract(result)

    def test_connected_result_requires_android_artifacts_and_complete_receipts(self):
        module = self.module
        for mutate in (
            lambda result: result.pop("artifacts"),
            lambda result: result["baseline"].pop("android"),
            lambda result: result["baseline"]["observers"]["ap_klog"]["reads"][0].pop("sha256"),
            lambda result: result["baseline"]["observers"]["last_kmsg"]["reads"][1].update({"returncode": 1}),
        ):
            result = self.connected_result()
            mutate(result)
            with self.assertRaises(module.GateError):
                module.validate_connected_result_contract(result)

    def test_connected_pass_reopens_policy_bound_files_and_raw_receipts(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / module.RUN_ROOT / "connected"
            run_dir.mkdir(parents=True)
            result = self.connected_result()
            for name, observer in result["baseline"]["observers"].items():
                payload = b"stable-" + name.encode("ascii")
                digest = module.core.sha256_bytes(payload)
                for index, receipt in enumerate(observer["reads"]):
                    path = run_dir / (
                        "baseline_ap_klog.bin"
                        if name == "ap_klog"
                        else f"baseline_last_kmsg_{index + 1}.bin"
                    )
                    path.write_bytes(payload)
                    receipt.update(
                        {
                            "path": str(path),
                            "bytes": len(payload),
                            "sha256": digest,
                        }
                    )
                observer.update({"bytes": len(payload), "sha256": digest})
            result_path = run_dir / "result.json"
            module.core.durable_write_json(result_path, result)
            result_identity = module.core.hash_stable_file(result_path)
            created_at = "2026-07-19T06:43:18.380008Z"
            record = {
                "schema": "s22plus_fyg8_r4w1b_connected_pass_v1",
                "target": module.TARGET,
                "created_at_utc": created_at,
                "helper_sha256": "a" * 64,
                "test_sha256": "b" * 64,
                "core_sha256": "c" * 64,
                "core_test_sha256": "d" * 64,
                "result_path": str(result_path.relative_to(root)),
                "result_sha256": result_identity["sha256"],
                "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
                "device_writes": False,
            }
            pass_path = root / module.CONNECTED_PASS_STATE
            module.core.durable_create_json(pass_path, record)
            pass_identity = module.core.hash_stable_file(pass_path)
            (root / "AGENTS.md").write_text(
                "The load-bearing connected PASS record is\n"
                f"`{module.CONNECTED_PASS_STATE}`, created at `{created_at}`, size\n"
                f"`{pass_identity['size']}`, SHA256\n"
                f"`{pass_identity['sha256']}`. It binds connected result\n"
                f"`{result_path.relative_to(root)}`, size `{result_identity['size']}`, SHA256\n"
                f"`{result_identity['sha256']}`.\n",
                encoding="utf-8",
            )
            hashes = (
                mock.patch.object(module, "helper_sha256", return_value="a" * 64),
                mock.patch.object(module, "test_sha256", return_value="b" * 64),
                mock.patch.object(module, "core_sha256", return_value="c" * 64),
                mock.patch.object(module, "core_test_sha256", return_value="d" * 64),
            )
            with hashes[0], hashes[1], hashes[2], hashes[3]:
                reopened = module.validate_connected_pass(
                    root,
                    expected_artifacts=result["artifacts"],
                    require_policy_identity=True,
                )
                self.assertEqual(reopened, record)
                raw_path = run_dir / "baseline_last_kmsg_2.bin"
                raw_payload = raw_path.read_bytes()
                original_read = module.core.read_stable_file
                mutated = False

                def mutate_after_initial_read(path, *, maximum=None):
                    nonlocal mutated
                    payload = original_read(path, maximum=maximum)
                    if Path(path) == raw_path and not mutated:
                        mutated = True
                        raw_path.write_bytes(payload + b"tamper")
                    return payload

                with mock.patch.object(
                    module.core, "read_stable_file", side_effect=mutate_after_initial_read
                ), self.assertRaises(module.GateError):
                    module.validate_connected_pass(
                        root,
                        expected_artifacts=result["artifacts"],
                        require_policy_identity=True,
                    )
                raw_path.write_bytes(raw_payload)
                raw_path.write_bytes(raw_payload + b"tamper")
                with self.assertRaises(module.GateError):
                    module.validate_connected_pass(
                        root,
                        expected_artifacts=result["artifacts"],
                        require_policy_identity=True,
                    )

    def test_connected_raw_bytes_recompute_marker_semantics(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / module.RUN_ROOT / "connected"
            run_dir.mkdir(parents=True)
            result_path = run_dir / "result.json"
            result_path.write_text("{}", encoding="ascii")
            result = self.connected_result()
            for name, observer in result["baseline"]["observers"].items():
                payload = module.MARKER if name == "last_kmsg" else b"ordinary retained log"
                digest = module.core.sha256_bytes(payload)
                for index, receipt in enumerate(observer["reads"]):
                    path = run_dir / (
                        "baseline_ap_klog.bin"
                        if name == "ap_klog"
                        else f"baseline_last_kmsg_{index + 1}.bin"
                    )
                    path.write_bytes(payload)
                    receipt.update(
                        {"path": str(path), "bytes": len(payload), "sha256": digest}
                    )
                observer.update({"bytes": len(payload), "sha256": digest})
            with self.assertRaises(module.GateError):
                module.validate_connected_result_contract(
                    result,
                    root=root,
                    result_path=result_path,
                    expected_artifacts=result["artifacts"],
                )

    def test_connected_preflight_rehearses_double_last_kmsg_read(self):
        module = self.module
        observer = b"clean retained observer"

        def fake_capture(_serial, _command, output, **_kwargs):
            output.write_bytes(observer)
            return {
                "path": str(output),
                "bytes": len(observer),
                "sha256": module.core.sha256_bytes(observer),
                "returncode": 0,
                "stderr_bytes": 0,
                "read_to_eof": True,
            }

        state = (
            f"osrelease={module.transport.EXPECTED_RELEASE}\n"
            "sec_log_buf 1 0 - Live 0x0\n"
            "bind_ok=1\n/proc/ap_klog:1:400\n/proc/last_kmsg:1:400"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with mock.patch.object(
                module, "current_android_exact", return_value=("serial", {"exact": True})
            ), mock.patch.object(module, "remote_text", return_value=state), mock.patch.object(
                module,
                "pstore_console_absent",
                return_value={path: True for path in module.PSTORE_PATHS},
            ), mock.patch.object(
                module.core, "capture_adb_exec_out", side_effect=fake_capture
            ) as capture, mock.patch.object(module.time, "sleep"):
                _, baseline = module.connected_preflight(root, run_dir, Path("odin4"))
        self.assertEqual(capture.call_count, 3)
        self.assertEqual(baseline["observers"]["ap_klog"]["read_count"], 1)
        last_kmsg = baseline["observers"]["last_kmsg"]
        self.assertEqual(last_kmsg["read_count"], 2)
        self.assertTrue(last_kmsg["byte_identical"])

    def test_connected_preflight_rejects_nonidentical_last_kmsg_reads(self):
        module = self.module

        def fake_capture(_serial, _command, output, **_kwargs):
            payload = b"second" if output.name.endswith("last_kmsg_2.bin") else b"first"
            output.write_bytes(payload)
            return {
                "path": str(output),
                "bytes": len(payload),
                "sha256": module.core.sha256_bytes(payload),
                "returncode": 0,
                "stderr_bytes": 0,
                "read_to_eof": True,
            }

        state = (
            f"osrelease={module.transport.EXPECTED_RELEASE}\n"
            "sec_log_buf 1 0 - Live 0x0\n"
            "bind_ok=1\n/proc/ap_klog:1:400\n/proc/last_kmsg:1:400"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with mock.patch.object(
                module, "current_android_exact", return_value=("serial", {"exact": True})
            ), mock.patch.object(module, "remote_text", return_value=state), mock.patch.object(
                module.core, "capture_adb_exec_out", side_effect=fake_capture
            ), mock.patch.object(module.time, "sleep"), self.assertRaises(module.GateError):
                module.connected_preflight(root, run_dir, Path("odin4"))

    def test_policy_draft_requires_every_pin(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / module.POLICY_DRAFT
            path.parent.mkdir(parents=True)
            complete = "\n".join(
                (
                    "DRAFT_INACTIVE",
                    module.CONNECTED_ACTIVE_SENTINEL,
                    module.LIVE_ACTIVE_SENTINEL,
                    "pin-a",
                )
            )
            path.write_text(complete, encoding="utf-8")
            hashes = (
                mock.patch.object(module, "policy_required_values", return_value=("pin-a",)),
                mock.patch.object(module, "helper_sha256", return_value="a" * 64),
                mock.patch.object(module, "test_sha256", return_value="b" * 64),
                mock.patch.object(module, "core_sha256", return_value="c" * 64),
                mock.patch.object(module, "core_test_sha256", return_value="d" * 64),
                mock.patch.object(module, "policy_active", return_value=False),
            )
            with hashes[0], hashes[1], hashes[2], hashes[3], hashes[4], hashes[5]:
                result = module.verify_policy_draft(root)
                self.assertFalse(result["live_active"])
                path.write_text(complete.replace("pin-a", ""), encoding="utf-8")
                with self.assertRaises(module.GateError):
                    module.verify_policy_draft(root)

    def test_timeline_uses_only_canonical_events(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.module.core.TIMELINE_NAMES:
                self.module.core.append_event(path, events, name)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"events"})
            self.assertEqual(
                [event["name"] for event in payload["events"]],
                list(self.module.core.TIMELINE_NAMES),
            )

    def test_policy_requires_exact_active_sentinel_line(self):
        module = self.module
        values = "\n".join(module.policy_required_values(Path.cwd()))
        with mock.patch.object(module, "parse_live_connected_evidence_binding", return_value={}), mock.patch.object(
            Path,
            "read_text",
            return_value="prose " + module.LIVE_ACTIVE_SENTINEL + "\n" + values,
        ):
            self.assertFalse(module.policy_active(Path.cwd(), connected=False))
        with mock.patch.object(module, "parse_live_connected_evidence_binding", return_value={}), mock.patch.object(
            Path,
            "read_text",
            return_value=module.LIVE_ACTIVE_SENTINEL + "\n" + values,
        ):
            self.assertTrue(module.policy_active(Path.cwd(), connected=False))

    def test_source_has_no_rdx_protocol_or_nonboot_flash_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "PrEaMbLe",
            "DaTaXfEr",
            "Sahara",
            "Firehose",
            "fastboot",
            "/dev/block/by-name/efs",
            "/proc/sysrq-trigger",
        ):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count("require_unchanged_odin_endpoint("), 3)

    def test_first_rollback_reads_are_load_bearing_and_identical(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)

            def fake_capture(_serial, _command, output, **_kwargs):
                output.write_bytes(module.MARKER)
                return {
                    "path": str(output),
                    "bytes": len(module.MARKER),
                    "sha256": module.core.sha256_bytes(module.MARKER),
                    "returncode": 0,
                    "stderr_bytes": 0,
                    "read_to_eof": True,
                }

            with mock.patch.object(module.core, "capture_adb_exec_out", side_effect=fake_capture):
                result = module.collect_first_rollback_last_kmsg("serial", run_dir)
            self.assertTrue(result["load_bearing"])
            self.assertTrue(result["byte_identical"])
            self.assertTrue(result["marker"]["acceptance_present"])
            self.assertTrue(result["candidate_banner_is_not_unique"])

    def test_recovery_mode_bypasses_candidate_and_full_firmware_gate(self):
        module = self.module
        with mock.patch.object(module, "repo_root", return_value=Path.cwd()), mock.patch.object(
            module, "verify_recovery_artifacts", return_value={}
        ) as recovery, mock.patch.object(
            module, "rollback_from_download", return_value=0
        ) as rollback, mock.patch.object(
            module, "verify_artifacts"
        ) as candidate:
            rc = module.main(
                [
                    "--rollback-from-download",
                    "--ack",
                    module.ROLLBACK_ACK_TOKEN,
                ]
            )
        self.assertEqual(rc, 0)
        recovery.assert_called_once()
        rollback.assert_called_once()
        candidate.assert_not_called()

    def test_rollback_uses_stock_only_after_magisk_transfer_failure(self):
        module = self.module
        args = module.build_parser().parse_args(["--offline-check"])
        magisk_failure = module.transport.GateError("Odin flash failed rc=1")
        with mock.patch.object(
            module.transport,
            "flash_exact",
            side_effect=[magisk_failure, None],
        ) as flash, mock.patch.object(
            module, "strict_odin_devices", return_value=["odin-device"]
        ):
            target = module.flash_rollback_exact(
                Path.cwd(), args, Path("odin4"), "odin-device", Path("live.log")
            )
        self.assertEqual(target, "stock")
        self.assertEqual(flash.call_count, 2)

    def test_stock_cleanup_rejects_a_different_odin_endpoint(self):
        module = self.module
        args = module.build_parser().parse_args(["--offline-check"])
        with mock.patch.object(
            module.transport,
            "flash_exact",
            side_effect=module.transport.GateError("Odin flash failed rc=1"),
        ) as flash, mock.patch.object(
            module, "strict_odin_devices", return_value=["different-device"]
        ):
            with self.assertRaises(module.transport.GateError):
                module.flash_rollback_exact(
                    Path.cwd(),
                    args,
                    Path("odin4"),
                    "original-device",
                    Path("live.log"),
                )
        flash.assert_called_once()

    def test_live_preconsumption_failure_completes_timeline_without_flash(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = module.build_parser().parse_args(["--live", "--ack", module.LIVE_ACK_TOKEN])
            with mock.patch.object(module, "policy_active", return_value=True), mock.patch.object(
                module, "validate_connected_pass"
            ), mock.patch.object(
                module, "connected_preflight", side_effect=module.GateError("baseline stop")
            ), mock.patch.object(module.transport, "flash_exact") as flash:
                rc = module.live_run(root, args, {})
            self.assertEqual(rc, 1)
            flash.assert_not_called()
            run_dir = next((root / module.RUN_ROOT).iterdir())
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertTrue(module.core.timeline_complete(timeline["events"]))
            self.assertEqual(
                result["verdict"], "FAIL_R4W1B_PRECONSUMPTION_NO_CANDIDATE_FLASH"
            )
            self.assertFalse(result["candidate_flash_attempted"])

    def test_live_success_path_consumes_once_and_requires_magisk_marker_pass(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = module.build_parser().parse_args(["--live", "--ack", module.LIVE_ACK_TOKEN])
            completed = mock.Mock(returncode=0)
            positive_observer = {"marker": module.classify_marker(module.MARKER)}
            with mock.patch.object(module, "policy_active", return_value=True), mock.patch.object(
                module, "validate_connected_pass"
            ), mock.patch.object(
                module, "connected_preflight", return_value=("serial", {"baseline": True})
            ), mock.patch.object(
                module, "helper_sha256", return_value="a" * 64
            ), mock.patch.object(
                module.transport, "run", return_value=completed
            ), mock.patch.object(
                module, "wait_for_one_odin", side_effect=["candidate", "rollback"]
            ), mock.patch.object(
                module.transport, "flash_exact"
            ) as candidate_flash, mock.patch.object(
                module, "wait_for_strict_odin_absence", return_value=True
            ), mock.patch.object(
                module, "observe_raw_park", return_value={"bounded": True}
            ), mock.patch.object(
                module, "confirm_normal_download"
            ), mock.patch.object(
                module, "require_unchanged_odin_endpoint", return_value="rollback"
            ), mock.patch.object(
                module, "flash_rollback_exact", return_value="magisk"
            ), mock.patch.object(
                module, "wait_magisk_android_exact", return_value=("serial", {"exact": True})
            ), mock.patch.object(
                module, "collect_first_rollback_last_kmsg", return_value=positive_observer
            ):
                rc = module.live_run(root, args, {})
            self.assertEqual(rc, 0)
            candidate_flash.assert_called_once()
            self.assertTrue((root / module.CONSUMED_STATE).is_file())
            run_dir = next((root / module.RUN_ROOT).iterdir())
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertTrue(module.core.timeline_complete(timeline["events"]))
            self.assertEqual(
                result["verdict"], "PASS_R4W1B_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK"
            )
            self.assertTrue(result["candidate_transfer_ok"])
            self.assertTrue(result["rollback_ok"])

    def test_live_refuses_raw_park_until_candidate_odin_disconnects(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = module.build_parser().parse_args(["--live", "--ack", module.LIVE_ACK_TOKEN])
            completed = mock.Mock(returncode=0)
            absent_observer = {"marker": module.classify_marker(b"ordinary")}
            with mock.patch.object(module, "policy_active", return_value=True), mock.patch.object(
                module, "validate_connected_pass"
            ), mock.patch.object(
                module, "connected_preflight", return_value=("serial", {"baseline": True})
            ), mock.patch.object(
                module, "helper_sha256", return_value="a" * 64
            ), mock.patch.object(
                module.transport, "run", return_value=completed
            ), mock.patch.object(
                module, "wait_for_one_odin", side_effect=["candidate", "rollback"]
            ), mock.patch.object(
                module.transport, "flash_exact"
            ), mock.patch.object(
                module, "wait_for_strict_odin_absence", return_value=False
            ), mock.patch.object(module, "observe_raw_park") as raw_park, mock.patch.object(
                module, "confirm_normal_download"
            ), mock.patch.object(
                module, "require_unchanged_odin_endpoint", return_value="rollback"
            ), mock.patch.object(
                module, "flash_rollback_exact", return_value="magisk"
            ), mock.patch.object(
                module, "wait_magisk_android_exact", return_value=("serial", {"exact": True})
            ), mock.patch.object(
                module, "collect_first_rollback_last_kmsg", return_value=absent_observer
            ):
                rc = module.live_run(root, args, {})
            self.assertEqual(rc, 32)
            raw_park.assert_not_called()
            run_dir = next((root / module.RUN_ROOT).iterdir())
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertIn("did not disconnect", result["candidate_observation"]["error"])
            self.assertTrue(result["rollback_ok"])

    def test_failed_candidate_transfer_still_rolls_back_with_complete_timeline(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = module.build_parser().parse_args(["--live", "--ack", module.LIVE_ACK_TOKEN])
            completed = mock.Mock(returncode=0)
            absent_observer = {"marker": module.classify_marker(b"ordinary")}
            with mock.patch.object(module, "policy_active", return_value=True), mock.patch.object(
                module, "validate_connected_pass"
            ), mock.patch.object(
                module, "connected_preflight", return_value=("serial", {"baseline": True})
            ), mock.patch.object(
                module, "helper_sha256", return_value="a" * 64
            ), mock.patch.object(
                module.transport, "run", return_value=completed
            ), mock.patch.object(
                module, "wait_for_one_odin", side_effect=["candidate", "rollback"]
            ), mock.patch.object(
                module.transport,
                "flash_exact",
                side_effect=module.transport.GateError("candidate transfer failed"),
            ), mock.patch.object(
                module, "confirm_normal_download"
            ), mock.patch.object(
                module, "require_unchanged_odin_endpoint", return_value="rollback"
            ), mock.patch.object(
                module, "flash_rollback_exact", return_value="magisk"
            ), mock.patch.object(
                module, "wait_magisk_android_exact", return_value=("serial", {"exact": True})
            ), mock.patch.object(
                module, "collect_first_rollback_last_kmsg", return_value=absent_observer
            ):
                rc = module.live_run(root, args, {})
            self.assertEqual(rc, 24)
            run_dir = next((root / module.RUN_ROOT).iterdir())
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertTrue(module.core.timeline_complete(timeline["events"]))
            self.assertEqual(
                result["verdict"], "FAIL_R4W1B_CANDIDATE_TRANSFER_AND_ROLLED_BACK"
            )
            self.assertFalse(result["candidate_transfer_ok"])
            self.assertTrue(result["rollback_ok"])

    def test_observer_capture_failure_is_distinct_and_timeline_complete(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = module.build_parser().parse_args(["--live", "--ack", module.LIVE_ACK_TOKEN])
            completed = mock.Mock(returncode=0)
            with mock.patch.object(module, "policy_active", return_value=True), mock.patch.object(
                module, "validate_connected_pass"
            ), mock.patch.object(
                module, "connected_preflight", return_value=("serial", {"baseline": True})
            ), mock.patch.object(
                module, "helper_sha256", return_value="a" * 64
            ), mock.patch.object(
                module.transport, "run", return_value=completed
            ), mock.patch.object(
                module, "wait_for_one_odin", side_effect=["candidate", "rollback"]
            ), mock.patch.object(
                module.transport, "flash_exact"
            ), mock.patch.object(
                module, "wait_for_strict_odin_absence", return_value=True
            ), mock.patch.object(
                module, "observe_raw_park", return_value={"bounded": True}
            ), mock.patch.object(
                module, "confirm_normal_download"
            ), mock.patch.object(
                module, "require_unchanged_odin_endpoint", return_value="rollback"
            ), mock.patch.object(
                module, "flash_rollback_exact", return_value="magisk"
            ), mock.patch.object(
                module, "wait_magisk_android_exact", return_value=("serial", {"exact": True})
            ), mock.patch.object(
                module,
                "collect_first_rollback_last_kmsg",
                side_effect=module.GateError("non-identical observer reads"),
            ):
                rc = module.live_run(root, args, {})
            self.assertEqual(rc, 21)
            run_dir = next((root / module.RUN_ROOT).iterdir())
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertTrue(module.core.timeline_complete(timeline["events"]))
            self.assertEqual(result["verdict"], "FAIL_R4W1B_OBSERVER_CAPTURE")
            self.assertTrue(result["rollback_ok"])
            self.assertIn("rollback_boot_ready", [event["name"] for event in timeline["events"]])

    def test_rollback_from_download_succeeds_without_active_policy(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            consumed_run = root / module.RUN_ROOT / "consumed-run"
            consumed_run.mkdir(parents=True)
            with mock.patch.object(module, "helper_sha256", return_value="a" * 64):
                module.consume_exception(root, consumed_run)
            args = module.build_parser().parse_args(
                ["--rollback-from-download", "--ack", module.ROLLBACK_ACK_TOKEN]
            )
            with mock.patch.object(module, "policy_active") as policy, mock.patch.object(
                module, "strict_odin_devices", return_value=["odin-device"]
            ), mock.patch.object(
                module, "confirm_normal_download"
            ), mock.patch.object(
                module, "require_unchanged_odin_endpoint", return_value="odin-device"
            ), mock.patch.object(
                module, "flash_rollback_exact", return_value="magisk"
            ), mock.patch.object(
                module, "wait_magisk_android_exact", return_value=("serial", {"exact": True})
            ):
                rc = module.rollback_from_download(root, args)
            policy.assert_not_called()
            self.assertEqual(rc, 0)
            run_dir = next(
                path
                for path in (root / module.RUN_ROOT).iterdir()
                if path.name.startswith("s22plus-r4w1b-rollback")
            )
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertTrue(module.core.timeline_complete(timeline["events"]))
            self.assertEqual(result["verdict"], "PASS_R4W1B_MAGISK_ROLLBACK_FROM_DOWNLOAD")

    def test_rollback_from_download_refuses_without_consumed_state(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = module.build_parser().parse_args(
                ["--rollback-from-download", "--ack", module.ROLLBACK_ACK_TOKEN]
            )
            with self.assertRaises(module.GateError):
                module.rollback_from_download(root, args)


if __name__ == "__main__":
    unittest.main()
