from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "build_s20plus_g986n_native_canary_n1.py"
)
SPEC = importlib.util.spec_from_file_location("s20plus_n1_builder_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
EXPECTED_CANARY_SOURCE_SHA256 = "31a4413f5d1d320d81ddb8720ff2f0303fb5198cd14a746af4c6cbe47bed3f2e"
EXPECTED_BUILDER_SOURCE_SHA256 = "bcbbc60052631d810ffa3f866e7077fdbc394f161c701d00f17d9c1a3166c0cc"
EXPECTED_BINARY_SHA256 = "38e14e6f54374fc98604bdd61e50922ce9bff1c96feae7572221be548902066c"
EXPECTED_MODULE_ZIP_SHA256 = "e06c88c3a1c029658160b974bc5938acc1f89ab68ea9a7d7d7169d5bd51525a2"


class S20PlusNativeCanaryN1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._class_temp = tempfile.TemporaryDirectory(prefix="s20plus-n1-tests-")
        cls.class_root = Path(cls._class_temp.name)
        cls.host_binary = cls.class_root / "s20plus_native_canary_host_test"
        cls.host_audit = BUILDER.compile_canary(cls.host_binary, host_test=True)
        cls.host_binary_receipt = {
            "size": cls.host_binary.stat().st_size,
            "sha256": hashlib.sha256(cls.host_binary.read_bytes()).hexdigest(),
        }
        cls.fake_build = {
            "binary": cls.host_binary_receipt,
            "module_zip": {"size": 1, "sha256": "1" * 64},
        }
        cls.binding = BUILDER.render_binding(
            cls.fake_build,
            run_nonce="0123456789abcdef0123456789abcdef",
            pre_boot_id_sha256="0" * 64,
        )
        cls.intent_fault_cases: dict[str, tuple[Path, bytes]] = {}
        for index, fault in enumerate(
            ("intent-after-create", "intent-before-fsync", "intent-close-failure")
        ):
            fault_binary = cls.class_root / f"s20plus_native_canary_{fault}"
            BUILDER.compile_canary(
                fault_binary,
                host_test=True,
                host_fault=fault,
            )
            fault_receipt = {
                "size": fault_binary.stat().st_size,
                "sha256": hashlib.sha256(fault_binary.read_bytes()).hexdigest(),
            }
            binding = BUILDER.render_binding(
                {
                    "binary": fault_receipt,
                    "module_zip": {"size": 1, "sha256": "1" * 64},
                },
                run_nonce=f"{index + 1:032x}",
                pre_boot_id_sha256="0" * 64,
            )
            cls.intent_fault_cases[fault] = (fault_binary, binding)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._class_temp.cleanup()

    def run_canary(
        self, state: Path, binary: Path | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                "/usr/bin/qemu-aarch64",
                str(self.host_binary if binary is None else binary),
                str(state),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    def make_state(self, root: Path, binding: bytes | None = None) -> Path:
        state = root / "state"
        state.mkdir(mode=0o700)
        binding_path = state / "binding.txt"
        binding_path.write_bytes(self.binding if binding is None else binding)
        binding_path.chmod(0o600)
        return state

    @staticmethod
    def node_snapshot(state: Path) -> dict[str, tuple[int, bytes | None]]:
        result: dict[str, tuple[int, bytes | None]] = {}
        for path in sorted(state.iterdir(), key=lambda item: item.name):
            lst = path.lstat()
            data = path.read_bytes() if stat.S_ISREG(lst.st_mode) else None
            result[path.name] = (lst.st_mode, data)
        return result

    def test_two_builds_and_two_zips_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n1-repro-") as temp:
            base = Path(temp)
            first = BUILDER.build(base / "first")
            second = BUILDER.build(base / "second")
            self.assertEqual(first["verdict"], BUILDER.VERDICT)
            self.assertFalse(first["live_authority"])
            self.assertTrue(first["two_builds_byte_identical"])
            self.assertTrue(first["two_zips_byte_identical"])
            self.assertEqual(first["binary"], second["binary"])
            self.assertEqual(first["module_zip"], second["module_zip"])
            self.assertEqual(
                first["builder_source"]["sha256"],
                hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                set(first["compiler_closure"]),
                {
                    "cc1", "collect2", "assembler", "linker", "crt1", "crti",
                    "crtn", "crtbeginT", "crtend", "libc", "libc_nonshared",
                    "libgcc", "libgcc_eh",
                },
            )
            self.assertIn("zipfile_source", first["python_closure"])
            self.assertEqual(
                (base / "first/s20plus_native_canary").read_bytes(),
                (base / "second/s20plus_native_canary").read_bytes(),
            )
            self.assertEqual(
                (base / "first/s20plus_native_canary.zip").read_bytes(),
                (base / "second/s20plus_native_canary.zip").read_bytes(),
            )
            self.assertEqual(first["device_commands"], 0)
            self.assertEqual(first["adb_commands"], 0)
            self.assertEqual(first["su_commands"], 0)
            self.assertEqual(first["install_commands"], 0)
            self.assertEqual(first["reboot_commands"], 0)

    def test_elf_and_zip_surface_are_closed(self) -> None:
        self.assertTrue(self.host_audit["static"])
        self.assertFalse(self.host_audit["pt_interp"])
        self.assertEqual(self.host_audit["dt_needed"], [])
        self.assertEqual(self.host_audit["undefined_symbols"], [])
        self.assertFalse(self.host_audit["writable_executable_load"])
        with tempfile.TemporaryDirectory(prefix="s20plus-n1-zip-") as temp:
            out = Path(temp) / "build"
            result = BUILDER.build(out)
            archive_path = out / "s20plus_native_canary.zip"
            with zipfile.ZipFile(archive_path) as archive:
                infos = archive.infolist()
                self.assertEqual(tuple(info.filename for info in infos), BUILDER.MODULE_FILES)
                self.assertEqual(len(infos), 4)
                self.assertEqual(len({info.filename for info in infos}), 4)
                for info in infos:
                    mode = info.external_attr >> 16
                    self.assertTrue(stat.S_ISREG(mode))
                    self.assertEqual(stat.S_IMODE(mode), BUILDER.MODULE_MODES[info.filename])
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
            self.assertTrue(result["module_zip_audit"]["exact_four_regular_members"])

    def test_zip_audit_rejects_noncanonical_metadata_and_trailing_bytes(self) -> None:
        binary = self.host_binary.read_bytes()
        cases = (
            "extra", "symlink", "wrong-mode", "archive-comment",
            "entry-extra", "entry-comment", "trailing-bytes",
        )
        for label in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="s20plus-n1-badzip-") as temp:
                archive_path = Path(temp) / "bad.zip"
                if label == "trailing-bytes":
                    archive_path.write_bytes(BUILDER.module_zip_bytes(binary) + b"tail")
                else:
                    with zipfile.ZipFile(
                        archive_path, "w", compression=zipfile.ZIP_STORED
                    ) as archive:
                        for name in BUILDER.MODULE_FILES:
                            info = zipfile.ZipInfo(
                                name, date_time=(1980, 1, 1, 0, 0, 0)
                            )
                            info.create_system = 3
                            mode = stat.S_IFREG | BUILDER.MODULE_MODES[name]
                            if label == "symlink" and name == "service.sh":
                                mode = stat.S_IFLNK | 0o777
                            if label == "wrong-mode" and name == "service.sh":
                                mode = stat.S_IFREG | 0o777
                            if label == "entry-extra" and name == "service.sh":
                                info.extra = b"\x0a\x00\x00\x00"
                            if label == "entry-comment" and name == "service.sh":
                                info.comment = b"comment"
                            info.external_attr = mode << 16
                            archive.writestr(
                                info, BUILDER.module_contents(binary)[name]
                            )
                        if label == "extra":
                            info = zipfile.ZipInfo(
                                "extra", date_time=(1980, 1, 1, 0, 0, 0)
                            )
                            info.create_system = 3
                            info.external_attr = (stat.S_IFREG | 0o644) << 16
                            archive.writestr(info, b"extra")
                        if label == "archive-comment":
                            archive.comment = b"comment"
                with self.assertRaises(BUILDER.BuildError):
                    BUILDER.audit_module_zip(archive_path, binary)

    def test_module_metadata_and_service_have_no_generic_command_surface(self) -> None:
        self.assertEqual(
            BUILDER.module_prop().decode("ascii").splitlines()[0],
            "id=s20plus_native_canary",
        )
        service = BUILDER.service_sh().decode("ascii")
        self.assertIn("MODDIR=${0%/*}", service)
        self.assertIn('exec "$MODDIR/bin/s20plus_native_canary"', service)
        self.assertIn('[ "$i" -lt 120 ]', service)
        for forbidden in (
            "eval", "sh -c", "su ", "magisk ", "adb", "curl", "wget",
            "/dev/block", "reboot", "setprop", "resetprop", "post-fs-data",
        ):
            self.assertNotIn(forbidden, service)
        safety = BUILDER.source_safety()
        self.assertFalse(any(value is True for key, value in safety.items() if key != "bounded_boot_wait_seconds"))
        self.assertEqual(safety["bounded_boot_wait_seconds"], 120)

    def test_binding_grammar_is_exact(self) -> None:
        lines = self.binding.decode("ascii").splitlines()
        self.assertEqual(
            [line.split("=", 1)[0] for line in lines],
            [
                "schema", "target_model", "target_device", "target_product",
                "target_incremental", "module_zip_sha256", "module_zip_size",
                "binary_sha256", "binary_size", "run_nonce",
                "pre_boot_id_sha256",
            ],
        )
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.render_binding(
                self.fake_build, run_nonce="A" * 32, pre_boot_id_sha256="0" * 64
            )
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.render_binding(
                self.fake_build, run_nonce="0" * 32, pre_boot_id_sha256="0" * 63
            )

    def test_native_canary_runs_once_and_preserves_immutable_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n1-once-") as temp:
            state = self.make_state(Path(temp))
            first = self.run_canary(state)
            self.assertEqual(first.returncode, 0, first.stderr.decode(errors="replace"))
            self.assertEqual(first.stdout, b"")
            self.assertEqual(first.stderr, b"")
            self.assertEqual(
                {path.name for path in state.iterdir()},
                {"binding.txt", "intent.json", "result.json"},
            )
            intent = json.loads((state / "intent.json").read_text())
            result = json.loads((state / "result.json").read_text())
            self.assertEqual(intent["schema"], "s20plus_native_canary_n1_intent_v1")
            self.assertFalse(intent["replay_permitted"])
            self.assertEqual(result["schema"], "s20plus_native_canary_n1_result_v1")
            self.assertEqual(result["target_model"], "SM-G986N")
            self.assertEqual(result["target_device"], "y2q")
            self.assertEqual(result["target_product"], "y2qksx")
            self.assertEqual(result["target_incremental"], "G986NKSS8IYC2")
            self.assertEqual(result["self_sha256"], self.host_binary_receipt["sha256"])
            self.assertEqual(result["self_size"], self.host_binary_receipt["size"])
            self.assertEqual(result["uid"], os.getuid())
            self.assertEqual(result["gid"], os.getgid())
            self.assertTrue(result["pre_boot_id_changed"])
            self.assertFalse(result["replay_permitted"])
            self.assertLess((state / "result.json").stat().st_size, 8192)
            result_bytes = (state / "result.json").read_bytes()
            intent_bytes = (state / "intent.json").read_bytes()
            second = self.run_canary(state)
            self.assertEqual(second.returncode, 10)
            self.assertEqual((state / "intent.json").read_bytes(), intent_bytes)
            self.assertEqual((state / "result.json").read_bytes(), result_bytes)
            self.assertFalse((state / ".result.pending").exists())

    def test_completed_journal_rejects_every_mutated_result_without_replay(self) -> None:
        mutators = {
            "wrong-schema": lambda value: value.replace(
                b"s20plus_native_canary_n1_result_v1", b"forged_result_schema_0000000000000000"
            ),
            "wrong-model": lambda value: value.replace(b"SM-G986N", b"SM-G999N"),
            "wrong-device": lambda value: value.replace(b'"y2q"', b'"g0q"', 1),
            "wrong-product": lambda value: value.replace(
                b'"y2qksx"', b'"g0qksx"', 1
            ),
            "wrong-incremental": lambda value: value.replace(
                b"G986NKSS8IYC2", b"G986NKSS8FORGED"
            ),
            "extra-key": lambda value: value.replace(
                b"\"replay_permitted\":false}\n",
                b"\"replay_permitted\":false,\"extra\":0}\n",
            ),
            "duplicate-key": lambda value: value.replace(
                b"\"target_device\":\"y2q\",",
                b"\"target_device\":\"y2q\",\"target_device\":\"y2q\",",
            ),
            "replay-true": lambda value: value.replace(
                b"\"replay_permitted\":false", b"\"replay_permitted\":true"
            ),
            "wrong-self": lambda value: value.replace(
                self.host_binary_receipt["sha256"].encode(), b"2" * 64
            ),
            "unchanged-boot": lambda value: value.replace(
                json.loads(value)["boot_id_sha256"].encode(), b"0" * 64
            ),
            "boolean-uid": lambda value: value.replace(
                f'\"uid\":{os.getuid()}'.encode(), b'\"uid\":true'
            ),
            "negative-pid": lambda value: value.replace(b'\"pid\":', b'\"pid\":-'),
            "bad-capability": lambda value: value.replace(
                json.loads(value)["cap_eff"].encode(), b"g" * 16, 1
            ),
            "bad-namespace": lambda value: value.replace(
                json.loads(value)["mnt_ns"].encode(), b"mnt:[0]", 1
            ),
            "backslash-nul": lambda value: value.replace(
                json.loads(value)["selinux_context"].encode(), b"x\\\x00", 1
            ),
            "noncanonical-slash-escape": lambda value: value.replace(
                json.loads(value)["selinux_context"].encode(), b"x\\/", 1
            ),
            "noncanonical-unicode-printable": lambda value: value.replace(
                json.loads(value)["selinux_context"].encode(), b"\\u0041", 1
            ),
            "trailing-bytes": lambda value: value + b"forged",
        }
        for label, mutate in mutators.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                prefix="s20plus-n1-result-mutation-"
            ) as temp:
                state = self.make_state(Path(temp))
                self.assertEqual(self.run_canary(state).returncode, 0)
                result_path = state / "result.json"
                original = result_path.read_bytes()
                mutated = mutate(original)
                self.assertNotEqual(mutated, original)
                result_path.write_bytes(mutated)
                before = self.node_snapshot(state)
                completed = self.run_canary(state)
                self.assertEqual(completed.returncode, 20)
                self.assertEqual(self.node_snapshot(state), before)

    def test_completed_journal_requires_exact_intent_without_replay(self) -> None:
        mutators = {
            "wrong-schema": lambda value: value.replace(
                b"s20plus_native_canary_n1_intent_v1", b"forged_native_canary_intent_schema"
            ),
            "extra-key": lambda value: value.replace(b"}\n", b',"extra":0}\n'),
            "replay-true": lambda value: value.replace(b"false", b"true"),
        }
        for label, mutate in mutators.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                prefix="s20plus-n1-intent-mutation-"
            ) as temp:
                state = self.make_state(Path(temp))
                self.assertEqual(self.run_canary(state).returncode, 0)
                intent_path = state / "intent.json"
                original = intent_path.read_bytes()
                mutated = mutate(original)
                self.assertNotEqual(mutated, original)
                intent_path.write_bytes(mutated)
                before = self.node_snapshot(state)
                completed = self.run_canary(state)
                self.assertEqual(completed.returncode, 20)
                self.assertEqual(self.node_snapshot(state), before)

    def test_intent_publish_failures_consume_run_and_cannot_replay(self) -> None:
        for label, (binary, binding) in self.intent_fault_cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                prefix="s20plus-n1-intent-fault-"
            ) as temp:
                state = self.make_state(Path(temp), binding)
                first = self.run_canary(state, binary)
                self.assertEqual(first.returncode, 23)
                self.assertEqual(
                    {path.name for path in state.iterdir()},
                    {"binding.txt", "intent.json"},
                )
                before = self.node_snapshot(state)
                second = self.run_canary(state, binary)
                self.assertEqual(second.returncode, 20)
                self.assertEqual(self.node_snapshot(state), before)

    def test_rejects_malformed_stale_and_oversized_binding_without_effect(self) -> None:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip().encode()
        current_boot_hash = hashlib.sha256(boot_id).hexdigest()
        variants = {
            "wrong-model": self.binding.replace(b"target_model=SM-G986N", b"target_model=SM-G999N"),
            "stale-binary": self.binding.replace(
                self.host_binary_receipt["sha256"].encode(), b"2" * 64
            ),
            "extra-key": self.binding + b"extra=forbidden\n",
            "missing-newline": self.binding.rstrip(b"\n"),
            "blank-line": self.binding.replace(
                b"target_device=y2q\n", b"target_device=y2q\n\n"
            ),
            "carriage-return": self.binding.replace(
                b"target_device=y2q\n", b"target_device=y2q\r\n"
            ),
            "unchanged-boot": BUILDER.render_binding(
                self.fake_build,
                run_nonce="0123456789abcdef0123456789abcdef",
                pre_boot_id_sha256=current_boot_hash,
            ),
            "oversized": self.binding + b"x" * 2048,
        }
        for label, binding in variants.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="s20plus-n1-binding-") as temp:
                state = self.make_state(Path(temp), binding)
                before = self.node_snapshot(state)
                completed = self.run_canary(state)
                self.assertIn(completed.returncode, {20, 21})
                self.assertEqual(self.node_snapshot(state), before)

    def test_rejects_symlink_hardlink_special_extra_and_pending_nodes(self) -> None:
        cases = ("binding-symlink", "binding-hardlink", "fifo", "extra", "pending")
        for label in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="s20plus-n1-node-") as temp:
                root = Path(temp)
                state = root / "state"
                state.mkdir(mode=0o700)
                if label == "binding-symlink":
                    outside = root / "outside-binding"
                    outside.write_bytes(self.binding)
                    outside.chmod(0o600)
                    (state / "binding.txt").symlink_to(outside)
                elif label == "binding-hardlink":
                    outside = root / "outside-binding"
                    outside.write_bytes(self.binding)
                    outside.chmod(0o600)
                    os.link(outside, state / "binding.txt")
                else:
                    (state / "binding.txt").write_bytes(self.binding)
                    (state / "binding.txt").chmod(0o600)
                    if label == "fifo":
                        os.mkfifo(state / "unexpected-fifo", 0o600)
                    elif label == "extra":
                        (state / "extra").write_bytes(b"x")
                        (state / "extra").chmod(0o600)
                    else:
                        (state / ".result.pending").write_bytes(b"partial")
                        (state / ".result.pending").chmod(0o600)
                before = self.node_snapshot(state)
                completed = self.run_canary(state)
                self.assertEqual(completed.returncode, 20)
                self.assertEqual(self.node_snapshot(state), before)

    def test_rejects_partial_or_impossible_journal_without_replay(self) -> None:
        cases = {
            "intent-only": {"intent.json": b"{}\n"},
            "result-only": {"result.json": b"{}\n"},
            "malformed-complete": {"intent.json": b"{}\n", "result.json": b"{}\n"},
        }
        for label, additions in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="s20plus-n1-journal-") as temp:
                state = self.make_state(Path(temp))
                for name, data in additions.items():
                    path = state / name
                    path.write_bytes(data)
                    path.chmod(0o600)
                before = self.node_snapshot(state)
                completed = self.run_canary(state)
                self.assertEqual(completed.returncode, 20)
                self.assertEqual(self.node_snapshot(state), before)

    def test_completed_journal_rejects_result_hardlink_and_symlink(self) -> None:
        for label in ("hardlink", "symlink"):
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="s20plus-n1-result-node-") as temp:
                root = Path(temp)
                state = self.make_state(root)
                self.assertEqual(self.run_canary(state).returncode, 0)
                result = state / "result.json"
                if label == "hardlink":
                    os.link(result, root / "second-result-link")
                else:
                    original = root / "original-result"
                    result.rename(original)
                    result.symlink_to(original)
                before = self.node_snapshot(state)
                completed = self.run_canary(state)
                self.assertEqual(completed.returncode, 20)
                self.assertEqual(self.node_snapshot(state), before)

    def test_state_directory_symlink_and_wrong_mode_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n1-state-") as temp:
            root = Path(temp)
            real = self.make_state(root)
            link = root / "state-link"
            link.symlink_to(real, target_is_directory=True)
            self.assertEqual(self.run_canary(link).returncode, 20)
            real.chmod(0o755)
            before = self.node_snapshot(real)
            self.assertEqual(self.run_canary(real).returncode, 20)
            self.assertEqual(self.node_snapshot(real), before)

    def test_output_builder_refuses_clobber(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n1-clobber-") as temp:
            out = Path(temp) / "existing"
            out.mkdir()
            sentinel = out / "sentinel"
            sentinel.write_bytes(b"keep")
            with self.assertRaisesRegex(BUILDER.BuildError, "refusing to clobber"):
                BUILDER.build(out)
            self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_public_documents_bind_h0_bytes_without_activating_live_authority(self) -> None:
        self.assertEqual(
            hashlib.sha256(BUILDER.SOURCE.read_bytes()).hexdigest(),
            EXPECTED_CANARY_SOURCE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
            EXPECTED_BUILDER_SOURCE_SHA256,
        )
        goal = (ROOT / "GOAL_S20PLUS.md").read_text()
        report = (
            ROOT / "docs/reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md"
        ).read_text()
        draft = (
            ROOT
            / "docs/plans/"
            "S20PLUS_G986N_NATIVE_CANARY_ROOT_DATA_TRANSACTION_DRAFT_2026-08-15.md"
        ).read_text()
        phased = (
            ROOT
            / "docs/plans/"
            "S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md"
        ).read_text()
        for document in (goal, report):
            self.assertIn(EXPECTED_CANARY_SOURCE_SHA256, document)
            self.assertIn(EXPECTED_BUILDER_SOURCE_SHA256, document)
            self.assertIn(EXPECTED_BINARY_SHA256, document)
            self.assertIn(EXPECTED_MODULE_ZIP_SHA256, document)
        self.assertIn("NOT BINDING - NOT ACTIVE - NO DEVICE AUTHORITY", draft)
        self.assertIn("Neither routine shared-storage staging", draft)
        self.assertIn("This branch is not currently executable", draft)
        self.assertIn("Bootstrap and resident-F1 recovery authority", draft)
        self.assertIn("durable pre-bound handoff", draft)
        self.assertIn("LIVE CAPABILITY NOT ACTIVE", report)
        self.assertIn("INDEPENDENT REVIEW PASS_GO", report)
        self.assertIn("received independent `PASS_GO`", draft)
        self.assertIn(
            "N1 H0 PASS_GO; R1 BASE CAPABILITY ACTIVE; ONE GUARDED POST-INSTALL RUN; EXACT NO-INSTALL CONTINUATION ACTIVE",
            phased,
        )
        self.assertNotIn("R1 REVIEW PENDING", phased)
        self.assertNotIn(
            "S20PLUS_NATIVE_CANARY_ROOT_DATA_V1",
            (ROOT / "AGENTS.md").read_text(),
        )
        self.assertNotIn(
            "S20PLUS_NATIVE_CANARY_ROOT_DATA_V1",
            (
                ROOT
                / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
            ).read_text(),
        )


if __name__ == "__main__":
    unittest.main()
