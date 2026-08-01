from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p294_formal_input_preflight as preflight  # noqa: E402


def _receipt(value: bytes) -> dict[str, object]:
    return {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _build(directory: Path) -> None:
    directory.mkdir()
    outputs = []
    for name in sorted(set(preflight.formal.ARTIFACT_LIMITS) - {"build-result.json"}):
        value = name.encode("ascii")
        (directory / name).write_bytes(value)
        outputs.append({"name": name, **_receipt(value)})
    (directory / "build-result.json").write_text(
        json.dumps({"schema": preflight.formal.build.SCHEMA, "outputs": outputs})
    )


class FormalInputPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        source = self.root / preflight.formal.DEFAULT_SOURCE
        source.mkdir(parents=True)
        _build(self.root / "a")
        _build(self.root / "b")
        for name in ("intent", "patch", "nm", "objdump"):
            (self.root / name).write_bytes(name.encode("ascii"))
        (self.root / "nm").chmod(0o755)
        (self.root / "objdump").chmod(0o755)
        self.inputs = {
            "build_a": Path("a"),
            "build_b": Path("b"),
            "intent": Path("intent"),
            "patch": Path("patch"),
            "nm": Path("nm"),
            "objdump": Path("objdump"),
            "formal_result": Path("formal.json"),
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_actual_shape_passes_without_invoking_formal(self) -> None:
        result = preflight.validate(self.root, **self.inputs)
        self.assertEqual(result["verdict"], preflight.VERDICT)
        self.assertIs(result["source_argument_omitted"], True)
        self.assertIs(result["formal_invoked"], False)

    def test_contract_file_cannot_replace_source_tree(self) -> None:
        source_file = self.root / "source-contract.py"
        source_file.write_text("contract")
        parsed = argparse.Namespace(
            source=Path("source-contract.py"),
            build_a=self.inputs["build_a"],
            build_b=self.inputs["build_b"],
            intent=self.inputs["intent"],
            patch=self.inputs["patch"],
            nm=self.inputs["nm"],
            objdump=self.inputs["objdump"],
        )
        with (
            mock.patch.object(preflight.formal, "DEFAULT_SOURCE", parsed.source),
            mock.patch.object(preflight.formal, "parse_args", return_value=parsed),
            self.assertRaisesRegex(preflight.PreflightError, "source is missing or indirect"),
        ):
            preflight.validate(self.root, **self.inputs)

    def test_preserved_nine_artifact_directory_is_rejected(self) -> None:
        (self.root / "a" / "Image.lz4").write_bytes(b"extra")
        with self.assertRaisesRegex(preflight.PreflightError, "inventory mismatch"):
            preflight.validate(self.root, **self.inputs)

    def test_existing_formal_result_is_rejected(self) -> None:
        (self.root / self.inputs["formal_result"]).write_text("occupied")
        with self.assertRaisesRegex(preflight.PreflightError, "already exists"):
            preflight.validate(self.root, **self.inputs)


if __name__ == "__main__":
    unittest.main()
