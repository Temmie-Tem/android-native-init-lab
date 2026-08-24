from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from contextlib import ExitStack
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
D0_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d0_fresh_baseline.py"
)
REDUCER_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_fresh_baseline_capability.py"
)
D1_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v1.json"
)
D0_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d0_fresh_baseline_v1.json"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, module, raw, binding, snapshot: Path):
        self.module = module
        self.raw = raw
        self.binding = binding
        self.snapshot = snapshot
        self.serial = "FIXTURE-S22"
        self.topology_value = "usb:1-2.3"
        self.serial_calls = 0
        self.topology_calls = 0
        self.commanded_serials: list[str] = []
        self.raw_dir = None
        self.replace_serial = False
        self.replace_topology = False
        self.replace_boot = False
        self.capture_sequence = 0
        self.operation_order: list[str] = []

    def bind_raw_capture_dir(self, run_dir):
        self.raw_dir = self.raw.prepare_capture_dir(run_dir, "raw-adb")

    def _capture(self, label: str, payload: bytes = b"fixture\n"):
        self.operation_order.append(label)
        name = f"{self.capture_sequence:04d}-{label}"
        self.capture_sequence += 1
        self.raw.publish_captured_bytes(
            self.raw_dir, name, stdout=payload, stderr=b"",
            argv0_name="adb",
        )

    def receipt(self):
        self._capture("adb-version")
        payload = self.snapshot.read_bytes()
        return {
            "path": str(self.snapshot),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "version_output_sha256": hashlib.sha256(b"fixture adb version").hexdigest(),
        }

    def one_serial(self):
        self._capture("adb-devices")
        self.serial_calls += 1
        return "REPLACED-S22" if self.replace_serial and self.serial_calls > 1 else self.serial

    def topology(self, serial):
        self._capture("adb-get-devpath")
        self.commanded_serials.append(serial)
        self.topology_calls += 1
        return "usb:9-9" if self.replace_topology and self.topology_calls > 1 else self.topology_value

    def properties(self, serial):
        self._capture("adb-read-only-shell-properties")
        self.commanded_serials.append(serial)
        health = self.binding["health"]
        boot_id = (
            "33333333-3333-3333-3333-333333333333"
            if self.replace_boot and self.serial_calls > 1
            else self.binding["boot_id"]
        )
        return {
            "model": "SM-S906N", "device": "g0q",
            "bootloader": "fixture", "incremental": "S906NKSS7FYG8",
            "boot_completed": "1", "bootanim": "stopped",
            "verified_boot_state": health["verified_boot_state"],
            "boot_id": boot_id, "kernel_release": health["kernel_release"],
        }

    def root_health(self, serial):
        self._capture("adb-read-only-shell-root-health")
        self.commanded_serials.append(serial)
        health = self.binding["health"]
        return {
            "root": "uid=0(root) gid=0(root)",
            "boot": health["boot_sha256"],
            **health["supporting_partition_sha256"],
        }


class P319D0FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d0 = load(D0_SOURCE, "p319_d0_fresh_test")
        cls.reducer = load(REDUCER_SOURCE, "p319_d0_reducer_test")

    def binding_value(self, *, review=None):
        d0 = self.d0
        reducer_payload = d0.REDUCER.read_bytes()
        d1_payload = d0.D1_SOURCE.read_bytes()
        d0_payload = d0.D0_RUNTIME.read_bytes()
        profile_payload = d0.PROFILE.read_bytes()
        intent_payload = d0.INTENT.read_bytes()
        qualification_payload = d0.QUALIFICATION.read_bytes()
        candidate = d0._candidate_identity(intent_payload, qualification_payload)
        design = d0._baseline_design(
            reducer_payload, d1_payload, d0_payload, profile_payload
        )
        return d0._expected_manifest(
            script_payload=d0.SCRIPT.read_bytes(),
            reducer_payload=reducer_payload,
            d0_payload=d0_payload,
            raw_payload=d0.RAW_CAPTURE.read_bytes(),
            adapter_payloads=d0._adapter_payloads(),
            d1_payload=d1_payload,
            d1_binding_payload=d0.D1_BINDING.read_bytes(),
            profile_payload=profile_payload,
            adb_payload=d0.HOST_ADB.read_bytes(),
            candidate=candidate,
            design=design,
            review=review or {"status": "review-pending", "verdict": None},
        )

    def patch_paths(self, root: Path):
        run = root / "d0-p319-fresh-baseline-1"
        arm = Path(str(run) + ".arm.json")
        stop = Path(str(run) + ".stop.json")
        result = run / "result.json"
        observer = run / "baseline-observer.bin"
        receipt = run / "baseline-observer.capture.json"
        snapshot = run / ("adb-" + self.d0.HOST_ADB_SHA256)
        binding = root / "d0-binding.json"
        return {
            "run": run, "arm": arm, "stop": stop, "result": result,
            "observer": observer, "receipt": receipt,
            "snapshot": snapshot, "binding": binding,
        }

    def patched_environment(self, paths):
        stack = ExitStack()
        stack.enter_context(mock.patch.multiple(
            self.d0,
            RUN_PARENT=paths["run"].parent,
            RUN_DIR=paths["run"], RUN_ARM=paths["arm"], RUN_STOP=paths["stop"],
            RESULT_PATH=paths["result"], OBSERVER_PATH=paths["observer"],
            RAW_RECEIPT=paths["receipt"], RAW_ADB_DIR=paths["run"] / "raw-adb",
            ADB_SNAPSHOT=paths["snapshot"],
            BINDING_MANIFEST=paths["binding"],
        ))
        stack.enter_context(mock.patch.multiple(
            self.reducer,
            D0_RUN_DIR=paths["run"], D0_RUN_ARM=paths["arm"],
            D0_RUN_STOP=paths["stop"], DEFAULT_D0=paths["result"],
            D0_OBSERVER=paths["observer"], D0_RAW_RECEIPT=paths["receipt"],
            D0_RAW_ADB_DIR=paths["run"] / "raw-adb",
            D0_ADB_SNAPSHOT=paths["snapshot"],
            D0_EXECUTION_MANIFEST=paths["binding"],
        ))
        return stack

    def write_binding(self, path: Path, *, pass_go: bool):
        review = (
            {"status": "pass-go", "verdict": self.d0.REVIEW_VERDICT}
            if pass_go else {"status": "review-pending", "verdict": None}
        )
        value = self.binding_value(review=review)
        path.write_bytes(self.d0.canonical(value))
        return value

    def d1_value(self, inputs, *, serial="FIXTURE-S22", topology="usb:1-2.3", boot_id=None):
        boot_id = boot_id or "22222222-2222-2222-2222-222222222222"
        expected = inputs["profile"]["start_health"]
        health = {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": expected["verified_boot_state"],
            "root_verified": True,
            "boot_sha256": expected["boot_sha256"],
            "supporting_partition_sha256": expected["supporting_partition_sha256"],
            "odin_endpoint_absent": True,
            "kernel_release": "5.10.226-fixture",
            "boot_id_sha256": hashlib.sha256(boot_id.encode()).hexdigest(),
        }
        return {
            "after": health,
            "selection": {
                "selected_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
                "selected_topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
                "inventory_count": 2,
                "inventory_digest": hashlib.sha256(b"fixture inventory").hexdigest(),
                "other_targets_commanded": False,
            },
            "receipt": {
                "path": self.d0._relative(self.d0.D1_RESULT),
                "size": 1,
                "sha256": hashlib.sha256(b"d1").hexdigest(),
            },
            "boot_id": boot_id,
            "health": health,
        }

    @staticmethod
    def usb_snapshot(download=0):
        return {
            "enumerated_devices": 1,
            "download_endpoint_count": download,
            "snapshot_sha256": hashlib.sha256(f"usb:{download}".encode()).hexdigest(),
        }

    def capture(self, payload=None, *, stderr=b"", returncode=0, timed_out=False):
        payload = bytes(self.d0.RAW_SIZE) if payload is None else payload

        def factory(raw, _argv, run_dir):
            if timed_out:
                writer = raw.RawCaptureWriter(
                    run_dir, "baseline-observer",
                    stdout_maximum=max(1, len(payload)), stderr_maximum=max(1, len(stderr)),
                    stdout_name="baseline-observer.bin",
                    stderr_name="baseline-observer.bin.stderr",
                )
                writer.write_stdout(payload)
                writer.write_stderr(stderr)
                return writer.finalize(returncode=-15, timed_out=True)
            return raw.publish_captured_bytes(
                run_dir, "baseline-observer", stdout=payload, stderr=stderr,
                returncode=returncode, stdout_name="baseline-observer.bin",
                stderr_name="baseline-observer.bin.stderr",
            )

        return factory

    def prepare(self, *, pass_go=True):
        root = Path(tempfile.mkdtemp(prefix="p319-d0-producer-"))
        paths = self.patch_paths(root)
        stack = self.patched_environment(paths)
        stack.__enter__()
        self.addCleanup(stack.__exit__, None, None, None)
        self.write_binding(paths["binding"], pass_go=pass_go)
        inputs = self.d0._validated_static_inputs()
        inputs = self.d0._validated_execution_inputs(inputs)
        d1 = self.d1_value(inputs)
        return root, paths, inputs, d1

    def execute(self, inputs, d1, *, client=None, capture=None, usb=None, adapter=None):
        holder = {}

        def factory(module, raw, snapshot):
            if client is None:
                value = FakeClient(
                    module, raw,
                    {"health": d1["health"], "boot_id": d1["boot_id"]},
                    snapshot,
                )
            else:
                value = client
                value.module = module
                value.raw = raw
                value.snapshot = snapshot
            holder["client"] = value
            return value

        self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
        result = self.d0._execute(
            inputs, d1, client_factory=factory,
            capture_factory=capture or self.capture(),
            usb_factory=usb or (lambda _root, _download: self.usb_snapshot()),
            adapter=adapter,
        )
        return result, holder["client"]

    def test_default_self_test_is_zero_device_and_capability_reviewed(self):
        value = self.d0.self_test()
        self.assertEqual(value["classification"], "ZERO_AMBIGUOUS")
        self.assertEqual(value["raw_bytes"], self.d0.RAW_SIZE)
        self.assertEqual(value["review_status"], "pass-go")
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["approval_created"])

    def test_d1_binding_repin_is_narrow_and_predecessor_is_recorded(self):
        current = D1_BINDING.read_bytes()
        value = json.loads(current)
        d0_binding = json.loads(D0_BINDING.read_text())
        self.assertEqual(
            hashlib.sha256(current).hexdigest(),
            d0_binding["inputs"]["d1_execution_binding"]["sha256"],
        )
        self.assertEqual(value["independent_review"], {
            "status": "pass-go",
            "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1",
        })
        self.assertEqual(value["inputs"]["fresh_baseline_reducer"]["sha256"], hashlib.sha256(REDUCER_SOURCE.read_bytes()).hexdigest())
        self.assertEqual(
            self.d0.D1_BINDING_SUPERSEDED_SHA256,
            "d92e7e463e26f1fae4f9a5515e00feb0c09fb2d83930839e89c391b58931fb4e",
        )

    def test_review_and_approval_gate_precede_intent_and_d1_load(self):
        pending = {"manifest": {"independent_review": {"status": "review-pending", "verdict": None}}, "authority": "expected"}
        with mock.patch.object(self.d0, "_validated_static_inputs", return_value=pending), mock.patch.object(self.d0, "_validated_execution_inputs") as load_execution, mock.patch.object(self.d0, "_load_d1_evidence") as load_d1, mock.patch.object(self.d0, "_durable_create") as durable:
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live("expected")
            load_execution.assert_not_called(); load_d1.assert_not_called(); durable.assert_not_called()
        passed = {"manifest": {"independent_review": {"status": "pass-go", "verdict": self.d0.REVIEW_VERDICT}}, "authority": "expected"}
        with mock.patch.object(self.d0, "_validated_static_inputs", return_value=passed), mock.patch.object(self.d0, "_validated_execution_inputs") as load_execution, mock.patch.object(self.d0, "_load_d1_evidence") as load_d1, mock.patch.object(self.d0, "_durable_create") as durable:
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live("wrong")
            load_execution.assert_not_called(); load_d1.assert_not_called(); durable.assert_not_called()

    def test_live_argv_is_closed(self):
        for argv in (["--live"], ["--live", "--approval", "x", "extra"], ["--serial", "x"]):
            with self.subTest(argv=argv):
                self.assertEqual(self.d0.main(list(argv)), 2)

    def test_clean_fixture_result_and_reducer_binding_validation(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        result, client = self.execute(inputs, d1)
        self.assertTrue(result["candidate_marker_family_absent"])
        self.assertEqual(result["observer"]["bytes"], self.d0.RAW_SIZE)
        self.assertEqual(set(client.commanded_serials), {"FIXTURE-S22"})
        self.assertEqual(client.serial_calls, 2)
        snapshot = paths["snapshot"].stat(follow_symlinks=False)
        self.assertEqual(snapshot.st_mode & 0o777, 0o500)
        self.assertEqual(snapshot.st_nlink, 1)
        self.assertTrue(result["raw_adb"]["complete"])
        self.assertEqual(len(result["raw_adb"]["handles"]), 9)
        self.assertEqual(len(result["raw_adb"]["children"]), 27)
        self.assertEqual(result["initial_health"], result["health"])
        with self.assertRaises(self.d0.D0FreshBaselineError):
            self.d0._prepare_snapshot(inputs["adb_payload"], paths["snapshot"])
        validated, payload, _adapter, _adapter_payload = self.reducer._validate_d0(
            result, inputs["baseline_design"], d1, inputs["candidate"],
            self.reducer._profile(),
        )
        self.assertEqual(len(payload), self.d0.RAW_SIZE)
        self.assertEqual(validated["result"], result)

    def test_producer_reducer_target_and_initial_health_parity(self):
        for mutation in (
            "extra-key", "missing-transport", "wrong-transport",
            "initial-boot", "usb-extra", "host-extra",
        ):
            with self.subTest(mutation=mutation):
                _root, _paths, inputs, d1 = self.prepare(pass_go=True)
                result, _client = self.execute(inputs, d1)
                value = copy.deepcopy(result)
                row = value["target_evidence"]["targets"][0]
                if mutation == "extra-key":
                    row["unexpected"] = "x"
                elif mutation == "missing-transport":
                    row.pop("android_transport")
                elif mutation == "wrong-transport":
                    row["android_transport"] = "usb"
                else:
                    if mutation == "initial-boot":
                        value["initial_health"]["boot_id_sha256"] = "0" * 64
                    elif mutation == "usb-extra":
                        value["usb"]["initial"]["unexpected"] = 1
                    else:
                        value["host_tool"]["unexpected"] = 1
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0.validate_result(
                        value, inputs, d1, publishing=True
                    )
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.reducer._validate_d0(
                        value, inputs["baseline_design"], d1,
                        inputs["candidate"], self.reducer._profile(),
                    )

    def test_properties_root_then_usb_and_final_usb_is_last_live_observation(self):
        _root, _paths, inputs, d1 = self.prepare(pass_go=True)
        client = FakeClient(
            None, None,
            {"health": d1["health"], "boot_id": d1["boot_id"]},
            self.d0.ADB_SNAPSHOT,
        )

        def usb(_root, _download):
            client.operation_order.append("usb-snapshot")
            return self.usb_snapshot()

        self.execute(inputs, d1, client=client, usb=usb)
        self.assertEqual(client.operation_order, [
            "adb-version", "adb-devices", "adb-get-devpath",
            "adb-read-only-shell-properties",
            "adb-read-only-shell-root-health", "usb-snapshot",
            "adb-devices", "adb-get-devpath",
            "adb-read-only-shell-properties",
            "adb-read-only-shell-root-health", "usb-snapshot",
        ])

    def test_invalid_initial_and_final_usb_publish_consumed_stop(self):
        def invalid(kind):
            value = self.usb_snapshot()
            if kind == "empty":
                return {}
            if kind == "enumerated-bool":
                value["enumerated_devices"] = True
            elif kind == "download-bool":
                value["download_endpoint_count"] = False
            elif kind == "missing":
                value.pop("snapshot_sha256")
            elif kind == "extra":
                value["unexpected"] = 1
            elif kind == "bad-sha":
                value["snapshot_sha256"] = "not-a-sha"
            return value

        for stage in ("initial", "final"):
            for kind in (
                "empty", "enumerated-bool", "download-bool",
                "missing", "extra", "bad-sha",
            ):
                with self.subTest(stage=stage, kind=kind):
                    _root, paths, inputs, d1 = self.prepare(pass_go=True)
                    calls = {"count": 0}

                    def usb(_root, _download):
                        calls["count"] += 1
                        if calls["count"] == (1 if stage == "initial" else 2):
                            return invalid(kind)
                        return self.usb_snapshot()

                    real_execute = self.d0._execute

                    def execute(bound_inputs, bound_d1, **kwargs):
                        return real_execute(
                            bound_inputs, bound_d1,
                            client_factory=lambda module, raw, snapshot: FakeClient(
                                module, raw,
                                {"health": d1["health"], "boot_id": d1["boot_id"]},
                                snapshot,
                            ),
                            capture_factory=self.capture(),
                            usb_factory=usb,
                            progress=kwargs["progress"],
                        )

                    with mock.patch.object(
                        self.d0, "_validated_static_inputs", return_value=inputs
                    ), mock.patch.object(
                        self.d0, "_validated_execution_inputs", return_value=inputs
                    ), mock.patch.object(
                        self.d0, "_load_d1_evidence", return_value=d1
                    ), mock.patch.object(
                        self.d0, "_execute", side_effect=execute
                    ):
                        with self.assertRaises(self.d0.D0FreshBaselineError) as caught:
                            self.d0.run_live(inputs["authority"])
                    self.assertNotIn("stop publication failed", str(caught.exception))
                    stop = json.loads(paths["stop"].read_text())
                    self.assertTrue(stop["consumed"])
                    self.assertFalse(stop["replay_authorized"])
                    self.assertIsNone(stop["final"])
                    if stage == "initial":
                        self.assertIsNone(stop["initial"])
                    else:
                        self.assertIsNotNone(stop["initial"])
                    self.d0.validate_stop(stop, inputs, d1)

    def test_static_gate_executes_no_reducer_adapter_or_runtime(self):
        _root, _paths, _inputs, _d1 = self.prepare(pass_go=True)
        with mock.patch.object(
            self.d0, "_load_reducer", side_effect=AssertionError("reducer loaded")
        ), mock.patch.object(
            self.d0, "_load_adapter", side_effect=AssertionError("adapter loaded")
        ), mock.patch.object(
            self.d0, "_load_runtime", side_effect=AssertionError("runtime loaded")
        ):
            static = self.d0._validated_static_inputs()
        self.assertNotIn("reducer", static)

    def test_reducer_executes_only_prevalidated_d0_source_bytes(self):
        root = Path(tempfile.mkdtemp(prefix="p319-d0-reducer-pin-"))
        source = root / "p319-d0.py"
        pinned = D0_SOURCE.read_bytes()
        source.write_bytes(pinned)
        marker = root / "marker"
        source.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed')\n"
        )
        with mock.patch.object(self.reducer, "D0_SUCCESSOR", source):
            with self.assertRaises(self.reducer.FreshBaselineError):
                self.reducer._compile_d0_producer(pinned)
        self.assertFalse(marker.exists())

    def test_reducer_rejects_binding_approval_and_journal_mutations(self):
        _root, _paths, inputs, d1 = self.prepare(pass_go=True)
        result, _client = self.execute(inputs, d1)
        for mutation in ("manifest", "approval", "journal"):
            with self.subTest(mutation=mutation):
                value = copy.deepcopy(result)
                if mutation == "manifest":
                    value["binding"]["execution_manifest"]["sha256"] = "0" * 64
                elif mutation == "approval":
                    value["binding"]["approval_sha256"] = "0" * 64
                else:
                    value["journal"]["result"]["path"] = "foreign.json"
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.reducer._validate_d0(
                        value, inputs["baseline_design"], d1,
                        inputs["candidate"], self.reducer._profile(),
                    )

    def test_other_target_is_never_commanded(self):
        _root, _paths, inputs, d1 = self.prepare(pass_go=True)
        result, client = self.execute(inputs, d1)
        self.assertEqual(result["target_evidence"]["targets"][0]["adb_serial_sha256"], d1["selection"]["selected_serial_sha256"])
        self.assertEqual(set(client.commanded_serials), {"FIXTURE-S22"})

    def test_d1_serial_topology_and_boot_mismatch_reject(self):
        for mutation in ("serial", "topology", "boot"):
            with self.subTest(mutation=mutation):
                _root, _paths, inputs, d1 = self.prepare(pass_go=True)
                bad = copy.deepcopy(d1)
                if mutation == "serial": bad["selection"]["selected_serial_sha256"] = "0" * 64
                elif mutation == "topology": bad["selection"]["selected_topology_sha256"] = "0" * 64
                else: bad["after"]["boot_id_sha256"] = "0" * 64
                self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0._execute(inputs, bad, client_factory=lambda m, r, s: FakeClient(m, r, {"health": d1["health"], "boot_id": d1["boot_id"]}, s), capture_factory=self.capture(), usb_factory=lambda _r, _d: self.usb_snapshot())

    def test_target_replacement_and_download_appearance_reject(self):
        for mutation in ("serial", "topology", "boot", "download"):
            with self.subTest(mutation=mutation):
                _root, _paths, inputs, d1 = self.prepare(pass_go=True)
                client = FakeClient(None, None, {"health": d1["health"], "boot_id": d1["boot_id"]}, self.d0.ADB_SNAPSHOT)
                setattr(client, "replace_" + mutation, True) if mutation != "download" else None
                calls = {"n": 0}
                def usb(_root, _download):
                    calls["n"] += 1
                    return self.usb_snapshot(1 if mutation == "download" and calls["n"] == 2 else 0)
                self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0._execute(inputs, d1, client_factory=lambda m, r, s: (setattr(client, "module", m) or setattr(client, "raw", r) or setattr(client, "snapshot", s) or client), capture_factory=self.capture(), usb_factory=usb)

    def test_raw_failure_shapes_reject(self):
        cases = {
            "short": self.capture(bytes(self.d0.RAW_SIZE - 1)),
            "long": self.capture(bytes(self.d0.RAW_SIZE + 1)),
            "stderr": self.capture(stderr=b"x"),
            "nonzero": self.capture(returncode=1),
            "timeout": self.capture(timed_out=True),
        }
        for name, capture in cases.items():
            with self.subTest(name=name):
                _root, _paths, inputs, d1 = self.prepare(pass_go=True)
                self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0._execute(inputs, d1, client_factory=lambda m, r, s: FakeClient(m, r, {"health": d1["health"], "boot_id": d1["boot_id"]}, s), capture_factory=capture, usb_factory=lambda _r, _d: self.usb_snapshot())

    def test_interruption_and_raw_mutation_reject(self):
        for mutation in ("interrupt", "stdout", "receipt"):
            with self.subTest(mutation=mutation):
                _root, _paths, inputs, d1 = self.prepare(pass_go=True)
                def capture(raw, argv, run):
                    if mutation == "interrupt": raise KeyboardInterrupt("fixture")
                    handle = self.capture()(raw, argv, run)
                    path = handle.stdout_path if mutation == "stdout" else handle.receipt_path
                    path.chmod(0o600); path.write_bytes(path.read_bytes() + b"x"); path.chmod(0o400)
                    return handle
                self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
                expected = KeyboardInterrupt if mutation == "interrupt" else self.d0.D0FreshBaselineError
                with self.assertRaises(expected):
                    self.d0._execute(inputs, d1, client_factory=lambda m, r, s: FakeClient(m, r, {"health": d1["health"], "boot_id": d1["boot_id"]}, s), capture_factory=capture, usb_factory=lambda _r, _d: self.usb_snapshot())

    def test_raw_adb_extra_symlink_missing_and_receipt_mutation_reject(self):
        for mutation in ("extra", "symlink", "missing", "receipt"):
            with self.subTest(mutation=mutation):
                _root, paths, inputs, d1 = self.prepare(pass_go=True)
                result, _client = self.execute(inputs, d1)
                raw_dir = paths["run"] / "raw-adb"
                receipt = sorted(raw_dir.glob("*.capture.json"))[0]
                if mutation == "extra":
                    node = raw_dir / "extra"
                    node.write_bytes(b"x"); node.chmod(0o400)
                elif mutation == "symlink":
                    node = raw_dir / "indirect"
                    node.symlink_to(receipt)
                elif mutation == "missing":
                    node = raw_dir / json.loads(receipt.read_text())["stdout"]["name"]
                    node.unlink()
                else:
                    node = receipt
                    node.chmod(0o600)
                    node.write_bytes(node.read_bytes() + b" ")
                    node.chmod(0o400)
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0.validate_result(
                        result, inputs, d1, publishing=True
                    )
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.reducer._validate_d0(
                        result, inputs["baseline_design"], d1,
                        inputs["candidate"], self.reducer._profile(),
                    )

    def test_initial_command_failure_stop_preserves_complete_raw_handle(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        client = FakeClient(
            None, None,
            {"health": d1["health"], "boot_id": d1["boot_id"]},
            paths["snapshot"],
        )
        original_receipt = client.receipt

        def failed_receipt():
            original_receipt()
            raise RuntimeError("fixture initial command parse failure")

        client.receipt = failed_receipt
        progress = {}
        self.d0._durable_create(paths["arm"], self.d0._arm_value(inputs))
        try:
            self.d0._execute(
                inputs, d1,
                client_factory=lambda module, raw, snapshot: (
                    setattr(client, "module", module)
                    or setattr(client, "raw", raw)
                    or setattr(client, "snapshot", snapshot)
                    or client
                ),
                capture_factory=self.capture(),
                usb_factory=lambda _root, _download: self.usb_snapshot(),
                progress=progress,
            )
        except RuntimeError as exc:
            self.d0._publish_stop(inputs, d1, exc, progress)
        else:
            self.fail("fixture initial command failure did not stop")
        stop = json.loads(paths["stop"].read_text())
        self.assertTrue(stop["raw_adb"]["complete"])
        self.assertEqual(len(stop["raw_adb"]["handles"]), 1)
        self.assertEqual(len(stop["raw_adb"]["children"]), 3)
        self.d0.validate_stop(stop, inputs, d1)

    def test_parser_runs_only_after_raw_receipt_publication(self):
        _root, _paths, inputs, d1 = self.prepare(pass_go=True)
        state = {"published": False, "parsed": False}
        def capture(raw, argv, run):
            handle = self.capture()(raw, argv, run)
            state["published"] = handle.receipt_path.exists()
            return handle
        adapter = types.SimpleNamespace(PROFILE="E1A")
        def classify(payload, **_kwargs):
            self.assertTrue(state["published"])
            self.assertTrue(self.d0.RAW_RECEIPT.exists())
            state["parsed"] = True
            return {"classification": "ZERO_AMBIGUOUS", "accepted": False, "records": [], "baseline_size": len(payload), "baseline_clean": True, "integrity_issue": False}
        adapter.classify_clean_baseline = classify
        result, _client = self.execute(inputs, d1, capture=capture, adapter=adapter)
        self.assertTrue(state["parsed"]); self.assertTrue(result["observer"]["parser_started_after_raw_publish"])

    def test_dependency_path_drift_does_not_execute_replacement(self):
        root = Path(tempfile.mkdtemp(prefix="p319-d0-import-pin-"))
        runtime = root / "device_action_d0_v2.py"
        original = self.d0.D0_RUNTIME.read_bytes()
        runtime.write_bytes(original)
        marker = root / "marker"
        replacement = f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n".encode()
        pinned = self.d0._stable_read(runtime, "fixture runtime")
        runtime.write_bytes(replacement)
        with mock.patch.object(self.d0, "D0_RUNTIME", runtime):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0._load_runtime(pinned, self.d0.RAW_CAPTURE.read_bytes())
        self.assertFalse(marker.exists())

    def test_pinned_raw_and_adapter_replacements_never_execute(self):
        root = Path(tempfile.mkdtemp(prefix="p319-d0-graph-pin-"))
        marker = root / "marker"
        replacement = (
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed')\n"
        ).encode()

        raw_path = root / "device_action_raw_capture_v1.py"
        raw_payload = self.d0.RAW_CAPTURE.read_bytes()
        raw_path.write_bytes(replacement)
        with mock.patch.object(self.d0, "RAW_CAPTURE", raw_path):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0._load_runtime(
                    self.d0.D0_RUNTIME.read_bytes(), raw_payload
                )
        self.assertFalse(marker.exists())

        adapter_root = root / "adapter"
        adapter_root.mkdir()
        payloads = self.d0._adapter_payloads()
        for name, payload in payloads.items():
            (adapter_root / f"{name}.py").write_bytes(payload)
        (adapter_root / f"{self.d0.ADAPTER_ROOT}.py").write_bytes(replacement)
        with mock.patch.object(self.d0, "SCRIPT_DIR", adapter_root):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0._load_adapter(payloads)
        self.assertFalse(marker.exists())

    def test_partial_arm_and_result_cuts_publish_typed_stop(self):
        for cut in ("arm", "result"):
            with self.subTest(cut=cut):
                _root, paths, inputs, d1 = self.prepare(pass_go=True)
                real_create = self.d0._durable_create
                if cut == "arm":
                    def create(path, value):
                        if path == paths["arm"]:
                            path.write_bytes(b'{"partial":true}\n'); path.chmod(0o400)
                            raise RuntimeError("arm cut")
                        return real_create(path, value)
                    execute = self.d0._execute
                else:
                    create = real_create
                    def execute(_inputs, _d1, **_kwargs):
                        paths["run"].mkdir(mode=0o700)
                        paths["result"].write_bytes(b'{"partial":true}\n'); paths["result"].chmod(0o400)
                        raise RuntimeError("result cut")
                with mock.patch.object(self.d0, "_validated_static_inputs", return_value=inputs), mock.patch.object(self.d0, "_load_d1_evidence", return_value=d1), mock.patch.object(self.d0, "_durable_create", side_effect=create), mock.patch.object(self.d0, "_execute", side_effect=execute):
                    with self.assertRaises(self.d0.D0FreshBaselineError):
                        self.d0.run_live(inputs["authority"])
                stop = json.loads(paths["stop"].read_text())
                self.assertTrue(stop["arm_present"]); self.assertFalse(stop["replay_authorized"])
                self.assertEqual(stop["arm_bytes_complete"], cut != "arm")
                if cut == "result":
                    self.assertTrue(stop["result_present"])
                    self.assertTrue(stop["result_node_valid"])
                    self.assertFalse(stop["result_bytes_complete"])
                self.d0.validate_stop(stop, inputs, d1)

    def test_post_arm_runtime_import_failure_still_publishes_typed_stop(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        with mock.patch.object(
            self.d0, "_validated_static_inputs", return_value=inputs
        ), mock.patch.object(
            self.d0, "_validated_execution_inputs", return_value=inputs
        ), mock.patch.object(
            self.d0, "_load_d1_evidence", return_value=d1
        ), mock.patch.object(
            self.d0, "_load_runtime", side_effect=RuntimeError("fixture import cut")
        ):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live(inputs["authority"])
        stop = json.loads(paths["stop"].read_text())
        self.assertTrue(stop["arm_bytes_complete"])
        self.assertTrue(stop["run_directory_node_valid"])
        self.assertFalse(stop["raw_adb"]["directory_present"])
        self.d0.validate_stop(stop, inputs, d1)

    def test_pre_intent_failure_has_no_stop(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        with mock.patch.object(self.d0, "_validated_static_inputs", return_value=inputs), mock.patch.object(self.d0, "_load_d1_evidence", return_value=d1), mock.patch.object(self.d0, "_durable_create", side_effect=RuntimeError("pre-intent")):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live(inputs["authority"])
        self.assertFalse(paths["arm"].exists()); self.assertFalse(paths["stop"].exists())

    def test_existing_consumed_arm_never_replays_execution(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        self.d0._durable_create(paths["arm"], self.d0._arm_value(inputs))
        with mock.patch.object(self.d0, "_validated_static_inputs", return_value=inputs), mock.patch.object(self.d0, "_load_d1_evidence", return_value=d1), mock.patch.object(self.d0, "_execute") as execute:
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live(inputs["authority"])
            execute.assert_not_called()
        stop = json.loads(paths["stop"].read_text())
        self.assertTrue(stop["consumed"])
        self.assertFalse(stop["replay_authorized"])

    def test_stop_namespace_symlink_hardlink_and_extra_child_reject(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        self.d0._durable_create(paths["arm"], self.d0._arm_value(inputs))
        paths["run"].mkdir(mode=0o700)
        self.d0._publish_stop(inputs, d1, RuntimeError("fixture"), {})
        stop_value = json.loads(paths["stop"].read_text())
        self.d0.validate_stop(stop_value, inputs, d1)
        for attack in ("extra", "symlink", "hardlink"):
            with self.subTest(attack=attack):
                node = paths["run"] / ("extra" if attack == "extra" else "result.json")
                foreign = paths["run"].parent / f"foreign-{attack}"
                foreign.write_bytes(b"x"); foreign.chmod(0o400)
                if attack == "symlink": node.symlink_to(foreign)
                elif attack == "hardlink": node.hardlink_to(foreign)
                else: node.write_bytes(b"x")
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0.validate_stop(stop_value, inputs, d1)
                node.unlink(); foreign.unlink()

    def test_invalid_arm_run_and_result_nodes_are_typed_without_traversal(self):
        for attack in ("arm-symlink", "arm-hardlink", "arm-fifo"):
            with self.subTest(attack=attack):
                _root, paths, inputs, d1 = self.prepare(pass_go=True)
                foreign = paths["arm"].parent / (attack + "-foreign")
                if attack == "arm-symlink":
                    foreign.write_bytes(b"foreign"); foreign.chmod(0o400)
                    paths["arm"].symlink_to(foreign)
                elif attack == "arm-hardlink":
                    foreign.write_bytes(b"foreign"); foreign.chmod(0o400)
                    paths["arm"].hardlink_to(foreign)
                else:
                    os.mkfifo(paths["arm"], 0o400)
                with mock.patch.object(
                    self.d0, "_validated_static_inputs", return_value=inputs
                ), mock.patch.object(
                    self.d0, "_validated_execution_inputs", return_value=inputs
                ), mock.patch.object(
                    self.d0, "_load_d1_evidence", return_value=d1
                ), mock.patch.object(self.d0, "_execute") as execute:
                    with self.assertRaises(self.d0.D0FreshBaselineError):
                        self.d0.run_live(inputs["authority"])
                    execute.assert_not_called()
                stop = json.loads(paths["stop"].read_text())
                self.assertTrue(stop["arm_present"])
                self.assertFalse(stop["arm_node_valid"])
                self.assertFalse(stop["arm_bytes_complete"])
                self.d0.validate_stop(stop, inputs, d1)

        for attack in ("run-symlink", "result-symlink"):
            with self.subTest(attack=attack):
                _root, paths, inputs, d1 = self.prepare(pass_go=True)
                self.d0._durable_create(paths["arm"], self.d0._arm_value(inputs))
                foreign = paths["run"].parent / (attack + "-foreign")
                if attack == "run-symlink":
                    foreign.mkdir(mode=0o700)
                    (foreign / "must-not-traverse").write_bytes(b"x")
                    paths["run"].symlink_to(foreign, target_is_directory=True)
                else:
                    paths["run"].mkdir(mode=0o700)
                    foreign.write_bytes(b"x"); foreign.chmod(0o400)
                    paths["result"].symlink_to(foreign)
                self.d0._publish_stop(
                    inputs, d1, RuntimeError("fixture namespace cut"), {}
                )
                stop = json.loads(paths["stop"].read_text())
                if attack == "run-symlink":
                    self.assertTrue(stop["run_directory_present"])
                    self.assertFalse(stop["run_directory_node_valid"])
                    self.assertFalse(stop["result_presence_known"])
                    self.assertFalse(stop["raw_adb"]["directory_presence_known"])
                else:
                    self.assertTrue(stop["result_presence_known"])
                    self.assertTrue(stop["result_present"])
                    self.assertFalse(stop["result_node_valid"])
                    self.assertFalse(stop["result_bytes_complete"])
                self.d0.validate_stop(stop, inputs, d1)

    def test_partial_stop_and_forged_progress_reject(self):
        _root, paths, inputs, d1 = self.prepare(pass_go=True)
        self.d0._durable_create(paths["arm"], self.d0._arm_value(inputs))
        paths["run"].mkdir(mode=0o700)
        initial = {
            "target_evidence": self.d0._target_evidence(
                "FIXTURE-S22", "usb:1-2.3"
            ),
            "health": d1["health"],
            "usb": self.usb_snapshot(),
            "host_tool": {
                "path": str(paths["snapshot"]),
                "size": self.d0.HOST_ADB_SIZE,
                "sha256": self.d0.HOST_ADB_SHA256,
                "version_output_sha256": hashlib.sha256(b"fixture").hexdigest(),
            },
        }
        self.d0._publish_stop(
            inputs, d1, RuntimeError("fixture"), {"initial": initial}
        )
        value = json.loads(paths["stop"].read_text())
        self.d0.validate_stop(value, inputs, d1)
        for mutation in ("serial", "topology", "boot"):
            forged = copy.deepcopy(value)
            if mutation == "serial":
                forged["initial"]["target_evidence"]["targets"][0][
                    "adb_serial_sha256"
                ] = "0" * 64
            elif mutation == "topology":
                forged["initial"]["target_evidence"]["targets"][0][
                    "usb_topology_sha256"
                ] = "0" * 64
            else:
                forged["initial"]["health"]["boot_id_sha256"] = "0" * 64
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.validate_stop(forged, inputs, d1)
        paths["stop"].chmod(0o600)
        paths["stop"].write_bytes(b'{"partial":true}\n')
        paths["stop"].chmod(0o400)
        with self.assertRaises(self.d0.D0FreshBaselineError):
            self.d0.validate_stop(value, inputs, d1)

    def test_duplicate_key_bool_integer_and_binding_drift_reject(self):
        original = D0_BINDING.read_bytes()
        duplicate = original[:-2] + b',"schema":"duplicate"}\n'
        with self.assertRaises(self.d0.D0FreshBaselineError):
            self.d0._strict_object(duplicate, "duplicate fixture")
        value = json.loads(original)
        value["limits"]["observer_read_count"] = True
        root = Path(tempfile.mkdtemp(prefix="p319-d0-binding-hostile-"))
        binding = root / "binding.json"
        binding.write_bytes(self.d0.canonical(value))
        with mock.patch.object(self.d0, "BINDING_MANIFEST", binding):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0._validated_static_inputs()


if __name__ == "__main__":
    unittest.main()
