import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
PLANNER = REVALIDATION / "s22plus_fyg8_p319_module_closure_plan.py"
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_STAGE_A_PROBE_RESULT_2026-08-18.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fake_ko(depends: list[str], vermagic: str = "5.10.226-test") -> bytes:
    """A minimal ELF64 object carrying only a .modinfo section."""
    fields = [f"vermagic={vermagic}".encode(), b"license=GPL"]
    fields.append(
        ("depends=" + ",".join(d[:-3] for d in depends)).encode()
    )
    modinfo = b"\x00".join(fields) + b"\x00"
    names = b"\x00.modinfo\x00.shstrtab\x00"
    header_size, entsize = 64, 64
    modinfo_off = header_size
    names_off = modinfo_off + len(modinfo)
    sh_off = names_off + len(names)
    out = bytearray()
    out += b"\x7fELF" + bytes([2, 1, 1]) + b"\x00" * 9
    out += struct.pack("<HHI", 1, 183, 1)          # type, machine, version
    out += struct.pack("<QQQ", 0, 0, sh_off)        # entry, phoff, shoff
    out += struct.pack("<IHHHHHH", 0, header_size, 0, 0, entsize, 3, 2)
    assert len(out) == 64, len(out)
    out += modinfo + names
    # section 0: null
    out += b"\x00" * entsize
    # section 1: .modinfo
    sh = struct.pack("<IIQQQQ", 1, 1, 0, 0, modinfo_off, len(modinfo))
    out += sh + b"\x00" * (entsize - len(sh))
    # section 2: .shstrtab
    sh = struct.pack("<IIQQQQ", 10, 3, 0, 0, names_off, len(names))
    out += sh + b"\x00" * (entsize - len(sh))
    return bytes(out)


class P319ModuleClosurePlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(PLANNER, "p319_module_closure_plan")
        cls.report = REPORT.read_text(encoding="utf-8")

    def build(self, root: Path, graph: dict[str, list[str]], first_stage=(), recovery=()):
        for name, deps in graph.items():
            (root / name).write_bytes(fake_ko(deps))
        closure = [n for n in graph if n != "top.ko"]
        (root / "modules.dep").write_text(
            "/lib/modules/top.ko: "
            + " ".join(f"/lib/modules/{n}" for n in closure)
            + "\n"
        )
        (root / "modules.load").write_text("".join(f"{n}\n" for n in first_stage))
        (root / "modules.load.recovery").write_text(
            "".join(f"{n}\n" for n in recovery)
        )

    def test_modinfo_is_read_without_an_elf_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.ko"
            path.write_bytes(fake_ko(["a.ko", "b.ko"], vermagic="5.10.226-abc"))
            self.assertEqual(
                self.module.direct_dependencies(path), ["a.ko", "b.ko"]
            )
            self.assertEqual(
                self.module.modinfo(path)["vermagic"], ["5.10.226-abc"]
            )

    def test_a_module_with_no_dependencies_reads_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.ko"
            path.write_bytes(fake_ko([]))
            self.assertEqual(self.module.direct_dependencies(path), [])

    def test_non_elf_input_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.ko"
            path.write_bytes(b"not an elf at all" * 8)
            with self.assertRaises(self.module.ClosurePlanError):
                self.module.direct_dependencies(path)

    def test_topological_order_is_dependency_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = {"base.ko": [], "mid.ko": ["base.ko"], "top.ko": ["mid.ko", "base.ko"]}
            self.build(root, graph, recovery=["top.ko", "mid.ko", "base.ko"])
            order = self.module.topological(root, list(graph))
            self.assertLess(order.index("base.ko"), order.index("mid.ko"))
            self.assertLess(order.index("mid.ko"), order.index("top.ko"))
            self.assertEqual(
                self.module.order_violations(order, root, list(graph)), []
            )

    def test_a_shipped_list_order_that_violates_dependencies_is_caught(self):
        # This is the finding the tool exists for: modules.load.recovery is a
        # modprobe input, and modprobe resolves order itself.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = {"base.ko": [], "mid.ko": ["base.ko"], "top.ko": ["mid.ko"]}
            self.build(root, graph, recovery=["top.ko", "mid.ko", "base.ko"])
            value = self.module.plan(root, "top.ko")
            self.assertFalse(value["recovery_order_is_insmod_safe"])
            self.assertTrue(value["insmod_order_is_safe"])
            self.assertEqual(
                sorted(
                    (v["module"], v["needs"])
                    for v in value["recovery_order_violations"]
                ),
                [("mid.ko", "base.ko"), ("top.ko", "mid.ko")],
            )

    def test_first_stage_members_drop_out_of_the_marginal_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = {"base.ko": [], "mid.ko": ["base.ko"], "top.ko": ["mid.ko"]}
            self.build(root, graph, first_stage=["base.ko"], recovery=list(graph))
            value = self.module.plan(root, "top.ko")
            self.assertEqual(value["members"], 3)
            self.assertEqual(value["already_loaded_by_first_stage"], ["base.ko"])
            self.assertEqual(value["marginal_count"], 2)
            self.assertNotIn("base.ko", value["insmod_order"])

    def test_a_cycle_stops_rather_than_emitting_an_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = {"a.ko": ["b.ko"], "b.ko": ["a.ko"], "top.ko": ["a.ko"]}
            self.build(root, graph)
            with self.assertRaisesRegex(
                self.module.ClosurePlanError, "dependency cycle"
            ):
                self.module.topological(root, list(graph))

    def test_a_missing_module_file_is_reported_not_assumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = {"base.ko": [], "top.ko": ["base.ko"]}
            self.build(root, graph)
            (root / "base.ko").unlink()
            (root / "base.ko").write_bytes(fake_ko([]))
            value = self.module.plan(root, "top.ko")
            self.assertTrue(value["all_present"])

    def test_report_records_the_reachability_and_order_findings(self):
        for token in (
            "all 24 are\npresent in the vendor_boot ramdisk",
            "is not an insmod order",
            "5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_ledger_records_the_closure_plan_row(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-module-closure-plan-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("| H0 |", rows[0])


if __name__ == "__main__":
    unittest.main()
