from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P328StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load(
            "p328_stock_candidate_build_test",
            ANALYSIS / "s22plus_fyg8_p328_stock_candidate_build.py",
        )

    def _key(self, directory: Path, payload: bytes = bytes(range(32))) -> Path:
        path = directory / "auth-key-v1.bin"
        path.write_bytes(payload)
        path.chmod(0o400)
        return path

    def test_exact_predecessor_and_runtime_bindings_are_visible(self) -> None:
        builder = self.builder
        self.assertEqual(builder.P328_RUN_ID_HEX, "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b")
        self.assertEqual(builder.P327_OUTPUT.name, "stock-candidate-build-v1-20260902-04")
        self.assertEqual(builder.P327_RESULT_IDENTITY["size"], 42_906)
        runtime = builder._require_runtime()
        self.assertEqual(runtime.P328_RUN_ID_HEX, builder.P328_RUN_ID_HEX)
        self.assertEqual(runtime.CONTRACT_ID, "s22plus-fyg8-p328-auth-exec-runtime-v1")
        self.assertTrue(callable(runtime.transform_artifacts))

    def test_runtime_transform_materializes_fixture_key_without_path(self) -> None:
        builder = self.builder
        source = (
            builder.P327_OUTPUT
            / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path = self._key(Path(temporary))
            key, metadata = builder._read_auth_key(path)
            builder._ACTIVE_AUTH_KEY = key
            builder._ACTIVE_AUTH_KEY_META = metadata
            try:
                transformed, receipt = builder._runtime_transform(source, key)
            finally:
                builder._clear_auth_key()
        self.assertNotEqual(transformed, source)
        self.assertTrue(receipt["authenticated"])
        self.assertEqual(receipt["auth_key"], metadata)
        self.assertNotIn("path", receipt["auth_key"])
        self.assertEqual(receipt["run_id_hex"], builder.P328_RUN_ID_HEX)

    def test_full_build_reopens_ab_boot_only_and_unchanged_rollback(self) -> None:
        builder = self.builder
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            key_path = self._key(temporary_root)
            output = temporary_root / "p328-output"
            result = builder.build_result(output, auth_key=key_path)
            reopened = builder.audit_existing(output, auth_key=key_path)
        self.assertEqual(result, reopened)
        self.assertEqual(result["run_id_hex"], builder.P328_RUN_ID_HEX)
        candidate = result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p327"])
        self.assertEqual(candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"])
        self.assertNotEqual(
            candidate["a"]["ap_tar_md5"], result["lineage"]["predecessor_ap"]
        )
        for label in ("a", "b"):
            package = candidate[label]["package"]
            self.assertEqual(package["members"], ["boot.img.lz4"])
            self.assertEqual(package["schema"], "s22plus_fyg8_p328_boot_only_package_v1")
            self.assertEqual(package["busybox"], builder.BUSYBOX_IDENTITY)
        self.assertTrue(result["preservation"]["rollback_untouched"])
        self.assertTrue(result["preservation"]["p327_consumed_candidate_unchanged"])
        self.assertTrue(result["framed_exec"]["authenticated"])
        self.assertEqual(result["framed_exec"]["auth_key"]["size"], 32)
        self.assertNotIn("path", result["framed_exec"]["auth_key"])
        self.assertEqual(result["scope"]["tier"], "H0")
        self.assertFalse(result["scope"]["device_contact"])
        self.assertEqual(result["scope"]["odin_invocations"], 0)
        self.assertEqual(builder._normalize_result(result), result)

    def test_cli_has_explicit_auth_key_but_no_key_generation_switch(self) -> None:
        builder = self.builder
        with self.assertRaises(SystemExit) as context:
            builder.main(["--create-auth-key"])
        self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
