from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
import sys

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_live_v2 as live  # noqa: E402


def _endpoint() -> SimpleNamespace:
    return SimpleNamespace(
        tty_name="ttyACM0",
        tty_class=Path("/sys/class/tty/ttyACM0"),
        major=166,
        minor=0,
        identity_sha256="e" * 64,
    )


def _session(guard: SimpleNamespace) -> live._P329ObserverSession:
    base = SimpleNamespace(
        guard=guard,
        dev_root=Path("/dev"),
    )
    return live._P329ObserverSession(
        SimpleNamespace(),
        base,
        {
            "usb_vendor_id": "04e8",
            "usb_product_id": "6861",
            "usb_serial": "S22E3" + live.typed_evidence.P329_RUN_ID,
            "usb_driver": "cdc_acm",
            "usb_interface_number": "00",
            "banner_hex": live.p329_auth_runtime.DEVICE_BANNER.hex(),
        },
        Path("/unused/run"),
        {},
        {},
        Path("/sys/bus/usb/devices"),
        Path("/sys/class/typec"),
    )


def _stable_endpoint() -> tuple[SimpleNamespace, SimpleNamespace]:
    identity = SimpleNamespace()
    repeated = SimpleNamespace(identity_sha256="e" * 64)
    return identity, repeated


class P329UdevSettleTests(unittest.TestCase):
    def test_backend_selects_p329_before_p328(self) -> None:
        backend = live.SamsungOdinBackend.__new__(live.SamsungOdinBackend)
        backend.usb_root = Path("/unused/usb")
        backend.typec_root = Path("/unused/typec")
        prepared = SimpleNamespace(
            bundle=SimpleNamespace(
                manifest={"observation": {"candidate_observer": {"p329": True}}}
            )
        )
        sentinel = object()
        with (
            mock.patch.object(live, "_p329_bundle", return_value=True),
            mock.patch.object(
                live,
                "_p324_typec_lane_value",
                return_value=({"lane": True}, {"receipt": True}),
            ),
            mock.patch.object(
                live, "_p329_candidate_observer_session", return_value=sentinel
            ) as selected,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), sentinel)
        selected.assert_called_once()

    def test_initial_missing_properties_settle_before_open(self) -> None:
        matches = mock.Mock(side_effect=[False, True, True])
        guard = SimpleNamespace(
            healthy=mock.Mock(return_value=True),
            matches_node=matches,
        )
        session = _session(guard)
        character = SimpleNamespace(st_mode=0o020600, st_rdev=0)
        with (
            mock.patch.object(live.time, "monotonic", side_effect=[0.0, 0.0]),
            mock.patch.object(live.time, "sleep") as sleep,
            mock.patch.object(
                live.cdc_acm_observer,
                "_resolve_endpoint",
                return_value=_stable_endpoint(),
            ),
            mock.patch.object(live.cdc_acm_observer, "_matches", return_value=True),
            mock.patch.object(Path, "stat", return_value=character),
            mock.patch.object(live.os, "major", return_value=166),
            mock.patch.object(live.os, "minor", return_value=0),
        ):
            self.assertIsNone(session._settle_guard_properties(_endpoint(), 10.0))
        sleep.assert_called_once_with(live.P329_UDEV_SETTLE_POLL_SEC)
        self.assertEqual(matches.call_count, 2)

    def test_persistent_missing_properties_stop_at_half_second(self) -> None:
        now = [0.0]

        def sleep(amount: float) -> None:
            now[0] += amount

        guard = SimpleNamespace(
            healthy=mock.Mock(return_value=True),
            matches_node=mock.Mock(return_value=False),
        )
        session = _session(guard)
        character = SimpleNamespace(st_mode=0o020600, st_rdev=0)
        with (
            mock.patch.object(live.time, "monotonic", side_effect=lambda: now[0]),
            mock.patch.object(live.time, "sleep", side_effect=sleep),
            mock.patch.object(
                live.cdc_acm_observer,
                "_resolve_endpoint",
                return_value=_stable_endpoint(),
            ),
            mock.patch.object(live.cdc_acm_observer, "_matches", return_value=True),
            mock.patch.object(Path, "stat", return_value=character),
            mock.patch.object(live.os, "major", return_value=166),
            mock.patch.object(live.os, "minor", return_value=0),
        ):
            self.assertEqual(
                session._settle_guard_properties(_endpoint(), 10.0),
                "guard-property-timeout",
            )
        self.assertAlmostEqual(now[0], live.P329_UDEV_SETTLE_SEC)
        self.assertLessEqual(guard.matches_node.call_count, 22)

    def test_guard_or_identity_drift_stops_without_open(self) -> None:
        endpoint = _endpoint()
        guard = SimpleNamespace(
            healthy=mock.Mock(side_effect=[True, False]),
            matches_node=mock.Mock(return_value=False),
        )
        session = _session(guard)
        character = SimpleNamespace(st_mode=0o020600, st_rdev=0)
        with (
            mock.patch.object(live.time, "monotonic", side_effect=[0.0, 0.0]),
            mock.patch.object(live.time, "sleep"),
            mock.patch.object(
                live.cdc_acm_observer,
                "_resolve_endpoint",
                return_value=_stable_endpoint(),
            ),
            mock.patch.object(live.cdc_acm_observer, "_matches", return_value=True),
            mock.patch.object(Path, "stat", return_value=character),
            mock.patch.object(live.os, "major", return_value=166),
            mock.patch.object(live.os, "minor", return_value=0),
        ):
            self.assertEqual(
                session._settle_guard_properties(endpoint, 10.0), "guard-lost"
            )

        guard = SimpleNamespace(
            healthy=mock.Mock(return_value=True),
            matches_node=mock.Mock(return_value=False),
        )
        session = _session(guard)
        drifted = SimpleNamespace(identity_sha256="d" * 64)
        with (
            mock.patch.object(live.time, "monotonic", return_value=0.0),
            mock.patch.object(
                live.cdc_acm_observer,
                "_resolve_endpoint",
                return_value=(SimpleNamespace(), drifted),
            ),
            mock.patch.object(Path, "stat", return_value=character),
        ):
            self.assertEqual(
                session._settle_guard_properties(endpoint, 10.0),
                "identity-mismatch",
            )

    def test_protocol_open_occurs_only_after_settle(self) -> None:
        guard = SimpleNamespace(
            healthy=mock.Mock(return_value=True),
            matches_node=mock.Mock(return_value=True),
        )
        session = _session(guard)
        writer = mock.Mock()
        with mock.patch.object(
            live._P328ObserverSession,
            "_read_endpoint",
            return_value="accepted",
        ) as inherited:
            self.assertEqual(session._read_endpoint(_endpoint(), 10.0, writer), "accepted")
        inherited.assert_called_once()
        self.assertEqual(guard.matches_node.call_count, 1)

    def test_manifest_spec_keeps_both_properties_and_finite_bounds(self) -> None:
        spec = live.typed_evidence.p329_authenticated_framed_observer_spec()
        self.assertEqual(spec["udev_guard_settle_timeout_ms"], 500)
        self.assertEqual(spec["udev_guard_settle_poll_ms"], 25)
        self.assertEqual(
            spec["guard_properties_required"],
            ["ID_MM_DEVICE_IGNORE=1", "ID_MM_PORT_IGNORE=1"],
        )
        self.assertEqual(spec["wire_magic"], "S328")
        self.assertIn(live.typed_evidence.P329_RUN_ID, spec["usb_serial"])


if __name__ == "__main__":
    unittest.main()
