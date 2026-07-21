import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_r4w1e_e1_host_contract.py"


class S22PlusFyg8R4W1EE1HostContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1e_e1_host_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        cls.runtime_path = ROOT / cls.module.DEFAULT_RUNTIME
        cls.child_path = ROOT / cls.module.DEFAULT_CHILD
        cls.client_path = ROOT / cls.module.DEFAULT_CLIENT
        cls.header_path = ROOT / cls.module.DEFAULT_HEADER
        cls.inventory_path = ROOT / cls.module.DEFAULT_INVENTORY
        cls.runtime = cls.runtime_path.read_text(encoding="ascii")
        cls.child = cls.child_path.read_text(encoding="ascii")
        cls.client = cls.client_path.read_text(encoding="ascii")
        cls.header = cls.header_path.read_text(encoding="ascii")
        cls.inventory = cls.inventory_path.read_text(encoding="ascii")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_stage_values_match_the_p2_7_e1_carrier_sequence(self):
        result = self.module.check_header(self.header)
        sequence = [
            result["stages"][stage]
            for stage, _item, _operation in self.module.E1_STEPS
        ] + [result["stages"]["S22_R4W1E_STAGE_E1_SUCCESS"]]
        self.assertEqual(
            tuple(sequence),
            self.module.carrier.PROFILE_STAGE_SEQUENCES["E1"],
        )

    def test_source_contract_components_pass(self):
        self.assertTrue(self.module.check_header(self.header)["verified"])
        self.assertTrue(self.module.check_client(self.client)["verified"])
        self.assertTrue(self.module.check_runtime(self.runtime)["verified"])
        self.assertTrue(self.module.check_child(self.child)["verified"])
        self.assertTrue(self.module.check_inventory(self.inventory)["verified"])

    def test_full_host_contract_builds_two_identical_static_artifacts(self):
        result = self.module.run_check(
            self.runtime_path,
            self.child_path,
            self.client_path,
            self.header_path,
            self.inventory_path,
        )
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertTrue(result["build"]["byte_identical"])
        first = result["build"]["reproduction_a"]
        second = result["build"]["reproduction_b"]
        self.assertEqual(first, second)
        self.assertEqual(first["child"]["qemu_exit"], 23)
        self.assertEqual(
            first["child"]["qemu_stdout"].encode("ascii"),
            self.module.CHILD_TOKEN,
        )
        self.assertTrue(first["init"]["static_aarch64"])
        self.assertFalse(first["init"]["pt_interp"])

    def test_full_contract_has_no_kernel_image_or_device_authority(self):
        result = self.module.run_check(
            self.runtime_path,
            self.child_path,
            self.client_path,
            self.header_path,
            self.inventory_path,
        )
        self.assertTrue(result["safety"]["host_only"])
        for key in (
            "kernel_build",
            "boot_image_created",
            "vendor_ramdisk_created",
            "candidate_packaged",
            "device_contact",
            "flash",
            "live_authorized",
        ):
            self.assertFalse(result["safety"][key])
        self.assertIn("never live evidence", result["build"]["run_id_kind"])

    def test_runtime_rejects_stage_reorder_or_operation_substitution(self):
        mutations = (
            self.runtime.replace(
                "E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());",
                "E1_REQUIRE(S22_R4W1E_STAGE_SYS_MOUNTED, 0U, mount_proc());",
                1,
            ),
            self.runtime.replace(
                "E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_reap(&child));",
                "E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_start(&child));",
                1,
            ),
        )
        for changed in mutations:
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_runtime(changed)

    def test_runtime_rejects_weakened_operation_checkpoint_dominance(self):
        mutations = (
            self.runtime.replace(
                "fail_at((stage), (item_index), e1_operation_result);",
                "quiet_park();",
                1,
            ),
            self.runtime.replace(
                "static long mount_proc(void) {",
                "static long mount_proc(void) {\n"
                "    (void)s22_r4w1e_checkpoint_progress(\n"
                "        &g_checkpoint, S22_R4W1E_STAGE_PROC_MOUNTED, 0U);",
                1,
            ),
            self.runtime.replace(
                "static long mount_proc(void) {",
                "static long mount_proc(void) {\n"
                "    long (*publish_early)(\n"
                "        struct s22_r4w1e_checkpoint_client *, uint8_t, uint8_t) =\n"
                "        s22_r4w1e_checkpoint_progress;\n"
                "    (void)publish_early(\n"
                "        &g_checkpoint, S22_R4W1E_STAGE_PROC_MOUNTED, 0U);",
                1,
            ),
        )
        for changed in mutations:
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_runtime(changed)

    def test_runtime_rejects_raw_or_unlisted_syscall_growth(self):
        mutations = (
            self.runtime.replace(
                "#define NR_KILL 129",
                "#define NR_KILL 129\n#define NR_REBOOT 142",
                1,
            ).replace(
                "if (sys_getpid() != 1) {",
                "(void)syscall6(NR_REBOOT, 0, 0, 0, 0, 0, 0);\n"
                "    if (sys_getpid() != 1) {",
                1,
            ),
            self.runtime.replace(
                "if (sys_getpid() != 1) {",
                "(void)syscall6(142, 0, 0, 0, 0, 0, 0);\n"
                "    if (sys_getpid() != 1) {",
                1,
            ),
        )
        for changed in mutations:
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_runtime(changed)

    def test_raw_syscall_wrappers_reject_argument_register_swaps(self):
        changed_runtime = self.runtime.replace(
            'register long x1 asm("x1") = a1;\n'
            '    register long x2 asm("x2") = a2;',
            'register long x1 asm("x1") = a2;\n'
            '    register long x2 asm("x2") = a1;',
            1,
        )
        changed_client = self.client.replace(
            'register long x1 asm("x1") = a1;\n'
            '    register long x2 asm("x2") = a2;',
            'register long x1 asm("x1") = a2;\n'
            '    register long x2 asm("x2") = a1;',
            1,
        )
        changed_child = self.child.replace(
            'register long x1 asm("x1") = a1;\n'
            '    register long x2 asm("x2") = a2;',
            'register long x1 asm("x1") = a2;\n'
            '    register long x2 asm("x2") = a1;',
            1,
        )
        checks = (
            (self.module.check_runtime, changed_runtime),
            (self.module.check_client, changed_client),
            (self.module.check_child, changed_child),
        )
        for check, changed in checks:
            with self.subTest(), self.assertRaises(self.module.CheckError):
                check(changed)

    def test_runtime_rejects_failure_or_terminal_checkpoint_reorder(self):
        changed_failure = self.runtime.replace(
            "(void)s22_r4w1e_checkpoint_failure(\n"
            "        &g_checkpoint, stage, item_index, operation_error);\n"
            "    quiet_park();",
            "quiet_park();\n"
            "    (void)s22_r4w1e_checkpoint_failure(\n"
            "        &g_checkpoint, stage, item_index, operation_error);",
            1,
        )
        changed_terminal = self.runtime.replace(
            "E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULES_VERIFIED, 0U, "
            "verify_exact_modules());\n"
            "    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0)",
            "if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0)\n"
            "    E1_REQUIRE(S22_R4W1E_STAGE_WDT_MODULES_VERIFIED, 0U, "
            "verify_exact_modules());",
            1,
        )
        for changed in (changed_failure, changed_terminal):
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_runtime(changed)

    def test_runtime_rejects_module_reorder_and_scope_growth(self):
        changed_order = self.runtime.replace(
            '{"smem.ko", "smem"},\n    {"minidump.ko", "minidump"},',
            '{"minidump.ko", "minidump"},\n    {"smem.ko", "smem"},',
            1,
        )
        changed_scope = self.runtime + '\nstatic const char *bad = "/dev/block/sda";\n'
        for changed in (changed_order, changed_scope):
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_runtime(changed)

    def test_runtime_pins_exec_token_eof_exit_reap_and_bounded_park(self):
        for token in (
            "wait_for_exec_result(child)",
            "token_equals(token, used, k_child_token)",
            "status == (23 << 8)",
            "while (sys_wait4(-1, &status, WNOHANG) > 0)",
            "sys_nanosleep(10000000000LL)",
        ):
            self.assertIn(token, self.runtime)
        self.assertNotIn('asm volatile("wfe"', self.module.extract_function(
            self.runtime, "static void quiet_park(void)"
        ))

    def test_client_rejects_abi_crc_path_and_publish_order_mutations(self):
        mutations = (
            self.client.replace("0xedb88320U", "0x82f63b78U", 1),
            self.client.replace("uint32_t crc = ~0U;", "uint32_t crc = 0U;", 1),
            self.client.replace("return crc ^ ~0U;", "return crc;", 1),
            self.client.replace(
                "#define S22_R4W1E_PROFILE_E1 1U",
                "#define S22_R4W1E_PROFILE_E1 2U",
                1,
            ),
            self.client.replace(
                '"/proc/s22_checkpoint"', '"/proc/not-the-checkpoint"', 1
            ),
            self.client.replace(
                "client->stage = stage;",
                "client->stage = 0;",
                1,
            ),
            self.client.replace(
                "offsetof(struct s22_r4w1e_checkpoint_request, crc32) == 28U",
                "offsetof(struct s22_r4w1e_checkpoint_request, crc32) == 24U",
                1,
            ),
        )
        for changed in mutations:
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_client(changed)

    def test_client_probe_rejects_semantic_crc_or_profile_bypass(self):
        mutations = (
            self.client.replace(
                "crc ^= bytes[index];", "crc ^= bytes[index] ^ 1U;", 1
            ),
            self.client.replace(
                "request.profile = S22_R4W1E_PROFILE_E1;",
                "request.profile = S22_R4W1E_PROFILE_E1;\n"
                "    request.profile = 2U;",
                1,
            ),
        )
        for changed in mutations:
            with self.subTest(), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(self.module.CheckError):
                    self.module.probe_client_request(
                        Path(temporary),
                        changed,
                        self.header.encode("ascii"),
                        self.module.carrier.MODEL_RUN_IDS["E1"],
                        self.module.require_tools(),
                    )

    def test_client_rejects_openat_path_and_flags_argument_swap(self):
        changed = self.client.replace(
            "NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, flags, 0, 0, 0",
            "NR_OPENAT, AT_FDCWD, flags, (long)(uintptr_t)path, 0, 0, 0",
            1,
        )
        with self.assertRaises(self.module.CheckError):
            self.module.check_client(changed)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(self.module.CheckError):
                self.module.probe_client_request(
                    Path(temporary),
                    changed,
                    self.header.encode("ascii"),
                    self.module.carrier.MODEL_RUN_IDS["E1"],
                    self.module.require_tools(),
                )

    def test_full_contract_rejects_any_unpinned_source_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            child = Path(temporary) / "child.c"
            child.write_text(self.child + "\n", encoding="ascii")
            with self.assertRaises(self.module.CheckError):
                self.module.run_check(
                    self.runtime_path,
                    child,
                    self.client_path,
                    self.header_path,
                    self.inventory_path,
                )

    def test_compile_ignores_unpinned_adjacent_header_shadow(self):
        baseline = self.module.run_check(
            self.runtime_path,
            self.child_path,
            self.client_path,
            self.header_path,
            self.inventory_path,
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            runtime = directory / self.runtime_path.name
            client = directory / self.client_path.name
            runtime.write_text(self.runtime, encoding="ascii")
            client.write_text(self.client, encoding="ascii")
            shadow = directory / self.header_path.name
            shadow.write_text(
                self.header.replace(
                    "#define S22_R4W1E_STAGE_PROC_MOUNTED 0x10U",
                    "#define S22_R4W1E_STAGE_PROC_MOUNTED 0x09U",
                    1,
                ),
                encoding="ascii",
            )
            result = self.module.run_check(
                runtime,
                self.child_path,
                client,
                self.header_path,
                self.inventory_path,
            )
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["build"], baseline["build"])

    def test_compile_ignores_poisoned_ambient_cpath(self):
        baseline = self.module.run_check(
            self.runtime_path,
            self.child_path,
            self.client_path,
            self.header_path,
            self.inventory_path,
        )
        with tempfile.TemporaryDirectory() as temporary:
            include = Path(temporary)
            (include / "stdint.h").write_text(
                "#include_next <stdint.h>\n"
                "#ifdef __aarch64__\n"
                "#define long short\n"
                "#endif\n",
                encoding="ascii",
            )
            with mock.patch.dict(os.environ, {"CPATH": str(include)}):
                result = self.module.run_check(
                    self.runtime_path,
                    self.child_path,
                    self.client_path,
                    self.header_path,
                    self.inventory_path,
                )
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["build"], baseline["build"])

    def test_child_rejects_token_exit_and_authority_mutations(self):
        mutations = (
            self.child.replace("4c3e58c0785b", "000000000000", 1),
            self.child.replace("sys_exit(23);", "sys_exit(0);", 1),
            self.child + "\n#define NR_OPENAT 56\n",
            self.child.replace(
                "#define NR_EXIT 93",
                "#define NR_EXIT 93\n#define NR_KILL 129",
                1,
            ).replace(
                "size_t offset = 0;",
                "(void)syscall3(NR_KILL, 1, 9, 0);\n    size_t offset = 0;",
                1,
            ),
            self.child.replace(
                "size_t offset = 0;",
                "(void)syscall3(129, 1, 9, 0);\n    size_t offset = 0;",
                1,
            ),
        )
        for changed in mutations:
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_child(changed)

    def test_inventory_rejects_module_hash_or_exclusion_loss(self):
        changed_hash = self.inventory.replace(
            self.module.MODULE_SPECS[0][3], "0" * 64, 1
        )
        without_excluded = "\n".join(
            line
            for line in self.inventory.splitlines()
            if not line.startswith("sec_log_buf.ko\t")
        )
        for changed in (changed_hash, without_excluded):
            with self.subTest(), self.assertRaises(self.module.CheckError):
                self.module.check_inventory(changed)

    def test_direct_reader_rejects_symlinks_and_oversize(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source"
            source.write_bytes(b"exact")
            alias = directory / "alias"
            alias.symlink_to(source)
            with self.assertRaises(self.module.CheckError):
                self.module.read_direct(alias, "alias")
            with self.assertRaises(self.module.CheckError):
                self.module.read_direct(source, "source", 4)


if __name__ == "__main__":
    unittest.main()
