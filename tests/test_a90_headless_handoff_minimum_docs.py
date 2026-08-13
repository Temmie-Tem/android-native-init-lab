"""Public-only checks for the A90 headless isolation H0 boundary."""

from __future__ import annotations

import os
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
GOAL = REPO / "GOAL_A90.md"
CONTRACT = REPO / "docs/operations/targets/A90_TARGET_CONTRACT.md"
PLAN = REPO / (
    "docs/plans/"
    "A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md"
)
DIAGNOSTIC_DESIGN = REPO / (
    "docs/plans/"
    "A90_ATOMIC_WIFI_OWNERSHIP_DIAGNOSTIC_RESIDENT_DESIGN_2026-08-14.md"
)
ISOLATED_DESIGN = REPO / (
    "docs/plans/"
    "A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md"
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
REAPER = REPO / "workspace/public/src/native-init/a90_reaper.c"
SHELL_DISPATCH = REPO / (
    "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
)
RETIRED_W0_RUNNER = REPO / (
    "workspace/public/src/scripts/server-distro/"
    "a90_h24_wifi_ownership_w0_runner_v1.py"
)
RETIRED_W0_TEST = REPO / "tests/test_a90_h24_wifi_ownership_w0_v1.py"
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

    def test_contract_requires_isolation_decision_before_candidate(self) -> None:
        contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
        for phrase in (
            "Before allocating that identity, the Wi-Fi ownership boundary must be selected",
            "A90_WIFI_OWNERSHIP_ATOMICITY_GATE_V1",
            "attempted atomic diagnostic is `NO_GO_RETIRED`",
            "A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md",
            "fresh PID, mount, and network namespaces",
            "bound veth peer",
            "HEALTH_PENDING_PERSISTENT_DEBIAN",
            "No headless successor may inherit this process model",
        ):
            self.assertIn(phrase, contract)

    def test_h24_shell_inventory_is_retired_as_mutating_not_d0(self) -> None:
        dispatch = SHELL_DISPATCH.read_text(encoding="utf-8")
        reaper = REAPER.read_text(encoding="utf-8")
        goal = GOAL.read_text(encoding="utf-8")

        self.assertIn('a90_reaper_reap_orphans("shell-prompt")', dispatch)
        self.assertIn('a90_reaper_reap_orphans("cmd-end")', dispatch)
        self.assertIn("waitpid(-1, &status, WNOHANG)", reaper)
        self.assertIn("a `run`-based inventory is not connected read-only D0", goal)
        self.assertFalse(os.path.lexists(RETIRED_W0_RUNNER))
        self.assertFalse(os.path.lexists(RETIRED_W0_TEST))

    def test_plan_separates_minimum_test_features_and_later_removal(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        reduction = (REPO / (
            "docs/plans/"
            "A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md"
        )).read_text(encoding="utf-8")
        reduction_flat = " ".join(reduction.split())
        for heading in (
            "## Current implementation inventory",
            "## Absolute production requirements",
            "## Wi-Fi ownership diagnostic disposition",
            "## Test and benchmark features",
            "## Removal schedule",
            "## Why the implementation became large",
        ):
            self.assertIn(heading, plan)
        self.assertIn("HEALTH_PENDING_PERSISTENT_DEBIAN", plan)
        self.assertIn("Native PID 1 retains the exact native Wi-Fi owner", plan)
        self.assertIn("Benchmark collection never delays", plan)
        self.assertIn("atomic diagnostic grant no exception", reduction_flat)
        self.assertIn("no diagnostic identity", reduction_flat)
        self.assertIn(
            "installed artifact and runtime binding contain neither",
            reduction_flat,
        )

    def test_atomic_diagnostic_is_retired_and_not_live_authority(self) -> None:
        design = " ".join(DIAGNOSTIC_DESIGN.read_text(encoding="utf-8").split())
        for phrase in (
            "Status: `NO_GO_RETIRED`",
            "historical rejected design only",
            "different UID/GID/capability identities",
            "would defeat the production reduction objective",
            "No code, candidate identity, manifest, approval",
            "This retired diagnostic can never satisfy the gate",
        ):
            self.assertIn(phrase, design)

    def test_selected_isolated_debian_design_is_bounded_h0(self) -> None:
        design = " ".join(ISOLATED_DESIGN.read_text(encoding="utf-8").split())
        for phrase in (
            "Native PID 1 does not call the current in-place `switch_root`",
            "separate PID, mount, and network namespaces",
            "reviewed veth and forwarding boundary",
            "default drop in both forwarding directions",
            "The SD card is not a runtime dependency",
            "duplicates only the two child write ends to reviewed fixed descriptor numbers",
            "`HEALTH_PENDING_PERSISTENT_DEBIAN`",
            "neither a shared network namespace nor a userspace proxy is an allowed fallback",
            "No H26 ordinal, version, build string",
            "This document is H0 only",
        ):
            self.assertIn(phrase, design)

    def test_no_successor_identity_or_live_authority_is_created(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        incident = INCIDENT.read_text(encoding="utf-8")
        self.assertFalse(os.path.lexists(H26_MANIFEST))
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
