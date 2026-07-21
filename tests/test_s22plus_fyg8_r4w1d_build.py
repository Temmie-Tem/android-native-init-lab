import importlib.util
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1d_build.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_r4w1d_build_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1DBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def make_outputs(
        self,
        *,
        image_size=1024,
        proof_count=1,
        config_count=1,
        legacy_config_count=0,
        fips_count=1,
        historical_count=0,
    ):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        dist = root / "out/msm-waipio-waipio-gki/gki_kernel/dist"
        config = root / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
        dist.mkdir(parents=True)
        config.parent.mkdir(parents=True)
        payload = (
            self.module.PROOF_BYTES * proof_count
            + self.module.HISTORICAL_FAMILIES[0] * historical_count
        )
        content = payload + bytes(max(0, image_size - len(payload)))
        (dist / "Image").write_bytes(content)
        (dist / "vmlinux").write_bytes(payload)
        config.write_text(
            f"{self.module.contract.CONFIG}=y\n" * config_count
            + "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y\n" * legacy_config_count
            + "CONFIG_CRYPTO_FIPS=y\n" * fips_count,
            encoding="ascii",
        )
        return temporary, root

    def gate(self, root, *, image_size=1024, capacity=4096):
        with mock.patch.object(
            self.module.engine, "STOCK_IMAGE_SIZE", image_size
        ), mock.patch.object(
            self.module.engine, "FIXED_KERNEL_SLOT_CAPACITY", capacity
        ):
            return self.module.witness_output_gate(root)

    def test_witness_gate_accepts_one_contiguous_proof(self):
        temporary, root = self.make_outputs()
        self.addCleanup(temporary.cleanup)
        result = self.gate(root)
        self.assertTrue(result["verified"])
        self.assertEqual(result["image_proof_count"], 1)
        self.assertEqual(result["legacy_config_enable_count"], 0)

    def test_witness_gate_rejects_duplicate_or_missing_proof(self):
        for proof_count in (0, 2):
            with self.subTest(proof_count=proof_count):
                temporary, root = self.make_outputs(proof_count=proof_count)
                self.addCleanup(temporary.cleanup)
                self.assertFalse(self.gate(root)["verified"])

    def test_witness_gate_rejects_historical_family_and_legacy_config(self):
        temporary, root = self.make_outputs(
            historical_count=1, legacy_config_count=1
        )
        self.addCleanup(temporary.cleanup)
        result = self.gate(root)
        self.assertFalse(result["verified"])
        self.assertEqual(result["legacy_config_enable_count"], 1)
        self.assertEqual(
            result["historical_family_counts"]["[[S22R4W1B|"]["image"], 1
        )

    def test_witness_gate_rejects_layout_change(self):
        temporary, root = self.make_outputs(image_size=4097)
        self.addCleanup(temporary.cleanup)
        result = self.gate(root, image_size=4097, capacity=4096)
        self.assertFalse(result["verified"])
        self.assertFalse(result["fits_fixed_ramdisk_layout"])

    def test_checked_patch_uses_new_contract_and_restores_source(self):
        source_argument = Path(
            os.environ.get(
                "S22PLUS_FYG8_TEST_SOURCE",
                str(self.module.contract.DEFAULT_SOURCE),
            )
        )
        source = (
            source_argument
            if source_argument.is_absolute()
            else ROOT / source_argument
        )
        patch = ROOT / self.module.contract.DEFAULT_PATCH
        with tempfile.TemporaryDirectory() as temporary:
            work_tree = Path(temporary)
            originals = {}
            for relative in self.module.contract.BASE_FILES:
                src = source / relative
                dst = work_tree / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                originals[relative] = dst.read_bytes()
            previous = self.module.engine.patch_check
            with self.module.apply_checked_patch(work_tree, patch) as runtime:
                self.assertIs(self.module.engine.patch_check, self.module.contract)
                self.assertTrue(runtime["applied"])
            self.assertIs(self.module.engine.patch_check, previous)
            self.assertTrue(runtime["restored"])
            for relative, content in originals.items():
                self.assertEqual((work_tree / relative).read_bytes(), content)

    def test_checked_patch_restores_engine_binding_on_error(self):
        previous = self.module.engine.patch_check
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises((self.module.engine.BuildError, OSError)):
                with self.module.apply_checked_patch(
                    Path(temporary), ROOT / self.module.contract.DEFAULT_PATCH
                ):
                    pass
        self.assertIs(self.module.engine.patch_check, previous)

    def test_sec_log_buf_timing_gate_requires_module_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "out/msm-waipio-waipio-gki/msm-kernel/.config"
            module = root / "out/msm-waipio-waipio-gki/dist/sec_log_buf.ko"
            config.parent.mkdir(parents=True)
            module.parent.mkdir(parents=True)
            config.write_text("CONFIG_SEC_LOG_BUF=m\n", encoding="ascii")
            module.write_bytes(b"\x7fELFmodule")
            result = self.module.sec_log_buf_timing_gate(root)
            self.assertTrue(result["verified"])
            module.write_bytes(b"not-elf")
            self.assertFalse(self.module.sec_log_buf_timing_gate(root)["verified"])
            module.write_bytes(b"\x7fELFmodule")
            config.write_text("CONFIG_SEC_LOG_BUF=y\n", encoding="ascii")
            self.assertFalse(self.module.sec_log_buf_timing_gate(root)["verified"])

    def make_symlink_control(self, root):
        work_tree = root / "source"
        audit = root / "audit"
        audit.mkdir()
        rows = [
            {
                "path": "vendor/include/a.h",
                "type": "symlink",
                "link_target": "/archive/source/a.h",
            },
            {
                "path": "toolchain/libgcc_s.so",
                "type": "symlink",
                "link_target": "/lib/libgcc_s.so.1",
            },
        ]
        for row in rows:
            path = work_tree / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(row["link_target"])
        members = audit / "reconstructed-final-members.jsonl"
        payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        members.write_text(payload, encoding="utf-8")
        manifest = audit / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "artifacts": {
                        members.name: {
                            "bytes": members.stat().st_size,
                            "sha256": hashlib.sha256(members.read_bytes()).hexdigest(),
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        source_overlay = {"verified": True, "manifest_path": str(manifest)}
        return work_tree, source_overlay, rows

    def test_source_symlink_control_restores_vendor_build_mutations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            self.assertTrue(control["verified"])
            self.assertEqual(control["absolute_symlink_count"], 2)
            with self.module.preserve_source_symlinks(work_tree, control) as runtime:
                first = work_tree / rows[0]["path"]
                first.unlink()
                first.symlink_to("/tmp/vendor-build/a.h")
                second = work_tree / rows[1]["path"]
                second.unlink()
            self.assertTrue(runtime["verified"])
            self.assertTrue(runtime["restored"])
            self.assertEqual(runtime["mutation_count"], 2)
            for row in rows:
                self.assertEqual(
                    os.readlink(work_tree / row["path"]), row["link_target"]
                )

    def test_source_symlink_control_applies_runtime_override_then_restores(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            runtime_target = root / "runtime-toolchain"
            runtime_target.mkdir()
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            relative = rows[1]["path"]
            path = work_tree / relative
            with self.module.preserve_source_symlinks(
                work_tree,
                control,
                runtime_target_overrides={relative: str(runtime_target)},
            ) as runtime:
                self.assertEqual(os.readlink(path), str(runtime_target))
            self.assertTrue(runtime["verified"])
            self.assertEqual(runtime["runtime_override_count"], 1)
            self.assertTrue(
                next(
                    row
                    for row in runtime["links"]
                    if row["relative_path"] == relative
                )["runtime_override_applied"]
            )
            self.assertEqual(os.readlink(path), rows[1]["link_target"])

    def test_source_clang_link_is_separately_qualified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, _ = self.make_symlink_control(root)
            clang_link = work_tree / self.module.SOURCE_CLANG_LINK
            clang_link.parent.mkdir(parents=True)
            recorded_target = Path("/archive-owner").joinpath(
                *self.module.SOURCE_CLANG_RECORDED_TARGET_SUFFIX
            )
            clang_link.symlink_to(recorded_target)
            archive_control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            control = self.module.qualify_recorded_source_clang_link(
                work_tree, archive_control
            )
            self.assertTrue(control["verified"])
            self.assertEqual(control["archive_absolute_symlink_count"], 2)
            self.assertEqual(control["qualified_external_symlink_count"], 1)
            self.assertEqual(control["absolute_symlink_count"], 3)
            row = next(
                row
                for row in control["links"]
                if row["relative_path"] == str(self.module.SOURCE_CLANG_LINK)
            )
            self.assertEqual(row["provenance"], "separately-pinned-toolchain-link")
            self.assertEqual(row["actual_target"], str(recorded_target))
            self.assertEqual(row["expected_target"], str(recorded_target))

            runtime_target = root / "runtime-toolchain"
            runtime_target.mkdir()
            with self.module.preserve_source_symlinks(
                work_tree,
                control,
                runtime_target_overrides={
                    str(self.module.SOURCE_CLANG_LINK): str(runtime_target)
                },
            ) as runtime:
                self.assertEqual(os.readlink(clang_link), str(runtime_target))
            self.assertTrue(runtime["verified"])
            self.assertEqual(os.readlink(clang_link), str(recorded_target))

    def test_source_clang_link_rejects_relative_recorded_target(self):
        target = Path(*self.module.SOURCE_CLANG_RECORDED_TARGET_SUFFIX)
        self.assertFalse(
            self.module.recorded_source_clang_target_matches(str(target))
        )

    def test_source_clang_link_rejects_wrong_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, _ = self.make_symlink_control(root)
            clang_link = work_tree / self.module.SOURCE_CLANG_LINK
            clang_link.parent.mkdir(parents=True)
            clang_link.symlink_to("/tmp/unqualified-clang")
            control = self.module.qualify_recorded_source_clang_link(
                work_tree,
                self.module.inspect_source_symlink_control(
                    work_tree, source_overlay
                ),
            )
            self.assertFalse(control["verified"])
            self.assertEqual(control["reason"], "clang-link-target-mismatch")

    def test_source_symlink_control_rejects_unknown_runtime_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, _ = self.make_symlink_control(root)
            runtime_target = root / "runtime-toolchain"
            runtime_target.mkdir()
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            with self.assertRaises(self.module.BuildError):
                with self.module.preserve_source_symlinks(
                    work_tree,
                    control,
                    runtime_target_overrides={
                        "not/archive-owned": str(runtime_target)
                    },
                ):
                    pass

    def test_source_symlink_control_rejects_dirty_preflight(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            path = work_tree / rows[0]["path"]
            path.unlink()
            path.symlink_to("/tmp/wrong")
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            self.assertFalse(control["verified"])
            with self.assertRaises(self.module.BuildError):
                with self.module.preserve_source_symlinks(work_tree, control):
                    pass

    def test_source_symlink_control_rejects_replaced_parent_without_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            parent = work_tree / "vendor/include"
            original_parent = work_tree / "vendor/include.original"
            outside = root / "outside"
            outside.mkdir()
            with self.assertRaises(self.module.BuildError):
                with self.module.preserve_source_symlinks(work_tree, control):
                    parent.rename(original_parent)
                    parent.symlink_to(outside, target_is_directory=True)
                    leaf = original_parent / "a.h"
                    leaf.unlink()
                    leaf.symlink_to("/tmp/vendor-build/a.h")
            self.assertFalse((outside / "a.h").exists())
            self.assertEqual(
                os.readlink(original_parent / "a.h"), rows[0]["link_target"]
            )

    def test_source_symlink_cleanup_attempts_every_link_before_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            original_restore = self.module._atomic_restore_symlink_at
            calls = []

            def fail_first(parent_fd, name, target):
                calls.append(name)
                if len(calls) == 1:
                    raise OSError("injected restore failure")
                return original_restore(parent_fd, name, target)

            with mock.patch.object(
                self.module, "_atomic_restore_symlink_at", side_effect=fail_first
            ):
                with self.assertRaises(self.module.BuildError):
                    with self.module.preserve_source_symlinks(
                        work_tree, control
                    ):
                        for row in rows:
                            path = work_tree / row["path"]
                            path.unlink()
                            path.symlink_to("/tmp/vendor-build/changed")
            self.assertEqual(len(calls), 2)
            self.assertEqual(
                os.readlink(work_tree / rows[1]["path"]), rows[1]["link_target"]
            )
            self.assertNotEqual(
                os.readlink(work_tree / rows[0]["path"]), rows[0]["link_target"]
            )

    def test_source_symlink_cleanup_reports_body_and_cleanup_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            original_restore = self.module._atomic_restore_symlink_at
            calls = []

            def fail_first(parent_fd, name, target):
                calls.append(name)
                if len(calls) == 1:
                    raise OSError("cleanup-injected")
                return original_restore(parent_fd, name, target)

            with mock.patch.object(
                self.module, "_atomic_restore_symlink_at", side_effect=fail_first
            ):
                with self.assertRaises(self.module.BuildError) as raised:
                    with self.module.preserve_source_symlinks(
                        work_tree, control
                    ):
                        for row in rows:
                            path = work_tree / row["path"]
                            path.unlink()
                            path.symlink_to("/tmp/vendor-build/changed")
                        raise RuntimeError("body-injected")
            message = str(raised.exception)
            self.assertIn("body-injected", message)
            self.assertIn("source symlink cleanup failed", message)
            self.assertIn("cleanup-injected", message)
            self.assertEqual(len(calls), 2)
            self.assertEqual(
                os.readlink(work_tree / rows[1]["path"]), rows[1]["link_target"]
            )

    def test_source_symlink_control_restores_metadata_only_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_tree, source_overlay, rows = self.make_symlink_control(root)
            control = self.module.inspect_source_symlink_control(
                work_tree, source_overlay
            )
            first = work_tree / rows[0]["path"]
            original = next(
                row
                for row in control["links"]
                if row["relative_path"] == rows[0]["path"]
            )
            with self.module.preserve_source_symlinks(work_tree, control) as runtime:
                os.utime(
                    first,
                    ns=(
                        original["original_atime_ns"] + 1_000_000_000,
                        original["original_mtime_ns"] + 1_000_000_000,
                    ),
                    follow_symlinks=False,
                )
            metadata = first.stat(follow_symlinks=False)
            self.assertTrue(runtime["verified"])
            self.assertGreaterEqual(runtime["metadata_mutation_count"], 1)
            self.assertEqual(metadata.st_atime_ns, original["original_atime_ns"])
            self.assertEqual(metadata.st_mtime_ns, original["original_mtime_ns"])


if __name__ == "__main__":
    unittest.main()
