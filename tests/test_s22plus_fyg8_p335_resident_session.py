from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/revalidation"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))
p335 = importlib.import_module("s22plus_fyg8_p335_resident_session")
runtime = importlib.import_module("s22plus_fyg8_p335_retained_listener_runtime")


def binding() -> dict:
    run_id = "a1" * 16
    return {
        "target": dict(p335.TARGET),
        "topology": {"sha256": "b2" * 32},
        "candidate": {"run_id": run_id, "boot_sha256": "c3" * 32, "ap_sha256": "d4" * 32},
        "key": {"size": 32, "sha256": "e5" * 32},
        "catalog": p335.catalog_for(run_id),
        "recovery": {"kind": "magisk_boot_only", "owner": "s22plus-fyg8-p335", "rollback_ap_sha256": "f6" * 32},
        "per_boot_id": "07" * 32,
    }


def observation() -> dict:
    return {"state": "OBSERVED", "candidate_boot_ready": True, "journal_sha256": "18" * 32}


def result(status: str = "ok") -> dict:
    return {"status": status, "receipt_bytes": 0, "receipt_sha256": hashlib.sha256(b"").hexdigest()}


class P335ResidentSessionTests(unittest.TestCase):
    def lease(self, root: Path, now: int = 1_000_000) -> p335.ResidentLease:
        return p335.ResidentLease.publish(root, binding(), observation(), now_ns=now, lease_id="12" * 16)

    def test_canonical_json_is_strict_and_typed(self) -> None:
        with self.assertRaises(p335.LeaseError):
            p335.parse_canonical(b'{"a":1,"a":2}')
        with self.assertRaises(p335.LeaseError):
            p335.parse_canonical(b'{"a":1} ')
        with self.assertRaises(p335.LeaseError):
            p335.canonical_bytes({"a": 1.0})
        bad = binding()
        bad["key"]["size"] = True
        with self.assertRaises(p335.LeaseError):
            p335.validate_binding(bad)

    def test_named_catalog_is_the_exact_device_command_tuple(self) -> None:
        catalog = p335.catalog_for(runtime.P335_RUN_ID_HEX)
        commands = tuple(
            " ".join(catalog[name]["argv"]).encode("ascii")
            for name in p335.ACTION_NAMES
        )
        self.assertEqual(commands, tuple(runtime.DEFAULT_COMMANDS))

    def test_publish_requires_durable_observed_ready_and_no_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad = observation()
            bad["candidate_boot_ready"] = False
            with self.assertRaises(p335.LeaseError):
                p335.ResidentLease.publish(root, binding(), bad, now_ns=1)
            lease = self.lease(root)
            self.assertEqual(lease.snapshot(now_ns=1_000_001)["state"], "ACTIVE")
            self.assertEqual(stat.S_IMODE((root / "lease.json").stat().st_mode), 0o400)
            self.assertEqual(stat.S_IMODE((root / "lease.guard.json").stat().st_mode), 0o400)
            with self.assertRaises(p335.LeaseError):
                p335.ResidentLease.publish(root, binding(), observation(), now_ns=2)

    def test_binding_drift_is_durable_rollback_and_active_intent_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.lease(root)
            intent = lease.begin_action("identity", binding(), now_ns=2_000_000)
            with self.assertRaises(p335.RollbackRequired):
                lease.begin_action("kernel", binding(), now_ns=2_000_001)
            self.assertTrue(lease.snapshot()["rollback_required"])
            self.assertEqual(lease.snapshot()["active_intent"], "identity")
            lease.record_action_result(intent, result(), binding(), now_ns=2_000_002)
            changed = binding()
            changed["per_boot_id"] = "19" * 32
            with self.assertRaises(p335.RollbackRequired):
                lease.begin_action("kernel", changed, now_ns=2_000_003)
            self.assertEqual(p335.ResidentLease.open(root).snapshot()["terminal_event"], "DRIFT")

    def test_uncertain_result_never_reopens_the_lease(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.lease(root)
            intent = lease.begin_action("kernel", binding(), now_ns=2_000_000)
            lease.record_action_result(intent, result("uncertain"), binding(), now_ns=2_000_001)
            state = p335.ResidentLease.open(root).snapshot()
            self.assertEqual(state["state"], "ROLLBACK_REQUIRED")
            self.assertEqual(state["terminal_event"], "ACTION_RESULT")
            with self.assertRaises(p335.RollbackRequired):
                lease.begin_action("identity", binding(), now_ns=2_000_002)

    def test_stop_expiry_and_partial_guard_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.lease(root)
            lease.stop()
            self.assertEqual(p335.ResidentLease.open(root).snapshot()["terminal_event"], "STOP")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.lease(root, now=100)
            lease.expire(now_ns=100 + p335.MAX_LEASE_SECONDS * 1_000_000_000)
            self.assertEqual(p335.ResidentLease.open(root).snapshot()["terminal_event"], "EXPIRY")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.lease(root)
            (root / "lease.guard.json").unlink()
            with self.assertRaises(p335.RollbackRequired):
                p335.ResidentLease.open(root)

    def test_sixteen_successful_actions_consume_the_only_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = self.lease(root)
            for ordinal in range(1, p335.MAX_ACTIONS + 1):
                intent = lease.begin_action("session-nonce", binding(), now_ns=2_000_000 + ordinal)
                lease.record_action_result(intent, result(), binding(), now_ns=2_000_000 + ordinal + 1)
            state = p335.ResidentLease.open(root).snapshot()
            self.assertEqual(state["actions_completed"], p335.MAX_ACTIONS)
            self.assertEqual(state["terminal_event"], "ACTION_BUDGET")
            with self.assertRaises(p335.RollbackRequired):
                lease.begin_action("identity", binding(), now_ns=3_000_000)


if __name__ == "__main__":
    unittest.main()
