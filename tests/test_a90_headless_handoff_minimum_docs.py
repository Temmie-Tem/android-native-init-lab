"""Public-only checks for the A90 headless/Wi-Fi ownership H0 boundary."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
GOAL = REPO / "GOAL_A90.md"
CONTRACT = REPO / "docs/operations/targets/A90_TARGET_CONTRACT.md"
PLAN = REPO / (
    "docs/plans/"
    "A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md"
)
INCIDENT = REPO / (
    "docs/reports/"
    "A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md"
)
H24 = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h24/manifest.toml"
)
MAIN = REPO / "workspace/public/src/native-init/v724/90_main.inc.c"
HELPER = REPO / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
HANDOFF = REPO / "workspace/public/src/native-init/a90_server_distro.c"
BENCH = REPO / "workspace/public/src/native-init/a90_benchmark.c"
H26_MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h26/manifest.toml"
)


class A90HeadlessHandoffBoundaryTests(unittest.TestCase):
    def test_current_h24_wifi_sidecar_and_shared_proc_hazard_is_exact(self) -> None:
        manifest = H24.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        helper = HELPER.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")

        self.assertIn('"-DA90_WIFI_PERSISTENT_HANDOFF_V1=1"', manifest)
        self.assertIn('"-DA90_WIFI_AUTOCONNECT_PRIVATE_MOUNT_NS=1"', manifest)
        direct = main[main.index("A90DIRECT_BOOT mode=min-network-wifi") :]
        direct = direct[: direct.index("if (direct_handoff_rc < 0)")]
        self.assertLess(
            direct.index("v1393_run_wifi_test_boot_once();"),
            direct.index("a90_auto_handoff_run_once();"),
        )
        self.assertIn("run_persistent_wifi_handoff", helper)
        self.assertIn("unshare(CLONE_NEWNS)", helper)
        self.assertNotIn("CLONE_NEWPID", helper)
        move = handoff[
            handoff.index("static int d3_move_core_mounts(") :
            handoff.index("static int d3_restore_core_mounts(")
        ]
        self.assertIn('d3_move_mount_one("/proc", "proc")', move)

    def test_contract_requires_wifi_decision_before_candidate(self) -> None:
        contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
        for phrase in (
            "Before allocating that identity, the Wi-Fi ownership boundary must be selected",
            "TRANSFER_FEASIBLE",
            "TRANSFER_REFUTED",
            "NO_PROOF",
            "No headless successor may inherit this process model",
            "fresh attended approval remain mandatory",
        ):
            self.assertIn(phrase, contract)

    def test_plan_separates_minimum_test_features_and_later_removal(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        reduction = (REPO / (
            "docs/plans/"
            "A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md"
        )).read_text(encoding="utf-8")
        for heading in (
            "## Current implementation inventory",
            "## Absolute production requirements",
            "## Wi-Fi ownership gate W0",
            "## Test and benchmark features",
            "## Removal schedule",
            "## Why the implementation became large",
        ):
            self.assertIn(heading, plan)
        self.assertIn("HEALTH_PENDING_PERSISTENT_DEBIAN", plan)
        self.assertIn("Every native helper must be gone before", plan)
        self.assertIn("Benchmark collection never delays", plan)
        self.assertIn("Before any fresh A90 successor candidate", reduction)
        self.assertNotIn("must either retain a known exact SD", reduction)
        self.assertIn("installed artifact and runtime binding contain neither", reduction)

    def test_no_successor_identity_or_live_authority_is_created(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        incident = INCIDENT.read_text(encoding="utf-8")
        self.assertFalse(H26_MANIFEST.exists())
        self.assertIn("No H26 identity or path is", goal)
        self.assertIn("no successor candidate allocated", incident)
        self.assertIn("grants no D0, D1,", incident)
        self.assertIn("Device, `/dev`, USB, network", incident)

    def test_current_benchmark_limit_and_ufs_followup_are_not_overclaimed(self) -> None:
        source = BENCH.read_text(encoding="utf-8")
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn('strcmp(name, "mmcblk0") == 0', source)
        self.assertIn("storage counters from exact UFS whole device `sda`", plan)
        self.assertIn("Missing telemetry is `na`", plan)


if __name__ == "__main__":
    unittest.main()
