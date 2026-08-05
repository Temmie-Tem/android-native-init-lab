"""Host-only contract tests for the A90 H2 F1 and D1 integration."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_phase2d_finalize_f1 as finalizer  # noqa: E402
import a90_resident_manifest_builder_v1 as builder  # noqa: E402
import a90_resident_promotion_v1 as promotion  # noqa: E402
import a90_v3403_f1_orchestrator as orchestrator  # noqa: E402


EXPECTED_FIRST_BOOT = {
    "schema": "a90-auto-handoff-first-boot-v1",
    "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h2.enable",
    "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h2.done",
    "pre_transfer_state": "both-absent",
    "post_boot_status": "binding=1-enable=0-latch=0",
    "post_boot_log": "A90AUTO state=unarmed-stay-native",
}


def receipt(command: list[str], text: str, *, rc: int = 0) -> dict:
    return {
        "command": command,
        "rc": rc,
        "status": "ok" if rc == 0 else "error",
        "trust": "A90P1_V1_STRUCTURAL_ONLY",
        "begin": {
            "argc": str(len(command)),
            "cmd": command[0],
            "flags": "0x0",
            "seq": "1",
        },
        "end": {
            "cmd": command[0],
            "duration_ms": "1",
            "errno": "0",
            "flags": "0x0",
            "rc": str(rc),
            "seq": "1",
            "status": "ok" if rc == 0 else "error",
        },
        "text": text,
    }


class A90H2LiveIntegrationV1Tests(unittest.TestCase):
    def test_manifest_consumers_bind_one_exact_h2_candidate(self) -> None:
        left = finalizer.MINIMAL_H2_CANDIDATE
        right = builder.MINIMAL_H2_CANDIDATE
        self.assertEqual(
            (left.size, left.sha256, left.version, left.build),
            (right.size, right.sha256, right.version, right.build),
        )
        self.assertEqual(finalizer.candidate_first_boot_contract(left), EXPECTED_FIRST_BOOT)
        self.assertEqual(builder.candidate_first_boot_contract(right), EXPECTED_FIRST_BOOT)

    def test_orchestrator_requires_exact_h2_first_boot_contract(self) -> None:
        value = orchestrator.validate_candidate_first_boot_contract(
            EXPECTED_FIRST_BOOT,
            candidate_version="0.11.170",
            candidate_build="phase3-minimal-h2-two-phase-auto-benchmark",
        )
        self.assertEqual(value, EXPECTED_FIRST_BOOT)
        with self.assertRaisesRegex(orchestrator.ContractError, "not exact"):
            orchestrator.validate_candidate_first_boot_contract(
                None,
                candidate_version="0.11.170",
                candidate_build="phase3-minimal-h2-two-phase-auto-benchmark",
            )
        with self.assertRaisesRegex(orchestrator.ContractError, "unexpected"):
            orchestrator.validate_candidate_first_boot_contract(
                EXPECTED_FIRST_BOOT,
                candidate_version="0.11.168",
                candidate_build="phase3-minimal-g-server-core",
            )

    def test_f1_source_orders_absence_and_first_boot_proofs(self) -> None:
        source = Path(orchestrator.__file__).read_text(encoding="utf-8")
        main = source[
            source.index("def execute_approved_f1(") :
            source.index("def continue_attended_f1(")
        ]
        absence = main.index("require_candidate_first_boot_state_absent(spec, args)")
        transfer = main.index('"candidate-transfer-started"')
        candidate_health = main.index("candidate_health = verify_candidate_health(")
        unarmed = main.index("require_candidate_first_boot_unarmed(")
        boot_ready = main.index('"candidate-boot-ready"')
        self.assertLess(absence, transfer)
        self.assertLess(candidate_health, unarmed)
        self.assertLess(unarmed, boot_ready)

    def test_resident_repair_revalidates_h2_first_boot_proofs(self) -> None:
        status = receipt(
            ["auto-handoff-status"],
            (
                "A90AUTO_STATUS binding=1 enable=0 latch=0 "
                "build=phase3-minimal-h2-two-phase-auto-benchmark\n"
            ),
        )
        log = receipt(["logcat"], "A90AUTO state=unarmed-stay-native\n")
        preflight_script = orchestrator.candidate_first_boot_state_absence_script(
            EXPECTED_FIRST_BOOT
        )
        by_action = {
            "rootfs-candidate-preflight": {
                "candidate_first_boot_preflight": {
                    "proof": True,
                    "enable_path": EXPECTED_FIRST_BOOT["enable_path"],
                    "latch_path": EXPECTED_FIRST_BOOT["latch_path"],
                    "record": receipt(
                        ["run", "/bin/busybox", "sh", "-c", preflight_script],
                        "A90AUTO_F1_PRE enable_absent=1 latch_absent=1\n",
                    ),
                }
            },
            "candidate-boot-ready": {
                "candidate_first_boot_health": {
                    "proof": True,
                    "status": status,
                    "log": log,
                    "enable": 0,
                    "latch": 0,
                    "unarmed_log_unique": True,
                }
            },
        }
        spec = SimpleNamespace(candidate_first_boot=EXPECTED_FIRST_BOOT)
        promotion._validate_candidate_first_boot_journal(spec, by_action)
        by_action["candidate-boot-ready"]["candidate_first_boot_health"][
            "latch"
        ] = 1
        with self.assertRaisesRegex(promotion.ContractError, "proof changed"):
            promotion._validate_candidate_first_boot_journal(spec, by_action)

    def test_f1_repair_rejects_substring_only_and_wrong_command_receipts(self) -> None:
        status = receipt(
            ["auto-handoff-status"],
            "A90AUTO_STATUS binding=1 enable=0 latch=0 "
            "build=phase3-minimal-h2-two-phase-auto-benchmark\n",
        )
        log = receipt(["logcat"], "A90AUTO state=unarmed-stay-native\n")
        preflight_script = orchestrator.candidate_first_boot_state_absence_script(
            EXPECTED_FIRST_BOOT
        )
        by_action = {
            "rootfs-candidate-preflight": {
                "candidate_first_boot_preflight": {
                    "proof": True,
                    "enable_path": EXPECTED_FIRST_BOOT["enable_path"],
                    "latch_path": EXPECTED_FIRST_BOOT["latch_path"],
                    "record": receipt(
                        ["run", "/bin/busybox", "sh", "-c", preflight_script],
                        "A90AUTO_F1_PRE enable_absent=1 latch_absent=1\n",
                    ),
                }
            },
            "candidate-boot-ready": {
                "candidate_first_boot_health": {
                    "proof": True,
                    "status": status,
                    "log": log,
                    "enable": 0,
                    "latch": 0,
                    "unarmed_log_unique": True,
                }
            },
        }
        spec = SimpleNamespace(candidate_first_boot=EXPECTED_FIRST_BOOT)
        for mutate in (
            lambda value: value["rootfs-candidate-preflight"][
                "candidate_first_boot_preflight"
            ].__setitem__("record", {"text": "A90AUTO_F1_PRE enable_absent=1 latch_absent=1"}),
            lambda value: value["candidate-boot-ready"][
                "candidate_first_boot_health"
            ]["status"].__setitem__("command", ["logcat"]),
            lambda value: value["candidate-boot-ready"][
                "candidate_first_boot_health"
            ]["log"].__setitem__("rc", 9),
        ):
            import copy

            changed = copy.deepcopy(by_action)
            mutate(changed)
            with self.assertRaises((promotion.ContractError, orchestrator.ContractError)):
                promotion._validate_candidate_first_boot_journal(spec, changed)

    def test_non_h2_journal_rejects_unexpected_first_boot_proof(self) -> None:
        spec = SimpleNamespace(candidate_first_boot=None)
        by_action = {
            "rootfs-candidate-preflight": {},
            "candidate-boot-ready": {},
        }
        promotion._validate_candidate_first_boot_journal(spec, by_action)
        by_action["candidate-boot-ready"]["candidate_first_boot_health"] = {}
        with self.assertRaisesRegex(promotion.ContractError, "non-H2"):
            promotion._validate_candidate_first_boot_journal(spec, by_action)


if __name__ == "__main__":
    unittest.main()
