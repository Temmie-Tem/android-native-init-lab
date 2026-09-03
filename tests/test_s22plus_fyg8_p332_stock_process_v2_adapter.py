from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p332_stock_process_v2_adapter as adapter  # noqa: E402


class P332StockProcessV2AdapterTests(unittest.TestCase):
    def test_acceptance_is_two_fixed_p330_sessions_on_one_tty(self) -> None:
        value = adapter.acceptance_fixture()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["run_id"], adapter.P332_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_ids_rejected"],
            [adapter.P330_PREDECESSOR_RUN_ID_HEX, adapter.P331_PREDECESSOR_RUN_ID_HEX],
        )
        self.assertEqual(value["overlay_contract_id"], adapter.OVERLAY_CONTRACT_ID)
        self.assertEqual(value["decoder"], adapter.DECODER_ID)
        self.assertEqual(value["observer_contract"]["id"], adapter.OBSERVER_CONTRACT_ID)
        self.assertEqual(value["resident_sessions"], 2)
        self.assertEqual(value["resident_reconnects"], 0)
        self.assertEqual(value["command_count_per_session"], 3)
        self.assertTrue(value["fixed_p330_commands"])
        self.assertFalse(value["fixed_heartbeat_only"])
        self.assertTrue(value["logical_same_tty"])
        self.assertFalse(value["host_tty_close_reopen"])
        self.assertFalse(value["transport_reconnect"])
        self.assertFalse(value["candidate_success"])

    def test_audit_does_not_grant_device_authority(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(
            value["verdict"],
            "PASS_P332_STOCK_PROCESS_V2_ADAPTER_H0_LOGICAL_RESIDENT",
        )
        self.assertEqual(value["run_id"], adapter.P332_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_ids"],
            [adapter.P330_PREDECESSOR_RUN_ID_HEX, adapter.P331_PREDECESSOR_RUN_ID_HEX],
        )
        self.assertTrue(value["logical_same_tty_bounded"])
        self.assertFalse(value["resident_reconnect_bounded"])
        self.assertFalse(value["fixed_heartbeat_only"])
        self.assertTrue(value["fixed_p330_commands"])
        self.assertFalse(value["lineage"]["auth_key_path_published"])
        self.assertEqual(
            adapter.OBSERVER_CONTRACT_ID,
            "s22plus-fyg8-p332-logical-resident-acm-observer-v1",
        )

    def test_retained_raw_classification_clears_caller_selected_claim(self) -> None:
        record = adapter.encode_fixture()
        raw = bytes(adapter.RAW_SIZE - len(record)) + record
        value = adapter.classify_observation(raw)
        self.assertEqual(value["run_id"], adapter.P332_RUN_ID_HEX)
        self.assertTrue(value["authenticated_exec"])
        self.assertTrue(value["authentication_required"])
        self.assertFalse(value["caller_selected_command"])
        self.assertFalse(value["auth_key_path_published"])


if __name__ == "__main__":
    unittest.main()
