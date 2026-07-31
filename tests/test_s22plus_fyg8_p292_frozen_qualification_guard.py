from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from workspace.public.src.scripts.revalidation import (
    s22plus_fyg8_p292_frozen_qualification_guard as guard,
)


class P292FrozenQualificationGuardTest(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        implementations = {}
        for index in range(guard.EXPECTED_UNIQUE_IMPLEMENTATION_COUNT - 1):
            relative = Path("impl") / f"gate-{index:02d}.py"
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = f"gate={index}\n".encode("ascii")
            target.write_bytes(payload)
            implementations[f"gate_{index:02d}"] = {
                "path": relative.as_posix(),
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        relative = Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p292_linked_audit.py"
        )
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = b"linked-audit\n"
        target.write_bytes(payload)
        identity = {
            "path": relative.as_posix(),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        implementations["linked_audit"] = dict(identity)
        implementations["p292_linked_audit"] = dict(identity)
        qualification = {
            "schema": guard.QUALIFICATION_SCHEMA,
            "verdict": guard.QUALIFICATION_VERDICT,
            "build_allowed": True,
            "gate_implementation": {**implementations, "verified": True},
        }
        path = root / "qualification.json"
        path.write_text(json.dumps(qualification), encoding="ascii")
        return path

    def check(self, root: Path, qualification: Path):
        receipt = guard._receipt(qualification.read_bytes())
        with mock.patch.object(guard, "FROZEN_QUALIFICATION_RECEIPT", receipt):
            return guard.check(root, qualification)

    def test_exact_inventory_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.check(root, self.fixture(root))
            self.assertTrue(result["verified"])
            self.assertEqual(result["implementation_count"], 51)
            self.assertEqual(result["unique_implementation_count"], 50)
            self.assertEqual(result["changed_count"], 0)

    def test_changed_implementation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification = self.fixture(root)
            (root / "impl/gate-17.py").write_bytes(b"changed\n")
            with self.assertRaisesRegex(guard.GuardError, "changed: gate_17"):
                self.check(root, qualification)

    def test_duplicate_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification = self.fixture(root)
            value = json.loads(qualification.read_text(encoding="ascii"))
            value["gate_implementation"]["gate_48"] = dict(
                value["gate_implementation"]["gate_47"]
            )
            qualification.write_text(json.dumps(value), encoding="ascii")
            with self.assertRaisesRegex(guard.GuardError, "alias inventory"):
                self.check(root, qualification)

    def test_symlink_implementation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification = self.fixture(root)
            target = root / "impl/gate-03.py"
            target.unlink()
            target.symlink_to("gate-02.py")
            with self.assertRaisesRegex(guard.GuardError, "indirect"):
                self.check(root, qualification)

    def test_frozen_qualification_receipt_is_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification = self.fixture(root)
            expected = guard._receipt(qualification.read_bytes())
            value = json.loads(qualification.read_text(encoding="ascii"))
            value["extra"] = "mutation"
            qualification.write_text(json.dumps(value), encoding="ascii")
            with mock.patch.object(
                guard, "FROZEN_QUALIFICATION_RECEIPT", expected
            ):
                with self.assertRaisesRegex(guard.GuardError, "receipt differs"):
                    guard.check(root, qualification)


if __name__ == "__main__":
    unittest.main()
