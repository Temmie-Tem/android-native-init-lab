import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_baseline_rotation_d1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_baseline_rotation_d1", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.18 D1 adapter import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTopologyClient:
    def __init__(self, topologies):
        self.topologies = iter(topologies)
        self.calls = 0

    def topology(self, _serial):
        self.calls += 1
        return next(self.topologies)


class P318BaselineRotationD1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    @staticmethod
    def rows(serial="EXACT_S22", transport_id="2"):
        return [
            (
                "OTHER_TARGET",
                "device",
                {"model:SM_G986N", "device:y2q", "transport_id:1"},
            ),
            (
                serial,
                "device",
                {
                    "model:SM_S906N",
                    "device:g0q",
                    f"transport_id:{transport_id}",
                },
            ),
        ]

    def target(self, serial="EXACT_S22"):
        return {
            "model": "SM-S906N",
            "device": "g0q",
            "firmware_incremental": "S906NKSS7FYG8",
            "adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
        }

    def test_pinned_inputs_are_exact_and_historical_topology_is_not_authority(self):
        (
            base,
            d0_runtime,
            binding,
            prior,
            profile,
            authority,
            adb_payload,
        ) = self.module._validate_inputs()
        self.assertEqual(len(base), self.module.BASE_SIZE)
        self.assertEqual(hashlib.sha256(base).hexdigest(), self.module.BASE_SHA256)
        self.assertEqual(len(d0_runtime), self.module.D0_RUNTIME_SIZE)
        self.assertEqual(
            hashlib.sha256(d0_runtime).hexdigest(), self.module.D0_RUNTIME_SHA256
        )
        self.assertEqual(
            binding["ready_manifest"]["sha256"], self.module.MANIFEST_SHA256
        )
        self.assertEqual(
            binding["historical_d0_identity_health"]["sha256"],
            self.module.HISTORICAL_D0_SHA256,
        )
        self.assertEqual(binding["host_adb"]["sha256"], self.module.ADB_SHA256)
        self.assertEqual(
            binding["pinned_d0_runtime_source"]["sha256"],
            self.module.D0_RUNTIME_SHA256,
        )
        self.assertEqual(len(adb_payload), self.module.ADB_SIZE)
        self.assertEqual(
            binding["host_adb_execution_snapshot"]["mode"], "0500"
        )
        self.assertFalse(binding["historical_topology_is_current_authority"])
        self.assertTrue(binding["live_exact_serial_identity_required"])
        self.assertTrue(binding["live_topology_continuity_required"])
        self.assertEqual(
            binding["run_directory"]["path"],
            str(self.module.RUN_DIR.relative_to(self.module.ROOT)),
        )
        self.assertEqual(
            binding["run_approval_arm"]["path"],
            str(self.module.RUN_ARM.relative_to(self.module.ROOT)),
        )
        self.assertNotIn("usb_topology_sha256", prior["target"])
        self.assertEqual(profile["profile_id"], "s22plus-fyg8")
        self.assertEqual(binding["independent_review"]["status"], "pass-go")
        self.assertEqual(
            binding["independent_review"]["verdict"],
            "PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1",
        )
        self.assertTrue(authority.startswith(self.module.AUTHORITY_PREFIX))
        self.assertEqual(
            authority.removeprefix(self.module.AUTHORITY_PREFIX),
            binding["binding_manifest"]["sha256"],
        )
        self.assertFalse(binding["payload"])
        self.assertFalse(binding["odin"])
        self.assertFalse(binding["download_transition"])
        self.assertFalse(binding["f1_authorized"])

    def test_current_topology_can_differ_from_history_but_cannot_drift_in_run(self):
        serial = "EXACT_S22"
        target = self.target(serial)
        selected, topology_sha, selection = self.module._select_current_topology(
            self.rows(serial), target, "usb:3-1.3", None, None
        )
        self.assertEqual(selected, serial)
        self.assertEqual(
            topology_sha, hashlib.sha256(b"usb:3-1.3").hexdigest()
        )
        self.assertEqual(selection["inventory_models"], ["SM_G986N", "SM_S906N"])
        self.assertFalse(selection["other_targets_commanded"])
        with self.assertRaisesRegex(
            self.module.AdapterError, "topology changed during D1"
        ):
            self.module._select_current_topology(
                self.rows(serial), target, "usb:2-1.3", serial, topology_sha
            )

    def test_wrong_serial_and_multiple_s22_candidates_fail_before_topology_read(self):
        base, d0_runtime, _binding, prior, _profile, authority, _adb = (
            self.module._validate_inputs()
        )
        pinned = self.module._load_base(base, d0_runtime, authority)
        transport = pinned.RealTransport.__new__(pinned.RealTransport)
        transport.binding = prior
        transport.selected = None
        transport.current_topology_sha256 = None
        transport._inventory = lambda: self.rows("WRONG_S22")
        transport.client = FakeTopologyClient(["usb:3-1.3"])
        with self.assertRaisesRegex(pinned.RotationError, "serial identity differs"):
            transport.select_exact()
        self.assertEqual(transport.client.calls, 0)

        transport._inventory = lambda: self.rows("WRONG_S22") + [
            (
                "SECOND_S22",
                "device",
                {"model:SM_S906N", "device:g0q", "transport_id:3"},
            )
        ]
        with self.assertRaisesRegex(pinned.RotationError, "found 2"):
            transport.select_exact()
        self.assertEqual(transport.client.calls, 0)

    def test_live_transport_allows_ephemeral_transport_id_rotation(self):
        base, d0_runtime, _binding, prior, _profile, authority, _adb = (
            self.module._validate_inputs()
        )
        pinned = self.module._load_base(base, d0_runtime, authority)
        serial = "EXACT_S22"
        prior["target"]["adb_serial_sha256"] = hashlib.sha256(
            serial.encode()
        ).hexdigest()
        transport = pinned.RealTransport.__new__(pinned.RealTransport)
        transport.binding = prior
        transport.selected = None
        transport.current_topology_sha256 = None
        inventories = iter((self.rows(serial, "2"), self.rows(serial, "3")))
        transport._inventory = lambda: next(inventories)
        transport.client = FakeTopologyClient(["usb:3-1.3", "usb:3-1.3"])
        first_serial, first = transport.select_exact()
        second_serial, second = transport.select_exact()
        self.assertEqual(first_serial, serial)
        self.assertEqual(second_serial, serial)
        self.assertEqual(first, second)
        self.assertEqual(transport.client.calls, 2)

    def test_inventory_digest_detects_same_count_and_model_replacement(self):
        serial = "EXACT_S22"
        target = self.target(serial)
        _selected, _topology, first = self.module._select_current_topology(
            self.rows(serial), target, "usb:3-1.3", None, None
        )
        replaced = [
            (
                "DIFFERENT_OTHER_TARGET",
                "device",
                {"model:SM_G986N", "device:y2q", "transport_id:1"},
            ),
            self.rows(serial)[1],
        ]
        _selected, _topology, second = self.module._select_current_topology(
            replaced, target, "usb:3-1.3", None, None
        )
        self.assertEqual(first["inventory_count"], second["inventory_count"])
        self.assertEqual(first["inventory_models"], second["inventory_models"])
        self.assertNotEqual(first["inventory_sha256"], second["inventory_sha256"])

    def test_transport_id_ephemeral_grammar_is_exact_ascii_singleton(self):
        serial = "EXACT_S22"
        target = self.target(serial)
        for label, token_set in (
            ("missing", set()),
            ("malformed", {"transport_id:abc"}),
            ("unicode-wide", {"transport_id:２"}),
            ("unicode-superscript", {"transport_id:²"}),
            ("multiple", {"transport_id:2", "transport_id:3"}),
        ):
            rows = self.rows(serial)
            rows[0] = (
                rows[0][0],
                rows[0][1],
                {
                    item
                    for item in rows[0][2]
                    if not item.startswith("transport_id:")
                }
                | token_set,
            )
            with (
                self.subTest(label=label),
                self.assertRaisesRegex(
                    self.module.AdapterError, "transport_id"
                ),
            ):
                self.module._select_current_topology(
                    rows, target, "usb:3-1.3", None, None
                )

    def test_health_snapshot_topology_must_match_selection(self):
        base, d0_runtime, _binding, prior, _profile, authority, _adb = (
            self.module._validate_inputs()
        )
        pinned = self.module._load_base(base, d0_runtime, authority)
        transport = pinned.RealTransport.__new__(pinned.RealTransport)
        transport.binding = prior
        transport.selected = "EXACT_S22"
        transport.current_topology_sha256 = hashlib.sha256(b"usb:3-1.3").hexdigest()
        inherited = pinned.RealTransport.__mro__[1]
        with (
            mock.patch.object(
                inherited, "snapshot", return_value={"topology": "usb:2-1.3"}
            ),
            self.assertRaisesRegex(
                pinned.RotationError, "topology changed during health snapshot"
            ),
        ):
            transport.snapshot("EXACT_S22")

    def test_verified_d0_runtime_ignores_ambient_local_module_injection(self):
        base, d0_runtime, _binding, _prior, _profile, authority, _adb = (
            self.module._validate_inputs()
        )
        fake_d0 = types.ModuleType("device_action_d0_v2")
        fake_f1 = types.ModuleType("device_action_f1_v2")
        with mock.patch.dict(
            sys.modules,
            {
                "device_action_d0_v2": fake_d0,
                "device_action_f1_v2": fake_f1,
            },
        ):
            pinned = self.module._load_base(base, d0_runtime, authority)
            self.assertIsNot(pinned.d0, fake_d0)
            self.assertEqual(pinned.d0.__file__, str(self.module.D0_RUNTIME))
            self.assertIs(sys.modules["device_action_d0_v2"], fake_d0)
            self.assertIs(sys.modules["device_action_f1_v2"], fake_f1)

    def test_fixture_runs_one_reboot_without_device_contact(self):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--self-test"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(
            receipt["verdict"], "PASS_P318_D1_BASELINE_ROTATION_FIXTURE_H0"
        )
        self.assertEqual(receipt["reboot_count"], 1)
        self.assertEqual(receipt["other_target_commands"], 0)
        self.assertFalse(receipt["device_contact"])
        self.assertFalse(receipt["live_authorized"])
        self.assertEqual(
            receipt["p318_adapter_binding"]["binding_manifest"]["sha256"],
            hashlib.sha256(self.module.BINDING_MANIFEST.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            receipt["p318_adapter_binding"]["independent_review"]["status"],
            "pass-go",
        )

    def test_adb_execution_snapshot_is_exact_no_replace_and_executable(self):
        *_prefix, adb_payload = self.module._validate_inputs()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "owned" / "adb-snapshot"
            self.module._prepare_executable_snapshot(adb_payload, destination)
            metadata = destination.stat()
            self.assertEqual(metadata.st_mode & 0o777, 0o500)
            self.assertEqual(metadata.st_nlink, 1)
            self.assertEqual(destination.read_bytes(), adb_payload)
            self.module._prepare_executable_snapshot(adb_payload, destination)
            destination.chmod(0o400)
            with self.assertRaisesRegex(self.module.AdapterError, "metadata differs"):
                self.module._prepare_executable_snapshot(adb_payload, destination)

    def test_approval_arm_is_exact_durable_and_no_replace(self):
        value = {
            "schema": "fixture-arm-v1",
            "approval_sha256": "a" * 64,
            "device_contact_before_arm": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            arm = Path(temporary) / "owned" / "run.arm.json"
            prior_umask = os.umask(0o777)
            try:
                self.module._durable_arm(arm, value)
            finally:
                os.umask(prior_umask)
            metadata = arm.stat()
            self.assertEqual(metadata.st_mode & 0o777, 0o400)
            self.assertEqual(metadata.st_nlink, 1)
            self.assertEqual(json.loads(arm.read_bytes()), value)
            with self.assertRaisesRegex(
                self.module.AdapterError, "approval arm already exists"
            ):
                self.module._durable_arm(arm, value)

    def test_pending_review_rejects_live_before_run_directory_or_device(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "must-not-exist"
            value = json.loads(self.module.BINDING_MANIFEST.read_text())
            value["independent_review"] = {
                "status": "review-pending",
                "verdict": None,
            }
            changed = root / "binding.json"
            changed.write_text(json.dumps(value), encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch.object(self.module, "BINDING_MANIFEST", changed),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                rc = self.module.main(
                    [
                        "--live",
                        "--approval",
                        "WRONG",
                        "--run-dir",
                        str(run_dir),
                    ]
                )
            self.assertEqual(rc, 2)
            self.assertFalse(run_dir.exists())
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("independent D1 adapter review is absent", stderr.getvalue())

    def test_binding_manifest_adapter_mutation_is_rejected(self):
        value = json.loads(self.module.BINDING_MANIFEST.read_text())
        value["inputs"]["adapter"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "binding.json"
            changed.write_text(json.dumps(value), encoding="utf-8")
            with (
                mock.patch.object(self.module, "BINDING_MANIFEST", changed),
                self.assertRaisesRegex(
                    self.module.AdapterError, "pinned input semantics differ"
                ),
            ):
                self.module._validate_inputs()

    def test_binding_manifest_requires_exact_types_shape_and_finite_json(self):
        value = json.loads(self.module.BINDING_MANIFEST.read_text())
        mutations = (
            ("bool-command-count", {**value, "command_count": True}),
            ("extra-key", {**value, "unreviewed": False}),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, mutation in mutations:
                with self.subTest(name=name):
                    changed = root / f"{name}.json"
                    changed.write_text(json.dumps(mutation), encoding="utf-8")
                    with (
                        mock.patch.object(self.module, "BINDING_MANIFEST", changed),
                        self.assertRaisesRegex(
                            self.module.AdapterError, "pinned input semantics differ"
                        ),
                    ):
                        self.module._validate_inputs()
            nonfinite = root / "nonfinite.json"
            nonfinite.write_bytes(
                self.module.BINDING_MANIFEST.read_bytes().replace(
                    b'"command_count": 1', b'"command_count": NaN'
                )
            )
            with (
                mock.patch.object(self.module, "BINDING_MANIFEST", nonfinite),
                self.assertRaisesRegex(self.module.AdapterError, "non-finite JSON"),
            ):
                self.module._validate_inputs()

    def test_pass_go_manifest_still_rejects_wrong_approval_and_caller_adb(self):
        value = json.loads(self.module.BINDING_MANIFEST.read_text())
        value["independent_review"] = {
            "status": "pass-go",
            "verdict": "PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            changed = root / "binding.json"
            changed.write_text(json.dumps(value), encoding="utf-8")
            with mock.patch.object(self.module, "BINDING_MANIFEST", changed):
                *_inputs, authority, _adb = self.module._validate_inputs()
                for arguments, message in (
                    (
                        [
                            "--live",
                            "--approval",
                            "WRONG",
                        ],
                        "live D1 accepts only the exact approval",
                    ),
                    (
                        [
                            "--live",
                            "--approval",
                            authority,
                            "--adb",
                            str(self.module.ADB),
                        ],
                        "caller paths are forbidden",
                    ),
                    (
                        [
                            "--live",
                            "--approval",
                            authority,
                            "--run-dir",
                            str(self.module.RUN_DIR / "../../../../../../tmp/escape"),
                        ],
                        "caller paths are forbidden",
                    ),
                ):
                    with self.subTest(message=message):
                        stdout = io.StringIO()
                        stderr = io.StringIO()
                        with redirect_stdout(stdout), redirect_stderr(stderr):
                            rc = self.module.main(arguments)
                        self.assertEqual(rc, 2)
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertIn(message, stderr.getvalue())
                self.assertFalse(self.module.RUN_DIR.exists())

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaisesRegex(self.module.AdapterError, "duplicate key"):
            self.module._decode_object(b'{"a":1,"a":2}', "fixture")


if __name__ == "__main__":
    unittest.main()
