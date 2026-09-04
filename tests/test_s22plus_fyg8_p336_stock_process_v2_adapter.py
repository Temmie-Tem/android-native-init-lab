from __future__ import annotations

from pathlib import Path
import copy
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p336_stock_process_v2_adapter as adapter  # noqa: E402


class P336StockProcessV2AdapterTests(unittest.TestCase):
    def test_fresh_contract_and_exact_long_idle_projection(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["run_id"], adapter.P336_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], adapter.P335_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["observer_contract_id"], adapter.P336_OBSERVER_CONTRACT_ID)
        self.assertEqual(value["resident_lease_schema"], adapter.LEASE_SCHEMA)
        self.assertEqual(value["command_count_per_session"], 3)
        self.assertFalse(value["fixed_heartbeat_only"])
        self.assertTrue(value["fixed_p330_commands"])
        self.assertTrue(value["long_idle_host_resync"])
        self.assertTrue(value["later_action_open_before_resync"])
        self.assertFalse(value["action_retry"])

    def test_acceptance_rejects_p335_and_has_named_three_command_catalog(self) -> None:
        value = adapter.acceptance_fixture()
        self.assertEqual(adapter.validate_acceptance_item(value), value)
        self.assertEqual(value["run_id"], adapter.P336_RUN_ID_HEX)
        self.assertIn(adapter.P335_PREDECESSOR_RUN_ID_HEX, value["predecessor_run_ids_rejected"])
        self.assertEqual(value["command_count_per_session"], 3)
        self.assertEqual(len(adapter.DEFAULT_COMMANDS), 3)
        self.assertEqual(
            adapter.DEFAULT_COMMANDS[2],
            f"/bin/busybox echo P328-NONCE {adapter.P336_RUN_ID_HEX}".encode("ascii"),
        )
        self.assertEqual(value["resident_lease_schema"], adapter.LEASE_SCHEMA)
        self.assertTrue(value["long_idle_host_resync"])
        self.assertFalse(value["caller_selected_command"] if "caller_selected_command" in value else False)

        changed = copy.deepcopy(value)
        changed["run_id"] = adapter.P335_PREDECESSOR_RUN_ID_HEX
        with self.assertRaises(adapter.ContractError):
            adapter.validate_acceptance_item(changed)

    def test_contract_validator_owns_the_p336_identity(self) -> None:
        value = adapter.audit()["contract"]
        self.assertEqual(adapter.validate_contract(value), value)
        changed = dict(value)
        changed["userspace_overlay_contract_id"] = "s22plus-fyg8-p335-attended-resident-v1"
        with self.assertRaises(adapter.ContractError):
            adapter.validate_contract(changed)

    def test_wrong_expected_identity_is_fail_closed(self) -> None:
        with self.assertRaises(adapter.AdapterIdentityError):
            adapter.classify_observation(
                b"",
                expected_profile=adapter.PROFILE,
                expected_run_id=adapter.P335_PREDECESSOR_RUN_ID,
            )

    def test_source_pin_does_not_publish_auth_key(self) -> None:
        self.assertEqual(adapter.identity(adapter.SOURCE.read_bytes()), adapter.SOURCE_IDENTITY)
        bound = adapter.bind_exact_sources()
        self.assertEqual(bound["run_id"], adapter.P336_RUN_ID_HEX)
        self.assertFalse(bound.get("auth_key_path_published", True))


if __name__ == "__main__":
    unittest.main()
