import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_kernel_build_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8KernelBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_environment_fixes_variant_release_and_parent_git(self):
        work = Path("/tmp/fyg8-work")
        env = self.module.build_environment(work, lto="full", jobs=8)
        self.assertEqual(env["TARGET_BUILD_VARIANT"], "user")
        self.assertEqual(env["LOCALVERSION"], "-30958166-abS906NKSS7FYG8")
        self.assertNotIn("BUILD_NUMBER", env)
        self.assertEqual(env["KBUILD_BUILD_TIMESTAMP"], "Fri Aug 1 05:55:56 UTC 2025")
        self.assertEqual(env["GIT_CEILING_DIRECTORIES"], "/tmp")
        self.assertEqual(env["MAKEFLAGS"], "-j8")

    def test_environment_does_not_inherit_compiler_poison(self):
        with mock.patch.dict(
            self.module.os.environ,
            {"CC": "/tmp/not-clang", "CFLAGS": "-DBROKEN", "BASH_ENV": "/tmp/hook"},
            clear=False,
        ):
            env = self.module.build_environment(Path("/tmp/fyg8-work"), lto="full", jobs=8)
        self.assertNotIn("CC", env)
        self.assertNotIn("CFLAGS", env)
        self.assertNotIn("BASH_ENV", env)
        self.assertEqual(env["LC_ALL"], "C")

    def test_output_gate_requires_every_r1_owned_artifact(self):
        complete = [
            {"name": name}
            for name in (*self.module.DIST_OUTPUTS, ".config")
        ]
        self.assertTrue(self.module.output_gate(complete)["verified"])
        incomplete = [item for item in complete if item["name"] != "vmlinux"]
        gate = self.module.output_gate(incomplete)
        self.assertFalse(gate["verified"])
        self.assertEqual(gate["missing"], ["vmlinux"])

    def test_source_overlay_is_a_hard_preflight_input(self):
        source = self.module.Path("/tmp/source")
        clang = self.module.Path("/tmp/clang")
        with mock.patch.object(self.module, "run", return_value=self.module.subprocess.CompletedProcess([], 1, "", "")), mock.patch.object(
            self.module, "host_resources", return_value={"disk_ok": True, "full_lto_memory_ok": True}
        ), mock.patch.object(self.module, "git_identity", return_value={"verified": True}), mock.patch.object(
            self.module.Path, "exists", return_value=True
        ), mock.patch.object(self.module.Path, "is_file", return_value=True):
            result = self.module.preflight(
                self.module.ROOT if hasattr(self.module, "ROOT") else Path("/tmp"),
                source,
                clang,
                lto="full",
                jobs=8,
                source_overlay={"verified": False},
            )
        self.assertFalse(result["build_allowed"])

    def test_full_lto_memory_gate_requires_nominal_32_gib_physical_ram(self):
        fake_disk = self.module.shutil._ntuple_diskusage(100, 10, 90)
        with mock.patch.object(
            self.module,
            "meminfo",
            return_value={"MemTotal": 15 * 1024**3, "SwapTotal": 16 * 1024**3},
        ), mock.patch.object(self.module.shutil, "disk_usage", return_value=fake_disk):
            resources = self.module.host_resources(Path("/tmp"))
        self.assertFalse(resources["full_lto_memory_ok"])
        self.assertTrue(resources["swap_recommended_ok"])

    def test_32_gib_host_with_swap_passes_resource_gate(self):
        fake_disk = self.module.shutil._ntuple_diskusage(100, 10, 90)
        with mock.patch.object(
            self.module,
            "meminfo",
            return_value={"MemTotal": 31 * 1024**3, "SwapTotal": 16 * 1024**3},
        ), mock.patch.object(self.module.shutil, "disk_usage", return_value=fake_disk):
            resources = self.module.host_resources(Path("/tmp"))
        self.assertTrue(resources["full_lto_memory_ok"])

    def test_32_gib_host_without_swap_is_allowed_with_advisory(self):
        fake_disk = self.module.shutil._ntuple_diskusage(100, 10, 90)
        with mock.patch.object(
            self.module,
            "meminfo",
            return_value={"MemTotal": 31 * 1024**3, "SwapTotal": 0},
        ), mock.patch.object(self.module.shutil, "disk_usage", return_value=fake_disk):
            resources = self.module.host_resources(Path("/tmp"))
        self.assertTrue(resources["full_lto_memory_ok"])
        self.assertFalse(resources["swap_recommended_ok"])


if __name__ == "__main__":
    unittest.main()
