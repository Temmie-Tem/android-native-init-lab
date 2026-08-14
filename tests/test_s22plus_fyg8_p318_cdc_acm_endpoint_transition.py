from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_endpoint_transition", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 endpoint transition contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318EndpointTransitionTest(unittest.TestCase):
    def authority(self):
        return {
            "schema": P318.AUTHORITY_SCHEMA,
            "target": P318.TARGET,
            "derivation": "sealed_p317_sidecar_exact_path_pair",
            "source_topology": "2-1.3",
            "source_usb_device_path": (
                "/devices/pci0000:00/0000:00:0d.0/usb2/2-1/2-1.3"
            ),
            "source_id_path": "pci-0000:00:0d.0-usb-0:1.3",
            "source_controller": "0000:00:0d.0",
            "candidate_topology": "3-1.3",
            "candidate_usb_device_path": (
                "/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1.3"
            ),
            "candidate_id_path": "pci-0000:00:14.0-usb-0:1.3",
            "candidate_controller": "0000:00:14.0",
            "candidate_identity": {
                "vendor": "04e8",
                "product": "6861",
                "serial_sha256": "a" * 64,
                "driver": "cdc_acm",
                "interface": "00",
            },
            "same_port_suffix": True,
            "same_controller": False,
            "generic_companion_inference_forbidden": True,
            "scope": "p317_endpoint_replay_only",
        }

    def endpoint(self, **changes):
        value = {
            "tty_name": "ttyACM0",
            "topology": "3-1.3",
            "usb_device_path": (
                "/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1.3"
            ),
            "vendor": "04e8",
            "product": "6861",
            "serial_sha256": "a" * 64,
            "driver": "cdc_acm",
            "interface": "00",
        }
        value.update(changes)
        return value

    def build_default(self, **overrides):
        paths = {
            "prepared_data": P318.DEFAULT_PREPARED,
            "target_data": P318.DEFAULT_TARGET_PRIVATE,
            "observer_receipt_data": P318.DEFAULT_OBSERVER_RECEIPT,
            "sidecar_result_data": P318.DEFAULT_SIDECAR_RESULT,
            "kernel_data": P318.DEFAULT_KERNEL_LOG,
            "udev_data": P318.DEFAULT_UDEV_LOG,
            "observer_source_data": P318.DEFAULT_OBSERVER_SOURCE,
            "f_acm_data": P318.DEFAULT_F_ACM_SOURCE,
            "u_serial_data": P318.DEFAULT_U_SERIAL_SOURCE,
        }
        values = {
            key: (ROOT / path).read_bytes()
            for key, path in paths.items()
        }
        values["extractor_data"] = SCRIPT.read_bytes()
        values.update(overrides)
        return P318.build_contract(**values)

    def test_exact_p317_evidence_localizes_selector_miss(self):
        result = self.build_default()
        self.assertEqual(result["verdict"], P318.VERDICT)
        authority = result["authority"]
        self.assertEqual(authority["source_topology"], "2-1.3")
        self.assertEqual(authority["candidate_topology"], "3-1.3")
        self.assertEqual(authority["source_controller"], "0000:00:0d.0")
        self.assertEqual(authority["candidate_controller"], "0000:00:14.0")
        self.assertFalse(authority["same_controller"])
        self.assertTrue(authority["same_port_suffix"])
        self.assertEqual(
            result["frozen_observer"]["corrected_classification"],
            "exact-candidate-on-unrecognized-topology",
        )
        self.assertFalse(result["frozen_observer"]["tty_open_attempted"])
        self.assertEqual(
            result["corrected_selector"]["classification"],
            "selected-exact-transition",
        )
        self.assertTrue(result["scope"]["p317_only"])
        self.assertFalse(result["scope"]["prior_campaign_silence_reclassified"])
        self.assertFalse(result["dtr_source_audit"]["dtr_hypothesis_retained"])

    def test_positive_exact_transition_is_selected(self):
        result = P318.classify_endpoints(self.authority(), [self.endpoint()])
        self.assertEqual(result["classification"], "selected-exact-transition")
        self.assertTrue(result["open_permitted"])
        self.assertEqual(result["exact_candidate_count"], 1)

    def test_same_suffix_on_other_controller_is_not_selected(self):
        endpoint = self.endpoint(
            topology="4-1.3",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:1d.0/usb4/4-1/4-1.3"
            ),
        )
        result = P318.classify_endpoints(self.authority(), [endpoint])
        self.assertEqual(
            result["classification"], "exact-candidate-unrecognized-path"
        )
        self.assertFalse(result["open_permitted"])

    def test_different_samsung_device_is_not_selected(self):
        foreign = self.endpoint(
            tty_name="ttyACM7",
            topology="5-2",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:1d.0/usb5/5-2/5-2"
            ),
            product="6860",
            serial_sha256="b" * 64,
        )
        result = P318.classify_endpoints(self.authority(), [foreign])
        self.assertEqual(result["classification"], "endpoint-absent")
        self.assertEqual(result["foreign_samsung_count"], 1)
        self.assertFalse(result["open_permitted"])

    def test_multiple_exact_candidates_are_ambiguous(self):
        duplicate = self.endpoint(
            tty_name="ttyACM8",
            topology="4-2",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:1d.0/usb4/4-2/4-2"
            ),
        )
        result = P318.classify_endpoints(
            self.authority(), [self.endpoint(), duplicate]
        )
        self.assertEqual(result["classification"], "exact-candidate-ambiguous")
        self.assertEqual(result["exact_candidate_count"], 2)
        self.assertFalse(result["open_permitted"])

    def test_authorized_path_with_wrong_identity_is_explicit(self):
        result = P318.classify_endpoints(
            self.authority(), [self.endpoint(serial_sha256="b" * 64)]
        )
        self.assertEqual(
            result["classification"], "authorized-path-identity-mismatch"
        )
        self.assertFalse(result["open_permitted"])

    def test_generic_companion_inference_cannot_be_enabled(self):
        authority = self.authority()
        authority["generic_companion_inference_forbidden"] = False
        with self.assertRaisesRegex(P318.TransitionError, "semantics"):
            P318.classify_endpoints(authority, [self.endpoint()])

    def test_observer_topology_predicate_mutation_fails(self):
        source = (ROOT / P318.DEFAULT_OBSERVER_SOURCE).read_bytes()
        mutated = source.replace(
            b"        endpoint.topology == topology\n        and identity",
            b"        identity",
            1,
        )
        self.assertNotEqual(source, mutated)
        with self.assertRaisesRegex(P318.TransitionError, "source seam"):
            self.build_default(observer_source_data=mutated)

    def test_dtr_source_mutation_fails(self):
        source = (ROOT / P318.DEFAULT_U_SERIAL_SOURCE).read_bytes()
        start = source.index(b"static int gs_write(")
        location = source.index(b"if (port->port_usb)", start)
        mutated = (
            source[:location]
            + b"if (port->port_usb && port->port_handshake_bits)"
            + source[location + len(b"if (port->port_usb)") :]
        )
        self.assertNotEqual(source, mutated)
        with self.assertRaisesRegex(P318.TransitionError, "TX source seam"):
            self.build_default(u_serial_data=mutated)

    def test_sidecar_hash_mutation_fails(self):
        sidecar = json.loads((ROOT / P318.DEFAULT_SIDECAR_RESULT).read_text())
        sidecar["sources"]["udev"]["sha256"] = "0" * 64
        mutated = json.dumps(sidecar, sort_keys=True).encode()
        with self.assertRaisesRegex(P318.TransitionError, "udev authority"):
            self.build_default(sidecar_result_data=mutated)

    def test_contract_never_exports_raw_candidate_serial(self):
        prepared = json.loads((ROOT / P318.DEFAULT_PREPARED).read_text())
        serial = prepared["approval_binding"]["base_binding"]["observation"][
            "candidate_observer"
        ]["usb_serial"]
        payload = P318.encode_contract(self.build_default())
        self.assertNotIn(serial.encode(), payload)
        self.assertIn(P318.digest(self.build_default()["authority"]).encode(), payload)


if __name__ == "__main__":
    unittest.main()
