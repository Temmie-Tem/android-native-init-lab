"""Regression tests for build_native_init_boot_v2273_workqueue_fwclass_func_sampler."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2273 = load_revalidation("build_native_init_boot_v2273_workqueue_fwclass_func_sampler")


def nested_namespace(*names, leaf):
    current = leaf
    for name in reversed(names):
        current = types.SimpleNamespace(**{name: current})
    return current


def fake_base_args():
    return [
        "--cycle", "OLD",
        "--decision", "old-decision",
        "--cycle-label", "old-label",
        "--init-version", "0.0.0",
        "--init-build", "old-build",
        "--out-dir", "old-out",
        "--init-binary", "old-init",
        "--helper-binary", "old-helper",
        "--ramdisk-cpio", "old-ramdisk",
        "--boot-image", "old-boot",
        "--wifi-test-klog-prefix", "OLD",
        "--wifi-test-disable", "old-disable",
        "--wifi-test-log", "old-log",
        "--wifi-test-summary", "old-summary",
        "--wifi-test-helper-result", "old-helper-result",
        "--wifi-test-pid", "old-pid",
        "--wifi-test-watcher-pid", "old-watcher",
        "--wifi-test-property-root", "old-prop",
        "--wifi-test-helper-mode", "old-mode",
        "--wifi-test-watch-sec", "1",
        "--wifi-test-supervisor-timeout-sec", "2",
    ]


def fake_v2237_with_base(fake_base):
    def set_arg(args, key, value):
        index = args.index(key)
        args[index + 1] = value

    helper_builder = types.SimpleNamespace(HELPER_FLAGS=("builder-initial",))
    prev2131 = types.SimpleNamespace(HELPER_FLAGS=("prev2131-initial",))
    prev2133 = types.SimpleNamespace(prev2131=prev2131, HELPER_FLAGS=("prev2133-initial",))
    prev2135 = types.SimpleNamespace(prev2133=prev2133, HELPER_FLAGS=("prev2135-initial",))
    prev2137 = types.SimpleNamespace(
        prev2135=prev2135,
        HELPER_FLAGS=(
            "-DOTHER=1",
            "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1",
            v2273.WORKQUEUE_SAMPLER_FLAGS[0],
        ),
    )
    v726 = types.SimpleNamespace(set_arg=set_arg)
    v2230 = nested_namespace(
        "v2189",
        "v2188",
        "v2187",
        "v2182",
        "v2178",
        "v2176",
        "v2174",
        "v2169",
        "v726",
        leaf=v726,
    )

    def with_bridge_flag(flags):
        bridge = "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1"
        return (*tuple(flag for flag in flags if flag != bridge), bridge)

    fake = types.SimpleNamespace(
        OUT_DIR=None,
        REPORT_PATH=None,
        BOOT_IMAGE=None,
        INIT_BINARY=None,
        RAMDISK_CPIO=None,
        REMOTE_PROPERTY_ROOT=None,
        EXTRA_INIT_FLAGS=("-DEXTRA=1",),
        HELPER_MODE="fake-helper-mode",
        HELPER_RUNTIME_MODE="fake-runtime-mode",
        v2230=v2230,
        with_bridge_flag=with_bridge_flag,
        base_module=lambda: fake_base,
        helper_chain=lambda: prev2137,
        helper_builder_module=lambda: helper_builder,
    )
    fake.configure_base = lambda: setattr(fake, "configured", True)
    fake.patch_mkbootimg_tools = lambda base: setattr(base, "mkbootimg_patched", True)
    return fake, prev2137, helper_builder


class PatchV2237:
    def __init__(self, fake):
        self.fake = fake
        self.old = None

    def __enter__(self):
        self.old = v2273.v2237
        v2273.v2237 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2273.v2237 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_sha256_hashes_file_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "payload.bin"
            payload.write_bytes(b"v2273")

            digest = v2273.sha256(payload)

        self.assertEqual(digest, "8a9f7d47ce100e577adf2a787909b8da5f2beab560655a9e67f02f36e39a263b")

    def test_with_workqueue_flags_deduplicates_bridge_and_sampler_flags(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, _ = fake_v2237_with_base(fake_base)

        with PatchV2237(fake):
            flags = v2273.with_workqueue_flags((
                "-DOTHER=1",
                v2273.WORKQUEUE_SAMPLER_FLAGS[0],
                "-DSECOND=1",
                v2273.WORKQUEUE_SAMPLER_FLAGS[-1],
            ))

        self.assertEqual(flags[-len(v2273.WORKQUEUE_SAMPLER_FLAGS):], v2273.WORKQUEUE_SAMPLER_FLAGS)
        self.assertEqual(flags.count(v2273.WORKQUEUE_SAMPLER_FLAGS[0]), 1)
        self.assertIn("-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1", flags)

    def test_configure_base_rewrites_v2237_axes_and_propagates_sampler_flags(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, prev2137, helper_builder = fake_v2237_with_base(fake_base)

        with PatchV2237(fake):
            helper_flags = v2273.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake.configured)
        self.assertEqual(fake.OUT_DIR, v2273.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2273.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2273")
        self.assertEqual(args["--decision"], "v2273-workqueue-fwclass-func-sampler-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.273")
        self.assertEqual(args["--init-build"], "v2273-workqueue-fwclass-func-sampler")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2273")
        self.assertEqual(args["--wifi-test-watch-sec"], "190")
        self.assertEqual(args["--wifi-test-supervisor-timeout-sec"], "245")
        self.assertIn("a90_android_execns_probe_v431_workqueue_fwclass_func_sampler", args["--helper-binary"])
        self.assertEqual(helper_flags[-len(v2273.WORKQUEUE_SAMPLER_FLAGS):], v2273.WORKQUEUE_SAMPLER_FLAGS)
        self.assertEqual(prev2137.HELPER_FLAGS, helper_flags)
        self.assertEqual(prev2137.prev2135.HELPER_FLAGS, helper_flags)
        self.assertEqual(prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS, helper_flags)
        self.assertEqual(helper_builder.HELPER_FLAGS, helper_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2273.EXTRA_INIT_FLAGS)

    def test_patch_ramdisk_helpers_adds_workqueue_sampler_binary(self):
        original = lambda args: {"bin/existing": Path("existing")}
        base_wrapper = types.SimpleNamespace(base=types.SimpleNamespace(ramdisk_helpers=original))

        v2273.patch_ramdisk_helpers(base_wrapper)
        helpers = base_wrapper.base.ramdisk_helpers(types.SimpleNamespace())

        self.assertEqual(helpers["bin/existing"], Path("existing"))
        self.assertEqual(helpers[v2273.BPF_HELPER_RAMDISK_PATH], v2273.BPF_HELPER_BINARY)

    def test_render_report_includes_workqueue_contract_and_safety_scope(self):
        manifest = {
            "decision": "v2273-workqueue-fwclass-func-sampler-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2273.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.273",
            "init_build": "v2273-workqueue-fwclass-func-sampler",
            "helper_marker": "a90_android_execns_probe v431",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 245,
            },
        }

        report = v2273.render_report(manifest, ("-DOTHER=1", *v2273.WORKQUEUE_SAMPLER_FLAGS), "bpf-sha")

        self.assertIn("# Native Init V2273 Workqueue Firmware Class Function Sampler Source Build", report)
        self.assertIn("Decision: `v2273-workqueue-fwclass-func-sampler-source-build-pass`", report)
        self.assertIn("A90 Linux init 0.9.273 (v2273-workqueue-fwclass-func-sampler)", report)
        self.assertIn("Workqueue sampler SHA256: `bpf-sha`", report)
        self.assertIn("A90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_SAMPLER=1", report)
        self.assertIn("workqueue_queue_work", report)
        self.assertIn("workqueue_execute_start", report)
        self.assertIn("/cache/native-init-v2273-workqueue-fwclass.log", report)
        self.assertIn("does not write tracefs controls", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_live_candidate_without_running_real_build(self):
        tmp_parent = v2273.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2273_workqueue_fwclass_func_sampler.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2273-workqueue-fwclass-func-sampler-source-build-pass",
                "boot_image": str(boot_image.relative_to(v2273.REPO_ROOT)),
                "boot_sha256": "boot-sha",
                "init_version": "0.9.273",
                "init_build": "v2273-workqueue-fwclass-func-sampler",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2273.OUT_DIR,
                "BOOT_IMAGE": v2273.BOOT_IMAGE,
                "REPORT_PATH": v2273.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2273.configure_base,
                "build_bpf_helper": v2273.build_bpf_helper,
                "helper_builder_module": v2273.helper_builder_module,
                "base_module": v2273.base_module,
            }
            helper_builder = types.SimpleNamespace()
            fake_base = types.SimpleNamespace(
                base=types.SimpleNamespace(ramdisk_helpers=lambda args: {}),
                main=lambda: 0,
            )
            fake_v2237 = types.SimpleNamespace(
                patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True)
            )
            v2273.OUT_DIR = out_dir
            v2273.BOOT_IMAGE = boot_image
            v2273.REPORT_PATH = report_path
            v2273.configure_base = lambda: ("-DTEST=1", *v2273.WORKQUEUE_SAMPLER_FLAGS)
            v2273.build_bpf_helper = lambda: "bpf-sha"
            v2273.helper_builder_module = lambda: helper_builder
            v2273.base_module = lambda: fake_base
            try:
                with PatchV2237(fake_v2237):
                    rc = v2273.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2273, name, value)
                for name, value in old_functions.items():
                    setattr(v2273, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            live_candidate = json.loads((out_dir / "live-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2273.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2273.EXPECTED_HELPER_MARKER)
        self.assertEqual(manifest["candidate_tag"], "v2273-workqueue-fwclass-func-sampler")
        self.assertEqual(manifest["parent_baseline"], "v2237-supplicant-terminate-poll")
        self.assertFalse(manifest["promoted_baseline"])
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1", *v2273.WORKQUEUE_SAMPLER_FLAGS])
        self.assertEqual(manifest["workqueue_sampler"]["sha256"], "bpf-sha")
        self.assertEqual(manifest["workqueue_sampler"]["duration_ms"], v2273.WORKQUEUE_DURATION_MS)
        self.assertEqual(manifest["workqueue_sampler"]["print_limit"], v2273.WORKQUEUE_PRINT_LIMIT)
        self.assertEqual(manifest["workqueue_sampler"]["wait_ms"], v2273.WORKQUEUE_WAIT_MS)
        self.assertEqual(
            manifest["workqueue_sampler"]["events"],
            ["workqueue:workqueue_queue_work", "workqueue:workqueue_execute_start"],
        )
        self.assertEqual(live_candidate["candidate_tag"], "v2273-workqueue-fwclass-func-sampler")
        self.assertEqual(live_candidate["workqueue_sampler_sha256"], "bpf-sha")
        self.assertEqual(live_candidate["next_live_cycle"], "V2274")


if __name__ == "__main__":
    unittest.main()
