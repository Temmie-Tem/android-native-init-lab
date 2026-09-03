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

import s22plus_fyg8_p332_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as runtime  # noqa: E402
import s22plus_fyg8_p332_stock_candidate_build as builder  # noqa: E402


class P332StockCandidateBuildTests(unittest.TestCase):
    def test_both_consumed_lineages_are_reopened(self) -> None:
        predecessor, payload, source = builder._predecessor()  # noqa: SLF001 - H0 fixture
        self.assertEqual(predecessor["run_id_hex"], builder.P330_RUN_ID_HEX)
        self.assertEqual(builder.identity(payload), builder.P330_RESULT_IDENTITY)
        self.assertEqual(builder.identity(source), builder.P330_BUILDER_IDENTITY)
        p331, p331_payload = builder._predecessor_p331()  # noqa: SLF001 - H0 fixture
        self.assertEqual(p331["run_id_hex"], builder.P331_RUN_ID_HEX)
        self.assertEqual(builder.identity(p331_payload), builder.P331_RESULT_IDENTITY)
        self.assertEqual(
            p331["phase2"]["candidate"]["a"]["ap_tar_md5"],
            builder.P331_AP_IDENTITY,
        )

    def test_current_sources_exclude_p331_resident_bytes(self) -> None:
        sources = builder._current_sources()  # noqa: SLF001 - H0 fixture
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
            builder.identity(sources["p328_authenticated_exec_runtime.py"]),
            builder.RUNTIME_SOURCE_IDENTITY,
        )
        self.assertNotEqual(
            builder.RUNTIME_SOURCE_IDENTITY,
            {"size": 18_203, "sha256": "b146a1b9c46fc5db520c20d8c250dcc565c9882723ba82398fb8d1cd60f69750"},
        )

    def test_runtime_transform_is_bound_to_p330_input_and_auth_key(self) -> None:
        key = artifact.read_auth_key()
        source = (
            builder.P330_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
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
        self.assertEqual(receipt["run_id_hex"], runtime.P332_RUN_ID_HEX)
        self.assertEqual(receipt["predecessor"]["run_id_hex"], builder.P330_RUN_ID_HEX)
        self.assertEqual(set(transformed), {runtime.RUNTIME_KEY})
        self.assertEqual(hashlib.sha256(key).hexdigest(), artifact.auth_key_identity()["sha256"])

    def test_consumed_candidate_identities_are_not_current(self) -> None:
        self.assertNotEqual(builder.P332_RUN_ID_HEX, builder.P330_RUN_ID_HEX)
        self.assertNotEqual(builder.P332_RUN_ID_HEX, builder.P331_RUN_ID_HEX)
        self.assertNotEqual(builder.P330_AP_IDENTITY, builder.P331_AP_IDENTITY)


if __name__ == "__main__":
    unittest.main()
