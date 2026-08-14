import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p318_topology_receipt as receipt


BINDING = "1" * 64
RECOVERY = "2" * 64
DOWNLOAD_TARGET = {
    "vendor": "04e8",
    "product_id": "685d",
    "product": "ODIN",
    "manufacturer": "SAMSUNG",
    "serial": "",
}
CANDIDATE_TARGET = {
    "vendor": "04e8",
    "product_id": "6861",
    "serial": "S22E3fixture",
    "driver": "cdc_acm",
    "interface": "00",
}


def endpoint(mode, product, topology, controller, device, serial=""):
    return receipt._endpoint_row(  # noqa: SLF001
        mode=mode,
        identity={
            "vendor": "04e8",
            "product_id": product,
            "product": "ODIN" if mode == "download" else "S22+ E3 ACM",
            "manufacturer": "SAMSUNG" if mode == "download" else "Android Native Init Lab",
            "serial": serial,
            "driver": "" if mode == "download" else "cdc_acm",
            "interface": "" if mode == "download" else "00",
            "tty_name": "" if mode == "download" else "ttyACM0",
            "endpoint_node": "/dev/bus/usb/002/003" if mode == "download" else "/dev/ttyACM0",
        },
        topology=topology,
        controller_path=controller,
        usb_device_path=device,
    )


class P318TopologyReceiptTests(unittest.TestCase):
    @staticmethod
    def host_observer(endpoint_identity=None, classification=None):
        if classification is None:
            classification = (
                "read-timeout"
                if endpoint_identity is not None
                else "endpoint-timeout"
            )
        return {
            "classification": classification,
            "endpoint_identity_sha256": endpoint_identity,
            "receipt_sha256": "3" * 64,
            "topology_sha256": receipt.digest_bytes(b"2-1.3"),
            "bounded": True,
            "valid_receipt": True,
            "download_endpoint_absent": True,
        }

    def start_record(self):
        raw = receipt.raw_snapshot(
            phase="download_start",
            capture_complete=True,
            endpoints=[endpoint("download", "685d", "2-1.3", "/c0", "/c0/usb2/2-1/2-1.3")],
        )
        return receipt.build_phase_record(
            raw,
            phase="download_start",
            target_identity=DOWNLOAD_TARGET,
            binding_id_sha256=BINDING,
            comparison_binding_id_sha256=BINDING,
            authority_state="candidate_approved_exact",
            causal_terminal_ready=False,
            start_path=None,
        )

    def test_phase_records_distinguish_same_drift_absent_and_unavailable(self):
        start = self.start_record()
        start_path = receipt.start_path(start)
        same = endpoint("candidate", "6861", "2-1.3", "/c0", "/c0/usb2/2-1/2-1.3", "S22E3fixture")
        drift = endpoint("candidate", "6861", "3-1.3", "/c1", "/c1/usb3/3-1/3-1.3", "S22E3fixture")

        def build(endpoints, complete=True):
            raw = receipt.raw_snapshot(
                phase="candidate_end", capture_complete=complete, endpoints=endpoints
            )
            observed = (
                endpoints[0]["endpoint_identity_sha256"]
                if endpoints and endpoints[0]["topology"] == "2-1.3"
                else None
            )
            return receipt.build_phase_record(
                raw,
                phase="candidate_end",
                target_identity=CANDIDATE_TARGET,
                binding_id_sha256=BINDING,
                comparison_binding_id_sha256=BINDING,
                authority_state="candidate_approved_exact",
                causal_terminal_ready=True,
                start_path=start_path,
                host_observer=self.host_observer(observed),
            )

        self.assertEqual(build([same])["relationship_to_start"], "same")
        self.assertEqual(
            build([same])["decision"]["proof_class"],
            "RETAIN_EXPERIMENT_TERMINAL",
        )
        self.assertEqual(build([drift])["relationship_to_start"], "drift")
        self.assertEqual(
            build([drift])["decision"]["proof_class"],
            "NO_PROOF_EXPERIMENT_PRECONDITION",
        )
        self.assertEqual(build([])["relationship_to_start"], "absent")
        self.assertEqual(
            build([])["decision"]["proof_class"], "DEVICE_RESULT_HOST_SILENT"
        )
        self.assertEqual(build([], False)["relationship_to_start"], "unavailable")
        self.assertEqual(
            build([], False)["decision"]["proof_class"], "NO_PROOF_OBSERVER"
        )
        self.assertEqual(build([same, drift])["relationship_to_start"], "ambiguous")

    def test_rollback_authority_is_phase_specific(self):
        start_path = receipt.start_path(self.start_record())
        same = endpoint("download", "685d", "2-1.3", "/c0", "/c0/usb2/2-1/2-1.3")
        drift = endpoint("download", "685d", "3-1.3", "/c1", "/c1/usb3/3-1/3-1.3")

        def build(value, authority):
            raw = receipt.raw_snapshot(
                phase="rollback_download", capture_complete=True, endpoints=[value]
            )
            return receipt.build_phase_record(
                raw,
                phase="rollback_download",
                target_identity=DOWNLOAD_TARGET,
                binding_id_sha256=RECOVERY if authority == "recovery_rebound_exact" else BINDING,
                comparison_binding_id_sha256=BINDING,
                authority_state=authority,
                causal_terminal_ready=True,
                start_path=start_path,
            )

        self.assertTrue(build(same, "rollback_bound_exact")["decision"]["rollback_resume"])
        self.assertFalse(build(drift, "rollback_bound_exact")["decision"]["rollback_resume"])
        recovered = build(drift, "recovery_rebound_exact")
        self.assertTrue(recovered["decision"]["rollback_resume"])
        self.assertEqual(recovered["decision"]["rollback_path_kind"], "reviewed_recovery")
        self.assertFalse(recovered["decision"]["experiment_proof_reclassified_by_rollback"])

    def test_candidate_window_receipt_prevents_end_snapshot_false_silence(self):
        start_path = receipt.start_path(self.start_record())
        same = endpoint(
            "candidate", "6861", "2-1.3", "/c0",
            "/c0/usb2/2-1/2-1.3", "S22E3fixture",
        )

        def build(endpoints, host):
            raw = receipt.raw_snapshot(
                phase="candidate_end", capture_complete=True, endpoints=endpoints
            )
            return receipt.build_phase_record(
                raw,
                phase="candidate_end",
                target_identity=CANDIDATE_TARGET,
                binding_id_sha256=BINDING,
                comparison_binding_id_sha256=BINDING,
                authority_state="candidate_approved_exact",
                causal_terminal_ready=True,
                start_path=start_path,
                host_observer=host,
            )

        disappeared = build(
            [], self.host_observer(same["endpoint_identity_sha256"])
        )
        self.assertEqual(disappeared["relationship_to_start"], "same")
        self.assertNotEqual(
            disappeared["decision"]["proof_class"], "DEVICE_RESULT_HOST_SILENT"
        )
        appeared_after_window = build([same], self.host_observer())
        self.assertEqual(
            appeared_after_window["relationship_to_start"], "ambiguous"
        )
        self.assertEqual(
            appeared_after_window["decision"]["proof_class"],
            "NO_PROOF_EXPERIMENT_PRECONDITION",
        )

    def test_actual_candidate_sysfs_capture_scans_without_opening_tty(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            controller = root / "devices/pci0000:00/0000:00:14.0"
            usb_root = controller / "usb3"
            usb = usb_root / "3-1" / "3-1.3"
            interface = usb / "3-1.3:1.0"
            tty_device = interface / "tty/ttyACM0"
            tty_device.mkdir(parents=True)
            (interface / "bInterfaceNumber").write_text("00\n")
            driver = root / "bus/usb/drivers/cdc_acm"
            driver.mkdir(parents=True)
            (interface / "driver").symlink_to(driver)
            for filename, value in {
                "idVendor": "04e8\n",
                "idProduct": "6861\n",
                "serial": "S22E3fixture\n",
                "product": "S22+ E3 ACM\n",
                "manufacturer": "Android Native Init Lab\n",
            }.items():
                (usb / filename).write_text(value)
            tty_class = root / "class/tty/ttyACM0"
            tty_class.mkdir(parents=True)
            (tty_class / "device").symlink_to(tty_device)
            (tty_class / "dev").write_text("166:0\n")
            raw = receipt.capture_candidate_raw(
                phase="candidate_end", class_tty=root / "class/tty"
            )
            parsed = receipt.parse_raw_snapshot(raw, phase="candidate_end")
            self.assertTrue(parsed["capture_complete"])
            self.assertEqual(len(parsed["endpoints"]), 1)
            self.assertEqual(parsed["endpoints"][0]["topology"], "3-1.3")
            self.assertEqual(parsed["endpoints"][0]["identity"]["driver"], "cdc_acm")

    def test_raw_and_record_publish_are_no_clobber_and_same_byte_bound(self):
        start = self.start_record()
        raw = receipt.raw_snapshot(
            phase="candidate_end", capture_complete=True, endpoints=[]
        )
        with tempfile.TemporaryDirectory() as name:
            raw_path = Path(name) / "raw.json"
            record_path = Path(name) / "record.json"
            record, receipts = receipt.publish_phase(
                raw_path,
                record_path,
                raw,
                phase="candidate_end",
                target_identity=CANDIDATE_TARGET,
                binding_id_sha256=BINDING,
                comparison_binding_id_sha256=BINDING,
                authority_state="candidate_approved_exact",
                causal_terminal_ready=True,
                start_path=receipt.start_path(start),
                host_observer=self.host_observer(),
            )
            self.assertEqual(receipts["raw"]["sha256"], record["immutable_raw_snapshot_sha256"])
            self.assertEqual(json.loads(record_path.read_bytes()), record)
            with self.assertRaises(receipt.TopologyReceiptError):
                receipt.publish_phase(
                    raw_path,
                    Path(name) / "second.json",
                    raw,
                    phase="candidate_end",
                    target_identity=CANDIDATE_TARGET,
                    binding_id_sha256=BINDING,
                    comparison_binding_id_sha256=BINDING,
                    authority_state="candidate_approved_exact",
                    causal_terminal_ready=True,
                    start_path=receipt.start_path(start),
                    host_observer=self.host_observer(),
                )


if __name__ == "__main__":
    unittest.main()
