from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p327_framed_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p327_framed_exec_runtime as runtime  # noqa: E402


def framed_observer() -> dict[str, object]:
    return {
        "kind": "exact_cdc_acm_framed_fixed_commands_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + runtime.P327_RUN_ID_HEX,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": runtime.DEVICE_BANNER.hex(),
        "protocol_contract": observer.CONTRACT_ID,
        "wire_magic": "S327",
        "frame_header_size": 16,
        "max_frame_payload": 1024,
        "max_commands": 3,
        "command_timeout_sec": 10,
        "max_output_bytes": 131072,
        "commands": [
            {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
            for command in observer.DEFAULT_COMMANDS
        ],
        "caller_selected_command": False,
        "interactive_pty": False,
    }


class P327CommonRegistrationTests(unittest.TestCase):
    def test_framed_role_accepts_only_exact_observer(self) -> None:
        value = framed_observer()
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
                value,
                expected_run_id=runtime.P327_RUN_ID_HEX,
            ),
            evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
        )
        changed = dict(value)
        changed["interactive_pty"] = True
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
                changed,
                expected_run_id=runtime.P327_RUN_ID_HEX,
            )

    def test_core_observer_binding_rejects_predecessor_and_missing_observer(self) -> None:
        acceptance = {
            "source_contract_id": "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1",
            "profile": "E2",
            "run_id": runtime.P327_RUN_ID_HEX,
            "userspace_overlay_contract_id": (
                evidence.P327_STOCK_OVERLAY_CONTRACT_ID
            ),
        }
        core.verify_candidate_observer_binding(acceptance, framed_observer())
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(acceptance, None)
        predecessor = framed_observer()
        predecessor["banner_hex"] = (
            "S22PLUS-FYG8-E3:" + "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b" + "\n"
        ).encode().hex()
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(acceptance, predecessor)

    def test_p327_overlay_is_registered_without_predecessor_alias(self) -> None:
        self.assertIs(
            evidence.STOCK_ADAPTERS[evidence.P327_STOCK_OVERLAY_CONTRACT_ID],
            evidence.p327_stock_adapter,
        )
        self.assertNotEqual(
            evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
            evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
        )
        self.assertNotEqual(evidence.P327_RUN_ID, evidence.P326_RUN_ID)


if __name__ == "__main__":
    unittest.main()
