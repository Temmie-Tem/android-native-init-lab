import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py")
DRAFT = Path("docs/operations/S22PLUS_M18_P00_PREFIX_DOWNLOAD_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m18_p00_prefix_download_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM18P00PrefixDownloadLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_draft_has_required_markers(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_policy_marker_check_rejects_missing_ack_and_interpretation(self):
        missing = self.module.missing_policy_markers("S22+ M18 P00 prefix-download native-init boot-only")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn("wait for the original Odin endpoint to disconnect", missing)
        self.assertIn("no EUD sysfs write", missing)

    def test_expected_candidate_hashes_are_pinned(self):
        self.assertEqual(
            self.module.EXPECTED_P00_AP_SHA256,
            "b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b",
        )
        self.assertEqual(
            self.module.EXPECTED_P00_INIT_SHA256,
            "467947f7ba0c4b4088c9a21a19e5202609b833298f2e95256b1f011eb9af034e",
        )


if __name__ == "__main__":
    unittest.main()
