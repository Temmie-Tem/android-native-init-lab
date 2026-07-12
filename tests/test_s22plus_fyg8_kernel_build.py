import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py"
SCRIPT_DIR = str(SCRIPT.parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


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
        self.assertNotIn("ANDROID_PRODUCT_OUT", env)
        self.assertEqual(env["ANDROID_KERNEL_OUT"], "/tmp/fyg8-work/out/android-kernel-out")
        self.assertEqual(env["KBUILD_BUILD_TIMESTAMP"], "Fri Aug 1 05:55:56 UTC 2025")
        self.assertEqual(env["GIT_CEILING_DIRECTORIES"], "/tmp")
        self.assertEqual(env["MAKEFLAGS"], "-j8")
        self.assertEqual(
            env["PATH"].split(":"),
            [
                "workspace/private/inputs/toolchains/aosp-clang-android12-release/clang-r416183b/bin",
                "/tmp/host-tool-overrides",
                "/tmp/fyg8-work/kernel_platform/prebuilts/build-tools/path/linux-x86",
                "/tmp/fyg8-work/kernel_platform/prebuilts/kernel-build-tools/linux-x86/bin",
                "/usr/bin",
                "/bin",
            ],
        )

    def test_host_tool_override_selects_only_required_gnu_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            work.mkdir()
            result = self.module.prepare_host_tool_overrides(work)
            override = work.parent / "host-tool-overrides"
            self.assertTrue(result["verified"])
            self.assertEqual({path.name for path in override.iterdir()}, {"tar", "xargs"})
            self.assertEqual((override / "tar").resolve(), Path("/usr/bin/tar"))
            self.assertEqual((override / "xargs").resolve(), Path("/usr/bin/xargs"))

    def test_incremental_dist_refresh_removes_only_known_readonly_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            host_bin = work / "out/msm-waipio-waipio-gki/host/bin"
            host_bin.mkdir(parents=True)
            for name in self.module.INCREMENTAL_READONLY_DIST_TARGETS:
                path = host_bin / name
                path.write_text(name, encoding="ascii")
                path.chmod(0o555)
            unrelated = host_bin / "keep"
            unrelated.write_text("keep", encoding="ascii")

            result = self.module.prepare_incremental_dist_refresh(work)

            self.assertTrue(result["verified"])
            self.assertEqual(len(result["removed"]), 2)
            self.assertTrue(unrelated.is_file())
            for name in self.module.INCREMENTAL_READONLY_DIST_TARGETS:
                self.assertFalse((host_bin / name).exists())

    def test_timestamp_control_is_exact_temporary_and_restored(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            setup = work / self.module.SETUP_ENV_PATH
            setup.parent.mkdir(parents=True)
            original = "prefix\n" + self.module.SETUP_ENV_TIMESTAMP_ORIGINAL + "suffix\n"
            setup.write_text(original, encoding="utf-8")
            setup.chmod(0o444)
            control = self.module.inspect_timestamp_control(work)
            self.assertTrue(control["verified"])
            self.assertEqual(control["original_mode"], 0o444)
            with self.module.apply_timestamp_control(work, control) as runtime:
                patched = setup.read_text(encoding="utf-8")
                self.assertIn(self.module.SETUP_ENV_TIMESTAMP_PINNED, patched)
                self.assertNotIn(self.module.SETUP_ENV_TIMESTAMP_ORIGINAL, patched)
                self.assertEqual(setup.stat().st_mode & 0o777, 0o444)
                self.assertFalse(runtime["restored"])
            self.assertEqual(setup.read_text(encoding="utf-8"), original)
            self.assertEqual(setup.stat().st_mode & 0o777, 0o444)
            self.assertTrue(runtime["restored"])
            self.assertTrue(runtime["patched_content_unchanged"])

    def test_timestamp_control_rejects_nonunique_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            setup = work / self.module.SETUP_ENV_PATH
            setup.parent.mkdir(parents=True)
            setup.write_text(
                self.module.SETUP_ENV_TIMESTAMP_ORIGINAL * 2,
                encoding="utf-8",
            )
            self.assertFalse(self.module.inspect_timestamp_control(work)["verified"])

    def test_timestamp_control_restores_after_body_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            setup = work / self.module.SETUP_ENV_PATH
            setup.parent.mkdir(parents=True)
            original = self.module.SETUP_ENV_TIMESTAMP_ORIGINAL
            setup.write_text(original, encoding="utf-8")
            control = self.module.inspect_timestamp_control(work)
            with self.assertRaisesRegex(RuntimeError, "synthetic build failure"):
                with self.module.apply_timestamp_control(work, control):
                    raise RuntimeError("synthetic build failure")
            self.assertEqual(setup.read_text(encoding="utf-8"), original)

    def test_kernel_banner_gate_requires_stock_timestamp(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            image = work / "out/msm-waipio-waipio-gki/gki_kernel/dist/Image"
            image.parent.mkdir(parents=True)
            banner = (
                "Linux version 5.10.226-android12-9-30958166-abS906NKSS7FYG8 "
                "(build-user@build-host) (Android (7284624, based on r416183b) "
                "clang version 12.0.5) #1 SMP PREEMPT Fri Aug 1 05:55:56 UTC 2025"
            )
            image.write_bytes(banner.encode("ascii") + b"\n\x00")
            result = self.module.kernel_banner_gate(work, expected_banner=banner)
            self.assertTrue(result["verified"])
            self.assertEqual(result["banner"], banner)
            image.write_bytes(b"Sun Jul 12 07:16:46 UTC 2026")
            self.assertFalse(
                self.module.kernel_banner_gate(work, expected_banner=banner)["verified"]
            )

    def test_stock_baseline_is_a_hard_exact_banner_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            baseline = Path(temporary) / "stock.json"
            banner = (
                "Linux version 5.10.226-android12-9-30958166-abS906NKSS7FYG8 "
                "(build-user@build-host) (Android (7284624, based on r416183b) "
                "clang version 12.0.5) #1 SMP PREEMPT Fri Aug 1 05:55:56 UTC 2025"
            )
            baseline.write_text(
                self.module.json.dumps(
                    {
                        "target": self.module.TARGET,
                        "kernel_release": self.module.STOCK_KERNEL_RELEASE,
                        "linux_banner": banner,
                    }
                ),
                encoding="ascii",
            )
            result = self.module.inspect_stock_baseline(baseline)
            self.assertTrue(result["verified"])
            self.assertEqual(result["expected_banner"], banner)

            baseline.write_text(
                baseline.read_text(encoding="ascii").replace("UTC 2025", "UTC 2026"),
                encoding="ascii",
            )
            self.assertFalse(self.module.inspect_stock_baseline(baseline)["verified"])

    def test_provider_module_closure_requires_every_owned_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            result_dir = Path(temporary) / "result"
            (work / "kernel_platform").mkdir(parents=True)
            result_dir.mkdir()
            for outputs in self.module.PROVIDER_EXPECTED_OUTPUTS.values():
                for relative in outputs:
                    path = work / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(relative, encoding="ascii")
            completed = self.module.subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(
                self.module.subprocess, "run", return_value=completed
            ) as mocked_run:
                result = self.module.run_provider_module_closure(
                    work, {"PATH": "/usr/bin:/bin"}, result_dir, jobs=8
                )

            self.assertTrue(result["verified"])
            self.assertEqual(mocked_run.call_count, 2)
            self.assertEqual(
                {provider["name"] for provider in result["providers"]},
                {"dataipa", "datarmnet_shs"},
            )
            for provider in result["providers"]:
                self.assertIn("ARCH=arm64", provider["command"])
                self.assertIn("CROSS_COMPILE=aarch64-linux-gnu-", provider["command"])

    def test_host_tool_override_rejects_unexpected_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "source"
            override = work.parent / "host-tool-overrides"
            override.mkdir()
            (override / "make").write_text("unexpected\n", encoding="ascii")
            with self.assertRaises(self.module.BuildError):
                self.module.prepare_host_tool_overrides(work)

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
