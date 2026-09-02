from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P328ArtifactIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load(
            "p328_artifact_identity_test",
            REVALIDATION / "s22plus_fyg8_p328_artifact_identity.py",
        )

    def _key(self, directory: Path, payload: bytes = bytes(range(32))) -> Path:
        path = directory / "auth-key-v1.bin"
        path.write_bytes(payload)
        path.chmod(0o400)
        return path

    def test_fresh_identity_and_path_free_auth_key_projection(self) -> None:
        module = self.module
        self.assertEqual(module.P328_RUN_ID_HEX, "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b")
        with tempfile.TemporaryDirectory() as temporary:
            path = self._key(Path(temporary))
            self.assertEqual(module.read_auth_key(path), bytes(range(32)))
            projection = module.auth_key_identity(path)
            self.assertEqual(set(projection), {"size", "sha256"})
            self.assertEqual(projection["size"], 32)
            self.assertEqual(projection["sha256"], module.identity(bytes(range(32)))["sha256"])
            self.assertNotIn("path", projection)

    def test_auth_key_requires_direct_regular_0400_single_link_32_bytes(self) -> None:
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = self._key(directory)
            path.chmod(0o600)
            with self.assertRaises(module.ArtifactIdentityError):
                module.read_auth_key(path)
            path.chmod(0o400)

            path.chmod(0o600)
            path.write_bytes(b"short")
            path.chmod(0o400)
            with self.assertRaises(module.ArtifactIdentityError):
                module.read_auth_key(path)

            path.chmod(0o600)
            self._key(directory)
            link = directory / "auth-key-link.bin"
            link.symlink_to(path)
            with self.assertRaises(module.ArtifactIdentityError):
                module.read_auth_key(link)

            hardlink = directory / "auth-key-hardlink.bin"
            os.link(path, hardlink)
            with self.assertRaises(module.ArtifactIdentityError):
                module.read_auth_key(path)

    def test_image_transform_is_same_size_and_uses_fresh_run_id(self) -> None:
        module = self.module
        source = module.stable_bytes(
            module.P319_IMAGE,
            "P319 Image",
            64 << 20,
            module.P319_IMAGE_IDENTITY,
        )
        image, receipt = module.transform_image(source)
        self.assertEqual(len(image), len(source))
        self.assertEqual(receipt["target"]["run_id_hex"], module.P328_RUN_ID_HEX)
        self.assertEqual(
            module.validate_image(image)["run_id_hex"], module.P328_RUN_ID_HEX
        )

    def test_consumed_p327_ap_is_rejected(self) -> None:
        module = self.module
        ap = ROOT / (
            "workspace/private/outputs/s22plus_fyg8_p327/"
            "stock-candidate-build-v1-20260902-04/candidate-a/odin4/AP.tar.md5"
        )
        if not ap.is_file():
            self.skipTest("private consumed P327 AP is not present")
        with self.assertRaises(module.ArtifactIdentityError):
            module.inspect_ap(ap)


if __name__ == "__main__":
    unittest.main()
