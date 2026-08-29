from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d0_fresh_baseline_v3.py"
)
REDUCER_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_fresh_baseline_capability_v3.py"
)
BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d0_fresh_baseline_v3.json"
)
V2_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d0_fresh_baseline_v2.json"
)
D1_RESULT = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline-v3/"
    "p319-fresh-baseline-3/result.json"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, module, raw, snapshot: Path, health: dict[str, object]):
        self.module = module
        self.raw = raw
        self.snapshot = snapshot
        self.health = health
        self.serial = "FIXTURE-S22"
        self.topology_value = "usb:1-2.3"
        self.serial_calls = 0
        self.topology_calls = 0
        self.capture_sequence = 0
        self.commanded_serials: list[str] = []
        self.raw_dir: Path | None = None
        self.replace_serial = False
        self.replace_topology = False
        self.replace_boot = False

    def bind_raw_capture_dir(self, run_dir: Path):
        self.raw_dir = self.raw.prepare_capture_dir(run_dir, "raw-adb")

    def _capture(self, label: str, payload: bytes = b"fixture\n"):
        assert self.raw_dir is not None
        name = f"{self.capture_sequence:04d}-{label}"
        self.capture_sequence += 1
        return self.raw.publish_captured_bytes(
            self.raw_dir, name, stdout=payload, stderr=b"", argv0_name="adb"
        )

    def receipt(self):
        self._capture("adb-version")
        payload = self.snapshot.read_bytes()
        return {
            "path": str(self.snapshot),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "version_output_sha256": hashlib.sha256(
                b"fixture adb version"
            ).hexdigest(),
        }

    def one_serial(self):
        self._capture("adb-devices")
        self.serial_calls += 1
        if self.replace_serial and self.serial_calls > 1:
            return "REPLACED-S22"
        return self.serial

    def topology(self, serial: str):
        self._capture("adb-get-devpath")
        self.commanded_serials.append(serial)
        self.topology_calls += 1
        if self.replace_topology and self.topology_calls > 1:
            return "usb:9-9"
        return self.topology_value

    def properties(self, serial: str):
        self._capture("adb-read-only-shell-properties")
        self.commanded_serials.append(serial)
        boot_id = "22222222-2222-2222-2222-222222222222"
        if self.replace_boot and self.serial_calls > 1:
            boot_id = "33333333-3333-3333-3333-333333333333"
        return {
            "model": "SM-S906N",
            "device": "g0q",
            "bootloader": "fixture",
            "incremental": "S906NKSS7FYG8",
            "boot_completed": "1",
            "bootanim": "stopped",
            "verified_boot_state": self.health["verified_boot_state"],
            "boot_id": boot_id,
            "kernel_release": self.health["kernel_release"],
        }

    def root_health(self, serial: str):
        self._capture("adb-read-only-shell-root-health")
        self.commanded_serials.append(serial)
        return {
            "root": "uid=0(root) gid=0(root)",
            "boot": self.health["boot_sha256"],
            **self.health["supporting_partition_sha256"],
        }


class P319D0FreshBaselineV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d0 = load(SOURCE, "p319_d0_fresh_v3_test")
        cls.reducer = load(REDUCER_SOURCE, "p319_reducer_v3_test")

    def sandbox(self, *, pass_go: bool = False):
        temporary = tempfile.TemporaryDirectory(prefix="p319-d0-v3-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        parent = root / "d0-run-parent"
        run = parent / "d0-p319-fresh-baseline-3"
        arm = Path(str(run) + ".arm.json")
        stop = Path(str(run) + ".stop.json")
        observer = run / "baseline-observer.bin"
        receipt = run / "baseline-observer.capture.json"
        snapshot = root / "adb-snapshot"
        binding = root / "binding.json"
        patcher = mock.patch.multiple(
            self.d0,
            RUN_PARENT=parent,
            RUN_DIR=run,
            RUN_ARM=arm,
            RUN_STOP=stop,
            RESULT_PATH=run / "result.json",
            OBSERVER_PATH=observer,
            RAW_RECEIPT=receipt,
            RAW_ADB_DIR=run / "raw-adb",
            ADB_SNAPSHOT=snapshot,
            BINDING_MANIFEST=binding,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        payloads = {
            "reducer": self.d0.REDUCER.read_bytes(),
            "d1": self.d0.D1_SOURCE.read_bytes(),
            "d0": self.d0.D0_RUNTIME.read_bytes(),
            "profile": self.d0.PROFILE.read_bytes(),
        }
        candidate = self.d0._candidate_identity(
            self.d0.INTENT.read_bytes(), self.d0.QUALIFICATION.read_bytes()
        )
        design = self.d0._baseline_design(
            payloads["reducer"], payloads["d1"], payloads["d0"],
            payloads["profile"],
        )
        review = (
            {"status": "pass-go", "verdict": self.d0.REVIEW_VERDICT}
            if pass_go else {"status": "review-pending", "verdict": None}
        )
        value = self.d0._expected_manifest(
            script_payload=self.d0.SCRIPT.read_bytes(),
            reducer_payload=payloads["reducer"],
            d0_payload=payloads["d0"],
            raw_payload=self.d0.RAW_CAPTURE.read_bytes(),
            adapter_payloads=self.d0._adapter_payloads(),
            d1_payload=payloads["d1"],
            d1_binding_payload=self.d0.D1_BINDING.read_bytes(),
            profile_payload=payloads["profile"],
            adb_payload=self.d0.HOST_ADB.read_bytes(),
            candidate=candidate,
            design=design,
            review=review,
        )
        binding.write_bytes(self.d0.canonical(value))
        return root, value

    def static_execution(self, *, pass_go: bool = True):
        root, _ = self.sandbox(pass_go=pass_go)
        static = self.d0._validated_static_inputs()
        inputs = self.d0._validated_execution_inputs(static)
        return root, static, inputs

    def fake_health(self, inputs):
        expected = inputs["profile"]["start_health"]
        boot_id = "22222222-2222-2222-2222-222222222222"
        return {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": expected["verified_boot_state"],
            "root_verified": True,
            "boot_sha256": expected["boot_sha256"],
            "supporting_partition_sha256": expected[
                "supporting_partition_sha256"
            ],
            "odin_endpoint_absent": True,
            "kernel_release": "5.10.226-fixture",
            "boot_id_sha256": hashlib.sha256(boot_id.encode()).hexdigest(),
        }

    def fake_d1(self, inputs):
        serial = "FIXTURE-S22"
        topology = "usb:1-2.3"
        return {
            "receipt": {
                "path": self.d0._relative(self.d0.D1_RESULT),
                "size": 39594,
                "sha256": "a" * 64,
            },
            "after": self.fake_health(inputs),
            "selection": {
                "inventory_count": 1,
                "inventory_models": ["SM_S906N"],
                "inventory_sha256": "b" * 64,
                "selected_serial_sha256": hashlib.sha256(
                    serial.encode()
                ).hexdigest(),
                "selected_topology_sha256": hashlib.sha256(
                    topology.encode()
                ).hexdigest(),
                "other_targets_commanded": False,
            },
            "raw_evidence": {
                "schema": "s22plus_fyg8_p319_d1_fresh_baseline_v3_raw_inventory",
                "complete": True,
            },
        }

    def capture(self, *, payload: bytes | None = None, stderr: bytes = b"", rc: int = 0):
        payload = bytes(self.d0.RAW_SIZE) if payload is None else payload

        def factory(raw, _argv, run_dir):
            return raw.publish_captured_bytes(
                run_dir,
                "baseline-observer",
                stdout=payload,
                stderr=stderr,
                returncode=rc,
                stdout_name="baseline-observer.bin",
                stderr_name="baseline-observer.bin.stderr",
            )

        return factory

    def adapter(self):
        return types.SimpleNamespace(
            PROFILE="fixture-profile",
            classify_clean_baseline=lambda payload, **_kwargs: {
                "classification": "ZERO_AMBIGUOUS",
                "accepted": False,
                "records": [],
                "baseline_size": len(payload),
                "baseline_clean": True,
                "integrity_issue": False,
            },
        )

    def execute(self, inputs, d1, *, capture=None, client=None, adapter=None):
        health = d1["after"]
        client = client or FakeClient(None, None, self.d0.ADB_SNAPSHOT, health)
        self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
        return self.d0._execute(
            inputs,
            d1,
            client_factory=lambda module, raw, snapshot: (
                setattr(client, "module", module)
                or setattr(client, "raw", raw)
                or setattr(client, "snapshot", snapshot)
                or client
            ),
            capture_factory=capture or self.capture(),
            usb_factory=lambda _root, _download: {
                "enumerated_devices": 1,
                "download_endpoint_count": 0,
                "snapshot_sha256": hashlib.sha256(b"usb:0").hexdigest(),
            },
            adapter=adapter or self.adapter(),
        ), client

    def test_current_d1_v3_result_reopens_through_post_validate(self):
        _root, static, inputs = self.static_execution(pass_go=True)
        d1 = self.d0._load_d1_evidence(inputs)
        stored = json.loads(D1_RESULT.read_text(encoding="utf-8"))
        self.assertEqual(d1["result"], stored)
        self.assertEqual(d1["result"]["schema"], self.d0.D1_SOURCE.read_text().split(
            'RESULT_SCHEMA = "', 1
        )[1].split('"', 1)[0])
        self.assertTrue(d1["raw_evidence"]["complete"])
        self.assertEqual(len(d1["raw_evidence"]["handles"]), 30)
        self.assertEqual(static["manifest"]["independent_review"]["status"], "pass-go")

    def test_wrong_v2_path_and_predecessor_binding_are_rejected(self):
        _root, _static, inputs = self.static_execution(pass_go=True)
        value = json.loads(D1_RESULT.read_text(encoding="utf-8"))
        wrong_path = ROOT / (
            "workspace/private/runs/device-action-d1-p319-fresh-baseline-v2/"
            "p319-fresh-baseline-2/result.json"
        )
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.reducer._validate_d1(
                value,
                inputs["baseline_design"],
                inputs["candidate"],
                self.reducer._profile(),
                wrong_path,
            )
        self.assertNotEqual(
            self.d0.D1_BINDING.read_bytes(), V2_BINDING.read_bytes()
        )
        self.assertEqual(
            inputs["manifest"]["d1_dependency"]["canonical_validator"],
            "_post_validate",
        )

    def test_forged_d1_result_and_raw_evidence_are_rejected(self):
        _root, _static, inputs = self.static_execution(pass_go=True)
        value = json.loads(D1_RESULT.read_text(encoding="utf-8"))
        for mutation in ("after", "raw"):
            forged = copy.deepcopy(value)
            if mutation == "after":
                forged["after"]["boot_id_sha256"] = "0" * 64
            else:
                forged["raw_evidence"]["aggregate_sha256"] = "0" * 64
            with self.assertRaises(self.reducer.FreshBaselineError):
                self.reducer._validate_d1(
                    forged,
                    inputs["baseline_design"],
                    inputs["candidate"],
                    self.reducer._profile(),
                    self.reducer.DEFAULT_D1,
                )

    def test_v3_namespace_and_authority_are_distinct_from_v2(self):
        self.assertIn("d0-p319-fresh-baseline-v3", self.d0.RUN_PARENT.as_posix())
        self.assertIn("p319-fresh-baseline-3", self.d0.RUN_DIR.as_posix())
        self.assertTrue(self.d0.AUTHORITY_PREFIX.endswith("V3-APPROVE:"))
        self.assertTrue(self.d0.SCHEMA.endswith("_v3_result"))
        self.assertTrue(self.reducer.SCHEMA.endswith("_v3"))
        self.assertNotIn("v2", self.d0.BINDING_ID)

    def test_pending_review_and_wrong_approval_precede_any_acquisition(self):
        _root, _ = self.sandbox(pass_go=False)
        with mock.patch.object(
            self.d0, "_validated_execution_inputs", side_effect=AssertionError
        ), mock.patch.object(
            self.d0, "_load_d1_evidence", side_effect=AssertionError
        ), mock.patch.object(
            self.d0, "_durable_create", side_effect=AssertionError
        ):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live("anything")
        self.assertFalse(self.d0.RUN_ARM.exists())

        _root, _ = self.sandbox(pass_go=True)
        static = self.d0._validated_static_inputs()
        with mock.patch.object(
            self.d0, "_validated_execution_inputs", side_effect=AssertionError
        ), mock.patch.object(
            self.d0, "_durable_create", side_effect=AssertionError
        ):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live("wrong-approval")
        self.assertFalse(self.d0.RUN_ARM.exists())
        self.assertTrue(static["manifest"]["independent_review"]["status"] == "pass-go")

    def test_default_self_test_is_host_only_and_review_pending(self):
        with mock.patch("subprocess.Popen", side_effect=AssertionError("device call")):
            value = self.d0.self_test()
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["approval_created"])
        self.assertFalse(value["live_authorized"])
        self.assertEqual(value["review_status"], "review-pending")
        self.assertEqual(value["raw_bytes"], self.d0.RAW_SIZE)

    def test_clean_read_only_execution_reads_one_exact_observer_and_publishes_raw_first(self):
        _root, _static, inputs = self.static_execution(pass_go=True)
        d1 = self.fake_d1(inputs)
        result, client = self.execute(inputs, d1)
        self.assertEqual(result["observer"]["bytes"], self.d0.RAW_SIZE)
        self.assertTrue(result["observer"]["raw_first"])
        self.assertEqual(result["observer"]["stderr_bytes"], 0)
        self.assertTrue(result["candidate_marker_family_absent"])
        self.assertEqual(len(result["raw_adb"]["handles"]), 9)
        self.assertEqual(len(result["raw_adb"]["children"]), 27)
        self.assertEqual(set(client.commanded_serials), {"FIXTURE-S22"})
        self.assertEqual(result["binding"]["d1"]["raw_evidence"], d1["raw_evidence"])
        self.assertFalse(result["device_writes"])
        self.assertFalse(result["reboot_requested"])

    def test_observer_short_stderr_or_nonzero_stop_before_decode(self):
        for kwargs in (
            {"payload": bytes(self.d0.RAW_SIZE - 1)},
            {"stderr": b"unexpected"},
            {"rc": 1},
        ):
            with self.subTest(kwargs=kwargs):
                _root, _static, inputs = self.static_execution(pass_go=True)
                d1 = self.fake_d1(inputs)
                self.d0._durable_create(
                    self.d0.RUN_ARM, self.d0._arm_value(inputs)
                )
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0._execute(
                        inputs,
                        d1,
                        client_factory=lambda module, raw, snapshot: FakeClient(
                            module, raw, snapshot, d1["after"]
                        ),
                        capture_factory=self.capture(**kwargs),
                        usb_factory=lambda _root, _download: {
                            "enumerated_devices": 1,
                            "download_endpoint_count": 0,
                            "snapshot_sha256": hashlib.sha256(b"usb:0").hexdigest(),
                        },
                        adapter=self.adapter(),
                    )

    def test_target_or_download_change_fails_closed(self):
        for mutation in ("serial", "topology", "boot"):
            with self.subTest(mutation=mutation):
                _root, _static, inputs = self.static_execution(pass_go=True)
                d1 = self.fake_d1(inputs)
                client = FakeClient(None, None, self.d0.ADB_SNAPSHOT, d1["after"])
                setattr(client, "replace_" + mutation, True)
                self.d0._durable_create(
                    self.d0.RUN_ARM, self.d0._arm_value(inputs)
                )
                with self.assertRaises(self.d0.D0FreshBaselineError):
                    self.d0._execute(
                        inputs,
                        d1,
                        client_factory=lambda module, raw, snapshot: (
                            setattr(client, "module", module)
                            or setattr(client, "raw", raw)
                            or setattr(client, "snapshot", snapshot)
                            or client
                        ),
                        capture_factory=self.capture(),
                        usb_factory=lambda _root, _download: {
                            "enumerated_devices": 1,
                            "download_endpoint_count": 0,
                            "snapshot_sha256": hashlib.sha256(b"usb:0").hexdigest(),
                        },
                        adapter=self.adapter(),
                    )

    def test_durable_arm_is_canonical_and_readable_in_fresh_process(self):
        root, _static, inputs = self.static_execution(pass_go=True)
        arm = root / "durable.arm.json"
        value = self.d0._arm_value(inputs)
        self.d0._durable_create(arm, value)
        code = (
            "import json,sys; p=sys.argv[1]; v=json.load(open(p)); "
            "assert v['consumed'] is True and v['attempt'] == 1; "
            "print('durable-ok')"
        )
        completed = subprocess.run(
            ["python3", "-c", code, str(arm)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), "durable-ok")
        self.assertEqual(arm.stat().st_mode & 0o777, 0o400)
        self.assertEqual(arm.stat().st_nlink, 1)

    def test_existing_arm_is_consumed_and_never_replays(self):
        _root, _static, inputs = self.static_execution(pass_go=True)
        self.d0._durable_create(self.d0.RUN_ARM, self.d0._arm_value(inputs))
        with mock.patch.object(self.d0, "_execute", side_effect=AssertionError):
            with self.assertRaises(self.d0.D0FreshBaselineError):
                self.d0.run_live(inputs["authority"])
        stop = json.loads(self.d0.RUN_STOP.read_text(encoding="utf-8"))
        self.assertTrue(stop["consumed"])
        self.assertFalse(stop["replay_authorized"])


if __name__ == "__main__":
    unittest.main()
