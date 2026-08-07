#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_s22plus_fyg8_p310_candidate as builder  # noqa: E402


class P310CandidateBuilderTests(unittest.TestCase):
    def test_base_builder_emits_the_p310_safety_extension(self) -> None:
        safety = builder.artifact_safety(
            {
                "profile": "E2",
                "source_contract_id": builder.P310_SOURCE_CONTRACT_ID,
            }
        )
        self.assertIs(builder.base.artifact_safety, builder.artifact_safety)
        self.assertEqual(safety["candidate_module_binaries_injected"], 0)
        self.assertIs(safety["built_in_telemetry_only"], True)
        self.assertIs(safety["carrier_v2"], True)
        self.assertNotIn("no_userspace_sysfs_or_configfs_write", safety)
        self.assertEqual(
            safety["module_init_probe_authority"], "active-live-unproved"
        )
        self.assertEqual(
            safety["userspace_sysfs_configfs_write_scope"],
            "source-contract-bound-p282-prebind-child-reinit-and-e3-acm",
        )


if __name__ == "__main__":
    unittest.main()
