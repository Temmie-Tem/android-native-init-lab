from __future__ import annotations

import importlib.util
from pathlib import Path
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


class P328StockProcessV2AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load(
            "p328_stock_process_v2_adapter_test",
            REVALIDATION / "s22plus_fyg8_p328_stock_process_v2_adapter.py",
        )

    def test_fresh_authenticated_contract(self) -> None:
        module = self.module
        audit = module.audit()
        self.assertEqual(audit["run_id"], module.P328_RUN_ID_HEX)
        self.assertEqual(audit["predecessor_run_id"], module.P327_RUN_ID_HEX)
        self.assertTrue(audit["authenticated_exec"])
        self.assertTrue(audit["authentication_required"])
        self.assertEqual(audit["auth_key_size"], 32)
        self.assertFalse(audit["auth_key_path_published"])
        self.assertFalse(audit["encoder_failure_is_success"])
        self.assertFalse(audit["encoder_failure_is_causal"])

    def test_acceptance_fixture_is_fresh_and_auth_bound(self) -> None:
        module = self.module
        fixture = module.acceptance_fixture()
        self.assertEqual(fixture["schema"], module.SCHEMA)
        self.assertEqual(fixture["run_id"], module.P328_RUN_ID_HEX)
        self.assertTrue(fixture["authenticated_exec"])
        self.assertEqual(fixture["auth_key_size"], 32)
        self.assertNotIn("path", fixture.get("auth_key", {}))
        checked = module.validate_acceptance_item(fixture)
        self.assertEqual(checked["run_id"], module.P328_RUN_ID_HEX)

    def test_predecessor_record_and_run_binding_are_rejected(self) -> None:
        module = self.module
        with self.assertRaises(module.DecodeError):
            module.decode_record(
                module.P327_RUN_ID,
                expected_run_id=module.P327_RUN_ID,
            )
        with self.assertRaises(module.DecodeError):
            module.decode_record(b"P327", expected_run_id=module.P328_RUN_ID)

    def test_auth_key_projection_accepts_only_fixture_bytes_without_path(self) -> None:
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "auth-key-v1.bin"
            path.write_bytes(bytes(range(32)))
            path.chmod(0o400)
            projection = module.auth_key_identity(path)
            self.assertEqual(set(projection), {"size", "sha256"})
            self.assertEqual(projection["size"], 32)
            self.assertNotIn("path", projection)

    def test_lineage_never_publishes_auth_key_path(self) -> None:
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "auth-key-v1.bin"
            path.write_bytes(b"K" * 32)
            path.chmod(0o400)
            lineage = module.bind_exact_sources(path)
            self.assertEqual(lineage["auth_key"]["size"], 32)
            self.assertNotIn("path", lineage["auth_key"])
            self.assertNotIn("auth_key_path", lineage)


if __name__ == "__main__":
    unittest.main()
