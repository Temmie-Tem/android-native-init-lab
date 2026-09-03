from __future__ import annotations

from pathlib import Path
import copy
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p335_stock_process_v2_adapter as adapter  # noqa: E402


class P335StockProcessV2AdapterTests(unittest.TestCase):
    def test_fresh_contract_and_exact_runtime_observer_binding(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["run_id"], adapter.P335_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], adapter.P334_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(
            value["observer_contract_id"],
            "s22plus-fyg8-p335-retained-listener-acm-observer-v1",
        )
        self.assertEqual(value["resident_sessions"], 3)
        self.assertEqual(value["resident_reconnects"], 1)
        self.assertTrue(value["host_tty_close_reopen"])
        self.assertTrue(value["transport_reconnect"])
        self.assertFalse(value["fixed_heartbeat_only"])
        self.assertTrue(value["fixed_p330_commands"])
        self.assertFalse(value["action_retry"])

    def test_acceptance_rejects_p334_and_keeps_named_command_catalog(self) -> None:
        value = adapter.acceptance_fixture()
        self.assertEqual(adapter.validate_acceptance_item(value), value)
        self.assertEqual(value["run_id"], adapter.P335_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id_rejected"], adapter.P334_PREDECESSOR_RUN_ID_HEX)
        self.assertIn(adapter.P334_PREDECESSOR_RUN_ID_HEX, value["predecessor_run_ids_rejected"])
        self.assertEqual(value["command_count_per_session"], 3)
        self.assertEqual(len(adapter.DEFAULT_COMMANDS), 3)
        self.assertEqual(
            adapter.DEFAULT_COMMANDS[2],
            f"/bin/busybox echo P328-NONCE {adapter.P335_RUN_ID_HEX}".encode("ascii"),
        )
        self.assertTrue(value["per_boot_identity_required"])
        self.assertEqual(value["resident_lease_schema"], "s22plus_fyg8_p335_resident_lease_v1")
        self.assertNotIn("first_console_return_checkpoint_only", value)

        changed = copy.deepcopy(value)
        changed["run_id"] = adapter.P334_PREDECESSOR_RUN_ID_HEX
        with self.assertRaises(adapter.ContractError):
            adapter.validate_acceptance_item(changed)

    def test_contract_validator_owns_the_p335_identity(self) -> None:
        value = adapter.audit()["contract"]
        self.assertEqual(adapter.validate_contract(value), value)
        changed = dict(value)
        changed["userspace_overlay_contract_id"] = "s22plus-fyg8-p334-first-read-rc-v1"
        with self.assertRaises(adapter.ContractError):
            adapter.validate_contract(changed)

    def test_wrong_expected_identity_is_fail_closed(self) -> None:
        with self.assertRaises(adapter.AdapterIdentityError):
            adapter.classify_observation(
                b"",
                expected_profile=adapter.PROFILE,
                expected_run_id=adapter.P334_RUN_ID,
            )

    def test_source_pin_is_exact_and_auth_key_is_not_published(self) -> None:
        self.assertEqual(adapter.SOURCE.stat().st_size, adapter.SOURCE_IDENTITY["size"])
        self.assertEqual(adapter.identity(adapter.SOURCE.read_bytes()), adapter.SOURCE_IDENTITY)
        bound = adapter.bind_exact_sources()
        self.assertEqual(bound["run_id"], adapter.P335_RUN_ID_HEX)
        self.assertFalse(bound.get("auth_key_path_published", True))


if __name__ == "__main__":
    unittest.main()
