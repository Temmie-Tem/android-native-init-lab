"""Pin the A90 WLAN kernel-side composition finding and its declared limits.

The report shifts the prior on which vendor roles are load-bearing, away from
`cnss_daemon` and toward the protection-domain and remote-filesystem group. A
prior is only useful if it was recorded before the experiment and cannot be
quietly reshaped afterwards to match whatever the ablation returns. These tests
hold the claim, the limits it states about itself, and the acquisition status
that gates the confirming evidence.
"""

from __future__ import annotations

from pathlib import Path
import unittest


def flatten(text: str) -> str:
    """Collapse wrapping and blockquote markers, as the sibling docs tests do."""
    return " ".join(text.replace("> ", " ").split())


REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs/reports/A90_WLAN_KERNEL_SIDE_COMPOSITION_H0_2026-08-15.md"
V759 = REPO / "docs/plans/NATIVE_INIT_V759_SOURCE_ACQUISITION_PLAN_2026-05-24.md"
WIFI_OWNERSHIP = REPO / (
    "docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md"
)
ABLATION_DESIGN = REPO / (
    "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
    "/design/a90-h24-wlan-one-factor-ablation-design-v1.json"
)
CONFIG = REPO / "workspace/private/outputs/a90-phase2a-kernel.tBOMsQ/v3404.config"

# Every symbol the report quotes as an established fact. If the staged artifact
# stops agreeing with the report, the report is wrong, not the artifact.
QUOTED_SET = (
    "CONFIG_QCA_CLD_WLAN=y",
    "CONFIG_ICNSS=y",
    "CONFIG_ICNSS_QMI=y",
    "CONFIG_BTFM_SLIM_WCN3990=y",
    "CONFIG_QRTR=y",
    "CONFIG_QRTR_SMD=y",
    "CONFIG_QCOM_QMI_HELPERS=y",
    "CONFIG_QCOM_MDT_LOADER=y",
    "CONFIG_QCOM_SCM=y",
    "CONFIG_QCOM_SMEM=y",
    "CONFIG_MSM_PIL=y",
    "CONFIG_MSM_PIL_SSR_GENERIC=y",
    "CONFIG_MSM_SUBSYSTEM_RESTART=y",
    "CONFIG_CNSS_UTILS=y",
    "CONFIG_CNSS_GENL=y",
    "CONFIG_WCNSS_MEM_PRE_ALLOC=y",
)
QUOTED_UNSET = (
    "# CONFIG_CNSS2 is not set",
    "# CONFIG_CNSS is not set",
    "# CONFIG_PCIE_QCOM is not set",
    "# CONFIG_REMOTEPROC is not set",
)


class KernelSideCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = flatten(REPORT.read_text(encoding="utf-8"))
        self.raw = REPORT.read_text(encoding="utf-8")

    def test_the_quoted_symbols_match_the_staged_configuration(self) -> None:
        """The one test that can catch the report inventing its own evidence."""
        if not CONFIG.is_file():
            self.skipTest(f"private artifact not staged on this host: {CONFIG}")
        config = CONFIG.read_text(encoding="utf-8", errors="replace").splitlines()
        present = set(line.strip() for line in config)
        for symbol in QUOTED_SET + QUOTED_UNSET:
            self.assertIn(symbol, present, symbol)
            self.assertIn(symbol, self.raw, symbol)

    def test_the_report_states_the_compiled_versus_executed_limit_first(self) -> None:
        """This is the likeliest way the report is wrong, so it leads."""
        self.assertIn("proves what is **compiled in**, never what **executes**", self.report)
        self.assertIn("is a **prior**", self.report)
        head = flatten(self.raw[: self.raw.index("## Why this report exists")])
        self.assertIn("compiled in", head)

    def test_the_kernel_rebuild_question_is_answered_negatively(self) -> None:
        self.assertIn("rebuilding this kernel from its own sources removes none of the", self.report)
        self.assertIn("execution cost is unchanged by it", self.report)
        self.assertIn("not a WLAN ownership lever", self.report)

    def test_the_integrated_path_is_distinguished_from_the_pcie_path(self) -> None:
        """Evidence written for CNSS2 does not describe this device."""
        self.assertIn("integrated** WCN3990 path, not the PCIe CNSS2 path", self.report)
        self.assertIn("evidence written for one does not describe the other", self.report)

    def test_the_prior_shift_has_a_stated_direction(self) -> None:
        self.assertIn("weaker suspect than the record implies", self.report)
        self.assertIn("stronger suspect", self.report)
        self.assertIn("**away from the single daemon whose name matches the subsystem**", self.report)
        self.assertIn("**toward the protection-domain and remote-filesystem group**", self.report)

    def test_the_qrtr_ns_corroboration_is_recorded(self) -> None:
        """An internal check that does not depend on recollection about vintages."""
        self.assertIn("independent corroboration", self.report)
        self.assertIn("a userspace `qrtr_ns` can only be present because the name service is not", self.report)

    def test_the_report_refuses_the_overreadings_of_its_own_finding(self) -> None:
        self.assertIn("does not prove `cnss_daemon` removable", self.report)
        self.assertIn("does not prove the protection-domain group required", self.report)
        self.assertIn("does not re-attribute WSTA18", self.report)
        self.assertIn("does not license reordering the ablation program", self.report)
        self.assertIn("remains a real experiment with a real possible failure", self.report)

    def test_the_mainline_lead_is_marked_unverified(self) -> None:
        """Recollection has been wrong here before; the label is the safeguard."""
        self.assertIn("unverified recollection, not repository evidence", self.report)
        self.assertIn("Do not cite it as a basis for any decision until checked", self.report)
        self.assertIn("It is not proposed here", self.report)
        self.assertIn("trade is a working system for an unproved one", self.report)

    def test_the_acquisition_status_names_the_matching_build(self) -> None:
        self.assertIn("A908NKSU5EWA3", self.report)
        self.assertIn("`13272`", self.report)
        self.assertIn("reasoning about the running kernel requires the matching build", self.report)

    def test_the_captcha_gate_is_recorded_without_a_bypass(self) -> None:
        self.assertIn("terminates at an hCaptcha human-verification step", self.report)
        self.assertIn("No bypass was attempted and none is authorized", self.report)
        self.assertIn("Acquisition is an operator action", self.report)

    def test_the_stale_source_residue_is_described_accurately(self) -> None:
        self.assertIn("residue of eleven files", self.report)
        self.assertIn("matching `recovery` in its filename", self.report)

    def test_the_unexecuted_v759_plan_is_cited_and_still_says_so(self) -> None:
        self.assertTrue(V759.is_file(), str(V759))
        plan = flatten(V759.read_text(encoding="utf-8"))
        self.assertIn("no hCaptcha bypass attempt", plan)
        self.assertIn("no hCaptcha bypass attempt", self.report)
        self.assertIn("no runner and no report", self.report)

    def test_no_gate_is_retired_and_no_authority_is_created(self) -> None:
        self.assertIn("changes none of its gates", self.report)
        self.assertIn("remain `UNPROVED`", self.report)
        self.assertIn("Device or live effect: none", self.report)
        self.assertIn("no human-verification bypass", self.report)
        self.assertIn("authority is granted or implied", self.report)

    def test_the_cited_companions_still_exist(self) -> None:
        for path in (WIFI_OWNERSHIP, ABLATION_DESIGN):
            self.assertTrue(path.is_file(), str(path))


if __name__ == "__main__":
    unittest.main()
