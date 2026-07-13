import importlib.util
import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1b_repro_check.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1b_repro_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1BReproCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_normalized_config_ignores_only_whitelist_path(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            a = root / "a"
            b = root / "b"
            common = "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y\n"
            a.write_text(
                common + 'CONFIG_UNUSED_KSYMS_WHITELIST="/a/list"\n',
                encoding="ascii",
            )
            b.write_text(
                common + 'CONFIG_UNUSED_KSYMS_WHITELIST="/b/list"\n',
                encoding="ascii",
            )
            self.assertEqual(
                self.module.normalized_config(a), self.module.normalized_config(b)
            )

    def test_normalized_config_preserves_security_delta(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            a = root / "a"
            b = root / "b"
            a.write_text("CONFIG_RKP=y\n", encoding="ascii")
            b.write_text("# CONFIG_RKP is not set\n", encoding="ascii")
            self.assertNotEqual(
                self.module.normalized_config(a), self.module.normalized_config(b)
            )

    def test_image_gate_requires_exact_marker_and_size(self):
        with tempfile.TemporaryDirectory() as name:
            image = Path(name) / "Image"
            image.write_bytes(
                self.module.MARKER
                + bytes(self.module.IMAGE_SIZE - len(self.module.MARKER))
            )
            result = self.module.check_image(image)
            self.assertTrue(result["verified"])
            image.write_bytes(image.read_bytes().replace(self.module.MARKER, b"X", 1))
            self.assertFalse(self.module.check_image(image)["verified"])

    def test_artifact_binding_rejects_wrong_or_reused_path(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            recorded = root / "recorded"
            other = root / "other"
            recorded.write_bytes(b"expected")
            other.write_bytes(b"different")
            build = {
                "artifacts": {
                    "Image": {
                        "path": str(recorded),
                        "sha256": self.module.sha256_file(recorded),
                        "size": recorded.stat().st_size,
                    }
                }
            }
            self.assertTrue(
                self.module.check_artifact_binding(build, "Image", recorded)[
                    "verified"
                ]
            )
            self.assertFalse(
                self.module.check_artifact_binding(build, "Image", other)["verified"]
            )

    def test_build_gate_requires_complete_artifact_manifest(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "result.json"
            path.write_text(json.dumps({"outputs": []}), encoding="ascii")
            result = self.module.check_build(path)
            self.assertFalse(result["artifact_manifest_verified"])
            self.assertFalse(result["verified"])

    def test_same_artifact_path_cannot_prove_reproducibility(self):
        with tempfile.TemporaryDirectory() as name:
            image = Path(name) / "Image"
            image.write_bytes(b"same")
            result = self.module.check_distinct_artifact_paths(
                {"Image": [image, image]}
            )
            self.assertFalse(result["Image"])

    def test_artifact_binding_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            target = root / "target"
            link = root / "link"
            target.write_bytes(b"data")
            link.symlink_to(target)
            build = {
                "artifacts": {
                    "Image": {
                        "path": str(target),
                        "sha256": self.module.sha256_file(target),
                        "size": target.stat().st_size,
                    }
                }
            }
            with self.assertRaises(self.module.CheckError):
                self.module.check_artifact_binding(build, "Image", link)


if __name__ == "__main__":
    unittest.main()
