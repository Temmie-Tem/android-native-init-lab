import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_f1_backend_h0.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_f1_backend_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class FakeIntegration:
    STATUS = "H0_CONSUMER_INTEGRATION_PASS_GO_NOT_ACTIVE"
    INTEGRATION_ACTIVE = False

    @staticmethod
    def binding_sha256():
        return "2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6"

    @staticmethod
    def load_journal():
        return object()

    @staticmethod
    def _endpoint(_journal, value, _label):
        return value


class FakeBootstrap:
    ADB = Path("/fixed/adb")
    ANDROID_TIMEOUT = 420

    def __init__(self):
        self.calls = []
        self.identity = {
            "serial_sha256": "a" * 64,
            "topology_sha256": self.hash_text("usb:1-2"),
            "boot_id_sha256": "1" * 64,
        }
        self.selected = {"serial": "PRIVATE_SERIAL"}
        self.endpoint = {
            "device": "/dev/bus/usb/001/002",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": self.hash_text("/dev/bus/usb/001/002"),
            "topology_sha256": "e" * 64,
            "usb": {
                "idVendor": "04e8",
                "idProduct": "685d",
                "product": "SM8250",
                "manufacturer": "Samsung",
                "serial_absent": True,
            },
        }
        self.listing = [self.endpoint["device"]]
        self.listing_sha256 = "9" * 64
        self.repeat_listing_sha256 = self.listing_sha256
        self.odin_calls = []

    @staticmethod
    def hash_text(value):
        import hashlib

        return hashlib.sha256(value.encode()).hexdigest()

    def bounded_command(self, argv, timeout, maximum):
        self.calls.append((tuple(argv), timeout, maximum))
        if argv[-1] == "get-devpath":
            return 0, b"usb:1-2\n", b""
        if argv[-2:] == ["reboot", "download"]:
            return 0, b"", b""
        raise AssertionError(f"unexpected command: {argv}")

    def android_health_once(self, command, adb):
        self.calls.append(("android-health", command, adb))
        return self.selected, {"boot_completed": "1"}, dict(self.identity)

    def root_observation(self, command, adb, identity, timeout):
        self.calls.append(("root", command, adb, identity, timeout))
        return {"root_verified": True, "attempts": 1, "output_sha256": "7" * 64}

    def download_baseline(self, command):
        self.calls.append(("baseline", command))
        return {"empty": True}

    @staticmethod
    def canonical_sha(_value):
        return "2" * 64

    def enumerate_download(self, command):
        self.calls.append(("enumerate", command))
        count = sum(call[0] == "enumerate" for call in self.calls if isinstance(call, tuple))
        sha = self.listing_sha256 if count % 2 else self.repeat_listing_sha256
        return list(self.listing), sha

    def identify_download(self, command):
        self.calls.append(("identify", command))
        return dict(self.endpoint)

    @staticmethod
    def validate_download_endpoint_record(value, _label):
        return value

    def execute_odin_exact(self, path, size, sha256, kind, endpoint):
        self.odin_calls.append((path, size, sha256, kind, endpoint))
        return {"returncode": 0}, b"ODIN_OK", b""

    @staticmethod
    def persisted_transfer_classification(_receipt, _stdout, _stderr):
        return "odin_transfer_completed"

    def wait_android(self, command, adb, timeout):
        self.calls.append(("wait-android", command, adb, timeout))
        final = dict(self.identity)
        final["boot_id_sha256"] = "5" * 64
        return self.selected, {"boot_completed": "1"}, final


class FakeObserver:
    ARRIVAL_TIMEOUT_SEC = 180
    POLL_INTERVAL_SEC = 0.05
    RECEIPT_SCHEMA = "s20plus_g986n_n3u0_usb_receipt_v1"
    SCHEMA = "s20plus_g986n_n3u0_usb_observer_v1"
    BANNER = b"S20PLUS_N3U0_ACM_V1\n"

    def __init__(self):
        self.baselines = []

    def capture_baseline(self, node):
        self.baselines.append(node)
        return {"node": node, "candidate_absent": True}

    @staticmethod
    def _digest(value):
        import hashlib
        import json

        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def _hash_text(value):
        import hashlib

        return hashlib.sha256(value.encode()).hexdigest()


class FakeOwner:
    CANDIDATE_AP = Path("/fixed/candidate/AP.tar.md5")
    CANDIDATE_AP_SIZE = 101
    CANDIDATE_AP_SHA256 = "c" * 64
    CANDIDATE_MEMBER_SIZE = 91
    CANDIDATE_MEMBER_SHA256 = "d" * 64
    ROLLBACK_AP = Path("/fixed/rollback/AP.tar.md5")
    ROLLBACK_AP_SIZE = 102
    ROLLBACK_AP_SHA256 = "e" * 64
    ROLLBACK_MEMBER_SIZE = 92
    ROLLBACK_MEMBER_SHA256 = "f" * 64

    def __init__(self):
        self.audits = []

    def audit_boot_only_ap(self, path, **keywords):
        self.audits.append((path, keywords))
        return {"path": str(path)}


class S20PlusN3U0AttendedF1BackendH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def setUp(self):
        self.bootstrap = FakeBootstrap()
        self.observer = FakeObserver()
        self.owner = FakeOwner()
        self.sources = {
            "integration": FakeIntegration(),
            "bootstrap": self.bootstrap,
            "observer": self.observer,
            "owner": self.owner,
        }
        self.source_patch = mock.patch.object(
            self.module, "load_sources", return_value=self.sources
        )
        self.source_patch.start()
        self.backend = self.module.FixedBackend()
        self.active = mock.patch.object(self.module, "BACKEND_ACTIVE", True)

    def tearDown(self):
        self.source_patch.stop()

    def public_endpoint(self):
        return self.module._public_endpoint(
            self.sources["integration"], self.bootstrap, self.bootstrap.endpoint
        )

    def test_plan_is_dormant_and_exposes_no_backend(self):
        plan = self.module.render_plan()
        self.assertEqual(
            plan["status"], "H0_CONCRETE_BACKEND_PASS_GO_NOT_ACTIVE"
        )
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["backend_exposed"])
        self.assertFalse(plan["raw_evidence_durable"])
        self.assertFalse(plan["physical_entry_bridge"])
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])

    def test_unmocked_render_plan_loads_exact_dataclass_sources(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"active": false', completed.stdout)
        self.assertIn('"backend_exposed": false', completed.stdout)

    def test_transitive_bootstrap_imports_ignore_ambient_modules(self):
        fake_classifier = types.ModuleType("device_action_f1_v2")
        fake_classifier.classify_odin_output = lambda *_args: "forged"
        fake_transport = types.ModuleType("s22plus_boot_only_f1_transport")
        fake_transport.forged = True
        fake_inventory = types.ModuleType("s20plus_g986n_d0_inventory")
        fake_inventory.forged = True
        fake_routine = types.ModuleType("s20plus_g986n_routine_d0")
        fake_routine.forged = True
        fake_raw_capture = types.ModuleType("device_action_raw_capture_v1")
        fake_raw_capture.forged = True
        ambient = {
            "device_action_f1_v2": fake_classifier,
            "s22plus_boot_only_f1_transport": fake_transport,
            "s20plus_g986n_d0_inventory": fake_inventory,
            "s20plus_g986n_routine_d0": fake_routine,
            "device_action_raw_capture_v1": fake_raw_capture,
        }
        self.source_patch.stop()
        try:
            with mock.patch.dict(sys.modules, ambient, clear=False):
                sources = self.module.load_sources()
            self.assertIs(sources["bootstrap"].f1_core, sources["classifier"])
            self.assertIs(sources["bootstrap"].transport, sources["transport"])
            self.assertIs(sources["bootstrap"].base, sources["inventory"])
            self.assertIs(sources["bootstrap"].routine, sources["routine"])
            self.assertIs(sources["transport"].boot_verify, sources["boot_verify"])
            self.assertIs(sources["transport"].raw_capture, sources["raw_capture"])
            self.assertEqual(
                sources["classifier"].classify_odin_output(
                    1, b"Fail parse", b""
                ),
                "odin_local_parse_failure",
            )
        finally:
            self.source_patch.start()

    def test_every_primitive_is_dormant_before_command(self):
        calls = [
            lambda: self.backend.preflight(),
            lambda: self.backend.download_baseline("physical"),
            lambda: self.backend.reboot_download("initial", self.bootstrap.identity),
            lambda: self.backend.observe_download("initial"),
            lambda: self.backend.transfer_boot("candidate", self.public_endpoint()),
            lambda: self.backend.observe_candidate(),
            lambda: self.backend.physical_download_entry(),
            lambda: self.backend.final_resident_health(),
        ]
        for operation in calls:
            with self.assertRaisesRegex(self.module.BackendError, "not active"):
                operation()
        self.assertEqual(self.bootstrap.calls, [])
        self.assertEqual(self.bootstrap.odin_calls, [])

    def test_candidate_observer_helper_is_dormant_before_endpoint_open(self):
        observer = mock.Mock()
        with self.assertRaisesRegex(self.module.BackendError, "not active"):
            self.module._observe_candidate_fixed(observer, {"empty": True}, "1-2")
        observer.assert_not_called()
        self.assertEqual(observer.mock_calls, [])

    def test_preflight_binds_root_identity_devpath_and_empty_download(self):
        with self.active:
            receipt = self.backend.preflight()
        self.assertEqual(receipt["identity"], self.bootstrap.identity)
        self.assertEqual(receipt["empty_download_baseline_sha256"], "2" * 64)
        self.assertEqual(self.backend.expected_usb_node, "1-2")
        self.assertIn(
            (("/fixed/adb", "-s", "PRIVATE_SERIAL", "get-devpath"), 10, 65536),
            self.bootstrap.calls,
        )

    def test_preflight_rejects_devpath_identity_drift(self):
        self.bootstrap.identity["topology_sha256"] = "0" * 64
        with self.active, self.assertRaisesRegex(self.module.BackendError, "devpath differs"):
            self.backend.preflight()

    def test_reboot_revalidates_source_and_uses_fixed_adb_shape(self):
        with self.active:
            result = self.backend.reboot_download("initial", self.bootstrap.identity)
        self.assertEqual(result["outcome"], "dispatched")
        self.assertIn(
            (("/fixed/adb", "-s", "PRIVATE_SERIAL", "reboot", "download"), 20, 65536),
            self.bootstrap.calls,
        )

        before = len(self.bootstrap.calls)
        foreign = dict(self.bootstrap.identity)
        foreign["boot_id_sha256"] = "8" * 64
        with self.active, self.assertRaisesRegex(self.module.BackendError, "source identity"):
            self.backend.reboot_download("rollback", foreign)
        self.assertFalse(
            any(
                isinstance(call[0], tuple) and call[0][-2:] == ("reboot", "download")
                for call in self.bootstrap.calls[before:]
                if isinstance(call, tuple)
            )
        )

    def test_download_observation_requires_stable_listing_and_endpoint(self):
        with self.active:
            receipt = self.backend.observe_download("candidate")
        self.assertEqual(receipt["endpoint"], self.public_endpoint())
        self.bootstrap.repeat_listing_sha256 = "8" * 64
        with self.active, self.assertRaisesRegex(self.module.BackendError, "listing changed"):
            self.backend.observe_download("candidate")

    def test_candidate_transfer_uses_fixed_artifact_endpoint_and_observer_baseline(self):
        self.backend.expected_usb_node = "1-2"
        endpoint = self.public_endpoint()
        with self.active:
            result = self.backend.transfer_boot("candidate", endpoint)
        self.assertEqual(result["classification"], "odin_transfer_completed")
        self.assertEqual(self.observer.baselines, ["1-2"])
        self.assertEqual(self.owner.audits[0][0], self.owner.CANDIDATE_AP)
        self.assertEqual(
            self.bootstrap.odin_calls[0],
            (
                self.owner.CANDIDATE_AP,
                self.owner.CANDIDATE_AP_SIZE,
                self.owner.CANDIDATE_AP_SHA256,
                "candidate",
                self.bootstrap.endpoint,
            ),
        )

    def test_foreign_endpoint_blocks_audit_and_odin(self):
        self.backend.expected_usb_node = "1-2"
        endpoint = self.public_endpoint()
        endpoint["path_sha256"] = "8" * 64
        with self.active, self.assertRaisesRegex(self.module.BackendError, "durable intent"):
            self.backend.transfer_boot("candidate", endpoint)
        self.assertEqual(self.owner.audits, [])
        self.assertEqual(self.bootstrap.odin_calls, [])
        self.assertEqual(self.observer.baselines, [])

    def test_rollback_transfer_uses_only_resident_artifact(self):
        with self.active:
            self.backend.transfer_boot("rollback", self.public_endpoint())
        self.assertEqual(self.owner.audits[0][0], self.owner.ROLLBACK_AP)
        self.assertEqual(self.bootstrap.odin_calls[0][0], self.owner.ROLLBACK_AP)
        self.assertEqual(self.observer.baselines, [])

    def test_local_parse_classification_maps_to_journal_grammar(self):
        self.bootstrap.persisted_transfer_classification = (
            lambda _receipt, _stdout, _stderr: "odin_local_parse_failure"
        )
        with self.active:
            result = self.backend.transfer_boot("rollback", self.public_endpoint())
        self.assertEqual(result["classification"], "local_parse_failure")

    def test_candidate_observer_requires_prebound_baseline(self):
        with self.active, self.assertRaisesRegex(self.module.BackendError, "baseline is absent"):
            self.backend.observe_candidate()
        self.backend.expected_usb_node = "1-2"
        self.backend.candidate_baseline = {"candidate_absent": True}
        exact = {
            "schema": self.observer.RECEIPT_SCHEMA,
            "observer_schema": self.observer.SCHEMA,
            "baseline_sha256": self.observer._digest(
                self.backend.candidate_baseline
            ),
            "expected_topology_sha256": self.observer._hash_text("1-2"),
            "endpoint_identity_sha256": "a" * 64,
            "accepted": True,
            "exact": True,
            "banner_sha256": __import__("hashlib").sha256(
                self.observer.BANNER
            ).hexdigest(),
            "banner_size": len(self.observer.BANNER),
            "tty_number_stable": False,
        }
        with mock.patch.object(
            self.module, "_observe_candidate_fixed", return_value=exact
        ):
            with self.active:
                result = self.backend.observe_candidate()
        self.assertEqual(result, {"banner_accepted": True, "android_identity": None})
        self.assertEqual(self.backend.last_full_receipt, exact)

    def test_final_health_requires_exact_root_and_returns_fixed_schema(self):
        with self.active:
            receipt = self.backend.final_resident_health()
        self.assertEqual(receipt["identity"]["boot_id_sha256"], "5" * 64)
        self.assertTrue(receipt["exact_target_healthy"])
        self.assertTrue(receipt["root_verified"])
        self.assertEqual(receipt["root_attempts"], 1)

    def test_physical_bridge_is_explicitly_unimplemented(self):
        before = list(self.bootstrap.calls)
        with self.active, self.assertRaisesRegex(self.module.BackendError, "not implemented"):
            self.backend.physical_download_entry()
        self.assertEqual(self.bootstrap.calls, before)

    def test_source_drift_rejects_binding(self):
        changed = dict(self.module.SOURCES["observer"])
        changed["sha256"] = "0" * 64
        with mock.patch.dict(self.module.SOURCES, {"observer": changed}, clear=False):
            with self.assertRaisesRegex(self.module.BackendError, "hash differs"):
                self.module.source_receipts()


if __name__ == "__main__":
    unittest.main()
