from __future__ import annotations

import contextlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p324_cdc_acm_observer as p324  # noqa: E402


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="ascii")


def _endpoint(
    root: Path,
    usb_root: Path,
    class_tty: Path,
    topology: str,
    tty_name: str,
    serial: str,
) -> None:
    drivers = root / "sys/drivers/cdc_acm"
    drivers.mkdir(parents=True, exist_ok=True)
    usb = root / "sys/devices" / topology
    interface = usb / f"{topology}:1.0"
    tty_device = interface / "tty" / tty_name
    tty_device.mkdir(parents=True)
    _write(usb / "idVendor", "04e8")
    _write(usb / "idProduct", "6861")
    _write(usb / "serial", serial)
    _write(interface / "bInterfaceNumber", "00")
    (interface / "driver").symlink_to(drivers)
    tty_class = class_tty / tty_name
    tty_class.mkdir(parents=True)
    (tty_class / "device").symlink_to(tty_device)
    _write(tty_class / "dev", "1:3")
    link = usb_root / topology
    if not link.exists() and not link.is_symlink():
        link.symlink_to(usb)


def _spec() -> dict[str, str]:
    run_id = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
    return {
        "kind": "exact_cdc_acm_banner_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + run_id,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": ("S22PLUS-FYG8-E3:" + run_id + "\n").encode().hex(),
    }


class P324ObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.class_tty = self.root / "sys/class/tty"
        self.class_tty.mkdir(parents=True)
        self.usb_root = self.root / "usb"
        self.usb_root.mkdir()
        (self.root / "port0/port0-partner").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def session(self) -> p324.P324ObserverSession:
        delegate = mock.Mock(topology=p324.lane.CANDIDATE_TOPOLOGY)
        return p324.P324ObserverSession(
            delegate=delegate,
            spec=_spec(),
            run_dir=self.root,
            lane_binding={},
            lane_binding_receipt={},
            arm={},
            arm_receipt={},
            partner_before=p324._partner(self.root),  # noqa: SLF001
            class_tty=self.class_tty,
            usb_root=self.usb_root,
            typec_root=self.root,
        )

    def test_selector_opens_only_exact_candidate_lane(self) -> None:
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "3-1.3",
            "ttyACM0",
            _spec()["usb_serial"],
        )
        with mock.patch.object(
            p324.lane, "revalidate_binding", return_value={"bound": True}
        ):
            classification, endpoint = self.session()._select()  # noqa: SLF001
        self.assertEqual(classification, "accepted")
        self.assertEqual(endpoint.topology, "3-1.3")

    def test_lane_drift_blocks_candidate_before_open(self) -> None:
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "3-1.3",
            "ttyACM0",
            _spec()["usb_serial"],
        )
        with mock.patch.object(
            p324.lane,
            "revalidate_binding",
            side_effect=p324.lane.LaneBindingError("fixture drift"),
        ):
            classification, endpoint = self.session()._select()  # noqa: SLF001
        self.assertEqual(classification, "identity-mismatch")
        self.assertIsNone(endpoint)

    def test_source_lane_candidate_is_never_selected(self) -> None:
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "2-1.3",
            "ttyACM0",
            _spec()["usb_serial"],
        )
        classification, endpoint = self.session()._select()  # noqa: SLF001
        self.assertEqual(classification, "identity-mismatch")
        self.assertIsNone(endpoint)

    def test_two_lane_candidates_are_ambiguous_without_open(self) -> None:
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "2-1.3",
            "ttyACM0",
            _spec()["usb_serial"],
        )
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "3-1.3",
            "ttyACM1",
            _spec()["usb_serial"],
        )
        classification, endpoint = self.session()._select()  # noqa: SLF001
        self.assertEqual(classification, "endpoint-ambiguous")
        self.assertIsNone(endpoint)

    def test_foreign_candidate_like_endpoint_blocks_exact_lane(self) -> None:
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "3-1.3",
            "ttyACM0",
            _spec()["usb_serial"],
        )
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "4-7.2",
            "ttyACM1",
            "other-candidate",
        )
        session = self.session()
        classification, endpoint = session._select()  # noqa: SLF001
        self.assertEqual(classification, "endpoint-ambiguous")
        self.assertIsNone(endpoint)
        inventory = p324._inventory(  # noqa: SLF001
            _spec(), self.class_tty, self.usb_root
        )
        self.assertEqual(inventory["foreign_candidate_like_count"], 1)
        self.assertEqual(inventory["all_endpoint_count"], 2)

    def test_base_acceptance_is_gated_by_end_inventory_and_partner(self) -> None:
        session = self.session()
        session.delegate.observe.return_value = {
            "classification": "accepted",
            "accepted": True,
            "exact": True,
        }
        session.partner_before = {
            "entry_dev": 1,
            "entry_ino": 2,
            "entry_ctime_ns": 3,
            "target_dev": 4,
            "target_ino": 5,
            "target_ctime_ns": 6,
            "target_sha256": "b" * 64,
        }
        empty_inventory = p324._inventory(  # noqa: SLF001
            _spec(), self.class_tty, self.usb_root
        )
        with (
            mock.patch.object(
                p324.lane, "revalidate_binding", return_value={"bound": True}
            ),
            mock.patch.object(
                p324,
                "_partner",
                return_value={**session.partner_before, "entry_ino": 9},
            ),
            mock.patch.object(p324, "_inventory", return_value=empty_inventory),
            mock.patch.object(
                p324,
                "_file_receipt",
                return_value={"path": "private", "size": 1, "sha256": "a" * 64},
            ),
            mock.patch.object(p324.observer, "persist_json"),
        ):
            result = session.observe(
                timeout_sec=1,
                download_departure={
                    "download_endpoint_absent": True,
                    "absence_timed_out": False,
                    "sequence": 1,
                },
            )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "identity-mismatch")

    def test_arm_records_both_topologies_before_delegate(self) -> None:
        run_dir = self.root / "run"
        run_dir.mkdir()
        lane_value = {"bound": True}
        lane_receipt = {"path": "private", "size": 1, "sha256": "a" * 64}
        partner = {
            "entry_dev": 1,
            "entry_ino": 2,
            "entry_ctime_ns": 3,
            "target_dev": 4,
            "target_ino": 5,
            "target_ctime_ns": 6,
            "target_sha256": "b" * 64,
        }
        delegate = mock.Mock(topology=p324.lane.CANDIDATE_TOPOLOGY)

        @contextlib.contextmanager
        def delegated(*args, **kwargs):
            self.assertEqual(args[1], p324.lane.CANDIDATE_TOPOLOGY)
            yield delegate

        with (
            mock.patch.object(
                p324.lane, "revalidate_binding", return_value=lane_value
            ),
            mock.patch.object(p324, "_partner", return_value=partner),
            mock.patch.object(p324.observer, "observer_session", delegated),
        ):
            with p324.observer_session(
                _spec(),
                p324.lane.SOURCE_TOPOLOGY,
                run_dir,
                {"binding": "fixture"},
                lane_value,
                lane_receipt,
                class_tty=self.class_tty,
                usb_root=self.usb_root,
                typec_root=self.root,
            ) as wrapped:
                self.assertIs(wrapped.delegate, delegate)
        arm = json.loads((run_dir / p324.ARM_NAME).read_bytes())
        self.assertTrue(arm["candidate_absent_on_both"])
        self.assertEqual(
            set(arm["inventory"]["rows"]),
            {p324.lane.SOURCE_TOPOLOGY, p324.lane.CANDIDATE_TOPOLOGY},
        )
        self.assertEqual(arm["selector_topology_count"], 1)

    def test_exact_lane_receipt_reopens_as_accepted(self) -> None:
        run_dir = self.root / "receipt-run"
        run_dir.mkdir()
        lane_value = {"bound": True}
        lane_receipt = {"path": "private", "size": 1, "sha256": "a" * 64}
        partner = p324._partner(self.root)  # noqa: SLF001
        arm_inventory = p324._inventory(  # noqa: SLF001
            _spec(), self.class_tty, self.usb_root
        )
        arm = {
            "schema": p324.ARM_SCHEMA,
            "contract_id": p324.CONTRACT_ID,
            "target": p324.TARGET,
            "lane_binding": lane_receipt,
            "lane_binding_sha256": p324._digest(lane_value),  # noqa: SLF001
            "source_topology": p324.lane.SOURCE_TOPOLOGY,
            "candidate_topology": p324.lane.CANDIDATE_TOPOLOGY,
            "selector_topology_count": 1,
            "partner_before": partner,
            "inventory": arm_inventory,
            "both_topologies_inventory_complete": True,
            "candidate_absent_on_both": True,
            "candidate_like_absent_everywhere": True,
            "opens_candidate_acm": False,
            "device_commands": False,
        }
        arm_receipt = p324.observer.persist_json(
            run_dir / p324.ARM_NAME, arm
        )
        base_receipt = p324.observer.persist_json(
            run_dir / "candidate-observer.json", {"fixture": "base"}
        )
        _endpoint(
            self.root,
            self.usb_root,
            self.class_tty,
            "3-1.3",
            "ttyACM0",
            _spec()["usb_serial"],
        )
        end_inventory = p324._inventory(  # noqa: SLF001
            _spec(), self.class_tty, self.usb_root
        )
        value = {
            "schema": p324.SCHEMA,
            "contract_id": p324.CONTRACT_ID,
            "target": p324.TARGET,
            "lane_binding": lane_receipt,
            "lane_binding_sha256": p324._digest(lane_value),  # noqa: SLF001
            "arm": arm_receipt,
            "base_observer": base_receipt,
            "source_topology": p324.lane.SOURCE_TOPOLOGY,
            "candidate_topology": p324.lane.CANDIDATE_TOPOLOGY,
            "selector_topology_count": 1,
            "partner_before": partner,
            "partner_after": partner,
            "partner_poll_count": 1,
            "partner_continuous": True,
            "end_inventory": end_inventory,
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": True,
            "same_run_typec_partner_continuity": True,
            "accepted_for_p324": True,
            "opens_only_candidate_topology": True,
            "device_commands": False,
        }
        p324.observer.persist_json(run_dir / p324.SUPPLEMENT_NAME, value)
        base = {
            "classification": "accepted",
            "accepted": True,
            "exact": True,
            "download_endpoint_absent": True,
            "topology_sha256": "b" * 64,
            "endpoint_identity_sha256": "c" * 64,
            "bounded": True,
        }
        with (
            mock.patch.object(
                p324.lane, "validate_binding", return_value=lane_value
            ),
            mock.patch.object(
                p324.observer, "validate_receipt", return_value=base
            ),
        ):
            reopened = p324.validate_receipt(
                run_dir,
                spec=_spec(),
                binding={"binding": "fixture"},
                source_topology=p324.lane.SOURCE_TOPOLOGY,
                lane_binding=lane_value,
                lane_binding_receipt=lane_receipt,
            )
        self.assertTrue(reopened["accepted"])
        self.assertTrue(reopened["accepted_for_p324"])
        self.assertTrue(reopened["same_run_typec_partner_continuity"])


if __name__ == "__main__":
    unittest.main()
