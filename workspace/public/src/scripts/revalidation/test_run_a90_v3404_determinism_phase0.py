#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "phase0", HERE / "run_a90_v3404_determinism_phase0.py"
)
assert SPEC and SPEC.loader
phase0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase0)


class Phase0Test(unittest.TestCase):
    def test_chain_is_complete_and_unique(self):
        chain = phase0.builder_chain()
        self.assertEqual(len(chain), len(set(chain)))
        self.assertEqual(chain[0], phase0.ENTRYPOINT)
        self.assertEqual(chain[-1].name, "build_native_init_boot_v726_wifi_lifecycle.py")
        self.assertEqual(len(chain), 171)

    def test_accepted_boot_is_pinned(self):
        result = phase0.audit()
        self.assertEqual(
            result["accepted_boot_sha256"], phase0.EXPECTED_ACCEPTED_SHA256
        )


if __name__ == "__main__":
    unittest.main()
