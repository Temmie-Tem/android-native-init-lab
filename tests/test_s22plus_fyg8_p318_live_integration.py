import hashlib
import json
import sys
import types
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tests import test_device_action_f1_live_v2 as live_tests


SCRIPT_DIR = (
    live_tests.ROOT / "workspace/public/src/scripts/revalidation"
)
sys.path.insert(0, str(SCRIPT_DIR))


class P318LiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = live_tests.load_module()
        import s22plus_fyg8_p318_process_v2_adapter_fixture as adapter

        cls.adapter = adapter

    def prepared(self):
        temporary, prepared = live_tests.DeviceActionF1LiveV2Test.prepared(
            self, e3=True
        )
        self.addCleanup(temporary.cleanup)
        prepared.bundle.manifest["observation"]["acceptance"] = (
            self.adapter._acceptance()  # noqa: SLF001
        )
        return prepared

    def start_endpoint(self, prepared, phase="download_start"):
        download = prepared.bundle.profile["target"]["download"]
        return self.module.p318_topology._endpoint_row(  # noqa: SLF001
            mode="download",
            identity={
                "vendor": download["usb_vendor_id"],
                "product_id": download["usb_product_id"],
                "product": download["product"],
                "manufacturer": download["manufacturer"],
                "serial": "",
                "driver": "",
                "interface": "",
                "tty_name": "",
                "endpoint_node": "/dev/bus/usb/001/002",
            },
            topology="1-1",
            controller_path="/controller0",
            usb_device_path="/controller0/usb1/1-1",
        )

    def publish_start(self, prepared):
        endpoint = self.start_endpoint(prepared)
        raw = self.module.p318_topology.raw_snapshot(
            phase="download_start", capture_complete=True, endpoints=[endpoint]
        )
        record = self.module._p318_publish_or_reopen_phase(
            prepared,
            "download_start",
            raw,
            target_identity=self.module._p318_download_target(prepared),
            binding_id_sha256=prepared.binding_sha256,
            comparison_binding_id_sha256=prepared.binding_sha256,
            authority_state="candidate_approved_exact",
            causal_terminal_ready=False,
            start_path=None,
        )
        return endpoint, record

    def candidate_endpoint(self, prepared):
        spec = prepared.bundle.manifest["observation"]["candidate_observer"]
        return self.module.p318_topology._endpoint_row(  # noqa: SLF001
            mode="candidate",
            identity={
                "vendor": spec["usb_vendor_id"],
                "product_id": spec["usb_product_id"],
                "product": "S22+ E3 ACM",
                "manufacturer": "Android Native Init Lab",
                "serial": spec["usb_serial"],
                "driver": spec["usb_driver"],
                "interface": spec["usb_interface_number"],
                "tty_name": "ttyACM0",
                "endpoint_node": "/dev/ttyACM0",
            },
            topology="1-1",
            controller_path="/controller0",
            usb_device_path="/controller0/usb1/1-1",
        )

    def publish_observer(self, prepared, classification, endpoint_sha=None):
        observer = live_tests.FakeCandidateObserver(
            self.module, prepared, classification
        )
        observer.observe(
            timeout_sec=1,
            download_departure={
                "download_endpoint_absent": True,
                "absence_timed_out": False,
                "sequence": 1,
            },
        )
        if endpoint_sha is not None:
            path = prepared.run_dir / "candidate-observer.json"
            value = json.loads(path.read_bytes())
            value["endpoint_identity_sha256"] = endpoint_sha
            path.chmod(0o600)
            path.write_bytes(
                json.dumps(
                    value, sort_keys=True, separators=(",", ":")
                ).encode()
            )

    def classified(self, name):
        envelope = dict(self.adapter._boundary_rows())[name]  # noqa: SLF001
        _record, classified = self.adapter._round_trip(envelope)  # noqa: SLF001
        return classified

    def test_actual_wait_download_retains_start_and_rollback_same_path(self):
        prepared = self.prepared()
        backend = object.__new__(self.module.SamsungOdinBackend)
        backend.odin = prepared.root / "odin4"
        backend.usb_root = prepared.root / "sys-usb"
        endpoint = self.start_endpoint(prepared)
        start_raw = self.module.p318_topology.raw_snapshot(
            phase="download_start", capture_complete=True, endpoints=[endpoint]
        )
        rollback_raw = self.module.p318_topology.raw_snapshot(
            phase="rollback_download", capture_complete=True, endpoints=[endpoint]
        )
        wait = types.SimpleNamespace(
            timed_out=False,
            ticket=types.SimpleNamespace(device="/dev/bus/usb/001/002"),
            next_sequence=4,
        )
        with (
            mock.patch.object(
                self.module.odin_core, "list_snapshot_receipts", return_value=[]
            ),
            mock.patch.object(
                self.module.odin_core,
                "wait_for_single_live_endpoint",
                return_value=wait,
            ),
            mock.patch.object(
                self.module.p318_topology,
                "capture_download_inventory_raw",
                side_effect=[start_raw, rollback_raw],
            ),
            mock.patch.object(
                self.module,
                "validate_download_endpoint",
                return_value={"endpoint_sha256": "1" * 64},
            ),
            mock.patch.object(
                self.module.odin_core,
                "revalidate_endpoint_ticket",
                return_value={"device_identity": "2" * 64},
            ),
        ):
            backend.wait_download(prepared, prepared.run_dir, object(), 1)
            backend.wait_download(prepared, prepared.run_dir, object(), 1)
        _raw, start = self.module._p318_read_phase(prepared, "download_start")
        _raw, rollback = self.module._p318_read_phase(
            prepared, "rollback_download"
        )
        self.assertTrue(start["decision"]["candidate_eligible"])
        self.assertTrue(rollback["decision"]["rollback_resume"])
        self.assertEqual(rollback["relationship_to_start"], "same")

    def test_final_correlation_uses_window_receipt_and_exact_raw_bytes(self):
        prepared = self.prepared()
        self.publish_start(prepared)
        endpoint = self.candidate_endpoint(prepared)
        self.publish_observer(
            prepared, "accepted", endpoint["endpoint_identity_sha256"]
        )
        raw = self.module.p318_topology.raw_snapshot(
            phase="candidate_end", capture_complete=True, endpoints=[endpoint]
        )
        self.module._p318_publish_candidate_raw(prepared, raw)
        correlated, evidence = self.module._p318_finalize_candidate_phase(
            prepared, self.classified("lossless47_event_written")
        )
        self.assertTrue(correlated["accepted"])
        self.assertEqual(
            correlated["classification"], "RETAIN_EXPERIMENT_TERMINAL"
        )
        self.assertEqual(evidence["phase"]["relationship_to_start"], "same")
        self.assertEqual(
            evidence["phase"]["host_observer"]["receipt_sha256"],
            self.module._reopen_candidate_observation(prepared)[
                "receipt_sha256"
            ],
        )

    def test_actual_candidate_observer_closure_publishes_raw_snapshot(self):
        prepared = self.prepared()
        backend = object.__new__(self.module.SamsungOdinBackend)
        backend.odin = prepared.root / "odin4"
        absence = types.SimpleNamespace(
            absent=True, timed_out=False, next_sequence=7
        )
        raw = self.module.p318_topology.raw_snapshot(
            phase="candidate_end", capture_complete=True, endpoints=[]
        )
        observer = live_tests.FakeCandidateObserver(
            self.module, prepared, "endpoint-timeout"
        )
        with (
            mock.patch.object(
                self.module.odin_core, "list_snapshot_receipts", return_value=[]
            ),
            mock.patch.object(
                self.module.odin_core,
                "wait_for_no_live_endpoint",
                return_value=absence,
            ),
            mock.patch.object(
                self.module.p318_topology,
                "capture_candidate_raw",
                return_value=raw,
            ),
        ):
            result = backend.observe_candidate(
                prepared, prepared.run_dir, object(), observer
            )
        self.assertEqual(
            result["p318_candidate_topology_raw"],
            self.module._p318_candidate_raw_receipt(prepared),
        )
        self.assertEqual(
            result["candidate_observer_classification"], "endpoint-timeout"
        )

    def test_complete_window_timeout_plus_absent_snapshot_is_host_silent(self):
        prepared = self.prepared()
        self.publish_start(prepared)
        self.publish_observer(prepared, "endpoint-timeout")
        raw = self.module.p318_topology.raw_snapshot(
            phase="candidate_end", capture_complete=True, endpoints=[]
        )
        self.module._p318_publish_candidate_raw(prepared, raw)
        correlated, evidence = self.module._p318_finalize_candidate_phase(
            prepared, self.classified("lossless47_no_event_eagain")
        )
        self.assertTrue(correlated["accepted"])
        self.assertEqual(
            correlated["classification"], "DEVICE_RESULT_HOST_SILENT"
        )
        self.assertTrue(evidence["phase"]["observation_window_complete"])

    def test_topology_park_is_durable_and_precedes_rollback_transfer(self):
        prepared = self.prepared()

        class ParkBackend(live_tests.FakeBackend):
            def wait_download(inner_self, *args):
                inner_self.calls.append("wait-download")
                if inner_self.calls.count("wait-download") == 1:
                    return self.module.Endpoint("ep", 1, "1" * 64)
                raise self.module.P318TopologyPark("fixture drift")

            def observe_candidate(inner_self, *args):
                result = super(ParkBackend, inner_self).observe_candidate(*args)
                raw = self.module.p318_topology.raw_snapshot(
                    phase="candidate_end", capture_complete=False, endpoints=[]
                )
                result["p318_candidate_topology_raw"] = (
                    self.module._p318_publish_candidate_raw(prepared, raw)
                )
                return result

        backend = ParkBackend(self.module, acm="accepted")
        with mock.patch.object(self.module, "_p300_bundle", return_value=False):
            result = self.module.execute_prepared(
                prepared, prepared.approval_token, backend
            )
        self.assertEqual(
            result["verdict"],
            "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
        )
        self.assertEqual(
            result["outcome_class"], "rollback_topology_rebind_required"
        )
        self.assertTrue(result["live_state"]["p318_rollback_topology_parked"])
        self.assertNotIn("transfer-rollback", backend.calls)
        self.assertNotIn("rollback_flash_start", [
            row["name"] for row in result["timeline"]["events"]
        ])


if __name__ == "__main__":
    unittest.main()
