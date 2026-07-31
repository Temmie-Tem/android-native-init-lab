#!/usr/bin/env python3

from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import unittest

from a90_flat_builder import build
from a90_flat_builder import buildlib


HERE = Path(__file__).resolve().parent
REPO_ROOT = build.repo_root()
MANIFEST = (
    HERE / "a90_flat_builder/versions/v3404-effective/manifest.toml"
)


class A90FlatBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = buildlib.load_manifest(MANIFEST)
        cls.inputs = buildlib.validate_inputs(
            REPO_ROOT,
            MANIFEST,
            cls.manifest,
        )

    def test_flat_effective_identity_and_source_counts(self):
        self.assertEqual(
            self.manifest["profile"],
            "v3404-effective-portable-v1",
        )
        self.assertFalse(self.manifest["candidate_authority"])
        self.assertNotIn("extends", self.manifest)
        self.assertEqual(len(self.inputs["init_sources"]), 60)
        self.assertEqual(len(self.inputs["doom_sources"]), 80)
        self.assertEqual(len(self.manifest["init"]["cflags"]), 84)
        self.assertEqual(len(self.manifest["helper"]["cflags"]), 29)
        self.assertIn(
            '-DA90_DOOMGENERIC_BRIDGE_ENGINE='
            '"doomgeneric-private-link-v3404-d3-resolved-owner-timeout"',
            self.manifest["init"]["cflags"],
        )

    def test_materialized_sources_match_phase0_pins(self):
        self.assertEqual(
            self.inputs["materialized_sha256"],
            {
                "adapter":
                    "d5bcb088a554cf53278a5d4995bf24768c49964eb6b4159a33eb80b39ab953ca",
                "sfx":
                    "e52f5fef6db417359066aff1c00d0f11f8f3ac3462175093ec4a9eda99a7720f",
                "sdl_mixer_stub":
                    "18bf8a8f46a757399bfea90f7db828534e4b579efbf2e7754c10424dcbe690cd",
            },
        )

    def test_virtual_prefixes_are_public_and_random_seed_is_fixed(self):
        self.assertEqual(
            self.manifest["init"]["virtual_source_root"],
            "/usr/src/a90/native-init",
        )
        self.assertEqual(
            self.manifest["engine"]["virtual_doom_root"],
            "/usr/src/a90/doomgeneric",
        )
        self.assertEqual(
            self.manifest["random_seed"],
            "a90-v3404-effective-portable-v1",
        )
        flags = buildlib.init_flags(self.manifest, self.inputs)
        self.assertTrue(any(flag.startswith("-ffile-prefix-map=") for flag in flags))
        self.assertTrue(any(flag.endswith("=/usr/src/a90/native-init") for flag in flags))

    def test_pipeline_imports_no_legacy_builder(self):
        for path in (
            HERE / "a90_flat_builder/buildlib.py",
            HERE / "a90_flat_builder/build.py",
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module)
            self.assertFalse(
                any(name.startswith("build_native_init") for name in imported),
                path,
            )

    def test_output_contract_rejects_outside_private_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                build.output_root(REPO_ROOT, Path(directory) / "flat")

    def test_ramdisk_paths_reject_absolute_and_parent_escape(self):
        root = Path("/tmp/ramdisk")
        self.assertEqual(
            build.safe_ramdisk_path(root, "bin/helper", "test"),
            root / "bin/helper",
        )
        for relative in ("/bin/helper", "../helper", "bin/../../helper"):
            with self.assertRaises(RuntimeError):
                build.safe_ramdisk_path(root, relative, "test")


if __name__ == "__main__":
    unittest.main()
