from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/a90_resident_fast_handoff_v1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("a90_resident_fast_handoff_v1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ResidentFastHandoffV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def fixture(self, root: Path) -> Path:
        for slot in ("A", "B"):
            slot_dir = root / slot
            slot_dir.mkdir()
            (slot_dir / "phase2-display-v1.img").write_bytes(b"image")
        value = {
            "schema": self.module.AB_SCHEMA,
            "profile": self.module.EXPECTED_PROFILE,
            "host_only": True,
            "device_action": False,
            "flash": False,
            "candidate_authority": False,
            "image_byte_identical": True,
            "presenter_byte_identical": True,
            "source_unchanged": True,
            "manifest_sha256": self.module.EXPECTED_MANIFEST_SHA256,
            "base": {"unchanged": True},
            "source_sha256": {
                "builder": self.module.EXPECTED_BUILDER_SHA256,
                "presenter": self.module.EXPECTED_PRESENTER_SOURCE_SHA256,
            },
        }
        for slot in ("A", "B"):
            value[slot] = {
                "e2fsck_read_only_rc": 0,
                "image": {
                    "path": f"{slot}/phase2-display-v1.img",
                    "bytes": self.module.EXPECTED_IMAGE_BYTES,
                    "sha256": self.module.EXPECTED_IMAGE_SHA256,
                },
                "presenter": {
                    "bytes": 1,
                    "sha256": self.module.EXPECTED_PRESENTER_SHA256,
                },
                "overlays": [
                    {
                        "target": "/usr/local/sbin/a90-debian-display-v1",
                        "sha256": self.module.EXPECTED_PRESENTER_SHA256,
                        "mode": 0o755,
                        "uid": 0,
                        "gid": 0,
                    }
                ],
            }
        receipt = root / "ab-receipt.json"
        receipt.write_text(json.dumps(value), encoding="utf-8")
        return receipt

    def test_exact_fixture_builds_host_only_blocked_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            image_sha = hashlib.sha256(b"image").hexdigest()
            with mock.patch.object(self.module, "EXPECTED_IMAGE_BYTES", len(b"image")), mock.patch.object(
                self.module, "EXPECTED_IMAGE_SHA256", image_sha
            ):
                receipt = self.fixture(Path(tmp))
                value = self.module.build_host_receipt(receipt)
        self.assertEqual(value["status"], "HOST_AB_QUALIFIED_PROMOTION_NOT_AUTHORIZED")
        self.assertTrue(value["host_only"])
        self.assertFalse(value["device_action"])
        self.assertFalse(value["flash"])
        self.assertFalse(value["candidate_authority"])
        self.assertFalse(value["live_ready"])
        self.assertEqual(list(self.module.DAILY_STATES), value["daily_d1_state_machine"])
        self.assertIn("resident-promotion-policy-not-yet-adopted", value["blockers"])

    def test_changed_presenter_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            image_sha = hashlib.sha256(b"image").hexdigest()
            with mock.patch.object(self.module, "EXPECTED_IMAGE_BYTES", len(b"image")), mock.patch.object(
                self.module, "EXPECTED_IMAGE_SHA256", image_sha
            ):
                receipt = self.fixture(Path(tmp))
                value = json.loads(receipt.read_text(encoding="utf-8"))
                value["B"]["presenter"]["sha256"] = "0" * 64
                receipt.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(self.module.ContractError, "presenter SHA256 changed"):
                    self.module.validate_ab_receipt(receipt)

    def test_parent_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            receipt = self.fixture(Path(tmp))
            value = json.loads(receipt.read_text(encoding="utf-8"))
            value["A"]["image"]["path"] = "../outside.img"
            receipt.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(self.module.ContractError, "parent traversal"):
                self.module.validate_ab_receipt(receipt)

    def test_source_is_h0_only_and_has_no_execute_mode(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("import socket", source)
        self.assertNotIn("import a90ctl", source)
        self.assertNotIn("--execute", source)
        self.assertNotIn("--approval", source)
        self.assertIn('"device_action": False', source)
        self.assertIn('"candidate_authority": False', source)


if __name__ == "__main__":
    unittest.main()
