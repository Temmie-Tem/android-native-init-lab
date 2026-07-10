import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_v3432_pid1_keystone.py"
)
SOURCE = Path(
    "workspace/public/src/native-init/s22plus_init_v3432_pid1_keystone.c"
)
DEFAULT_MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3432_pid1_keystone_v0_1/manifest.json"
)
RUN_ID = "db4d3b66480bec29158c9ac9bfede880"


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "build_s22plus_v3432_pid1_keystone", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3432Pid1KeystoneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.repo_root()
        cls.source = cls.root / SOURCE
        cls.record = cls.module.marker_record(RUN_ID)
        cls.expectation = cls.module.make_expectation(RUN_ID)

    def test_source_contract_is_minimal_ordered_and_parks(self):
        contract = self.module.verify_source_contract(self.source)
        self.assertEqual(contract["module_load_call_count"], 1)
        self.assertEqual(contract["marker_emit_call_count"], 1)
        self.assertTrue(contract["marker_pid_derived_from_getpid"])
        self.assertTrue(contract["all_runtime_paths_park"])

    def test_context_is_non_circular_and_binds_load_bearing_inputs(self):
        context = self.record["context_manifest"]
        self.assertEqual(context["run_id"], RUN_ID)
        self.assertEqual(
            context["expected_live_osrelease"],
            self.module.keystone.EXPECTED_LIVE_OSRELEASE,
        )
        self.assertEqual(
            context["module"]["sha256"], self.module.keystone.MODULE_SHA256
        )
        self.assertEqual(
            context["keystone_contract_sha256"],
            self.module.keystone.CONTRACT_SHA256,
        )
        self.assertNotIn("source_sha256", context)
        self.assertNotIn("boot_sha256", context)
        changed = self.module.marker_record("f" * 32)
        self.assertNotEqual(
            self.record["context_sha256"], changed["context_sha256"]
        )

    def test_expected_marker_is_exact_positive(self):
        result = self.module.keystone.classify_snapshot(
            "retention",
            self.record["frame"].encode("ascii"),
            self.expectation,
        )
        self.assertEqual(
            result["classification"],
            "PASS_PID1_EXECUTION_AND_OBSERVER_LOAD",
        )

    def test_generated_header_pins_frame_and_pid_offset(self):
        header = self.module.render_generated_header(self.record)
        self.assertIn(self.record["frame"], header)
        self.assertIn(
            f'#define V3432_PID_HEX_OFFSET {self.record["pid_hex_offset"]}U',
            header,
        )
        frame = self.record["frame"]
        offset = self.record["pid_hex_offset"]
        self.assertEqual(frame[offset : offset + 8], "00000001")

    def test_runtime_has_no_pre_marker_osrelease_or_old_stage_a_gates(self):
        source = self.source.read_text(encoding="ascii")
        self.assertNotIn("/proc/sys/kernel/osrelease", source)
        self.assertNotIn("/proc/modules", source)
        self.assertNotIn("/sys/bus/platform/drivers", source)
        self.assertNotIn("PRECHECK", source)
        self.assertNotIn("FINAL", source)
        self.assertNotIn("emit_failure", source)

    def test_getpid_dominates_runtime_operations_in_source(self):
        source = self.source.read_text(encoding="ascii").rsplit("#else", 1)[-1]
        ordered = [
            "long pid = v3432_getpid();",
            "V3432_STAGE_START, pid == 1",
            "v3432_prepare_volatile_runtime()",
            "v3432_load_observer()",
            "v3432_observer_ready()",
            "v3432_emit_marker(pid)",
            "v3432_quiet_park();",
        ]
        position = 0
        positions = []
        for token in ordered:
            position = source.index(token, position)
            positions.append(position)
            position += len(token)
        self.assertEqual(positions, sorted(positions))

    def test_compile_disassembly_and_qemu_selftest(self):
        with tempfile.TemporaryDirectory() as temp:
            build_dir = Path(temp)
            generated = build_dir / "generated"
            generated.mkdir()
            (generated / self.module.GENERATED_HEADER).write_text(
                self.module.render_generated_header(self.record),
                encoding="ascii",
            )
            info = self.module.compile_init(
                self.source,
                generated,
                build_dir / "init",
                build_dir,
                self.record,
            )
            self.assertTrue(info["state_marker_qemu_selftest"])
            self.assertEqual(info["first_start_syscall"], "getpid")
            self.assertTrue(info["no_interp"])
            self.assertEqual(info["undefined_symbols"], [])
            self.assertLess(info["size"], 65536)

    def test_runtime_syscall_allowlist_is_narrow(self):
        expected = {
            "mknodat",
            "mkdirat",
            "mount",
            "openat",
            "close",
            "write",
            "nanosleep",
            "getpid",
            "finit_module",
        }
        self.assertEqual(set(self.module.EXPECTED_SYSCALLS), expected)
        forbidden = set(self.module.FORBIDDEN_RUNTIME_SYSCALLS)
        self.assertEqual(
            forbidden,
            {"read", "exit_group", "reboot", "clone", "execve"},
        )

    def test_exact_module_is_injected_at_deterministic_path(self):
        self.assertEqual(
            self.module.MODULE_RAMDISK_PATH, "observer/sec_log_buf.ko"
        )
        self.assertEqual(
            "/" + self.module.MODULE_RAMDISK_PATH,
            self.module.keystone.EMBEDDED_MODULE_PATH,
        )
        module = (
            self.root
            / self.module.keystone.observer.MODULE_DIR
            / self.module.keystone.MODULE_NAME
        )
        self.assertEqual(module.stat().st_size, self.module.keystone.MODULE_SIZE)
        self.assertEqual(
            self.module.sha256_file(module),
            self.module.keystone.MODULE_SHA256,
        )

    def test_keystone_design_remains_no_live(self):
        self.assertFalse(self.module.keystone.CONTRACT_CORE["live_authorized"])
        self.assertFalse(
            self.module.keystone.CONTRACT_CORE["image_build_authorized"]
        )

    @unittest.skipUnless(DEFAULT_MANIFEST.is_file(), "V3432 manifest unavailable")
    def test_built_manifest_is_host_only_and_exact(self):
        manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], self.module.SCHEMA)
        self.assertEqual(manifest["run_id"], RUN_ID)
        self.assertEqual(manifest["tar_members"], ["boot.img.lz4"])
        self.assertEqual(
            manifest["contracts"]["keystone_sha256"],
            self.module.keystone.CONTRACT_SHA256,
        )
        self.assertEqual(
            manifest["expected_marker_classification"]["classification"],
            "PASS_PID1_EXECUTION_AND_OBSERVER_LOAD",
        )
        self.assertEqual(
            manifest["ramdisk"]["added_entries"],
            ["observer", "observer/sec_log_buf.ko"],
        )
        self.assertEqual(
            manifest["ramdisk"]["module_sha256"],
            self.module.keystone.MODULE_SHA256,
        )
        self.assertEqual(manifest["init"]["first_start_syscall"], "getpid")
        self.assertTrue(manifest["init"]["state_marker_qemu_selftest"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["pid1_never_exits"])
        self.assertFalse(manifest["safety"]["candidate_transition"])


if __name__ == "__main__":
    unittest.main()
