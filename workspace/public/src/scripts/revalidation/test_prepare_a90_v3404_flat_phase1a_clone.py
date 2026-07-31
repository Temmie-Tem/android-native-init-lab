#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "phase1a", HERE / "prepare_a90_v3404_flat_phase1a_clone.py"
)
assert SPEC and SPEC.loader
phase1a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase1a)


class Phase1ACloneTest(unittest.TestCase):
    def test_rejects_outside_private_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                phase1a.require_output(Path(directory) / "a90-v3404-flat-phase1a-x")

    def test_rejects_wrong_leaf(self):
        with self.assertRaises(RuntimeError):
            phase1a.require_output(phase1a.PRIVATE_OUTPUTS / "wrong")

    def test_boot_pin(self):
        path = (
            phase1a.REPO_ROOT / "workspace/private/inputs/boot_images/"
            "boot_linux_v3404_d3_resolved_owner_timeout.img"
        )
        self.assertEqual(phase1a.sha256(path), phase1a.EXPECTED_BOOT_SHA256[path.name])


if __name__ == "__main__":
    unittest.main()
