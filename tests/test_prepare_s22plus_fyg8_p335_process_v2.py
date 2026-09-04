from __future__ import annotations

import stat
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import prepare_s22plus_fyg8_p335_process_v2 as prepare  # noqa: E402


def path_snapshot(path: Path):
    try:
        current = path.lstat()
    except FileNotFoundError:
        return None
    head = (
        current.st_mode,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
        current.st_ctime_ns,
    )
    if stat.S_ISREG(current.st_mode):
        return head + (path.read_bytes(),)
    if stat.S_ISDIR(current.st_mode):
        return head + (
            tuple(
                (str(child.relative_to(path)), path_snapshot(child))
                for child in sorted(path.rglob("*"))
            ),
        )
    return head


class P335PrepareTests(unittest.TestCase):
    def test_defaults_bind_fresh_p335_and_exact_rollback(self) -> None:
        self.assertEqual(prepare.SCHEMA, "s22plus_fyg8_p335_process_v2_promotion_v1")
        self.assertEqual(prepare.READY_SCHEMA, "s22plus_fyg8_p335_ready_manifest_builder_v1")
        self.assertEqual(prepare.DEFAULT_MANIFEST_ID, "s22plus-fyg8-p335-process-v2-ready-1")
        self.assertEqual(prepare.DEFAULT_LIVE_RUN_ID, "s22plus-fyg8-p335-live-1")
        self.assertEqual(
            prepare.ROLLBACK_IDENTITY["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(prepare.DEFAULT_BUILDER_OUTPUT.parent.name, "s22plus_fyg8_p335")
        self.assertEqual(prepare.DEFAULT_MANIFEST.name, "s22plus_fyg8_p335_process_v2_ready_1.json")

    def test_prepare_source_pin_and_host_only_identity(self) -> None:
        self.assertEqual(prepare.P334_PREPARE_SOURCE.stat().st_size, prepare.P334_PREPARE_IDENTITY["size"])
        self.assertEqual(prepare.identity(prepare.P334_PREPARE_SOURCE.read_bytes()), prepare.P334_PREPARE_IDENTITY)
        if prepare.DEFAULT_MANIFEST.exists():
            self.assertTrue(prepare.DEFAULT_MANIFEST.is_file())
            self.assertFalse(prepare.DEFAULT_MANIFEST.is_symlink())
        if prepare.DEFAULT_PROMOTION.exists():
            self.assertTrue(prepare.DEFAULT_PROMOTION.is_dir())
            self.assertFalse(prepare.DEFAULT_PROMOTION.is_symlink())

    def test_observer_spec_is_p335_and_no_external_authority(self) -> None:
        spec = prepare._p335_observer_spec()  # noqa: SLF001
        self.assertTrue(spec["usb_serial"].endswith("c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"))
        self.assertEqual(spec["protocol_contract"], "s22plus-fyg8-p335-retained-listener-acm-observer-v1")
        self.assertTrue(spec["per_boot_identity_required"])
        self.assertTrue(spec["host_only"])
        self.assertFalse(spec["device_contact"])

    def test_prepare_rehearsal_succeeds_without_publication(self) -> None:
        self.assertIsNotNone(prepare._P334)  # exact source is loaded only when dependencies exist
        manifest_before = path_snapshot(prepare.DEFAULT_MANIFEST)
        promotion_before = path_snapshot(prepare.DEFAULT_PROMOTION)
        manifest, payloads, verification = prepare.build()
        self.assertEqual(set(payloads), {"candidate_static", "run_manifest", "static_check"})
        self.assertEqual(manifest["status"], "ready-for-f1-approval")
        self.assertEqual(
            verification["schema"], "device_action_f1_p335_stock_offline_contract_v1"
        )
        self.assertEqual(path_snapshot(prepare.DEFAULT_MANIFEST), manifest_before)
        self.assertEqual(path_snapshot(prepare.DEFAULT_PROMOTION), promotion_before)


if __name__ == "__main__":
    unittest.main()
