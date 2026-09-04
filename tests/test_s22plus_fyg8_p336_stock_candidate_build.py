from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p336_stock_candidate_build as builder  # noqa: E402


class P336StockCandidateBuildTests(unittest.TestCase):
    def test_exact_p335_predecessor_is_reopened(self) -> None:
        value, payload, source = builder._predecessor()  # noqa: SLF001
        self.assertEqual(value["run_id_hex"], builder.P335_RUN_ID_HEX)
        self.assertEqual(builder.identity(payload), builder.P335_RESULT_IDENTITY)
        self.assertEqual(builder.identity(source), builder.P335_BUILDER_IDENTITY)
        self.assertEqual(value["phase2"]["candidate"]["a"], value["phase2"]["candidate"]["b"])
        self.assertEqual(value["phase2"]["candidate"]["a"]["ap_tar_md5"], builder.P335_AP_IDENTITY)

    def test_fresh_output_and_current_source_receipts_are_distinct(self) -> None:
        self.assertEqual(builder.DEFAULT_OUTPUT_ROOT.parent.name, "s22plus_fyg8_p336")
        self.assertNotEqual(builder.DEFAULT_OUTPUT_ROOT.parent.name, "s22plus_fyg8_p335")
        sources = builder._current_sources()  # noqa: SLF001
        self.assertEqual(
            set(sources),
            {
                "p328_stock_candidate_build.py",
                "p328_artifact_identity.py",
                "p328_stock_process_v2_adapter.py",
                "p328_authenticated_exec_runtime.py",
                "p328_authenticated_acm_observer.py",
            },
        )
        self.assertEqual(
            hashlib.sha256(sources["p328_authenticated_exec_runtime.py"]).hexdigest(),
            hashlib.sha256(Path(builder.runtime.__file__).read_bytes()).hexdigest(),
        )

    def test_runtime_transform_uses_only_p335_include_as_input(self) -> None:
        predecessor = builder._predecessor()[0]  # noqa: SLF001
        source = builder._stable(  # noqa: SLF001
            builder.P335_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
            "P3.35 runtime",
            2 << 20,
            predecessor["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"],
            mode=0o400,
        )
        key = builder.artifact.DEFAULT_AUTH_KEY_PATH.read_bytes()
        transformed, receipt = builder._runtime_transform(source, key)  # noqa: SLF001
        self.assertNotEqual(source, transformed)
        self.assertEqual(receipt["input_lineage"], "p335-runtime-include")
        self.assertEqual(receipt["run_id_hex"], builder.P336_RUN_ID_HEX)
        self.assertTrue(receipt["per_boot_identity_required"])
        self.assertTrue(receipt["long_idle_host_resync"])

    def test_completed_output_is_a_b_equal_boot_only(self) -> None:
        value = builder.audit_existing()
        self.assertEqual(value["schema"], builder.SCHEMA)
        self.assertEqual(value["run_id_hex"], builder.P336_RUN_ID_HEX)
        self.assertEqual(value["phase2"]["candidate"]["a"], value["phase2"]["candidate"]["b"])
        self.assertEqual(value["phase2"]["candidate"]["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertTrue(value["scope"]["host_only"])
        self.assertFalse(value["scope"]["device_contact"])
        self.assertFalse(value["scope"]["odin_invocations"])


if __name__ == "__main__":
    unittest.main()
