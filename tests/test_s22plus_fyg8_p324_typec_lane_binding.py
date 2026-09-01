from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p324_typec_lane_binding as lane  # noqa: E402


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="ascii")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    devices = tmp_path / "sys/devices"
    source_bus = devices / "pci0000:00/0000:00:0d.0/usb2"
    candidate_bus = devices / "pci0000:00/0000:00:14.0/usb3"
    source_port = source_bus / "2-0:1.0/usb2-port1"
    candidate_port = candidate_bus / "3-0:1.0/usb3-port1"
    source_port.mkdir(parents=True)
    candidate_port.mkdir(parents=True)
    for port in (source_port, candidate_port):
        _write(port / "location", "0x80000101")
        _write(port / "connect_type", "hotplug")

    source_hub = source_bus / "2-1"
    candidate_hub = candidate_bus / "3-1"
    fields = {
        source_hub: {
            "idVendor": "2109", "idProduct": "0822", "bDeviceClass": "09",
            "bDeviceProtocol": "03", "devpath": "1", "busnum": "2",
            "serial": "fixture-pair", "speed": "10000",
            "manufacturer": "fixture-hub",
        },
        candidate_hub: {
            "idVendor": "2109", "idProduct": "2822", "bDeviceClass": "09",
            "bDeviceProtocol": "02", "devpath": "1", "busnum": "3",
            "serial": "fixture-pair", "speed": "480",
            "manufacturer": "fixture-hub",
        },
    }
    for hub, values in fields.items():
        for name, value in values.items():
            _write(hub / name, value)

    usb_root = tmp_path / "sys/bus/usb/devices"
    usb_root.mkdir(parents=True)
    (usb_root / "usb2").symlink_to(source_bus)
    (usb_root / "usb3").symlink_to(candidate_bus)
    (usb_root / "2-1").symlink_to(source_hub)
    (usb_root / "3-1").symlink_to(candidate_hub)

    connector = devices / "platform/USBC000:00/typec/port0"
    connector.mkdir(parents=True)
    (connector / "usb2-port1").symlink_to(source_port)
    (connector / "usb3-port1").symlink_to(candidate_port)
    typec_root = tmp_path / "sys/class/typec"
    typec_root.mkdir(parents=True)
    (typec_root / "port0").symlink_to(connector)
    return usb_root, typec_root


class TypecLaneBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.usb_root, self.typec_root = _fixture(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_exact_connector_pair_selects_one_candidate_topology(self) -> None:
        value = lane.capture_binding(
            "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
        )
        self.assertEqual(value["candidate_topology"], "usb:3-1.3")
        self.assertEqual(value["selector_topology_count"], 1)
        self.assertIs(value["opens_candidate_acm"], False)
        self.assertEqual(
            lane.revalidate_binding(
                value,
                source_topology="usb:2-1.3",
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            ),
            value,
        )

    def test_source_topology_is_exact(self) -> None:
        for topology in ("usb:3-1.3", "usb:2-1.4", "usb:2-1"):
            with self.subTest(topology=topology), self.assertRaises(
                lane.LaneBindingError
            ):
                lane.capture_binding(
                    topology,
                    usb_root=self.usb_root,
                    typec_root=self.typec_root,
                )

    def test_usb4_sibling_is_never_a_selector_lane(self) -> None:
        usb4 = self.root / (
            "sys/devices/pci0000:00/0000:00:14.0/usb4/"
            "4-0:1.0/usb4_port1"
        )
        usb4.mkdir(parents=True)
        (self.typec_root / "port0/usb4_port1").symlink_to(usb4)
        value = lane.capture_binding(
            "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
        )
        self.assertEqual(value["selector_topology_count"], 1)
        self.assertNotIn("usb4", value)
        self.assertEqual(value["candidate_topology"], "usb:3-1.3")

    def test_connector_location_drift_rejects(self) -> None:
        _write(self.typec_root / "port0/usb3-port1/location", "0x80000201")
        with self.assertRaises(lane.LaneBindingError):
            lane.capture_binding(
                "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
            )

    def test_companion_hub_identity_drift_rejects(self) -> None:
        _write(self.usb_root / "3-1/serial", "other-hub")
        with self.assertRaises(lane.LaneBindingError):
            lane.capture_binding(
                "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
            )

    def test_candidate_controller_drift_rejects(self) -> None:
        wrong = self.root / (
            "sys/devices/pci0000:00/0000:00:15.0/usb3/"
            "3-0:1.0/usb3-port1"
        )
        wrong.mkdir(parents=True)
        (self.typec_root / "port0/usb3-port1").unlink()
        (self.typec_root / "port0/usb3-port1").symlink_to(wrong)
        with self.assertRaises(lane.LaneBindingError):
            lane.capture_binding(
                "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
            )

    def test_missing_bus_lane_is_normalized(self) -> None:
        (self.usb_root / "usb3").unlink()
        with self.assertRaises(lane.LaneBindingError):
            lane.capture_binding(
                "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
            )

    def test_binding_mutation_rejects(self) -> None:
        value = lane.capture_binding(
            "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
        )
        changed = copy.deepcopy(value)
        changed["candidate_topology"] = "usb:3-1.4"
        with self.assertRaises(lane.LaneBindingError):
            lane.validate_binding(changed, source_topology="usb:2-1.3")

    def test_self_hash_is_syntax_only_and_live_revalidation_rejects_forgery(self) -> None:
        value = lane.capture_binding(
            "usb:2-1.3", usb_root=self.usb_root, typec_root=self.typec_root
        )
        forged = copy.deepcopy(value)
        forged["typec_port_sha256"] = "0" * 64
        forged["binding_sha256"] = lane.binding_digest(
            {key: item for key, item in forged.items() if key != "binding_sha256"}
        )
        self.assertEqual(
            lane.validate_binding(forged, source_topology="usb:2-1.3"), forged
        )
        with self.assertRaisesRegex(
            lane.LaneBindingError, "lane binding changed"
        ):
            lane.revalidate_binding(
                forged,
                source_topology="usb:2-1.3",
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )

        for malformed in ({}, {"schema": lane.SCHEMA}):
            with self.assertRaises(lane.LaneBindingError):
                lane.validate_binding(
                    malformed, source_topology="usb:2-1.3"
                )

        changed = copy.deepcopy(value)
        changed["selector_topology_count"] = True
        with self.assertRaises(lane.LaneBindingError):
            lane.validate_binding(changed, source_topology="usb:2-1.3")

        changed = copy.deepcopy(value)
        changed["source_hub"]["speed"] = []
        changed["binding_sha256"] = lane.binding_digest(
            {key: item for key, item in changed.items() if key != "binding_sha256"}
        )
        with self.assertRaises(lane.LaneBindingError):
            lane.validate_binding(changed, source_topology="usb:2-1.3")


if __name__ == "__main__":
    unittest.main()
