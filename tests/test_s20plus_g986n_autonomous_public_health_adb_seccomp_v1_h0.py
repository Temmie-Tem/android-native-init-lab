#!/usr/bin/env python3
"""Hostile H0 tests for the inactive exact S20+ ADB seccomp candidate."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import signal
import struct
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_adb_seccomp_v1_h0.py"
)


def load_module():
    name = "s20plus_g986n_autonomous_public_health_adb_seccomp_v1_h0_tested"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load ADB seccomp candidate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeInstallOperations:
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.calls = []
        self.program = None
        self.binding = None

    def set_no_new_privs(self):
        self.calls.append("no-new-privs")
        if self.fail_at == "no-new-privs":
            raise OSError("injected no_new_privs failure")

    def install_filter(self, program):
        self.calls.append("filter")
        self.program = program
        if self.fail_at == "filter":
            raise OSError("injected filter failure")

    def execveat(self, binding):
        self.calls.append("execveat")
        self.binding = binding
        if self.fail_at == "execveat":
            raise OSError("injected execveat failure")


EXACT_HOST = (
    sys.platform.startswith("linux")
    and platform.machine() == "x86_64"
    and sys.byteorder == "little"
    and struct.calcsize("P") == 8
)


class AdbSeccompV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.source = SOURCE.read_bytes()
        cls.binding = cls.m.sample_binding()
        cls.instructions = cls.m.build_filter_instructions(cls.binding)
        cls.program = cls.m.build_filter_program(cls.binding)

    def assert_sigsys(self, result):
        self.assertFalse(result.timed_out)
        self.assertFalse(result.exited)
        self.assertIsNone(result.exit_code)
        self.assertTrue(result.signaled)
        self.assertEqual(result.signal_number, signal.SIGSYS)

    def test_render_plan_is_exact_inactive_h0(self):
        plan = self.m.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_SECCOMP_V1_PASS_GO_NOT_ACTIVE",
        )
        self.assertEqual(
            plan["target"],
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertTrue(plan["gates"])
        self.assertFalse(any(plan["gates"].values()))
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["connected_backends"], [])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["root_commands"], [])
        self.assertEqual(plan["odin_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])
        self.assertFalse(plan["authority"]["device_contact"])
        self.assertFalse(plan["authority"]["adb_executed"])
        self.assertFalse(plan["authority"]["socket_or_network_used"])
        self.assertFalse(plan["authority"]["production_filter_installed"])
        self.assertFalse(plan["authority"]["live_authority"])

    def test_self_normalized_anchor_is_exact_and_transition_stable(self):
        self.assertEqual(
            self.m.normalized_source_sha256(self.source),
            self.m.EXPECTED_SELF_NORMALIZED_SHA256,
        )
        self.assertEqual(
            self.m.render_plan()["self"]["sha256"],
            self.m.sha256_bytes(self.source),
        )
        transitioned, status_count = re.subn(
            rb'^STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_SECCOMP_V1_PASS_GO_NOT_ACTIVE"$',
            b'STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_SECCOMP_V1_REVIEWED_NOT_ACTIVE"',
            self.source,
            count=1,
            flags=re.MULTILINE,
        )
        self.assertEqual(status_count, 1)
        for name in self.m.NORMALIZED_GATE_NAMES:
            transitioned, count = re.subn(
                rf"^{name} = False$".encode("ascii"),
                f"{name} = True".encode("ascii"),
                transitioned,
                count=1,
                flags=re.MULTILINE,
            )
            self.assertEqual(count, 1)
        self.assertEqual(
            self.m.normalized_source_sha256(transitioned),
            self.m.EXPECTED_SELF_NORMALIZED_SHA256,
        )

    def test_exact_runtime_proxy_adb_and_helper_identities_are_pinned(self):
        for identity in (self.m.RUNTIME_IDENTITY, self.m.PROXY_IDENTITY):
            payload = Path(identity["path"]).read_bytes()
            self.assertEqual(len(payload), identity["size"])
            self.assertEqual(self.m.sha256_bytes(payload), identity["sha256"])
        for identity in (self.m.ADB_IDENTITY, self.m.HELPER_IDENTITY):
            path = Path(identity["path"])
            self.assertEqual(path.resolve(), Path(identity["canonical_realpath"]))
            payload = path.read_bytes()
            self.assertEqual(len(payload), identity["size"])
            self.assertEqual(self.m.sha256_bytes(payload), identity["sha256"])

    def test_exact_host_abi_and_ubuntu_identity_match(self):
        identity = self.m.HOST_IDENTITY
        self.assertEqual(platform.system(), identity["system"])
        self.assertEqual(platform.machine(), identity["machine"])
        self.assertEqual(platform.release(), identity["kernel_release"])
        self.assertEqual(sys.byteorder, identity["byteorder"])
        self.assertEqual(struct.calcsize("P") * 8, identity["pointer_bits"])
        self.assertEqual(platform.libc_ver(), (identity["libc_name"], identity["libc_version"]))
        os_release = Path(identity["os_release_path"]).read_bytes()
        self.assertEqual(len(os_release), identity["os_release_size"])
        self.assertEqual(self.m.sha256_bytes(os_release), identity["os_release_sha256"])
        text = os_release.decode("utf-8")
        self.assertIn('ID=ubuntu\n', text)
        self.assertIn('VERSION_ID="26.04"\n', text)
        self.assertTrue(self.m.exact_probe_host_matches())

    def test_pinned_helper_opener_returns_only_exact_cloexec_file(self):
        descriptor = self.m._open_pinned_helper()
        try:
            self.assertFalse(os.get_inheritable(descriptor))
            metadata = os.fstat(descriptor)
            self.assertEqual(metadata.st_size, self.m.HELPER_IDENTITY["size"])
            self.assertEqual(
                self.m.sha256_bytes(os.pread(descriptor, metadata.st_size + 1, 0)),
                self.m.HELPER_IDENTITY["sha256"],
            )
        finally:
            os.close(descriptor)

    def test_cli_is_render_only(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(self.m.run(["--render-plan"]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], self.m.STATUS)
        errors = io.StringIO()
        with redirect_stderr(errors):
            with self.assertRaises(SystemExit):
                self.m.run([])
            with self.assertRaises(SystemExit):
                self.m.run(["--connected"])
            with self.assertRaises(SystemExit):
                self.m.run(["--probe"])

    def test_false_gate_stops_before_executor(self):
        with self.assertRaisesRegex(self.m.AdbSeccompV1Error, "inactive"):
            self.m.attended_open_and_read()

    def test_all_true_gates_still_reach_unimplemented_stub(self):
        patches = [
            mock.patch.object(self.m, name, True)
            for name in self.m.NORMALIZED_GATE_NAMES
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        with self.assertRaisesRegex(
            self.m.AdbSeccompV1Error, "executor is not implemented"
        ):
            self.m.attended_open_and_read()

    def test_uapi_constants_and_syscall_closure_are_exact(self):
        self.assertEqual(self.m.AUDIT_ARCH_X86_64, 0xC000003E)
        self.assertEqual(self.m.X32_SYSCALL_BIT, 0x40000000)
        self.assertEqual(self.m.AT_EMPTY_PATH, 0x1000)
        self.assertEqual(self.m.SECCOMP_RET_KILL_PROCESS, 0x80000000)
        self.assertEqual(self.m.SECCOMP_RET_TRAP, 0x00030000)
        self.assertEqual(self.m.SECCOMP_RET_ALLOW, 0x7FFF0000)
        self.assertEqual(
            dict(self.m.FORBIDDEN_SYSCALLS),
            {
                "bind": 49,
                "listen": 50,
                "clone": 56,
                "fork": 57,
                "vfork": 58,
                "execve": 59,
                "clone3": 435,
            },
        )
        self.assertEqual(len(set(self.m.FORBIDDEN_SYSCALLS.values())), 7)
        self.assertNotIn(self.m.SYS_EXECVEAT, self.m.FORBIDDEN_SYSCALLS.values())
        self.assertEqual(
            dict(self.m.X32_REPRESENTATIVE_SYSCALLS),
            {
                "bind": 0x40000000 + 49,
                "listen": 0x40000000 + 50,
                "clone": 0x40000000 + 56,
                "fork": 0x40000000 + 57,
                "vfork": 0x40000000 + 58,
                "clone3": 0x40000000 + 435,
                "execve": 0x40000000 + 520,
                "execveat": 0x40000000 + 545,
            },
        )

    def test_linux_struct_layout_and_program_size_are_exact(self):
        self.assertEqual(self.m.SOCK_FILTER_STRUCT.size, 8)
        self.assertEqual(self.m.SECCOMP_DATA_STRUCT.size, 64)
        self.assertEqual(self.m.SECCOMP_DATA_ARGS_OFFSET, 16)
        self.assertEqual(self.m.SECCOMP_DATA_ARG_STRIDE, 8)
        self.assertEqual(len(self.instructions), 53)
        self.assertEqual(len(self.program), 424)
        self.assertEqual(
            self.m.sha256_bytes(self.program),
            self.m.EXPECTED_SAMPLE_FILTER_SHA256,
        )

    def test_filter_bytes_are_deterministic_and_parse_round_trip(self):
        self.assertEqual(self.program, self.m.build_filter_program(self.binding))
        self.assertEqual(self.instructions, self.m.parse_filter_program(self.program))
        self.assertEqual(self.program, self.m.pack_filter_program(self.instructions))
        result = self.m.validate_filter_program(self.program, self.binding)
        self.assertEqual(result.instruction_count, 53)
        self.assertEqual(result.byte_count, 424)
        self.assertEqual(result.sha256, self.m.sha256_bytes(self.program))

    def test_little_endian_instruction_encoding_is_explicit(self):
        first = self.instructions[0]
        self.assertEqual(
            self.program[:8],
            struct.pack("<HBBI", first.code, first.jump_true, first.jump_false, first.value),
        )
        self.assertEqual(first.code, self.m.BPF_LD_W_ABS)
        self.assertEqual(first.value, self.m.SECCOMP_DATA_ARCH_OFFSET)
        self.assertEqual(self.instructions[1].value, self.m.AUDIT_ARCH_X86_64)
        self.assertEqual(self.instructions[2].value, self.m.SECCOMP_RET_KILL_PROCESS)

    def test_parser_rejects_empty_partial_wrong_type_and_instruction_overflow(self):
        for payload in (b"", self.program[:-1], bytearray(self.program), None):
            with self.subTest(payload_type=type(payload)):
                with self.assertRaises(self.m.AdbSeccompV1Error):
                    self.m.parse_filter_program(payload)
        oversized = b"\x00" * (
            (self.m.MAX_CLASSIC_BPF_INSTRUCTIONS + 1) * self.m.SOCK_FILTER_STRUCT.size
        )
        with self.assertRaisesRegex(self.m.AdbSeccompV1Error, "ceiling"):
            self.m.parse_filter_program(oversized)

    def test_packer_rejects_bad_sequence_and_fields(self):
        instruction = self.m.SockFilterInstruction
        samples = (
            (),
            [object()],
            [instruction(-1, 0, 0, 0)],
            [instruction(0, 256, 0, 0)],
            [instruction(0, 0, 256, 0)],
            [instruction(0, 0, 0, 1 << 32)],
        )
        for sample in samples:
            with self.subTest(sample=sample):
                with self.assertRaises(self.m.AdbSeccompV1Error):
                    self.m.pack_filter_program(sample)

    def test_binding_type_fd_flags_and_pointer_ranges_are_exact(self):
        variants = (
            object(),
            replace(self.binding, exec_fd=4),
            replace(self.binding, exec_fd=True),
            replace(self.binding, empty_path_pointer=0),
            replace(self.binding, empty_path_pointer=True),
            replace(self.binding, empty_path_pointer=self.m.MAX_USER_POINTER + 1),
            replace(self.binding, argv_pointer=self.binding.empty_path_pointer),
            replace(self.binding, envp_pointer=self.binding.argv_pointer),
            replace(self.binding, flags=0),
            replace(self.binding, flags=True),
        )
        for binding in variants:
            with self.subTest(binding=binding):
                with self.assertRaises(self.m.AdbSeccompV1Error):
                    self.m.validate_binding(binding)

    def test_architecture_mismatch_kills_and_x86_64_default_allows(self):
        self.assertEqual(
            self.m.interpret_filter(
                self.instructions,
                arch=0x40000003,
                syscall_number=self.m.SYS_GETPID,
            ),
            self.m.SECCOMP_RET_KILL_PROCESS,
        )
        self.assertEqual(
            self.m.interpret_filter(
                self.instructions,
                arch=self.m.AUDIT_ARCH_X86_64,
                syscall_number=self.m.SYS_GETPID,
            ),
            self.m.SECCOMP_RET_ALLOW,
        )

    def test_every_forbidden_syscall_is_unconditionally_trapped_in_model(self):
        for name, syscall_number in self.m.FORBIDDEN_SYSCALLS.items():
            for argument_fill in (0, 0xFFFFFFFFFFFFFFFF):
                with self.subTest(name=name, argument_fill=argument_fill):
                    self.assertEqual(
                        self.m.interpret_filter(
                            self.instructions,
                            arch=self.m.AUDIT_ARCH_X86_64,
                            syscall_number=syscall_number,
                            arguments=(argument_fill,) * 6,
                        ),
                        self.m.SECCOMP_RET_TRAP,
                    )

    def test_complete_x32_abi_is_trapped_before_default_allow(self):
        representatives = dict(self.m.X32_REPRESENTATIVE_SYSCALLS)
        representatives.update(
            {
                "read": self.m.X32_SYSCALL_BIT + 0,
                "getpid": self.m.X32_SYSCALL_BIT + 39,
                "highest-bit-only": self.m.X32_SYSCALL_BIT,
                "all-lower-bits": self.m.X32_SYSCALL_BIT + 0x3FFFFFFF,
            }
        )
        for name, syscall_number in representatives.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self.m.interpret_filter(
                        self.instructions,
                        arch=self.m.AUDIT_ARCH_X86_64,
                        syscall_number=syscall_number,
                        arguments=(0xFFFFFFFFFFFFFFFF,) * 6,
                    ),
                    self.m.SECCOMP_RET_TRAP,
                )

    def test_only_exact_raw_execveat_arguments_are_allowed_in_model(self):
        exact = self.m._exact_execveat_arguments(self.binding)
        self.assertEqual(
            self.m.interpret_filter(
                self.instructions,
                arch=self.m.AUDIT_ARCH_X86_64,
                syscall_number=self.m.SYS_EXECVEAT,
                arguments=exact,
            ),
            self.m.SECCOMP_RET_ALLOW,
        )
        for index in range(5):
            for delta in (1, 1 << 32):
                changed = list(exact)
                changed[index] ^= delta
                with self.subTest(index=index, delta=delta):
                    self.assertEqual(
                        self.m.interpret_filter(
                            self.instructions,
                            arch=self.m.AUDIT_ARCH_X86_64,
                            syscall_number=self.m.SYS_EXECVEAT,
                            arguments=changed,
                        ),
                        self.m.SECCOMP_RET_TRAP,
                    )

    def test_sixth_unused_seccomp_argument_does_not_change_execveat_action(self):
        exact = list(self.m._exact_execveat_arguments(self.binding))
        exact[5] = 0xDEADBEEF
        self.assertEqual(
            self.m.interpret_filter(
                self.instructions,
                arch=self.m.AUDIT_ARCH_X86_64,
                syscall_number=self.m.SYS_EXECVEAT,
                arguments=exact,
            ),
            self.m.SECCOMP_RET_ALLOW,
        )

    def test_same_pointer_changed_argv_and_env_contents_remain_filter_allowed(self):
        exact = self.m._exact_execveat_arguments(self.binding)
        reviewed_referents = {
            "pathname": b"\x00",
            "argv": (b"adb", b"devices", b"-l"),
            "envp": (b"ADB_SERVER_SOCKET=localfilesystem:fixed", b"LC_ALL=C"),
        }
        changed_referents = {
            "pathname": b"\x00",
            "argv": (b"adb", b"kill-server"),
            "envp": (b"ADB_SERVER_SOCKET=tcp:127.0.0.1:5037", b"LC_ALL=C"),
        }
        self.assertNotEqual(reviewed_referents["argv"], changed_referents["argv"])
        self.assertNotEqual(reviewed_referents["envp"], changed_referents["envp"])
        actions = tuple(
            self.m.interpret_filter(
                self.instructions,
                arch=self.m.AUDIT_ARCH_X86_64,
                syscall_number=self.m.SYS_EXECVEAT,
                arguments=exact,
            )
            for _referents in (reviewed_referents, changed_referents)
        )
        self.assertEqual(
            actions, (self.m.SECCOMP_RET_ALLOW, self.m.SECCOMP_RET_ALLOW)
        )

    def test_every_instruction_mutation_is_rejected_by_exact_validator(self):
        for index in range(0, len(self.program), self.m.SOCK_FILTER_STRUCT.size):
            changed = bytearray(self.program)
            changed[index + 4] ^= 1
            with self.subTest(instruction=index // 8):
                with self.assertRaises(self.m.AdbSeccompV1Error):
                    self.m.validate_filter_program(bytes(changed), self.binding)

    def test_interpreter_rejects_unknown_opcode_bad_load_jump_and_fallthrough(self):
        instruction = self.m.SockFilterInstruction
        bad_programs = (
            (instruction(0xFFFF, 0, 0, 0),),
            (instruction(self.m.BPF_LD_W_ABS, 0, 0, 63),),
            (instruction(self.m.BPF_JMP_JEQ_K, 0, 1, 0),),
            (instruction(self.m.BPF_LD_W_ABS, 0, 0, 0),),
        )
        for program in bad_programs:
            with self.subTest(program=program):
                with self.assertRaises(self.m.AdbSeccompV1Error):
                    self.m.interpret_filter(
                        program,
                        arch=self.m.AUDIT_ARCH_X86_64,
                        syscall_number=0,
                    )

    def test_install_model_orders_no_new_privs_filter_then_execveat(self):
        operations = FakeInstallOperations()
        result = self.m.model_install_then_execveat(operations, self.binding)
        self.assertEqual(operations.calls, ["no-new-privs", "filter", "execveat"])
        self.assertEqual(
            result.events,
            ("no_new_privs-set", "filter-installed", "execveat-attempted"),
        )
        self.assertEqual(result.terminal, "execveat-returned-unexpectedly")
        self.assertTrue(result.exec_attempted)
        self.assertFalse(result.retry_permitted)
        self.assertEqual(operations.binding, self.binding)
        self.m.validate_filter_program(operations.program, self.binding)

    def test_no_new_privs_failure_is_terminal_before_filter_or_exec(self):
        operations = FakeInstallOperations("no-new-privs")
        result = self.m.model_install_then_execveat(operations, self.binding)
        self.assertEqual(operations.calls, ["no-new-privs"])
        self.assertEqual(result.events, ())
        self.assertEqual(result.terminal, "no-new-privs-failed")
        self.assertFalse(result.exec_attempted)
        self.assertFalse(result.retry_permitted)

    def test_filter_install_failure_is_terminal_before_exec(self):
        operations = FakeInstallOperations("filter")
        result = self.m.model_install_then_execveat(operations, self.binding)
        self.assertEqual(operations.calls, ["no-new-privs", "filter"])
        self.assertEqual(result.events, ("no_new_privs-set",))
        self.assertEqual(result.terminal, "filter-install-failed")
        self.assertFalse(result.exec_attempted)
        self.assertFalse(result.retry_permitted)

    def test_kernel_installer_revalidates_exact_bytes_before_prctl(self):
        changed = bytearray(self.program)
        changed[-4] ^= 1
        with mock.patch.object(self.m, "MODULE_IMPORT_PID", -1), mock.patch.object(
                self.m.ctypes,
                "CDLL",
                side_effect=AssertionError("prctl owner reached"),
            ):
            with self.assertRaisesRegex(self.m.AdbSeccompV1Error, "exact candidate"):
                self.m._install_filter_current_process(bytes(changed), self.binding)

    def test_kernel_installer_refuses_importing_process_before_prctl(self):
        with mock.patch.object(
            self.m.ctypes,
            "CDLL",
            side_effect=AssertionError("prctl owner reached"),
        ):
            with self.assertRaisesRegex(self.m.AdbSeccompV1Error, "fork child"):
                self.m._install_filter_current_process(self.program, self.binding)

    def test_execveat_failure_is_terminal_and_never_retried(self):
        operations = FakeInstallOperations("execveat")
        result = self.m.model_install_then_execveat(operations, self.binding)
        self.assertEqual(operations.calls.count("execveat"), 1)
        self.assertEqual(result.terminal, "execveat-failed")
        self.assertTrue(result.exec_attempted)
        self.assertFalse(result.retry_permitted)

    def test_missing_install_operations_are_rejected(self):
        with self.assertRaisesRegex(self.m.AdbSeccompV1Error, "absent"):
            self.m.model_install_then_execveat(None, self.binding)

    @unittest.skipUnless(EXACT_HOST, "requires exact Linux x86-64 H0 probe host")
    def test_isolated_exact_execveat_probe_installs_in_required_order(self):
        result = self.m.run_isolated_exact_execveat_probe()
        self.assertFalse(result.timed_out)
        self.assertTrue(result.exited)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.signaled)
        self.assertEqual(result.marker_bytes, b"NF")

    @unittest.skipUnless(EXACT_HOST, "requires exact Linux x86-64 H0 probe host")
    def test_isolated_kernel_traps_all_seven_forbidden_syscalls_as_sigsys(self):
        for name in self.m.FORBIDDEN_SYSCALLS:
            with self.subTest(name=name):
                self.assert_sigsys(self.m.run_isolated_forbidden_syscall_probe(name))

    @unittest.skipUnless(EXACT_HOST, "requires exact Linux x86-64 H0 probe host")
    def test_isolated_kernel_traps_x32_exec_process_and_listener_syscalls(self):
        for name in self.m.X32_REPRESENTATIVE_SYSCALLS:
            with self.subTest(name=name):
                self.assert_sigsys(self.m.run_isolated_x32_syscall_probe(name))

    @unittest.skipUnless(EXACT_HOST, "requires exact Linux x86-64 H0 probe host")
    def test_isolated_kernel_traps_every_execveat_raw_argument_mismatch(self):
        for field in ("fd", "pathname-pointer", "argv-pointer", "envp-pointer", "flags"):
            with self.subTest(field=field):
                self.assert_sigsys(self.m.run_isolated_execveat_mismatch_probe(field))

    @unittest.skipUnless(EXACT_HOST, "requires exact Linux x86-64 H0 probe host")
    def test_same_pointer_nonempty_path_is_not_trapped_and_preserves_limitation(self):
        result = self.m.run_isolated_nonempty_same_pointer_probe()
        self.assertFalse(result.timed_out)
        self.assertTrue(result.exited)
        self.assertEqual(result.exit_code, 42)
        self.assertFalse(result.signaled)
        self.assertEqual(result.marker_bytes, b"")

    def test_invalid_probe_selectors_are_rejected_before_fork(self):
        with mock.patch.object(self.m.os, "fork", side_effect=AssertionError("forked")):
            for value in ("", "getpid", "execveat", None, True):
                with self.subTest(value=value):
                    with self.assertRaises(self.m.AdbSeccompV1Error):
                        self.m.run_isolated_forbidden_syscall_probe(value)
            for value in ("", "path", "fd-number", None, True):
                with self.subTest(value=value):
                    with self.assertRaises(self.m.AdbSeccompV1Error):
                        self.m.run_isolated_execveat_mismatch_probe(value)
            for value in ("", "getpid", "socket", None, True):
                with self.subTest(value=value):
                    with self.assertRaises(self.m.AdbSeccompV1Error):
                        self.m.run_isolated_x32_syscall_probe(value)

    def test_host_identity_drift_stops_probe_before_fork(self):
        with mock.patch.object(self.m, "exact_probe_host_matches", return_value=False), mock.patch.object(
            self.m.os,
            "fork",
            side_effect=AssertionError("forked"),
        ):
            with self.assertRaisesRegex(self.m.AdbSeccompV1Error, "host identity"):
                self.m.run_isolated_forbidden_syscall_probe("bind")

    def test_render_preserves_classic_bpf_limitations(self):
        transition = self.m.render_plan()["initial_transition"]
        self.assertFalse(transition["filter_can_dereference_pathname"])
        self.assertFalse(transition["filter_can_dereference_argv"])
        self.assertFalse(transition["filter_can_dereference_envp"])
        self.assertFalse(transition["empty_path_contents_enforced_by_filter"])
        self.assertFalse(transition["argv_contents_enforced_by_filter"])
        self.assertFalse(transition["envp_contents_enforced_by_filter"])
        self.assertTrue(transition["exact_executor_owned_pointer_referents_required"])
        self.assertFalse(transition["exact_executor_owned_pointer_referents_proved"])
        self.assertFalse(transition["filter_is_stateful"])
        self.assertFalse(transition["maximum_execveat_successes_proved"])
        self.assertTrue(transition["held_fd_cloexec_required"])
        self.assertFalse(transition["held_fd_cloexec_transition_proved_for_adb"])
        self.assertFalse(transition["fd_number_reuse_bypass_closed"])
        self.assertFalse(transition["pointer_address_reuse_bypass_closed"])

    def test_render_preserves_failure_terminal_and_no_replay_claims(self):
        failure = self.m.render_plan()["failure_model"]
        self.assertFalse(failure["no_new_privs_failure_exec_attempted"])
        self.assertFalse(failure["filter_install_failure_exec_attempted"])
        self.assertEqual(failure["forbidden_syscall_terminal"], "SIGSYS")
        self.assertTrue(failure["terminal_means_controller_must_stop_without_retry"])
        self.assertFalse(failure["pinned_adb_sigsys_disposition_and_process_death_proved"])
        self.assertFalse(failure["retry_permitted_after_install_or_exec_uncertainty"])
        self.assertFalse(failure["candidate_replay_permitted"])

    def test_render_distinguishes_h0_helper_from_adb_compatibility(self):
        probe = self.m.render_plan()["isolated_h0_probe"]
        self.assertTrue(probe["available_only_by_import"])
        self.assertFalse(probe["public_cli_exposes_probe"])
        self.assertTrue(probe["fork_before_filter"])
        self.assertEqual(probe["executes_pinned_helper_only"], "/usr/bin/gnutrue")
        self.assertFalse(probe["executes_adb"])
        self.assertFalse(probe["kernel_filter_installation_is_production_integration"])
        self.assertFalse(probe["probe_results_are_embedded_authority"])
        self.assertFalse(self.m.render_plan()["gates"]["adb_child_compatibility_proved"])

    def test_source_has_no_connected_adb_socket_network_su_or_odin_backend(self):
        text = self.source.decode("utf-8")
        self.assertNotIn("import socket", text)
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("os.system", text)
        self.assertNotIn("Popen(", text)
        self.assertNotIn("create_connection(", text)
        self.assertNotIn("socket.socket(", text)
        self.assertNotIn("--connected", text)
        self.assertNotIn("shell su", text)
        self.assertNotIn("odin4 --", text)
        self.assertNotIn("execveat(ADB_IDENTITY", text)

    def test_no_caller_surface_can_supply_fd_path_pointer_or_syscall(self):
        plan = self.m.render_plan()
        self.assertEqual(plan["caller_inputs"], [])
        self.assertEqual(plan["callbacks"], [])
        self.assertEqual(plan["cli"], ["--render-plan"])
        rendered = json.dumps(plan, sort_keys=True)
        self.assertEqual(plan["classic_bpf"]["x32_syscall_bit"], "0x40000000")
        self.assertEqual(
            plan["classic_bpf"]["x32_abi_action"],
            "SECCOMP_RET_TRAP-SIGSYS-before-default-allow",
        )
        self.assertIn("fd-number-and-pointer-address-reuse-closure", rendered)
        self.assertIn(
            "exact-executor-owned-pathname-argv-env-byte-closure", rendered
        )
        self.assertIn("exact-pinned-ADB-child-compatibility-under-filter", rendered)


if __name__ == "__main__":
    unittest.main()
