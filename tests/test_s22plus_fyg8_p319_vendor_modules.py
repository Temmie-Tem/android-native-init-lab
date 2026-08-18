import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
RUNNER = REVALIDATION / "s22plus_fyg8_p319_vendor_modules_d0.py"
AUDIT = REVALIDATION / "s22plus_fyg8_raw_first_observer_audit.py"
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_STAGE_A_PROBE_RESULT_2026-08-18.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"

# The firmware copy's digest, recorded before it was ever recovered.
GATE0_SHA256 = "8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360"
GATE0_SIZE = 5843


def load(path: Path, name: str):
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P319VendorModulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load(RUNNER, "p319_vendor_modules_runner")
        cls.report = REPORT.read_text(encoding="utf-8")

    def test_contract_allows_exactly_two_pinned_reads(self):
        contract = self.runner.vendor_modules_safety_contract()
        self.assertEqual(contract["result"], "pass")
        self.assertTrue(contract["two_pinned_reads_only"])
        self.assertEqual(contract["body_read_count"], 1)
        self.assertEqual(contract["grep_count"], 1)
        self.assertEqual(contract["redirect_count"], 0)
        self.assertEqual(contract["forbidden_token_hits"], [])

    def test_contract_rejects_widened_or_writing_variants(self):
        base = self.runner.VENDOR_MODULES_SCRIPT
        mutations = {
            "second body read": base + 'cat "$target/modules.dep"\n',
            "retargeted": base.replace(
                "target=/vendor/lib/modules", "target=/sys/class/mxim/debug0"
            ),
            "write": base + 'echo x > "$target/modules.load"\n',
            "insmod": base + "insmod /vendor/lib/modules/pdic_max77705.ko\n",
            "second grep": base + 'grep -a x "$target/modules.dep"\n',
        }
        for label, script in mutations.items():
            with self.subTest(mutation=label):
                self.assertEqual(
                    self.runner.vendor_modules_safety_contract(script)["result"],
                    "fail",
                )

    # --- exact-byte recovery ------------------------------------------------

    def transcript(self, file_bytes: bytes, dep_lines=(b"a: b",)):
        parts = [b"vm\tbegin\n",
                 b"dir_present\tyes\n", b"load_present\tyes\n",
                 b"dep_present\tyes\n", b"ko_count\t356\n",
                 b"load\tbegin\n", file_bytes, b"load_rc\t0\n", b"load\tend\n",
                 b"dep\tbegin\n", b"\n".join(dep_lines), b"\ndep_rc\t0\n",
                 b"dep\tend\n", b"vm\tend\n"]
        return b"".join(parts)

    def test_the_hash_is_of_the_file_not_of_the_transcript(self):
        # `cat` output is framed by printf lines; if those leak into the slice
        # the digest is of the transcript and the Gate 0 comparison is void.
        content = b"a.ko\nb.ko\nc.ko\n"
        observation = self.runner.parse_vendor_modules(self.transcript(content))
        self.assertEqual(observation["load_bytes"], len(content))
        self.assertEqual(
            observation["load_sha256"], hashlib.sha256(content).hexdigest()
        )
        self.assertEqual(observation["load_entries"], 3)
        self.assertNotIn("load_rc", "".join(observation["load_first"]))

    def test_a_file_without_a_trailing_newline_still_hashes_as_itself(self):
        observation = self.runner.parse_vendor_modules(
            self.transcript(b"only.ko\n")
        )
        self.assertEqual(observation["load_entries"], 1)
        self.assertEqual(observation["load_first"], ["only.ko"])

    def test_missing_sections_do_not_fabricate_a_digest(self):
        observation = self.runner.parse_vendor_modules(b"vm\tbegin\nvm\tend\n")
        self.assertIsNone(observation["load_sha256"])
        self.assertEqual(observation["load_entries"], 0)
        self.assertTrue(observation["reached_end"])

    def test_mux_stack_entries_are_picked_out_with_their_order(self):
        content = b"\n".join(
            [b"a.ko", b"common_muic.ko", b"b.ko", b"mfd_max77705.ko",
             b"pdic_max77705.ko"]
        ) + b"\n"
        observation = self.runner.parse_vendor_modules(self.transcript(content))
        self.assertEqual(
            observation["max77705_entries"],
            [(1, "common_muic.ko"), (3, "mfd_max77705.ko"),
             (4, "pdic_max77705.ko")],
        )

    def test_runner_is_declared_to_the_raw_first_boundary(self):
        audit = load(AUDIT, "p319_vendor_modules_audit_doc")
        self.assertIsNotNone(audit.OBSERVER_FILE_RE.fullmatch(RUNNER.name))

    # --- documentation ------------------------------------------------------

    def test_report_records_gate_zero_closed_with_the_known_digest(self):
        for token in (
            "Gate 0 is closed",
            GATE0_SHA256,
            str(GATE0_SIZE),
            "pdic_max77705.ko",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_ledger_records_the_gate_zero_row(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " vendor-modules-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("| D0 |", rows[0])
        self.assertIn(GATE0_SHA256, rows[0])


if __name__ == "__main__":
    unittest.main()
