from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DISTRO = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SERVER_DISTRO) not in sys.path:
    sys.path.insert(0, str(SERVER_DISTRO))

keyer = importlib.import_module("a90_phase2d_keyed_rootfs")


class A90Phase2DKeyedRootfsTests(unittest.TestCase):
    def test_clean_base_is_exact_and_unkeyed(self) -> None:
        state = keyer.audit_clean_base()

        self.assertEqual(state["image_size"], keyer.IMAGE_BYTES)
        self.assertEqual(state["image_sha256"], keyer.CLEAN_IMAGE_SHA256)
        self.assertEqual(state["receipt_sha256"], keyer.CLEAN_RECEIPT_SHA256)

    def test_run_identity_and_directory_are_exact(self) -> None:
        run_id = "a90-v3406-debian-display-f1-20260731-01"
        self.assertEqual(keyer.validate_run_id(run_id), run_id)
        self.assertEqual(
            keyer.exact_run_dir(run_id),
            (keyer.PRIVATE_RUN_BASE / run_id).resolve(),
        )
        for invalid in (
            "a90-v3405-debian-display-f1-20260731-01",
            "a90-v3406-debian-f1-20260731-01",
            "a90-v3406-debian-display-f1-20260731-1",
            "../a90-v3406-debian-display-f1-20260731-01",
        ):
            with self.subTest(run_id=invalid):
                with self.assertRaises(keyer.ContractError):
                    keyer.validate_run_id(invalid)

    def test_public_key_validator_accepts_one_ed25519_line(self) -> None:
        valid = b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE3m7pP0wQ== \n"
        self.assertIsNotNone(keyer.PUBLIC_KEY_RE.fullmatch(valid))
        for invalid in (
            valid + b"ssh-ed25519 AAAA\n",
            b"ssh-rsa AAAA\n",
            b"ssh-ed25519 AAAA",
            b"command=x ssh-ed25519 AAAA\n",
        ):
            with self.subTest(value=invalid):
                self.assertIsNone(keyer.PUBLIC_KEY_RE.fullmatch(invalid))

    def test_copy_is_new_inode_no_reflink_and_refuses_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.img"
            source.write_bytes(b"x" * 4096)
            source.chmod(0o600)
            run_dir = root / "run"
            run_dir.mkdir()
            base = {
                "image": source,
                "image_size": 4096,
                "image_sha256": keyer.sha256_file(source),
                "image_inode": source.stat().st_ino,
                "image_device": source.stat().st_dev,
            }
            image = keyer.copy_clean_image(base, run_dir)
            self.assertNotEqual(image.stat().st_ino, source.stat().st_ino)
            self.assertEqual(image.read_bytes(), source.read_bytes())
            with self.assertRaises(keyer.ContractError):
                keyer.copy_clean_image(base, run_dir)

    def test_private_writer_is_exclusive_0600(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            old_umask = os.umask(0)
            try:
                keyer.write_private_json_exclusive(path, {"schema": "test"})
            finally:
                os.umask(old_umask)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                keyer.write_private_json_exclusive(path, {"schema": "test"})

    def test_source_contract_rejects_overwrite_reflink_and_device_paths(self) -> None:
        source = Path(keyer.__file__).read_text(encoding="utf-8")
        self.assertEqual(keyer.source_contract_issues(source), ())
        mutations = (
            source.replace("--reflink=never", "--reflink=auto", 1),
            source.replace(
                'if output.exists() or output.is_symlink():',
                "if False:",
                1,
            ),
            source.replace(
                'if output.exists() or output.is_symlink():',
                (
                    "if False:  # if output.exists() or "
                    "output.is_symlink():"
                ),
                1,
            ),
            source.replace('"device_contact": False', '"device_contact": True'),
        )
        for mutation in mutations:
            with self.subTest():
                self.assertTrue(keyer.source_contract_issues(mutation))

    def test_audit_mode_has_no_authority_or_device_surface(self) -> None:
        value = keyer.audit_payload()

        self.assertEqual(value["contract_issues"], [])
        self.assertTrue(value["ready_for_private_materialization"])
        for field in (
            "candidate_authority",
            "f1_authorized",
            "live_authority",
            "device_contact",
            "device_write",
            "rootfs_staged",
            "flash",
            "reboot",
        ):
            self.assertIs(value[field], False)


if __name__ == "__main__":
    unittest.main()
