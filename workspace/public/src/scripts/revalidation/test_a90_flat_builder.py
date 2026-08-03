#!/usr/bin/env python3

from __future__ import annotations

import ast
import copy
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
NOOP_MANIFEST = (
    HERE / "a90_flat_builder/versions/flat-builder-v1-noop/manifest.toml"
)
MINIMAL_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-a/manifest.toml"
)
MINIMAL_B_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-b/manifest.toml"
)


def newc_archive(entries: dict[str, bytes]) -> bytes:
    result = bytearray()
    for inode, (name, payload) in enumerate(
        [*entries.items(), ("TRAILER!!!", b"")],
        start=1,
    ):
        encoded_name = name.encode("utf-8") + b"\0"
        fields = [
            inode,
            0o100755,
            0,
            0,
            1,
            0,
            len(payload),
            0,
            0,
            0,
            0,
            len(encoded_name),
            0,
        ]
        result.extend(b"070701")
        result.extend("".join(f"{value:08x}" for value in fields).encode("ascii"))
        result.extend(encoded_name)
        result.extend(b"\0" * (-len(result) % 4))
        result.extend(payload)
        result.extend(b"\0" * (-len(result) % 4))
    result.extend(b"\0" * (-len(result) % 512))
    return bytes(result)


class A90FlatBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolution = buildlib.resolve_manifest(MANIFEST)
        cls.manifest = cls.resolution.data
        materialized = {
            name: (
                MANIFEST.parent / value["path"]
            ).resolve()
            for name, value in cls.manifest["engine"][
                "materialized_sources"
            ].items()
        }
        cls.inputs = {
            "init_root": (
                REPO_ROOT / cls.manifest["init"]["source_root"]
            ).resolve(),
            "init_sources": cls.manifest["init"]["sources"],
            "doom_sources": cls.manifest["engine"]["doom_sources"],
            "materialized": materialized,
            "materialized_sha256": {
                name: buildlib.sha256_file(path)
                for name, path in materialized.items()
            },
        }

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
        self.assertTrue(self.manifest["engine"]["enabled"])
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

    def test_phase3_minimal_a_disables_only_doom_product_surface(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-a-no-doom-engine",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 60)
        self.assertIn(
            "a90_doomgeneric_bridge.c",
            minimal["init"]["sources"],
        )
        self.assertEqual(len(minimal["init"]["cflags"]), 37)
        self.assertFalse(
            any("DOOMGENERIC" in item for item in minimal["init"]["cflags"])
        )
        engine_path = minimal["engine"]["ramdisk_path"]
        self.assertIn(engine_path, minimal["ramdisk"]["obsolete_engines"])
        self.assertNotIn(engine_path, minimal["ramdisk"]["required_entries"])
        self.assertEqual(minimal["validation"]["engine_strings"], [])
        self.assertNotIn("engine", build.artifact_names(minimal))
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_b_replaces_operational_doom_bridge(self):
        minimal = buildlib.resolve_manifest(MINIMAL_B_MANIFEST).data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-b-inert-doom-surface",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 60)
        self.assertNotIn(
            "a90_doomgeneric_bridge.c",
            minimal["init"]["sources"],
        )
        self.assertIn(
            "a90_doomgeneric_bridge_inert.c",
            minimal["init"]["sources"],
        )
        self.assertEqual(len(minimal["init"]["cflags"]), 37)
        self.assertFalse(
            any("DOOMGENERIC" in item for item in minimal["init"]["cflags"])
        )
        self.assertEqual(minimal["validation"]["engine_strings"], [])
        self.assertNotIn("engine", build.artifact_names(minimal))
        inputs = buildlib.validate_inputs(
            REPO_ROOT,
            buildlib.resolve_manifest(MINIMAL_B_MANIFEST),
            minimal,
        )
        self.assertEqual(
            inputs["init_closure_sha256"],
            minimal["init"]["closure_sha256"],
        )

    def test_disabled_engine_contract_rejects_ramdisk_reachability(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        cases = {
            "not-obsolete": lambda value: value["ramdisk"][
                "obsolete_engines"
            ].remove(value["engine"]["ramdisk_path"]),
            "still-required": lambda value: value["ramdisk"][
                "required_entries"
            ].append(value["engine"]["ramdisk_path"]),
            "marker-retained": lambda value: value["validation"][
                "engine_strings"
            ].append("stale engine marker"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(minimal)
                mutate(changed)
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "disabled engine is not removed",
                ):
                    buildlib.validate_component_selection(changed)

    def test_packed_ramdisk_rejects_stale_engine_variants(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        listing = set(minimal["ramdisk"]["required_entries"])
        listing.add("bin/a90_doomgeneric_private_engine_v3368")
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "packed ramdisk engine selection mismatch",
        ):
            buildlib.validate_ramdisk_component_listing(minimal, listing)

        active = set(self.manifest["ramdisk"]["required_entries"])
        buildlib.validate_ramdisk_component_listing(self.manifest, active)
        active.add("bin/a90_doomgeneric_private_engine_v3383")
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "packed ramdisk engine selection mismatch",
        ):
            buildlib.validate_ramdisk_component_listing(self.manifest, active)

    def test_actual_packed_archive_is_reopened_for_component_validation(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        entries = {
            name: b"content"
            for name in minimal["ramdisk"]["required_entries"]
        }
        entries["bin/a90_doomgeneric_private_engine_v9999"] = b"stale"
        with tempfile.TemporaryDirectory() as temp_name:
            archive = Path(temp_name) / "ramdisk.cpio"
            archive.write_bytes(newc_archive(entries))
            with self.assertRaisesRegex(
                buildlib.ManifestError,
                "packed ramdisk engine selection mismatch",
            ):
                build.validate_packed_ramdisk(minimal, archive)

            del entries["bin/a90_doomgeneric_private_engine_v9999"]
            archive.write_bytes(newc_archive(entries))
            self.assertEqual(
                build.validate_packed_ramdisk(minimal, archive),
                set(entries),
            )

    def test_builder_source_keys_bind_both_execution_files(self):
        keys = build.builder_source_keys(REPO_ROOT)
        self.assertEqual(
            set(keys),
            {"flat_builder", "flat_builder_library"},
        )
        for value in keys.values():
            path = REPO_ROOT / value["path"]
            self.assertEqual(value["size"], path.stat().st_size)
            self.assertEqual(value["sha256"], buildlib.sha256_file(path))

        changed = copy.deepcopy(keys)
        changed["flat_builder"]["sha256"] = "0" * 64
        resolution = buildlib.resolve_manifest(MINIMAL_B_MANIFEST)
        inputs = buildlib.validate_inputs(
            REPO_ROOT,
            resolution,
            resolution.data,
        )
        with self.assertRaisesRegex(RuntimeError, "source closure changed"):
            build.revalidate_execution_closure(
                REPO_ROOT,
                resolution,
                resolution.data,
                inputs,
                changed,
            )

    def test_newc_parser_rejects_truncated_or_nonzero_trailer_padding(self):
        valid = newc_archive({"init": b"payload"})
        with self.assertRaisesRegex(buildlib.ManifestError, "truncated"):
            buildlib.newc_archive_listing(valid[:100])
        changed = bytearray(valid)
        changed[-1] = 1
        with self.assertRaisesRegex(buildlib.ManifestError, "invalid newc trailer"):
            buildlib.newc_archive_listing(bytes(changed))

    def test_newc_parser_rejects_cpio_canonicalization_aliases(self):
        aliases = (
            "././bin/a90_doomgeneric_private_engine_v9999",
            "bin/./a90_doomgeneric_private_engine_v9999",
            "bin//a90_doomgeneric_private_engine_v9999",
            "./bin/../bin/a90_doomgeneric_private_engine_v9999",
        )
        for alias in aliases:
            with self.subTest(alias=alias):
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "noncanonical",
                ):
                    buildlib.newc_archive_listing(
                        newc_archive({alias: b"stale"})
                    )

    def test_newc_parser_requires_exact_eight_digit_ascii_hex_fields(self):
        valid = newc_archive({"init": b"payload"})
        name_size_offset = 6 + (11 * 8)
        for encoded in (b"+0000005", b" 0000005", b"0000_005"):
            with self.subTest(encoded=encoded):
                changed = bytearray(valid)
                changed[name_size_offset:name_size_offset + 8] = encoded
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "malformed newc header",
                ):
                    buildlib.newc_archive_listing(bytes(changed))

    def test_newc_parser_requires_zero_member_alignment_padding(self):
        valid = newc_archive({"abc": b"x"})
        name_padding = bytearray(valid)
        name_padding[114] = 1
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "invalid member-name padding",
        ):
            buildlib.newc_archive_listing(bytes(name_padding))

        data_padding = bytearray(valid)
        data_padding[117] = 1
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "invalid member-data padding",
        ):
            buildlib.newc_archive_listing(bytes(data_padding))

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

    def test_noop_child_resolves_exactly_to_flat_baseline(self):
        child = buildlib.resolve_manifest(NOOP_MANIFEST)
        self.assertEqual(child.data, self.manifest)
        self.assertEqual(
            child.effective_sha256,
            self.resolution.effective_sha256,
        )
        self.assertEqual(
            [path.parent.name for path in child.lineage],
            ["flat-builder-v1-noop", "v3404-effective"],
        )
        self.assertEqual(
            child.origin_for(
                "engine",
                "materialized_sources",
                "adapter",
                "path",
            ),
            MANIFEST.resolve(),
        )
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "native-init closure changed",
        ):
            buildlib.validate_inputs(REPO_ROOT, child, child.data)

    def test_child_rejects_unknown_top_level_and_nested_keys(self):
        cases = {
            "unknown-top": "surprise = true\n",
            "unknown-nested": "[init]\ntypo_flag = true\n",
        }
        for name, overlay in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                versions = Path(directory) / "versions"
                self._write_manifest_tree(versions)
                child = versions / "child/manifest.toml"
                child.parent.mkdir()
                child.write_text(
                    'schema = "a90-flat-builder-v1"\n'
                    'extends = "base"\n'
                    + overlay,
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "unknown",
                ):
                    buildlib.resolve_manifest(child)

    def test_child_rejects_inherited_value_type_change(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n'
                "[init]\n"
                'cflags = "not-a-list"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "changes type"):
                buildlib.resolve_manifest(child)

    def test_child_rejects_cycles_and_deep_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            versions.mkdir()
            for name, parent in (("a", "b"), ("b", "a")):
                path = versions / name / "manifest.toml"
                path.parent.mkdir()
                path.write_text(
                    'schema = "a90-flat-builder-v1"\n'
                    f'extends = "{parent}"\n',
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(buildlib.ManifestError, "cycle"):
                buildlib.resolve_manifest(versions / "a/manifest.toml")

        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            middle = versions / "middle/manifest.toml"
            middle.parent.mkdir()
            middle.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n',
                encoding="utf-8",
            )
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "middle"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "depth"):
                buildlib.resolve_manifest(child)

    def test_child_rejects_path_like_parent_and_authority_escalation(self):
        for parent in ("../base", "/base", "base/other"):
            with self.subTest(parent=parent), tempfile.TemporaryDirectory() as directory:
                child = Path(directory) / "versions/child/manifest.toml"
                child.parent.mkdir(parents=True)
                child.write_text(
                    'schema = "a90-flat-builder-v1"\n'
                    f'extends = "{parent}"\n',
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(buildlib.ManifestError, "invalid extends"):
                    buildlib.resolve_manifest(child)

        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n'
                "candidate_authority = true\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                buildlib.ManifestError,
                "candidate authority",
            ):
                buildlib.resolve_manifest(child)

    def test_manifest_resolution_rejects_file_and_profile_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.symlink_to(versions / "base/manifest.toml")
            with self.assertRaisesRegex(buildlib.ManifestError, "symlink"):
                buildlib.resolve_manifest(child)

    def test_manifest_lineage_hashes_detect_post_resolution_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n',
                encoding="utf-8",
            )
            resolution = buildlib.resolve_manifest(child)
            self.assertEqual(len(resolution.lineage_sha256), 2)
            buildlib.revalidate_manifest_lineage(resolution)
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n'
                "# drift\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "changed"):
                buildlib.revalidate_manifest_lineage(resolution)

        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            alias = versions / "alias"
            alias.symlink_to(versions / "base", target_is_directory=True)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "alias"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "symlink"):
                buildlib.resolve_manifest(child)

    def test_output_contract_rejects_outside_private_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                build.output_root(REPO_ROOT, Path(directory) / "flat")

    def test_manifest_argument_is_confined_to_one_profile_directory(self):
        self.assertEqual(build.selected_manifest(MANIFEST), MANIFEST.resolve())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "must stay below"):
                build.selected_manifest(Path(directory) / "manifest.toml")
        with self.assertRaisesRegex(RuntimeError, "versions/<host-profile>"):
            build.selected_manifest(
                MANIFEST.parent / "nested/manifest.toml"
            )
        with tempfile.TemporaryDirectory(
            dir=MANIFEST.parent.parent,
        ) as directory:
            alias = Path(directory) / "alias"
            alias.symlink_to(MANIFEST.parent, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                build.selected_manifest(alias / "manifest.toml")

    def test_ramdisk_paths_reject_absolute_and_parent_escape(self):
        root = Path("/tmp/ramdisk")
        self.assertEqual(
            build.safe_ramdisk_path(root, "bin/helper", "test"),
            root / "bin/helper",
        )
        for relative in ("/bin/helper", "../helper", "bin/../../helper"):
            with self.assertRaises(RuntimeError):
                build.safe_ramdisk_path(root, relative, "test")

    @staticmethod
    def _write_manifest_tree(versions: Path) -> None:
        base = versions / "base/manifest.toml"
        base.parent.mkdir(parents=True)
        data = copy.deepcopy(buildlib.resolve_manifest(MANIFEST).data)

        def toml_scalar(value):
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, str):
                return repr(value)
            raise TypeError(value)

        lines = []
        tables: list[tuple[tuple[str, ...], dict]] = [((), data)]
        while tables:
            prefix, table = tables.pop(0)
            if prefix:
                lines.append("[" + ".".join(prefix) + "]")
            for key, value in table.items():
                if isinstance(value, dict):
                    tables.append(((*prefix, key), value))
                elif isinstance(value, list):
                    items = ", ".join(toml_scalar(item) for item in value)
                    lines.append(f"{key} = [{items}]")
                else:
                    lines.append(f"{key} = {toml_scalar(value)}")
            lines.append("")
        base.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
