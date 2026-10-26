"""Hostile tests for the S20+ P1 direct-PID1 exec-handoff witness.

Three ACM candidates and the V4 minimal candidate closed NO_PROOF, and both of
the channels they used were refuted: a gadget chain whose silent failure is
indistinguishable from `/init` never running, and evidence - a Download arrival,
a fixed kmsg banner - that is characteristic of the candidate rather than
authenticated as coming from it.

So the properties that matter here are:

  * the PID1 gate still precedes every effect;
  * the handoff cannot re-enter the witness, which would hang the device as PID 1
    forever, and cannot be prevented or gated by the evidence;
  * the ramdisk edit is exactly the two declared entries, and the added one
    carries the resident magiskinit bytes - because magiskinit renames `/init`
    onto `/sdcard` to hijack second-stage init and copies it to
    `/data/magiskinit`, so its own bytes must be at `/init` when it runs;
  * the consumer refuses every verdict the record cannot support, and in
    particular refuses a record a later same-boot writer could have produced.
"""
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p1_pid1_witness_init.c"
CC = shutil.which("aarch64-linux-gnu-gcc-15") or shutil.which("aarch64-linux-gnu-gcc")
OBJDUMP = shutil.which("aarch64-linux-gnu-objdump")
STRIP = shutil.which("aarch64-linux-gnu-strip")
QEMU = shutil.which("qemu-aarch64")
TOOLCHAIN = all((CC, OBJDUMP, STRIP, QEMU))

sys.path.insert(0, str(REVALIDATION))


def load(name):
    path = REVALIDATION / (name + ".py")
    spec = importlib.util.spec_from_file_location("_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load("build_s20plus_g986n_p1_pid1_witness_h0")
EVIDENCE = load("s20plus_g986n_p1_pid1_witness_evidence")
OBSERVER = load("s20plus_g986n_p1_pid1_kmsg_observer")
OWNER = load("s20plus_g986n_p1_pid1_witness_f1")
TEXT = SOURCE.read_text()

COMPILE_FLAGS = (
    "-std=gnu11",
    "-nostdlib",
    "-static",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-tree-loop-distribute-patterns",
    "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-fno-ident",
    "-Wl,--build-id=none",
    "-Wl,-e,_start",
    "-Wl,-z,noexecstack",
)


def executable_text():
    """Source with comments stripped, so prose cannot satisfy a structural check."""
    without_block = re.sub(r"/\*.*?\*/", "", TEXT, flags=re.S)
    return "\n".join(line.split("//", 1)[0] for line in without_block.splitlines())


def device_body():
    """The non-selftest branch only. The selftest branch never runs on a device."""
    body = executable_text()
    return body[body.index("#else", body.index("S20PLUS_P1_WITNESS_SELFTEST_ONLY")) :]


class SourceShapeTests(unittest.TestCase):
    def test_pid1_gate_precedes_every_effect(self):
        body = device_body()
        start = body.index("void p1w_main(unsigned long *stack) {")
        gate = body.index("if (pid != 1) {", start)
        for effect in (
            "p1w_emit_evidence_best_effort((uint64_t)pid);",
            "p1w_restore_resident_init()",
            "p1w_handoff(argv, envp);",
        ):
            self.assertLess(gate, body.index(effect, start), f"{effect} precedes the PID1 gate")

    def test_exec_is_reachable_only_after_a_successful_rename(self):
        # A failed rename leaves this witness at /init. Exec'ing /init then would
        # re-enter it as PID 1, forever, with no operator-visible progress.
        body = device_body()
        start = body.index("void p1w_main(unsigned long *stack) {")
        rename = body.index("if (p1w_restore_resident_init() != 0) {", start)
        handoff = body.index("p1w_handoff(argv, envp);", start)
        self.assertLess(rename, handoff)
        guard = body[rename : body.index("}", rename) + 1]
        self.assertIn("p1w_park();", guard)

    def test_evidence_cannot_prevent_or_gate_the_handoff(self):
        body = device_body()
        start = body.index("void p1w_main(unsigned long *stack) {")
        tail = body[start:]
        evidence = tail.index("p1w_emit_evidence_best_effort((uint64_t)pid);")
        rename = tail.index("if (p1w_restore_resident_init() != 0) {")
        self.assertLess(evidence, rename)
        between = tail[evidence + len("p1w_emit_evidence_best_effort((uint64_t)pid);") : rename]
        for branching in (r"\bif\b", r"\bwhile\b", r"\bfor\b", r"\breturn\b", r"\?", r"&&", r"\|\|"):
            self.assertIsNone(re.search(branching, between), f"branching {branching} before the handoff")

    def test_evidence_helper_returns_nothing_and_inspects_only_its_own_bookkeeping(self):
        helper = TEXT[TEXT.index("static void p1w_emit_evidence_best_effort") :]
        helper = helper[: helper.index("\n}\n") + 3]
        self.assertTrue(helper.startswith("static void "), "the helper must not return a result")
        # Only the kmsg descriptor, the mount result and the first umount result
        # may be inspected, and only to decide the next local step.
        self.assertEqual(helper.count("if ("), 4)
        for condition in ("if (descriptor >= 0)", "if (mounted == 0)", "if (created == 0)",
                          "NR_UMOUNT2, (long)(uintptr_t)P1W_PROC_DIR, 0) != 0"):
            self.assertIn(condition, helper)

    def test_evidence_helper_restores_the_world_magiskinit_expects(self):
        helper = TEXT[TEXT.index("static void p1w_emit_evidence_best_effort") :]
        helper = helper[: helper.index("\n}\n") + 3]
        # magiskinit mounts /proc itself when /proc/cmdline is absent and falls
        # back to a /kmsg node when /dev/kmsg does not exist. Leaving either
        # behind changes its behaviour on a boot-critical path.
        self.assertIn("NR_UNLINKAT", helper)
        self.assertIn("NR_UMOUNT2", helper)

    def test_the_witness_never_exits(self):
        # PID 1 exiting is a kernel panic, so exit_group must not exist in the
        # device branch at all.
        self.assertNotIn("NR_EXIT_GROUP", device_body())

    def test_argv_and_envp_are_the_kernel_s_own(self):
        # magiskinit reads argv[0] and argv[1], and the original Samsung init
        # receives whatever the bootloader appended. Reconstructing either
        # vector would silently drop it.
        body = device_body()
        self.assertIn("argv = (char **)&stack[1];", body)
        self.assertIn("envp = argv + argc + 1;", body)
        self.assertIn("mov x0, sp", TEXT)

    def test_no_child_and_no_namespace_is_created(self):
        for forbidden in ("NR_CLONE", "NR_UNSHARE", "NR_SETNS", "NR_FORK", "NR_REBOOT"):
            self.assertNotIn(forbidden, TEXT, f"{forbidden} must not exist in this candidate")

    def test_staged_and_restored_paths_are_the_declared_ones(self):
        self.assertIn('#define P1W_MAGISK_INIT_STAGED "/init.magisk"', TEXT)
        self.assertIn('#define P1W_INIT_PATH "/init"', TEXT)
        self.assertEqual(BUILDER.RAMDISK_STAGED_ENTRY, "init.magisk")


class BuilderContractTests(unittest.TestCase):
    def test_candidate_identity_is_shared_by_producer_builder_and_consumer(self):
        self.assertEqual(BUILDER.CANDIDATE_ID, EVIDENCE.CANDIDATE_ID)
        self.assertIn(f'#define P1W_CANDIDATE_ID "{BUILDER.CANDIDATE_ID}"', TEXT)

    def test_record_grammar_is_shared_by_producer_builder_and_consumer(self):
        self.assertEqual(BUILDER.MAGIC, EVIDENCE.MAGIC)
        self.assertEqual(BUILDER.STAGE, EVIDENCE.STAGE)
        self.assertEqual(BUILDER.UNAVAILABLE, EVIDENCE.UNAVAILABLE)
        self.assertEqual(BUILDER.FIELD_ORDER, EVIDENCE.FIELD_ORDER)
        self.assertEqual(BUILDER.EXPECTED_PIDNS, EVIDENCE.EXPECTED_PIDNS)
        for constant in (BUILDER.MAGIC, BUILDER.STAGE, BUILDER.UNAVAILABLE):
            self.assertIn(f'"{constant}"', TEXT)

    def test_initial_pid_namespace_inode_is_the_kernel_constant(self):
        # include/linux/proc_ns.h, PROC_PID_INIT_INO, in this target's 4.19.113.
        self.assertEqual(BUILDER.PID_NS_INIT_INO, 0xEFFFFFFC)
        self.assertEqual(EVIDENCE.EXPECTED_PIDNS, "pid:[4026531836]")

    def test_expected_and_forbidden_syscall_sets_are_disjoint(self):
        expected = set(BUILDER.EXPECTED_RUNTIME_SYSCALLS.values())
        forbidden = set(BUILDER.FORBIDDEN_RUNTIME_SYSCALLS.values())
        self.assertEqual(expected & forbidden, set())
        self.assertIn(221, expected, "execve is the handoff and must be expected")
        self.assertIn(38, expected, "renameat restores magiskinit and must be expected")
        self.assertIn(142, forbidden, "the refuted download-request channel must stay out")

    def test_builder_declares_the_exact_ramdisk_delta(self):
        self.assertEqual(BUILDER.RAMDISK_INIT_ENTRY, "init")
        self.assertEqual(BUILDER.RAMDISK_INIT_MODE, "-rwxr-x---")
        source = (REVALIDATION / "build_s20plus_g986n_p1_pid1_witness_h0.py").read_text()
        # The added entry must be proved to carry the resident init bytes, not
        # merely to exist.
        self.assertIn("does not carry the resident init bytes", source)
        self.assertIn("membership or metadata changed beyond the two declared entries", source)

    def test_start_trampoline_check_rejects_a_stack_touching_prologue(self):
        # objdump's real line shape: address, tab, encoding, tab, mnemonic.
        good = (
            "00000000004000b0 <_start>:\n"
            "  4000b0:\t910003e0 \tmov\tx0, sp\n"
            "  4000b4:\t140000ef \tb\t400470 <p1w_main>\n"
        )
        self.assertTrue(BUILDER.start_is_stack_trampoline(good))
        pushed = (
            "00000000004000b0 <_start>:\n"
            "  4000b0:\ta9bf7bfd \tstp\tx29, x30, [sp, #-16]!\n"
            "  4000b4:\t910003e0 \tmov\tx0, sp\n"
            "  4000b8:\t140000ef \tb\t400470 <p1w_main>\n"
        )
        self.assertFalse(BUILDER.start_is_stack_trampoline(pushed))

    def test_gate_check_rejects_a_body_whose_first_syscall_is_not_getpid(self):
        wrong = (
            "0000000000400470 <p1w_main>:\n"
            "  400470:\td2800508 \tmov\tx8, #0x28\n"
            "  400474:\td4000001 \tsvc\t#0x0\n"
        )
        self.assertFalse(BUILDER.entry_first_syscall_is_getpid(wrong, "p1w_main"))
        right = (
            "0000000000400470 <p1w_main>:\n"
            "  400470:\td2801588 \tmov\tx8, #0xac\n"
            "  400474:\td4000001 \tsvc\t#0x0\n"
        )
        self.assertTrue(BUILDER.entry_first_syscall_is_getpid(right, "p1w_main"))


@unittest.skipUnless(TOOLCHAIN, "aarch64 cross toolchain and qemu-aarch64 are required")
class CompiledWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        work = Path(cls.tmp.name)
        cls.selftest = work / "selftest"
        cls.witness = work / "witness"
        cls.again = work / "witness.again"
        subprocess.run(
            [CC, *COMPILE_FLAGS, "-Wno-unused-function", "-DS20PLUS_P1_WITNESS_SELFTEST_ONLY=1",
             str(SOURCE), "-o", str(cls.selftest)],
            check=True, capture_output=True, timeout=180,
        )
        subprocess.run([CC, *COMPILE_FLAGS, str(SOURCE), "-o", str(cls.witness)],
                       check=True, capture_output=True, timeout=180)
        cls.unstripped = subprocess.run([OBJDUMP, "-d", str(cls.witness)],
                                        check=True, capture_output=True, timeout=60).stdout.decode()
        subprocess.run([CC, *COMPILE_FLAGS, str(SOURCE), "-o", str(cls.again)],
                       check=True, capture_output=True, timeout=180)
        for binary in (cls.witness, cls.again):
            subprocess.run([STRIP, "--strip-all", str(binary)], check=True, capture_output=True, timeout=60)
        cls.stripped = subprocess.run([OBJDUMP, "-d", str(cls.witness)],
                                      check=True, capture_output=True, timeout=60).stdout.decode()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_selftest_passes(self):
        completed = subprocess.run([QEMU, str(self.selftest)], capture_output=True, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_build_is_reproducible_and_small(self):
        self.assertEqual(self.witness.read_bytes(), self.again.read_bytes())
        self.assertLessEqual(self.witness.stat().st_size, 4096)

    def test_start_is_an_untouched_stack_pointer_trampoline(self):
        self.assertTrue(BUILDER.start_is_stack_trampoline(self.unstripped))

    def test_first_syscall_of_the_body_is_the_pid1_gate(self):
        self.assertTrue(BUILDER.entry_first_syscall_is_getpid(self.unstripped, "p1w_main"))

    def test_runtime_syscall_surface_is_exactly_the_declared_one(self):
        found = {int(match, 16) for match in
                 re.findall(r"mov\s+[xw]8, #0x([0-9a-f]+)", self.stripped)}
        self.assertEqual(found, set(BUILDER.EXPECTED_RUNTIME_SYSCALLS.values()))
        for name, number in BUILDER.FORBIDDEN_RUNTIME_SYSCALLS.items():
            self.assertNotIn(number, found, f"{name} is present")

    def test_required_and_forbidden_strings(self):
        binary = self.witness.read_bytes()
        for required in BUILDER.REQUIRED_STRINGS:
            self.assertIn(required, binary, f"missing {required!r}")
        for forbidden in BUILDER.FORBIDDEN_STRINGS:
            self.assertNotIn(forbidden, binary, f"retained {forbidden!r}")

    def test_the_gate_makes_the_binary_inert_anywhere_but_as_pid1(self):
        # Run the real device binary as an ordinary process. It must take the
        # park branch: no exit, no output, and none of its effects performed.
        # qemu-aarch64 gives it a PID that is not 1.
        work = Path(self.tmp.name) / "inert"
        work.mkdir()
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([QEMU, str(self.witness)], capture_output=True, timeout=5, cwd=work)
        self.assertEqual(sorted(os.listdir(work)), [])


def record(body, *, seq, ts_usec, facility=1, level=6, flag="-"):
    return f"{(facility << 3) | level},{seq},{ts_usec},{flag};{body}\n"


def witness_body(
    cand=None,
    pid="0000000001",
    procself="1",
    pidns=EVIDENCE.EXPECTED_PIDNS,
    bootid="3f7a1b20-91cc-4d0e-8a55-1c9e77b40d31",
    stage=EVIDENCE.STAGE,
):
    cand = EVIDENCE.CANDIDATE_ID if cand is None else cand
    return (
        f"{EVIDENCE.MAGIC};cand={cand};pid={pid};procself={procself}"
        f";pidns={pidns};bootid={bootid};stage={stage}"
    )


BOOT_ID = "3f7a1b20-91cc-4d0e-8a55-1c9e77b40d31"


def capture(
    *,
    witness=None,
    witness_facility=1,
    witness_flag="-",
    witness_line=None,
    witness_header_extra="",
    base_seq=0,
    lead_userspace=None,
    downstream=True,
    kernel_handover=True,
    kernel_init_path="/init",
    trailing=(),
):
    """One synthetic /dev/kmsg capture in the shape a real reader produces.

    Sequence numbers are contiguous and start at `base_seq`, because that is the
    only shape this kernel's ring can have: `log_store()` does `log_next_seq++`
    per record, `log_first_seq` starts at 0, and a fresh `devkmsg_open()` starts
    at the head. A gap can only come from a reader that fell behind, and tests
    that need one build it here deliberately.

    Facility matters as much as order. Kernel records are facility 0, which
    `devkmsg_write()` will not let a userspace writer claim, so the entries below
    are tagged with the origin they would really have.
    """
    entries = []
    entries.append(("Booting Linux on physical CPU 0x0", 0))
    entries.append(("Memory: 7000000K available", 0))
    if kernel_handover:
        entries.append((f"Run {kernel_init_path} as init process", 0))
    if lead_userspace is not None:
        entries.append((lead_userspace, 1))
    if witness is not None:
        entries.append((witness, witness_facility))
    if downstream:
        entries.append(("magiskinit: First Stage Init", 1))
        entries.append(("init: init first stage started!", 1))
    entries.extend(trailing)

    rendered = []
    for index, (body, facility) in enumerate(entries):
        seq = base_seq + index
        is_witness = witness is not None and body is witness
        if is_witness and witness_line is not None:
            rendered.append(witness_line)
            continue
        flag = witness_flag if is_witness else "-"
        if is_witness and witness_header_extra:
            prifac = (facility << 3) | 6
            rendered.append(
                f"{prifac},{seq},{100_000 * (index + 1)},{flag}{witness_header_extra};{body}\n"
            )
            continue
        rendered.append(record(body, seq=seq, ts_usec=100_000 * (index + 1),
                               facility=facility, flag=flag))
    return "".join(rendered).encode()


def renumber(capture_bytes, mapping):
    """Rewrite sequence numbers in place, for the captures a real reader cannot make."""
    out = []
    for line in capture_bytes.decode().splitlines(keepends=True):
        header, _, rest = line.partition(";")
        fields = header.split(",")
        seq = int(fields[1])
        if seq in mapping:
            fields[1] = str(mapping[seq])
        out.append(",".join(fields) + ";" + rest)
    return "".join(out).encode()


class ConsumerHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def run_consumer(self, capture_bytes, *, evaluate_raw=False, **attestation_overrides):
        capture_path = self.dir / "kmsg.raw"
        framed = OBSERVER.frame(capture_bytes)
        if evaluate_raw:
            # Hand the consumer the untrimmed bytes, as a caller who framed
            # badly - or lied about framing - would.
            framed = {**framed, "aligned": capture_bytes,
                      "aligned_size": len(capture_bytes),
                      "trailing_partial_bytes": 0,
                      "parse_status": OBSERVER.PARSE_ALIGNED}
        elif framed["parse_status"] == OBSERVER.PARSE_UNPARSABLE:
            # A capture the reader could never have produced. The attestation
            # still has to be well formed, or the test would be measuring the
            # attestation parser instead of the capture parser. The consumer
            # re-parses the bytes itself and refuses them there.
            framed = {**framed, "aligned": capture_bytes,
                      "aligned_size": len(capture_bytes),
                      "trailing_partial_bytes": 0,
                      "parse_status": OBSERVER.PARSE_ALIGNED}
        attestation = OBSERVER.build_attestation(
            framed=framed,
            acquisition_status=OBSERVER.STATUS_COMPLETE,
            target=EVIDENCE.TARGET,
            candidate_id=EVIDENCE.CANDIDATE_ID,
            candidate_boot_sha256=EVIDENCE.CANDIDATE_BOOT_SHA256,
            candidate_ap_sha256=EVIDENCE.CANDIDATE_AP_SHA256,
            boot_id=BOOT_ID,
        )
        attestation.update(attestation_overrides)
        capture_path.write_bytes(capture_bytes)
        attestation_path = self.dir / "attestation.json"
        attestation_path.write_text(json.dumps(attestation))
        return EVIDENCE.validate(capture_path, attestation_path)

    def assertRefused(self, result, reason):
        self.assertEqual(result["verdict"], "NO_PROOF", result)
        self.assertEqual(result["reason"], reason, result)
        self.assertEqual(result["establishes"], [])


class ConsumerPositiveTests(ConsumerHarness):
    def test_the_first_userspace_record_of_a_complete_boot_is_proved(self):
        result = self.run_consumer(capture(witness=witness_body()))
        self.assertEqual(result["verdict"], "PROVED", result)
        self.assertEqual(result["reason"], "first-userspace-record-of-a-complete-attested-boot")
        self.assertEqual(result["observation"]["witness_records"], 1)
        self.assertEqual(result["observation"]["kernel_init_marker"], "present")
        self.assertEqual(result["observation"]["first_userspace_seq"],
                         result["observation"]["witness_seq"])
        self.assertEqual(result["observation"]["first_seq"], 0)
        self.assertTrue(result["observation"]["sequence_contiguous"])

    def test_proved_does_not_claim_return_rollback_or_health(self):
        result = self.run_consumer(capture(witness=witness_body()))
        joined = " ".join(result["does_not_establish"])
        for separate in ("Android return", "rollback success", "final device health"):
            self.assertIn(separate, joined)
        self.assertNotIn("healthy", json.dumps(result["establishes"]))

    def test_no_log_bytes_leave_the_consumer(self):
        result = self.run_consumer(capture(witness=witness_body()))
        rendered = json.dumps(result)
        self.assertNotIn(BOOT_ID, rendered, "the raw boot id must not be republished")
        self.assertNotIn("First Stage Init", rendered)
        self.assertIn("boot_id_sha256", result["observation"])

    def test_the_consumer_has_no_device_surface(self):
        # Checked on the import graph rather than on the text, so the module's
        # own prose about not having a subprocess surface cannot fail its own
        # test - and so an import added later cannot hide inside a comment.
        tree = ast.parse((REVALIDATION / "s20plus_g986n_p1_pid1_witness_evidence.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertEqual(imported, {"__future__", "argparse", "hashlib", "json", "os", "re", "stat",
                                    "pathlib", "typing"})
        self.assertFalse(EVIDENCE.DEVICE_OBSERVATION_ACTIVE)
        for counter in ("device_commands", "adb_commands", "su_commands"):
            self.assertEqual(EVIDENCE.result_document(Path("a"), Path("b"), {"verdict": "NO_PROOF"})[counter], 0)

    def test_extra_header_fields_from_a_newer_kernel_are_tolerated(self):
        data = capture(witness=witness_body(), witness_header_extra=",caller=T1")
        self.assertEqual(self.run_consumer(data)["verdict"], "PROVED")


class ConsumerRefusalTests(ConsumerHarness):
    def test_non_pid1_execution_is_refused(self):
        self.assertRefused(self.run_consumer(capture(witness=witness_body(pid="0000000002"))),
                           "pid-not-one")

    def test_procfs_disagreeing_with_the_gate_is_refused(self):
        self.assertRefused(self.run_consumer(capture(witness=witness_body(procself="2"))),
                           "pid-not-one")

    def test_a_descendant_pid_namespace_is_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(pidns="pid:[4026532567]"))),
            "not-initial-pid-namespace",
        )

    def test_partial_evidence_emission_is_refused_and_named(self):
        for field in ("procself", "pidns", "bootid"):
            with self.subTest(field=field):
                result = self.run_consumer(
                    capture(witness=witness_body(**{field: EVIDENCE.UNAVAILABLE}))
                )
                self.assertRefused(result, "field-unavailable")
                self.assertEqual(result["detail"], field)

    def test_a_record_from_another_boot_is_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(bootid="00000000-0000-4000-8000-000000000000"))),
            "boot-id-mismatch",
        )

    def test_a_record_naming_another_candidate_is_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(cand="0" * 32))),
            "candidate-id-mismatch",
        )

    def test_an_attestation_naming_another_candidate_is_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()), candidate_id="1" * 32),
            "candidate-id-mismatch",
        )

    def test_a_duplicated_record_is_refused(self):
        data = capture(witness=witness_body(), trailing=[(witness_body(), 1)])
        self.assertRefused(self.run_consumer(data), "duplicate-witness-record")

    def test_a_malformed_record_is_refused(self):
        for broken in (
            witness_body().replace(";pidns=", ";pidns"),
            witness_body(pid="1"),
            witness_body() + ";extra=1",
            witness_body(stage=""),
        ):
            with self.subTest(broken=broken[:60]):
                self.assertRefused(self.run_consumer(capture(witness=broken)),
                                   "malformed-witness-record")

    def test_escaped_bytes_inside_the_record_are_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(procself="1") + "\\x00")),
            "malformed-witness-record",
        )

    def test_a_continuation_fragment_is_not_a_record(self):
        data = capture(witness=witness_body(), witness_flag="c")
        self.assertRefused(self.run_consumer(data), "malformed-witness-record")

    def test_a_record_a_later_writer_could_have_produced_is_refused(self):
        # The refuted shape: a userspace record precedes the witness, so the
        # witness was not the first userspace writer of this boot.
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(), lead_userspace="init: hello")),
            "witness-record-not-earliest",
        )

    def test_a_capture_with_no_kernel_handover_record_is_observed_not_proved(self):
        result = self.run_consumer(capture(witness=witness_body(), kernel_handover=False))
        self.assertEqual(result["verdict"], "OBSERVED", result)
        self.assertEqual(result["reason"], "no-kernel-handover-record")
        self.assertEqual(result["establishes"], [])

    def test_a_kernel_that_exec_d_a_different_init_is_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(), kernel_init_path="/sbin/init")),
            "unexpected-init-path",
        )

    def test_a_failed_handoff_does_not_retract_the_execution_evidence(self):
        # A handoff that never happened leaves no magiskinit or init records.
        # The witness still ran as PID 1, which is what this consumer decides,
        # and it still refuses to claim the exec completed.
        result = self.run_consumer(capture(witness=witness_body(), downstream=False))
        self.assertEqual(result["verdict"], "PROVED", result)
        self.assertEqual(result["observation"]["downstream_marker_counts"],
                         {"magiskinit:": 0, "init:": 0})
        joined = " ".join(result["does_not_establish"])
        self.assertIn("exec handoff to magiskinit completed", joined)

    def test_an_evicted_ring_head_is_not_reported_as_absence(self):
        self.assertRefused(self.run_consumer(capture(base_seq=4096)), "ring-head-evicted")

    def test_an_intact_ring_with_no_record_is_reported_as_absence(self):
        self.assertRefused(self.run_consumer(capture()), "witness-record-absent")

    def test_a_bounded_prefix_with_no_record_is_not_an_absence(self):
        # A prefix that stopped early looks exactly like a boot that never wrote
        # the record. It must not be reported as one.
        self.assertRefused(
            self.run_consumer(capture(), acquisition_status=OBSERVER.STATUS_IDLE),
            "incomplete-capture",
        )

    def test_a_substituted_capture_is_refused(self):
        good = capture(witness=witness_body())
        self.assertRefused(self.run_consumer(good, capture_sha256="0" * 64),
                           "capture-binding-mismatch")
        self.assertRefused(self.run_consumer(good, capture_size=len(good) + 1),
                           "capture-binding-mismatch")

    def test_a_retained_previous_boot_source_cannot_reach_proved(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()), source="retained-last-kmsg"),
            "unsupported-capture-source",
        )

    def test_another_target_is_refused(self):
        other = dict(EVIDENCE.TARGET, model="SM-S906N", device="g0q")
        self.assertRefused(self.run_consumer(capture(witness=witness_body()), target=other),
                           "target-mismatch")

    def test_a_malformed_attestation_is_refused(self):
        capture_path = self.dir / "kmsg.raw"
        data = capture(witness=witness_body())
        capture_path.write_bytes(data)
        for bad in (
            b"{",
            b"[]",
            json.dumps({"schema": EVIDENCE.ATTESTATION_SCHEMA}).encode(),
        ):
            with self.subTest(bad=bad[:20]):
                attestation_path = self.dir / "attestation.json"
                attestation_path.write_bytes(bad)
                result = EVIDENCE.validate(capture_path, attestation_path)
                self.assertRefused(result, "malformed-attestation")

    def test_an_extra_attestation_key_is_refused(self):
        result = self.run_consumer(capture(witness=witness_body()), extra_authority=True)
        self.assertRefused(result, "malformed-attestation")

    def test_a_capture_that_is_not_record_aligned_is_refused(self):
        for broken in (b"not a record\n", b" orphan dict line\n"):
            with self.subTest(broken=broken[:24]):
                self.assertRefused(self.run_consumer(broken), "malformed-capture")

    def test_a_capture_whose_sequence_does_not_advance_is_refused(self):
        # Not something this kernel's ring can produce: log_store() does
        # log_next_seq++ per record, so repeats and reversals are impossible.
        for broken in (
            record("a", seq=0, ts_usec=1).encode() + record("b", seq=0, ts_usec=2).encode(),
            record("a", seq=1, ts_usec=1).encode() + record("b", seq=0, ts_usec=2).encode(),
        ):
            with self.subTest(broken=broken[:24]):
                result = self.run_consumer(broken, parse_status=OBSERVER.PARSE_ALIGNED)
                self.assertEqual(result["verdict"], "NO_PROOF", result)
                self.assertIn(result["reason"], ("capture-sequence-gap", "ring-head-evicted"))

    def test_an_empty_capture_is_refused(self):
        self.assertRefused(self.run_consumer(b""), "empty-capture")

    def test_a_record_that_did_not_come_from_a_userspace_write_is_refused(self):
        data = capture(witness=witness_body(), witness_facility=0)
        self.assertRefused(self.run_consumer(data), "unexpected-facility")

    def test_an_indirect_input_is_refused(self):
        data = capture(witness=witness_body())
        real = self.dir / "real.raw"
        real.write_bytes(data)
        link = self.dir / "link.raw"
        link.symlink_to(real)
        attestation = self.dir / "attestation.json"
        attestation.write_text(json.dumps(OBSERVER.build_attestation(
            framed=OBSERVER.frame(data), acquisition_status=OBSERVER.STATUS_COMPLETE,
            target=EVIDENCE.TARGET, candidate_id=EVIDENCE.CANDIDATE_ID,
            candidate_boot_sha256=EVIDENCE.CANDIDATE_BOOT_SHA256,
            candidate_ap_sha256=EVIDENCE.CANDIDATE_AP_SHA256, boot_id=BOOT_ID)))
        self.assertRefused(EVIDENCE.validate(link, attestation), "indirect-input")


if __name__ == "__main__":
    unittest.main()


class ReproducedFalsePositiveTests(ConsumerHarness):
    """The two captures independent review drove to PROVED through the first
    predicate. Both are shaped exactly as reported: otherwise valid witness
    fields, matching size and digest attestations, and a well-formed `init:`
    line after the witness. Neither may reach PROVED again.

    They failed for one reason - the first predicate asked only that the witness
    record be stamped before the first record whose body began `init: `, which a
    late writer satisfies without backdating anything, because nothing showed
    that the observed `init: ` line was the first one of the boot.
    """

    CASE_A = (
        b"14,50000,900000000,-;" + witness_body().encode() + b"\n"
        b"14,50001,900000010,-;init: later ordinary log\n"
    )
    CASE_B = b"6,0,0,-;Booting Linux on physical CPU 0x0\n" + CASE_A

    def test_case_a_an_evicted_boot_prefix_is_not_proved(self):
        result = self.run_consumer(self.CASE_A)
        self.assertNotEqual(result["verdict"], "PROVED", result)
        self.assertRefused(result, "ring-head-evicted")

    def test_case_b_a_missing_intermediate_range_is_not_proved(self):
        # The framing sees the hole first; the consumer's own contiguity check
        # sees it too when the framing claims otherwise.
        self.assertRefused(self.run_consumer(self.CASE_B), "unusable-framing")
        self.assertRefused(
            self.run_consumer(self.CASE_B, parse_status=OBSERVER.PARSE_ALIGNED),
            "capture-sequence-gap",
        )

    def test_neither_case_is_reported_as_an_absence_of_the_record(self):
        # Both carry a witness record. Refusing them is a statement about the
        # capture, never about what the device wrote.
        for data in (self.CASE_A, self.CASE_B):
            result = self.run_consumer(data, parse_status=OBSERVER.PARSE_ALIGNED)
            self.assertNotEqual(result["reason"], "witness-record-absent")
            self.assertEqual(result["establishes"], [])


class CaptureCompletenessTests(ConsumerHarness):
    def test_a_sequence_gap_is_refused_by_the_framing(self):
        data = renumber(capture(witness=witness_body()), {5: 900})
        self.assertRefused(self.run_consumer(data), "unusable-framing")

    def test_a_sequence_gap_is_refused_again_when_the_framing_lies(self):
        # The consumer re-derives contiguity itself rather than trusting the
        # parse status it was handed.
        data = renumber(capture(witness=witness_body()), {5: 900})
        self.assertRefused(
            self.run_consumer(data, parse_status=OBSERVER.PARSE_ALIGNED),
            "capture-sequence-gap",
        )

    def test_a_capture_not_ending_on_a_record_boundary_is_refused(self):
        data = capture(witness=witness_body())
        self.assertRefused(self.run_consumer(data[:-12], evaluate_raw=True),
                           "truncated-capture")

    def test_a_derivative_that_does_not_span_the_raw_capture_is_refused(self):
        data = capture(witness=witness_body())
        self.assertRefused(self.run_consumer(data, raw_size=len(data) + 64),
                           "capture-binding-mismatch")

    def test_a_derivative_claiming_a_nonzero_offset_is_refused(self):
        self.assertRefused(self.run_consumer(capture(witness=witness_body()), aligned_offset=8),
                           "malformed-attestation")

    def test_a_reader_overrun_cannot_carry_a_capture_to_proved(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()),
                              acquisition_status=OBSERVER.STATUS_FAILED),
            "incomplete-acquisition",
        )

    def test_an_unreadable_read_cannot_carry_a_capture_to_proved(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()),
                              acquisition_status=OBSERVER.STATUS_UNREADABLE),
            "incomplete-acquisition",
        )

    def test_a_bounded_prefix_containing_the_record_is_still_proved(self):
        # The tail is not part of the predicate: every record that could precede
        # the witness has a lower sequence number and is therefore in the prefix.
        result = self.run_consumer(capture(witness=witness_body()),
                                   acquisition_status=OBSERVER.STATUS_IDLE)
        self.assertEqual(result["verdict"], "PROVED", result)

    def test_a_reader_extent_that_disagrees_with_the_bytes_is_refused(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()), reader_records=99),
            "capture-binding-mismatch",
        )

    def test_the_attested_candidate_artifacts_must_be_the_pinned_ones(self):
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()), candidate_boot_sha256="0" * 64),
            "candidate-artifact-mismatch",
        )
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body()), candidate_ap_sha256="0" * 64),
            "candidate-artifact-mismatch",
        )

    def test_kernel_records_before_the_witness_do_not_disqualify_it(self):
        # The capture opens with kernel-facility records, which is what a real
        # boot looks like. Only a USERSPACE record before the witness means
        # another process wrote first, because facility 0 is the one thing
        # devkmsg_write() will not let a userspace writer claim.
        proved = self.run_consumer(capture(witness=witness_body()))
        self.assertEqual(proved["verdict"], "PROVED", proved)
        self.assertGreater(proved["observation"]["witness_seq"], 0)
        self.assertRefused(
            self.run_consumer(capture(witness=witness_body(), lead_userspace="anything at all")),
            "witness-record-not-earliest",
        )

    def test_proved_states_its_assumptions(self):
        result = self.run_consumer(capture(witness=witness_body()))
        self.assertEqual(result["verdict"], "PROVED")
        joined = " ".join(result["assumptions"])
        self.assertIn("transfer journal", joined)
        self.assertIn("same", joined)
        self.assertIn("hostile resident root", joined)
        # And it does not claim the timestamp authenticated the producer.
        self.assertIn("timestamp establishes ordering and nothing more",
                      " ".join(result["does_not_establish"]))

    def test_a_refusal_never_publishes_assumptions_as_if_established(self):
        result = self.run_consumer(capture(base_seq=4096))
        self.assertEqual(result["establishes"], [])
        self.assertEqual(result["assumptions"], [])


HARNESS_SOURCE = ROOT / "tests/s20plus_p1_pid1_witness_fault_harness.c"
HOST_CC = shutil.which("gcc") or shutil.which("cc")


@unittest.skipUnless(HOST_CC, "a host C compiler is required")
class ProducerFaultInjectionTests(unittest.TestCase):
    """Failure paths executed, not read.

    The harness compiles the production source with
    S20PLUS_P1_WITNESS_FAULT_HARNESS defined, which replaces the `svc #0`
    primitive and nothing else. Every branch below is the device's own control
    flow; only the syscall results are injected. Both terminal states are
    observable because both go through the seam - the park loop calls nanosleep
    and a completed handoff calls execve.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "fault-harness"
        subprocess.run(
            [HOST_CC, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
             "-I", str(SOURCE.parent), str(HARNESS_SOURCE), "-o", str(cls.binary)],
            check=True, capture_output=True, timeout=180,
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_scenario(self, name):
        completed = subprocess.run([str(self.binary), name], check=True,
                                   capture_output=True, timeout=30)
        text = completed.stdout.decode()
        calls = [line[len("CALL ") :] for line in text.splitlines() if line.startswith("CALL ")]
        ending = [line for line in text.splitlines() if line.startswith("END ")][0]
        return {"text": text, "calls": calls, "names": [c.split(" ")[0] for c in calls],
                "end": ending.split(" ", 1)[1]}

    # --- the successful path, so the failure paths mean something ----------
    def test_a_clean_run_writes_the_record_and_hands_off_with_the_kernel_vectors(self):
        run = self.run_scenario("happy")
        self.assertEqual(run["end"], "exec")
        self.assertIn("HANDOFF_VECTORS argv_is_stack1=1 envp_is_stack4=1", run["text"])
        self.assertIn("HANDOFF argv0=/init argv1=selinux_setup argv2=(null)", run["text"])
        self.assertIn("envp0=PATH=/sbin envp1=(null)", run["text"])
        record_line = [l for l in run["text"].splitlines() if l.startswith("RECORD ")][0]
        self.assertTrue(record_line[len("RECORD ") :].startswith(EVIDENCE.MAGIC + ";"))
        # The record that reached /dev/kmsg is one whole record, written once.
        self.assertEqual(run["names"].count("write"), 1)
        self.assertIn("RECORD_BYTES", run["text"])

    def test_the_record_the_producer_actually_wrote_satisfies_the_consumer_grammar(self):
        run = self.run_scenario("happy")
        body = [l for l in run["text"].splitlines() if l.startswith("RECORD ")][0][len("RECORD ") :]
        match = EVIDENCE.WITNESS_GRAMMAR.match(body)
        self.assertIsNotNone(match, body)
        self.assertEqual(match.group("pid"), EVIDENCE.EXPECTED_PID)
        self.assertEqual(match.group("procself"), EVIDENCE.EXPECTED_PROCSELF)
        self.assertEqual(match.group("pidns"), EVIDENCE.EXPECTED_PIDNS)
        self.assertEqual(match.group("stage"), EVIDENCE.STAGE)

    # --- the PID1 gate -----------------------------------------------------
    def test_a_non_pid1_process_performs_no_effect_at_all(self):
        run = self.run_scenario("not-pid1")
        self.assertEqual(run["end"], "park")
        self.assertEqual(run["names"], ["getpid"])
        self.assertIn("RECORD none", run["text"])
        self.assertIn("HANDOFF none", run["text"])

    # --- evidence failures must never reach the handoff --------------------
    def test_a_failed_kmsg_open_still_hands_off(self):
        run = self.run_scenario("kmsg-open-fail")
        self.assertEqual(run["end"], "exec")
        self.assertNotIn("write", run["names"])
        self.assertIn("RECORD none", run["text"])

    def test_a_failed_mknod_still_hands_off_and_removes_nothing(self):
        run = self.run_scenario("mknod-fail")
        self.assertEqual(run["end"], "exec")
        self.assertNotIn("unlinkat", run["names"])

    def test_a_preexisting_kmsg_node_is_not_unlinked(self):
        # mknod refused with EEXIST means the node is not this witness's to
        # remove; unlinking it would hand magiskinit a world it did not have.
        run = self.run_scenario("mknod-exists")
        self.assertEqual(run["end"], "exec")
        self.assertNotIn("unlinkat", run["names"])

    def test_a_write_error_still_hands_off(self):
        run = self.run_scenario("write-fail")
        self.assertEqual(run["end"], "exec")
        self.assertIn("RECORD none", run["text"])
        self.assertEqual(run["names"].count("write"), 1, "a failed write is not retried")

    def test_a_short_write_is_not_retried_and_still_hands_off(self):
        run = self.run_scenario("short-write")
        self.assertEqual(run["end"], "exec")
        self.assertEqual(run["names"].count("write"), 1)
        self.assertIn("RECORD_BYTES 12 of", run["text"])

    def test_unreadable_procfs_values_become_the_placeholder_and_still_hand_off(self):
        run = self.run_scenario("readlink-fail")
        self.assertEqual(run["end"], "exec")
        body = [l for l in run["text"].splitlines() if l.startswith("RECORD ")][0][len("RECORD ") :]
        self.assertIn(f"procself={EVIDENCE.UNAVAILABLE}", body)
        self.assertIn(f"pidns={EVIDENCE.UNAVAILABLE}", body)

    def test_a_failed_proc_mount_still_hands_off_and_unmounts_nothing(self):
        run = self.run_scenario("mount-fail")
        self.assertEqual(run["end"], "exec")
        self.assertNotIn("umount2", run["names"])
        body = [l for l in run["text"].splitlines() if l.startswith("RECORD ")][0][len("RECORD ") :]
        self.assertIn(f"bootid={EVIDENCE.UNAVAILABLE}", body)

    def test_a_partially_emitted_record_is_still_refused_by_the_consumer(self):
        # The producer emits a well-formed record with placeholders rather than
        # silence, and the consumer names which field was missing.
        run = self.run_scenario("readlink-fail")
        body = [l for l in run["text"].splitlines() if l.startswith("RECORD ")][0][len("RECORD ") :]
        harness = ConsumerHarness("run")
        harness.setUp()
        self.addCleanup(harness.tmp.cleanup)
        result = harness.run_consumer(capture(witness=body), boot_id=HARNESS_BOOT_ID)
        self.assertEqual(result["verdict"], "NO_PROOF")
        self.assertEqual(result["reason"], "field-unavailable")

    # --- cleanup failure, where it changes what magiskinit inherits ---------
    def test_a_cleanup_that_cannot_unmount_proc_still_hands_off_and_says_so(self):
        run = self.run_scenario("umount-fail")
        self.assertEqual(run["end"], "exec")
        # Both the plain and the MNT_DETACH attempt were made, in that order.
        self.assertEqual(run["names"].count("umount2"), 2)
        # And magiskinit inherits a /proc this witness mounted. The claim that
        # the inherited world is unchanged does not hold on this path, and the
        # source comment says so rather than asserting otherwise.
        self.assertIn("STATE proc_mounted=1", run["text"])
        self.assertIn("magiskinit inherits a /proc this", SOURCE.read_text())

    # --- the two handoff failures ------------------------------------------
    def test_a_failed_rename_parks_without_exec_or_recursive_entry(self):
        run = self.run_scenario("rename-fail")
        self.assertEqual(run["end"], "park")
        self.assertNotIn("execve", run["names"], "exec after a failed rename re-enters this witness")
        self.assertIn("HANDOFF none", run["text"])
        # And the evidence still happened: the failure is in the handoff, not in
        # the record.
        self.assertIn(f"RECORD {EVIDENCE.MAGIC};", run["text"])

    def test_a_failed_exec_parks_without_exiting_pid_1(self):
        run = self.run_scenario("exec-fail")
        self.assertEqual(run["end"], "park")
        self.assertIn("execve", run["names"])
        self.assertNotIn("exit_group", run["names"], "PID 1 exiting is a kernel panic")

    def test_every_terminal_state_is_park_or_exec_and_never_a_fallthrough(self):
        for scenario in ("happy", "not-pid1", "mount-fail", "readlink-fail",
                         "bootid-open-fail", "kmsg-open-fail", "mknod-fail",
                         "mknod-exists", "write-fail", "short-write",
                         "umount-fail", "rename-fail", "exec-fail"):
            with self.subTest(scenario=scenario):
                self.assertIn(self.run_scenario(scenario)["end"], ("park", "exec"))

    def test_the_seam_is_guarded_and_absent_from_the_device_build(self):
        text = SOURCE.read_text()
        self.assertEqual(text.count("#ifdef S20PLUS_P1_WITNESS_FAULT_HARNESS"), 1)
        guarded = text.split("#ifdef S20PLUS_P1_WITNESS_FAULT_HARNESS", 1)[1].split("#else", 1)[0]
        self.assertIn("p1w_harness_syscall", guarded)
        self.assertEqual(text.count("p1w_harness_syscall"), guarded.count("p1w_harness_syscall"))
        # And the builder refuses a source where that stops being true.
        self.assertIn("fault-injection seam is not guarded exactly once",
                      (REVALIDATION / "build_s20plus_g986n_p1_pid1_witness_h0.py").read_text())


HARNESS_BOOT_ID = "3f7a1b20-91cc-4d0e-8a55-1c9e77b40d31"


EVIDENCE_VERDICT_NAMES = ("PROVED", "OBSERVED", "NO_PROOF")
