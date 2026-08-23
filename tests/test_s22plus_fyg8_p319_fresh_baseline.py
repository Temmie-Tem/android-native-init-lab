from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_fresh_baseline_capability.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p319_fresh_baseline_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("fresh-baseline capability cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    @staticmethod
    def write0400(path: Path, payload: bytes):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = path.open("xb")
        try:
            fd.write(payload)
            fd.flush()
        finally:
            fd.close()
        path.chmod(0o400)

    @staticmethod
    def rewrite0400(path: Path, payload: bytes):
        path.chmod(0o600)
        path.write_bytes(payload)
        path.chmod(0o400)

    def make_fixture(self):
        m = self.m
        root = Path(tempfile.mkdtemp(prefix="p319-fresh-baseline-"))
        d1_run = root / "d1" / "run"
        d1_run.mkdir(mode=0o700, parents=True)
        d0_run = d1_run.parent / "d0-p319-fresh-baseline-1"
        d0_run.mkdir(mode=0o700, parents=True)
        d1_path = d1_run / "result.json"
        d0_path = root / "d0-result.json"
        output = root / "result.json"
        design = m._baseline_design_identity()
        candidate = m._current_candidate_identity()
        profile = m._profile()
        before_id = hashlib.sha256(b"before-boot").hexdigest()
        after_id = hashlib.sha256(b"after-boot").hexdigest()
        health_base = {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": profile["start_health"]["verified_boot_state"],
            "root_verified": True,
            "boot_sha256": profile["start_health"]["boot_sha256"],
            "supporting_partition_sha256": profile["start_health"]["supporting_partition_sha256"],
            "odin_endpoint_absent": True,
            "kernel_release": "5.10.226-test",
        }
        before = {**health_base, "boot_id_sha256": before_id}
        after = {**health_base, "boot_id_sha256": after_id}
        arm = d1_run / "run.arm.json"
        start = d1_run / "start.json"
        self.write0400(arm, m._canonical({
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_arm_v1",
            "attempt": 1,
            "consumed": True,
        }))
        self.write0400(start, m._canonical({
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_start_v1",
            "reboot_count": 1,
            "reboot_requested": True,
            "before": before,
        }))
        journal = {
            "arm": {"path": str(arm), "size": arm.stat().st_size, "sha256": hashlib.sha256(arm.read_bytes()).hexdigest(), "mode": "0400", "nlink": 1},
            "start": {"path": str(start), "size": start.stat().st_size, "sha256": hashlib.sha256(start.read_bytes()).hexdigest(), "mode": "0400", "nlink": 1},
            "result": {"path": str(d1_path)},
        }
        binding = {
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1",
            "action": "one exact attended normal Android reboot",
            "adapter": m._d1_identity(),
            "baseline_design": design,
            "candidate": candidate,
            "run_directory": {"path": str(d1_run), "publication": "directory-no-replace-then-durable-start-no-replace"},
            "run_approval_arm": {"path": str(d1_run / "run.arm.json"), "publication": "file-no-replace-fsync-then-directory-fsync"},
            "journal": journal,
            "candidate_transfer": False,
            "partition_payload": False,
            "odin": False,
            "download_transition": False,
            "f1_authorized": False,
        }
        d1 = {
            "schema": m.D1_SCHEMA,
            "version": "device-action-d1-p319-v1",
            "mode": "attended-normal-reboot",
            "baseline_design_id": design["design_id"],
            "target": m.TARGET,
            "binding": binding,
            "before": before,
            "after": after,
            "selection": {"inventory_count": 2, "inventory_digest": "b" * 64, "selected_serial_sha256": "c" * 64, "selected_topology_sha256": "d" * 64, "other_targets_commanded": False},
            "journal": journal,
            "reboot_count": 1,
            "candidate_transfer": False,
            "device_writes": False,
            "download_transition_requested": False,
            "odin_invoked": False,
            "partition_transfer": False,
            "f1_authorized": False,
            "live_authorized": False,
            "other_targets_commanded": False,
            "verdict": "PASS_P319_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH",
        }
        # Build the raw-first capture using the repository's current capture
        # receipt format, not a parser-only stand-in.
        raw_spec = importlib.util.spec_from_file_location("raw_fixture", m.RAW_CAPTURE)
        assert raw_spec and raw_spec.loader
        raw = importlib.util.module_from_spec(raw_spec)
        sys.modules[raw_spec.name] = raw
        raw_spec.loader.exec_module(raw)
        observer = d0_run / "baseline-observer.bin"
        payload = bytes(m.RAW_SIZE)
        self.write0400(observer, payload)
        stderr = d0_run / "baseline-observer.bin.stderr"
        self.write0400(stderr, b"")
        receipt_path = d0_run / "fixture.capture.json"
        receipt_value = {
            "argv0_name": "fixture",
            "elapsed_msec": 1,
            "name": "fixture",
            "output_exceeded": False,
            "producer_error_type": None,
            "returncode": 0,
            "schema": raw.SCHEMA,
            "stderr": {"mode": "0400", "name": "baseline-observer.bin.stderr", "nlink": 1, "sha256": hashlib.sha256(b"").hexdigest(), "size": 0},
            "stdout": {"mode": "0400", "name": "baseline-observer.bin", "nlink": 1, "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)},
            "timed_out": False,
        }
        raw._durable_create(receipt_path, raw._canonical(receipt_value))
        d0_health = after
        d0 = {
            "schema": m.D0_SCHEMA,
            "version": "device-action-d0-p319-v1",
            "mode": "connected-read-only",
            "baseline_design_id": design["design_id"],
            "run_directory": str(d0_run),
            "runtime": m._d0_runtime_identity(),
            "target_evidence": {"targets": [{"model": "SM-S906N", "device": "g0q", "firmware_incremental": "S906NKSS7FYG8", "adb_serial_sha256": "c" * 64, "usb_topology_sha256": "d" * 64}], "odin_endpoint_absent": True},
            "health": d0_health,
            "observer": {"path": str(observer), "bytes": m.RAW_SIZE, "sha256": hashlib.sha256(payload).hexdigest(), "read_to_eof": True, "stderr_bytes": 0, "source": "/proc/last_kmsg", "raw_capture": {"path": str(receipt_path), "size": receipt_path.stat().st_size, "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()}, "raw_first": True, "parser_started_after_raw_publish": True},
            "usb": {"initial": {"enumerated_devices": 2, "download_endpoint_count": 0, "snapshot_sha256": "e" * 64}, "final": {"enumerated_devices": 2, "download_endpoint_count": 0, "snapshot_sha256": "f" * 64}},
            "host_tool": {"path": "fixture", "size": 1, "sha256": "0" * 64, "version_output_sha256": "1" * 64},
            "verdict": "PASS_P319_D0_FRESH_BASELINE_RAW_V1",
            "device_contact": True,
            "device_writes": False,
            "reboot_requested": False,
            "download_transition_requested": False,
            "odin_invoked": False,
            "partition_transfer": False,
            "f1_authorized": False,
            "live_authorized": False,
            "candidate_marker_family_absent": True,
            "marker_residual": False,
        }
        self.write0400(d1_path, m._canonical(d1))
        self.write0400(d0_path, m._canonical(d0))
        return root, d1_path, d0_path, output, d1, d0

    def fixture_patches(self, root, d1, d0, output):
        m = self.m
        d1_run = root / "d1" / "run"
        d0_run = root / "d0" / "run"
        return mock.patch.multiple(
            m,
            RUN_DIR=d1_run,
            RUN_ARM=d1_run / "run.arm.json",
            D0_RUN_DIR=d0_run,
            DEFAULT_D1=d1,
            DEFAULT_D0=d0,
            DEFAULT_OUT=output,
        )

    def test_baseline_design_is_internal_and_self_bound(self):
        m = self.m
        design = m._baseline_design_identity()
        self.assertEqual(design["schema"], m.BASELINE_DESIGN_SCHEMA)
        self.assertEqual(design["design_id"], m.BASELINE_DESIGN_ID)
        self.assertEqual(design["target"], m.TARGET)
        self.assertEqual(design["d1_source"]["path"], m._relative(m.D1_SUCCESSOR))
        self.assertEqual(design["reducer"]["path"], m._relative(m.SCRIPT))

    def test_d1_host_rehearsal_has_one_reboot_and_pending_live(self):
        d1 = importlib.util.spec_from_file_location("p319_d1", ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_d1_fresh_baseline.py")
        self.assertIsNotNone(d1)
        self.assertEqual(self.m._d1_identity()["schema"], "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1")
        assert d1 and d1.loader
        module = importlib.util.module_from_spec(d1)
        sys.modules[d1.name] = module
        d1.loader.exec_module(module)
        rehearsal = module.self_test()
        self.assertEqual(rehearsal["reboot_count"], 1)
        self.assertNotIn("durable_no_replay", rehearsal)

    def test_d0_live_requires_bound_approval_before_creating_run(self):
        root = Path(tempfile.mkdtemp(prefix="p319-d0-approval-"))
        fake_adb = root / "adb"
        self.write0400(fake_adb, b"fixture")
        with self.assertRaises(self.m.FreshBaselineError):
            self.m.collect_d0_live(fake_adb, "wrong-approval", root / "result.json")

    def test_d1_live_is_review_blocked_before_arm_or_device(self):
        d1_path = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_d1_fresh_baseline.py"
        spec = importlib.util.spec_from_file_location("p319_d1_live_block", d1_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        with self.assertRaises(module.D1FreshBaselineError):
            module.run_live(Path("/nonexistent/adb"), "wrong-approval", {})

    def test_design_sources_have_no_device_acquisition_primitives(self):
        d1_path = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_d1_fresh_baseline.py"
        d0_path = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_fresh_baseline_capability.py"
        audit_path = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_raw_first_observer_audit.py"
        audit_spec = importlib.util.spec_from_file_location("p319_raw_first_source_audit", audit_path)
        assert audit_spec and audit_spec.loader
        audit = importlib.util.module_from_spec(audit_spec)
        sys.modules[audit_spec.name] = audit
        audit_spec.loader.exec_module(audit)
        forbidden = (
            "AdbReadOnlyClient(",
            "bounded_command(",
            "subprocess.",
            "subprocess.Popen(",
            "os.system(",
            "os.popen(",
            "os.posix_spawn(",
            "pty.spawn(",
            "create_subprocess_",
            "capture_adb_exec_out",
        )
        for path in (d1_path, d0_path):
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, source, f"{path.name} retains {token}")
            tree = ast.parse(source, filename=str(path))
            self.assertFalse(audit._uses_legacy_acquisition(source, tree))
            self.assertFalse(
                any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"bounded_command", "system", "popen", "posix_spawn"}
                    for node in ast.walk(tree)
                )
            )

        d1 = load_module()
        with self.assertRaises(d1.FreshBaselineError):
            d1.collect_d0_live("unused", "unused")
        d1_source_spec = importlib.util.spec_from_file_location("p319_d1_stub_source", d1_path)
        assert d1_source_spec and d1_source_spec.loader
        d1_source_module = importlib.util.module_from_spec(d1_source_spec)
        sys.modules[d1_source_spec.name] = d1_source_module
        d1_source_spec.loader.exec_module(d1_source_module)
        with self.assertRaises(d1_source_module.D1FreshBaselineError):
            d1_source_module.run_live("unused", "unused", {})

    def test_normalizer_reopens_raw_and_binds_d1_d0(self):
        root, d1, d0, output, _d1, _d0 = self.make_fixture()
        with self.fixture_patches(root, d1, d0, output):
            result = self.m.normalize(d1, d0)
            self.assertTrue(result["fresh"])
            self.assertTrue(result["candidate_marker_family_absent"])
            self.assertFalse(result["device_contact"])
            self.m.publish_exclusive(output, result)
            validated = self.m.validate_published_result(output)
            self.assertFalse(validated["authoritative"])
            self.assertFalse(validated["result"]["producer_execution_closure_reviewed"])
            self.assertFalse(validated["result"]["producer_execution_closure_authoritative"])

    def test_handwritten_boolean_receipt_is_rejected_by_deterministic_reduction(self):
        root, d1, d0, output, _d1, _d0 = self.make_fixture()
        with self.fixture_patches(root, d1, d0, output):
            result = self.m.normalize(d1, d0)
            result["fresh"] = False
            self.write0400(output, self.m._canonical(result))
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.validate_published_result(output)

    def test_d0_device_contact_false_is_rejected(self):
        root, d1, d0, output, _d1, d0_value = self.make_fixture()
        d0_value["device_contact"] = False
        bad = root / "bad-d0.json"
        self.write0400(bad, self.m._canonical(d0_value))
        with self.fixture_patches(root, d1, bad, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, bad)

    def test_wrong_raw_size_and_hash_are_rejected(self):
        root, d1, d0, output, _d1, d0_value = self.make_fixture()
        observer = Path(d0_value["observer"]["path"])
        observer.chmod(0o600)
        observer.write_bytes(b"short")
        observer.chmod(0o400)
        with self.fixture_patches(root, d1, d0, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, d0)

    def test_candidate_marker_residual_is_rejected(self):
        root, d1, d0, output, _d1, d0_value = self.make_fixture()
        observer = Path(d0_value["observer"]["path"])
        payload = bytearray(observer.read_bytes())
        payload[: len(b"s22_checkpoint")] = b"s22_checkpoint"
        observer.chmod(0o600)
        observer.write_bytes(payload)
        observer.chmod(0o400)
        with self.fixture_patches(root, d1, d0, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, d0)

    def test_duplicate_d1_json_is_rejected(self):
        root, d1, d0, output, _d1, _d0 = self.make_fixture()
        d1.chmod(0o600)
        d1.write_bytes(b'{"schema":1,"schema":2}\n')
        d1.chmod(0o400)
        with self.fixture_patches(root, d1, d0, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, d0)

    def test_d1_journal_result_path_is_bound(self):
        root, d1, d0, output, d1_value, _d0 = self.make_fixture()
        d1_value["binding"]["journal"]["result"]["path"] = str(root / "foreign.json")
        d1.chmod(0o600)
        d1.write_bytes(self.m._canonical(d1_value))
        d1.chmod(0o400)
        d1.chmod(0o400)
        with self.fixture_patches(root, d1, d0, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, d0)

    def test_d1_journal_arm_and_start_paths_are_fixed(self):
        for name in ("arm", "start"):
            with self.subTest(name=name):
                root, d1, d0, output, d1_value, _d0 = self.make_fixture()
                foreign = root / "foreign" / f"{name}.json"
                d1_value["binding"]["journal"][name]["path"] = str(foreign)
                d1.chmod(0o600)
                d1.write_bytes(self.m._canonical(d1_value))
                d1.chmod(0o400)
                with self.fixture_patches(root, d1, d0, output):
                    with self.assertRaises(self.m.FreshBaselineError):
                        self.m.normalize(d1, d0)

    def test_d1_action_and_journal_content_are_cross_bound(self):
        cases = ("action", "top_level_journal", "start_before")
        for case in cases:
            with self.subTest(case=case):
                root, d1, d0, output, d1_value, _d0 = self.make_fixture()
                if case == "action":
                    d1_value["binding"]["action"] = "different reboot"
                elif case == "top_level_journal":
                    d1_value["journal"]["result"]["path"] = str(root / "foreign-result.json")
                else:
                    journal = d1_value["binding"]["journal"]
                    receipt_name = "arm" if case == "arm_approval" else "start"
                    receipt_path = Path(journal[receipt_name]["path"])
                    parsed = json.loads(receipt_path.read_text(encoding="utf-8"))
                    parsed["before"]["boot_id_sha256"] = "f" * 64
                    self.rewrite0400(receipt_path, self.m._canonical(parsed))
                    updated = {
                        "path": str(receipt_path),
                        "size": receipt_path.stat().st_size,
                        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                        "mode": "0400",
                        "nlink": 1,
                    }
                    d1_value["binding"]["journal"][receipt_name] = updated
                    d1_value["journal"][receipt_name] = copy.deepcopy(updated)
                self.rewrite0400(d1, self.m._canonical(d1_value))
                with self.fixture_patches(root, d1, d0, output):
                    with self.assertRaises(self.m.FreshBaselineError):
                        self.m.normalize(d1, d0)

    def test_d0_host_tool_receipt_shape_and_hash_are_strict(self):
        for mutation in ("missing_version", "bad_version_hash", "bool_size"):
            with self.subTest(mutation=mutation):
                root, d1, d0, output, _d1, d0_value = self.make_fixture()
                host_tool = d0_value["host_tool"]
                if mutation == "missing_version":
                    host_tool.pop("version_output_sha256")
                elif mutation == "bad_version_hash":
                    host_tool["version_output_sha256"] = "not-a-sha"
                else:
                    host_tool["size"] = True
                self.rewrite0400(d0, self.m._canonical(d0_value))
                with self.fixture_patches(root, d1, d0, output):
                    with self.assertRaises(self.m.FreshBaselineError):
                        self.m.normalize(d1, d0)

    def test_d1_selection_serial_and_topology_bind_to_d0_target(self):
        for field in ("selected_serial_sha256", "selected_topology_sha256"):
            with self.subTest(field=field):
                root, d1, d0, output, d1_value, _d0 = self.make_fixture()
                d1_value["selection"][field] = "f" * 64
                d1.chmod(0o600)
                d1.write_bytes(self.m._canonical(d1_value))
                d1.chmod(0o400)
                with self.fixture_patches(root, d1, d0, output):
                    with self.assertRaises(self.m.FreshBaselineError):
                        self.m.normalize(d1, d0)

    def test_current_candidate_source_and_plan_drift_is_rejected(self):
        intent, intent_id = self.m._json(self.m.INTENT, "current intent")
        qualification, qualification_id = self.m._json(self.m.QUALIFICATION, "current qualification")

        def reject(mutated_intent, mutated_qualification):
            def fake_json(path, _label, *args, **kwargs):
                if path == self.m.INTENT:
                    return mutated_intent, intent_id
                if path == self.m.QUALIFICATION:
                    return mutated_qualification, qualification_id
                return self.m._json(path, _label, *args, **kwargs)

            with mock.patch.object(self.m, "_json", side_effect=fake_json):
                with self.assertRaises(self.m.FreshBaselineError):
                    self.m._current_candidate_identity()

        source_drift = copy.deepcopy(intent)
        source_drift["source_keys"].pop("adapter")
        reject(source_drift, copy.deepcopy(qualification))

        eud_drift = copy.deepcopy(intent)
        eud_drift["module_plan"]["eud_index"] = 39
        reject(eud_drift, copy.deepcopy(qualification))

        overlay_drift = copy.deepcopy(intent)
        overlay_drift["module_plan"]["overlay_delta"] = ["foreign.ko"]
        reject(overlay_drift, copy.deepcopy(qualification))

    def test_symlink_and_hardlink_raw_inputs_are_rejected(self):
        root, d1, d0, output, _d1, d0_value = self.make_fixture()
        observer = Path(d0_value["observer"]["path"])
        original = observer.read_bytes()
        observer.unlink()
        observer.symlink_to(root / "foreign")
        with self.fixture_patches(root, d1, d0, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, d0)
        observer.unlink()
        self.write0400(root / "foreign", original)
        observer.hardlink_to(root / "foreign")
        with self.fixture_patches(root, d1, d0, output):
            with self.assertRaises(self.m.FreshBaselineError):
                self.m.normalize(d1, d0)


if __name__ == "__main__":
    unittest.main()
