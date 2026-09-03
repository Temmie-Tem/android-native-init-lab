from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p331_stock_process_v2_adapter as adapter  # noqa: E402


class P331StockProcessV2AdapterTests(unittest.TestCase):
    def test_acceptance_is_fresh_bounded_resident(self) -> None:
        value = adapter.acceptance_fixture()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["run_id"], adapter.P331_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id_rejected"], adapter.P330_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["overlay_contract_id"], adapter.OVERLAY_CONTRACT_ID)
        self.assertEqual(value["decoder"], adapter.DECODER_ID)
        self.assertEqual(value["observer_contract"]["id"], adapter.OBSERVER_CONTRACT_ID)
        self.assertEqual(value["resident_sessions"], 2)
        self.assertEqual(value["resident_reconnects"], 1)
        self.assertTrue(value["fixed_heartbeat_only"])
        self.assertFalse(value["candidate_success"])

    def test_audit_does_not_grant_device_authority(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["verdict"], "PASS_P331_STOCK_PROCESS_V2_ADAPTER_H0_RESIDENT_UDEV_SETTLE")
        self.assertEqual(value["run_id"], adapter.P331_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], adapter.P330_PREDECESSOR_RUN_ID_HEX)
        self.assertTrue(value["resident_sessions_bounded"])
        self.assertTrue(value["resident_reconnect_bounded"])
        self.assertTrue(value["fixed_heartbeat_only"])
        self.assertFalse(value["lineage"]["auth_key_path_published"])
        self.assertNotEqual(value["overlay_contract_id"], "s22plus-fyg8-p330-authenticated-exec-udev-settle-diagnostic-v1")


if __name__ == "__main__":
    unittest.main()
