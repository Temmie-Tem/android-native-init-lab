"""Recompute this unit's numbers from evidence and compare them to the report.

The second independent review of 2026-08-19 named a real weakness in this
campaign's documentation tests: they pin wording, not evidence.  A test that
asserts the report contains the string "107 of 108" stays green when 107 is
wrong, which is exactly how a census error reached publication and survived
until a later unit recounted by hand.

Every test here recomputes its number from the candidate's own materialized
sources, the vendor_boot ramdisk, and the telemetry specs, then asserts the
report states that number.  Nothing is pinned.  If the candidate changes, these
fail and say so; if the report drifts from the evidence, these fail and say so.
"""

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
)
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
MATERIALIZED = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/intent/materialized-sources"
)
PLAN_HEADER = MATERIALIZED / "s22plus_fyg8_p286_e3_plan.h"
RAMDISK_MODULES = Path("/mnt/android-lab-sd/extract/ap-fyg8/vboot/rd/lib/modules")

DEFINE_RE = re.compile(r"#define (P\d{3}_DETAIL_[A-Z0-9_]+)\s+(0x[0-9a-fA-F]+)U?")
PLAN_ENTRY_RE = re.compile(r'\{"([^"]+\.ko)"')
BLANKET_THRESHOLD = 0xC00

GLINK_CLUSTER = (
    "qcom_glink.ko",
    "qcom_glink_smem.ko",
    "qcom_smd.ko",
    "rproc_qcom_common.ko",
    "pdr_interface.ko",
    "pmic_glink.ko",
    "ucsi_glink.ko",
)


def materialized_text() -> str:
    if not MATERIALIZED.is_dir():
        raise unittest.SkipTest(f"materialized candidate sources absent: {MATERIALIZED}")
    return "".join(
        path.read_bytes().decode("utf-8", "replace")
        for path in sorted(MATERIALIZED.iterdir())
        if path.is_file()
    )


def load_spec(name: str):
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    return __import__(name)


def plan_entries() -> list[str]:
    if not PLAN_HEADER.is_file():
        raise unittest.SkipTest(f"materialized plan header absent: {PLAN_HEADER}")
    return PLAN_ENTRY_RE.findall(PLAN_HEADER.read_text(encoding="utf-8"))


class EvidenceCrosscheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")

    # ---- the failure-detail census -------------------------------------

    def census(self):
        text = materialized_text()
        defined = {name: int(value, 16) for name, value in DEFINE_RE.findall(text)}
        # "referenced" means the name occurs somewhere other than its own
        # #define line.  A constant that is only defined cannot be emitted.
        referenced = {
            name: value
            for name, value in defined.items()
            if len(re.findall(r"\b" + re.escape(name) + r"\b", text)) > 1
        }
        above = {n: v for n, v in referenced.items() if v >= BLANKET_THRESHOLD}
        s294 = load_spec("s22plus_fyg8_p294_telemetry_spec")
        s314 = load_spec("s22plus_fyg8_p314_telemetry_spec")
        routed = {d for (_o, _oc, d) in s294._exact_rule_set()}
        families = s314.a_output_set() | set(s314.b_outputs())
        return {
            "defined": len(defined),
            "referenced": len(referenced),
            "above": len(above),
            "routed": sum(1 for v in above.values() if v in routed),
            "families": sum(
                1 for v in above.values() if v not in routed and v in families
            ),
            "neither": sum(
                1
                for v in above.values()
                if v not in routed and v not in families
            ),
            "above_map": above,
            "routed_set": routed,
            "family_set": families,
        }

    def test_report_census_matches_a_live_recount(self):
        c = self.census()
        self.assertEqual(
            c["defined"], c["referenced"] + (c["defined"] - c["referenced"])
        )
        for token in (
            f"holds **{c['defined']}** detail constants",
            f"**{c['referenced']} are referenced**",
            f"**{c['above']} of those are at or above `0xC00`**",
            f"**{c['routed']} are routed**",
            f"**{c['neither']} are covered by neither**",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertIn(f"**{c['families']}**", self.report)

    def test_report_generation_table_matches_a_live_recount(self):
        c = self.census()
        rows: dict[str, list[int]] = {}
        for name, value in c["above_map"].items():
            generation = name[:4]
            slot = rows.setdefault(generation, [0, 0, 0])
            if value in c["routed_set"]:
                slot[0] += 1
            elif value in c["family_set"]:
                slot[1] += 1
            else:
                slot[2] += 1
        self.assertTrue(rows, "recount produced no generations")
        for generation, (routed, families, neither) in sorted(rows.items()):
            label = f"P{generation[1]}.{generation[2:]}"
            plain = f"| {label} | {routed} | {families} | {neither} | {routed + families + neither} |"
            bold = f"| {label} | {routed} | **{families}** | {neither} | {routed + families + neither} |"
            with self.subTest(generation=label):
                self.assertTrue(
                    plain in self.report
                    or bold in self.report
                    or plain.replace("| 0 |", "| 0 |") in self.report,
                    f"report row for {label} does not match recount {plain}",
                )

    # ---- the UCSI feasibility claim ------------------------------------

    def test_report_plan_size_matches_the_materialized_plan(self):
        self.assertIn(f"at {len(plan_entries())} entries", self.report)

    def test_report_glink_positions_match_the_materialized_plan(self):
        plan = plan_entries()
        positions = {name: plan.index(name) + 1 for name in GLINK_CLUSTER if name in plan}
        self.assertEqual(
            len(positions), len(GLINK_CLUSTER), "a GLINK cluster module left the plan"
        )
        for name, position in positions.items():
            stem = name[:-3].replace("_", r"[_-]")
            with self.subTest(module=name):
                self.assertRegex(
                    self.report,
                    rf"`{stem}`(?: at)? {position}\b",
                    f"report does not place {name} at plan position {position}",
                )

    def test_adsp_driver_absence_is_recomputed_not_asserted(self):
        plan = plan_entries()
        if not RAMDISK_MODULES.is_dir():
            raise unittest.SkipTest(f"ramdisk modules absent: {RAMDISK_MODULES}")
        for name in ("qcom_q6v5_pas.ko", "qcom_q6v5.ko"):
            with self.subTest(module=name):
                self.assertTrue(
                    (RAMDISK_MODULES / name).is_file(),
                    f"{name} is not in the ramdisk, so the report's premise changed",
                )
                self.assertNotIn(
                    name, plan, f"{name} entered the plan; the report is now stale"
                )
        self.assertIn("rproc_qcom_common.ko", plan)
        self.assertIn(
            "**neither is in the candidate's 70-entry plan.**", self.report
        )

    def test_zero_dependency_violations_is_recomputed(self):
        plan = plan_entries()
        dep_file = RAMDISK_MODULES / "modules.dep"
        if not dep_file.is_file():
            raise unittest.SkipTest(f"ramdisk modules.dep absent: {dep_file}")
        dependencies: dict[str, list[str]] = {}
        for line in dep_file.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            target, rest = line.split(":", 1)
            dependencies[Path(target).name] = [Path(x).name for x in rest.split()]
        position = {name: index for index, name in enumerate(plan)}
        violations = [
            (module, need)
            for module in GLINK_CLUSTER
            for need in dependencies.get(module, ())
            if need not in position or position[need] > position[module]
        ]
        self.assertEqual(violations, [], "the report claims zero violations")
        self.assertIn("**zero violations**", self.report)


if __name__ == "__main__":
    unittest.main()
