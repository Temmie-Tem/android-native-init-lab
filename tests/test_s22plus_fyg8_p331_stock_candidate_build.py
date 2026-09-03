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

import s22plus_fyg8_p331_resident_exec_runtime as runtime  # noqa: E402
import s22plus_fyg8_p331_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p331_artifact_identity as artifact  # noqa: E402


class P331StockCandidateBuildTests(unittest.TestCase):
    def test_final_ordinal_and_consumed_predecessor_are_bound(self) -> None:
        self.assertEqual(builder.DEFAULT_OUTPUT_ROOT.name, "stock-candidate-build-v1-20260903-03")
        predecessor, payload, source = builder._predecessor()  # noqa: SLF001 - H0 fixture
        self.assertEqual(predecessor["run_id_hex"], builder.P330_RUN_ID_HEX)
        self.assertEqual(builder.identity(payload), builder.P330_RESULT_IDENTITY)
        self.assertEqual(builder.identity(source), builder.P330_BUILDER_IDENTITY)
        self.assertEqual(
            predecessor["phase2"]["candidate"]["a"]["ap_tar_md5"],
            builder.P330_AP_IDENTITY,
        )

    def test_only_runtime_include_is_transformed(self) -> None:
        key = artifact.read_auth_key()
        source = (
            builder.P330_OUTPUT
            / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
        ).read_bytes()
        transformed = runtime.transform_artifacts(
            {runtime.RUNTIME_KEY: source}, key
        )
        after = transformed[runtime.RUNTIME_KEY]
        self.assertNotEqual(after, source)
        receipt = runtime.validate_transform(
            source,
            after,
            auth_key_sha256=hashlib.sha256(key).hexdigest(),
        )
        self.assertEqual(receipt["run_id_hex"], runtime.P331_RUN_ID_HEX)
        self.assertEqual(receipt["predecessor"]["run_id_hex"], builder.P330_RUN_ID_HEX)
        self.assertEqual(set(transformed), {runtime.RUNTIME_KEY})

    def test_consumed_p330_candidate_is_not_a_valid_fresh_result(self) -> None:
        predecessor, _, _ = builder._predecessor()  # noqa: SLF001 - H0 fixture
        candidate = predecessor["phase2"]["candidate"]
        self.assertEqual(candidate["a"]["ap_tar_md5"], builder.P330_AP_IDENTITY)
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertNotEqual(builder.P331_RUN_ID_HEX, builder.P330_RUN_ID_HEX)


if __name__ == "__main__":
    unittest.main()
