"""Hostile tests for the S20+ sec_log `/proc/last_kmsg` channel D0.

The PMSG lane shipped a defect that every host-shell test accepted and the
device rejected, so this suite executes the *complete* generated root script
through the target's own mksh and toybox binaries from the retained stock
ramdisk extract under qemu-aarch64 from the start.

The dynamic class skips when that private extract or qemu is unavailable, but
only while the runner is dormant: `test_device_shell_evidence_is_required_when_active`
makes the skip impossible to combine with activation, so the extract cannot be
missing at the moment the capability is armed.
"""
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_last_kmsg_observation_d0.py"
EXTRACT = ROOT / "workspace/private/work/s20plus-twrp-y2q-h0-20260831/ramdisk-stock-iyc2"
DEVICE_SHELL = EXTRACT / "system/bin/sh"
DEVICE_BIN = EXTRACT / "system/bin"
QEMU = shutil.which("qemu-aarch64")
DEVICE_TOOLS = ("stat", "cat", "printf", "head", "grep", "sha256sum", "readlink", "id", "wc")

# Everything the runner-owned section may invoke without an absolute path.
SHELL_WORDS = frozenset(
    "if then elif else fi for while do done case esac function return exit "
    "export local readonly set unset shift break continue emit true false : . [ [[ test".split()
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load("_s20_last_kmsg", RUNNER)


def owned(script=None):
    """The part this runner generates, after the shared pinned health guard."""
    script = M.ROOT_SCRIPT if script is None else script
    guard = M.health.ROOT_READ_SCRIPT
    if not script.startswith(guard):
        raise AssertionError("generated script no longer starts with the shared guard")
    return script[len(guard):]


def command_words(text):
    """First word of every command position, so a PATH check cannot be name-based.

    A blacklist of helper names is trivially evaded (`c=${x:-printf}; "$c"`), so
    the guard enumerates command *positions* and requires each to be a shell
    word or an absolute /system/bin path. Lexing is quote-aware and per line, so
    a `|` inside a regex argument is an argument, not a pipeline.
    """
    separators = {";", "|", "||", "&&", "&", "(", ")", "{", "}"}
    continuing = {"if", "then", "else", "elif", "do", "while", "until", "!"}
    words = []
    for line in text.splitlines():
        lexer = shlex.shlex(line, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = "#"
        expect = True
        try:
            tokens = list(lexer)
        except ValueError:  # an unbalanced quote is a defect the shell tests catch
            continue
        for token in tokens:
            if token in separators:
                expect = True
                continue
            if not expect:
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token) or token.startswith((">", "<")):
                continue
            words.append(token)
            expect = token in continuing
    return words


class ShapeTests(unittest.TestCase):
    def test_runner_is_dormant_and_declares_no_log_egress(self):
        self.assertIs(M.ACTIVE, False)
        plan = M.render_plan()
        self.assertEqual(plan["log_bytes_crossing_boundary"], 0)
        self.assertEqual(plan["log_bytes_retained"], 0)
        self.assertIs(plan["log_contents_read"], False)
        self.assertIs(plan["device_writes"], False)
        self.assertIs(plan["reboot_requested"], False)
        self.assertIs(plan["partition_access"], False)
        self.assertEqual(plan["planned_root_commands"], 1)

    def test_no_descriptor_is_addressed_through_proc_self(self):
        # The V1 PMSG defect: /proc/self names the exec'd helper, not the shell.
        self.assertNotIn("/proc/self/fd/", M.ROOT_SCRIPT)

    def test_every_owned_command_position_is_absolute_or_a_shell_word(self):
        for word in command_words(owned()):
            with self.subTest(word=word):
                # A `$`-prefixed command word is exactly the evasion this guard
                # exists to catch (`c=${x:-printf}; "$c"`), so it is not allowed
                # through: every command position must be literal and absolute,
                # or a shell word.
                self.assertTrue(
                    word.startswith("/system/bin/") or word in SHELL_WORDS,
                    f"PATH-resolved or unexpected command position: {word}",
                )

    def test_predicates_use_extended_regular_expressions(self):
        # BRE alternation (\|) is a GNU extension the target's toybox need not
        # implement, so every predicate must be dispatched with -E.
        for line in owned().splitlines():
            if "grep" in line:
                self.assertIn("/system/bin/grep -aEc ", line)
                self.assertNotIn(r"\|", line)

    def test_every_output_key_is_emitted_exactly_once(self):
        emitted = re.findall(r"^emit ([a-z_]+) ", owned(), flags=re.M)
        self.assertEqual(emitted, [k for k in M.OUTPUT_KEYS if k not in M.health.ROOT_OUTPUT_KEYS])
        self.assertEqual(len(emitted), len(set(emitted)))

    def test_no_branch_can_emit_log_content(self):
        # `emit` is only ever called with a declared key and a shell variable,
        # never with anything derived from the node's bytes.
        for key, value in re.findall(r'^emit ([a-z_]+) "?(\$[A-Za-z_{][^"\n]*)"?$', owned(), flags=re.M):
            self.assertIn(key, M.OUTPUT_KEYS)
            self.assertRegex(value, r'^\$\{?[a-z_]+\}?$')
        self.assertNotIn("/system/bin/cat \"$node\"", owned())


class ParserTests(unittest.TestCase):
    ORDER = ("state", "meta", "bounded", "scanned", "window", "recheck", "meta_after")

    def transcript(self, **overrides):
        values = {"state": "regular", "meta": f"{M.OBSERVED_SIZE}:1", "bounded": "yes",
                  "scanned": str(M.OBSERVED_SIZE), "window": "a" * 64 + "  -",
                  "recheck": "a" * 64 + "  -", "meta_after": f"{M.OBSERVED_SIZE}:1",
                  "lines_total": "1000", "priority_timestamp": "980",
                  "timestamp_only": "980", "priority_only": "0",
                  "seclog_cpu_field": "0", "no_record_prefix": "20"}
        values.update(overrides)
        body = "".join(f"{k}={v}\n" for k, v in M.health.EXPECTED_ROOT_OUTPUT.items())
        body += "".join(f"{k}={values[k]}\n" for k in (*self.ORDER, *M.PREDICATES))
        return (0, body.encode(), b"")

    def unscanned(self, **overrides):
        """A transcript for a node the shell never scanned."""
        values = {"state": "unavailable", "meta": "0:0", "bounded": "no", "scanned": "-1",
                  "window": "none", "recheck": "none", "meta_after": "0:0"}
        values.update({k: "0" for k in M.PREDICATES})
        values.update(overrides)
        return self.transcript(**values)

    def test_dominant_shape_is_reported_not_asserted(self):
        facts = M.parse_root(self.transcript(
            lines_total="1000", priority_timestamp="980", timestamp_only="980",
            priority_only="0", seclog_cpu_field="0", no_record_prefix="20",
        ))
        self.assertEqual(facts["shape_counts"]["lines_total"], 1000)
        self.assertTrue(facts["scan_complete"])
        self.assertIn(facts["dominant_shape"], M.SHAPES)
        self.assertEqual(
            M.channel_verdict(facts), "RECORDS_DOMINANTLY_" + facts["dominant_shape"].upper()
        )

    def test_a_seclog_cpu_field_is_surfaced_as_its_own_verdict(self):
        # The finding that would invalidate an anchor expecting the message
        # immediately after the timestamp, so it outranks the shape ranking.
        facts = M.parse_root(self.transcript(
            lines_total="1000", priority_timestamp="990", timestamp_only="990",
            priority_only="0", seclog_cpu_field="985", no_record_prefix="10",
        ))
        self.assertTrue(facts["seclog_cpu_field_present"])
        self.assertEqual(M.channel_verdict(facts), "RECORDS_CARRY_A_SECLOG_CPU_FIELD")

    def test_no_dominant_shape_is_itself_the_finding(self):
        facts = M.parse_root(self.transcript(
            lines_total="1000", priority_timestamp="100", timestamp_only="200",
            priority_only="150", seclog_cpu_field="0", no_record_prefix="300",
        ))
        self.assertEqual(facts["dominant_shape"], "no-dominant-shape")
        self.assertEqual(M.channel_verdict(facts), "RECORDS_HAVE_NO_DOMINANT_SHAPE")

    def test_nothing_in_the_result_interprets_content_or_names_a_boot(self):
        facts = M.parse_root(self.transcript())
        for withdrawn in (
            "channel_readable", "carries_terminal_record", "is_kernel_log",
            "carries_candidate_banner", "is_completed_prior_boot",
        ):
            self.assertNotIn(withdrawn, facts)
        verdict = M.channel_verdict(facts)
        for word in ("PROVEN", "PRIOR_BOOT", "BANNER", "READABLE_WITH"):
            self.assertNotIn(word, verdict)

    def test_absent_node_is_reported_without_a_shape(self):
        facts = M.parse_root(self.unscanned())
        self.assertEqual(M.channel_verdict(facts), "NODE_ABSENT_OR_UNREADABLE")

    def test_truncated_scan_is_refused_rather_than_counted_as_zero(self):
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.transcript(scanned=str(M.OBSERVED_SIZE - 1)))

    def test_growth_past_the_cap_is_refused(self):
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.transcript(meta_after=f"{M.OBSERVED_SIZE + 4096}:1"))

    def test_bound_must_follow_from_the_observed_node(self):
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.unscanned(state="regular", meta=f"{M.OBSERVED_SIZE}:1"))

    def test_inconsistent_transcripts_are_refused(self):
        cases = [
            {"state": "unavailable", "bounded": "yes"},
            {"bounded": "no", "window": "a" * 64 + "  -"},
            {"recheck": "b" * 64 + "  -"},
            {"recheck": "none"},
            {"meta": f"{M.OBSERVED_SIZE}:2"},
            {"window": "zz"},
            {"state": "elsewhere"},
            {"lines_total": "-1"},
            {"meta": "not-metadata"},
        ]
        for override in cases:
            with self.subTest(**override), self.assertRaises(M.ObservationError):
                M.parse_root(self.transcript(**override))

    def test_short_and_reordered_transcripts_are_refused(self):
        rc, stdout, stderr = self.transcript()
        lines = stdout.splitlines(keepends=True)
        with self.assertRaises(Exception):
            M.parse_root((rc, b"".join(lines[:-1]), stderr))
        with self.assertRaises(Exception):
            M.parse_root((rc, b"".join(lines[:-2] + [lines[-1], lines[-2]]), stderr))
        with self.assertRaises(Exception):
            M.parse_root((rc, stdout + b"extra=1\n", stderr))

    def test_nonzero_status_or_stderr_is_refused(self):
        _, stdout, _ = self.transcript()
        for result in ((65, stdout, b""), (0, stdout, b"warning\n")):
            with self.assertRaises(Exception):
                M.parse_root(result)


class ActivationGateTests(unittest.TestCase):
    def test_device_shell_evidence_is_required_when_active(self):
        # Fail closed: the dynamic class may skip only while dormant. Arming the
        # capability without the target-shell extract must be impossible.
        if M.ACTIVE:
            self.assertTrue(QEMU, "qemu-aarch64 is required to activate this capability")
            self.assertTrue(DEVICE_SHELL.exists(), "the target shell extract is required to activate")
            for name in DEVICE_TOOLS:
                self.assertTrue((DEVICE_BIN / name).exists(), f"missing target tool: {name}")

    def test_dormant_runner_refuses_every_connected_entry_point(self):
        for call in (M.require_active, M.FixedBackend, lambda: M.bounded_capture(["/bin/true"], 1.0, 16)):
            with self.assertRaises(M.ObservationError):
                call()


@unittest.skipUnless(QEMU and DEVICE_SHELL.exists(), "qemu-aarch64 or the private stock ramdisk extract is unavailable")
class DeviceShellTests(unittest.TestCase):
    KERNEL_LOG = (
        b"<6>[    0.000000] Booting Linux on physical CPU 0x0\n"
        b"<5>[    0.000000] Linux version 4.19.113-27166950 (builder@host)\n"
        b"<6>[    0.100000] sec_log_buf: buffer at 0x9f000000\n"
        b"<6>[    2.500000] init: init first stage started!\n"
        b"<6>[    9.900000] init: Command 'start' action=boot\n"
        b"<5>[  600.000000] reboot: Restarting system\n"
    )

    def fixture(self, root, node_bytes=None, node_kind="regular"):
        mapping = {}
        for path, content in (("/proc/self/attr/current", b"u:r:magisk:s0\n"),
                              ("/proc/1/attr/current", b"u:r:init:s0\n")):
            dest = root / path.lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            mapping[path] = str(dest)
        pid1 = root / "proc/1/exe"
        pid1.parent.mkdir(parents=True, exist_ok=True)
        pid1.symlink_to("/system/bin/init")
        mapping["/proc/1/exe"] = str(pid1)
        for name in DEVICE_TOOLS:
            mapping["/system/bin/" + name] = str(DEVICE_BIN / name)
        # Stubs run under the target shell and use only its builtins, so nothing
        # inside them depends on a path qemu would have to resolve itself.
        def stub(relative, body):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"#!" + str(DEVICE_SHELL).encode() + b"\n" + body)
            path.chmod(0o755)
            return str(path)

        mapping["/system/bin/getenforce"] = stub("tools/getenforce", b"echo Enforcing\n")
        mapping["/data/adb/magisk/magisk"] = stub(
            "tools/magisk",
            b'case "$1" in\n-v) echo 30.7:MAGISK:R;;\n-V) echo 30700;;\nesac\n')
        node = root / "last_kmsg"
        if node_kind == "regular":
            node.write_bytes(self.KERNEL_LOG if node_bytes is None else node_bytes)
        elif node_kind == "absent":
            pass
        elif node_kind == "symlink":
            node.symlink_to("/dev/null")
        mapping[M.NODE] = str(node)
        script = M.ROOT_SCRIPT
        # `id -u`/`id -g` come from the shared guard; give them a root answer.
        script = script.replace("$(/system/bin/id -u)", "0").replace("$(/system/bin/id -g)", "0")
        pattern = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
        return pattern.sub(lambda m: mapping[m.group()], script)

    def run_device_shell(self, script):
        env = dict(os.environ, QEMU_LD_PREFIX=str(EXTRACT))
        return subprocess.run([QEMU, str(DEVICE_SHELL), "-c", script],
                              capture_output=True, cwd=str(EXTRACT), env=env, timeout=180)

    def parsed(self, result):
        return M.parse_root((result.returncode, result.stdout, result.stderr))

    def test_fixture_is_the_targets_own_mksh(self):
        result = self.run_device_shell('echo "$KSH_VERSION"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"MIRBSD KSH", result.stdout)

    def test_shape_counters_measure_the_target_grep_not_the_host(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            counts = facts["shape_counts"]
            self.assertEqual(counts["lines_total"], len(self.KERNEL_LOG.splitlines()))
            # Every line of the fixture carries a priority and a timestamp.
            self.assertEqual(counts["priority_timestamp"], counts["lines_total"])
            self.assertEqual(counts["no_record_prefix"], 0)
            self.assertEqual(counts["seclog_cpu_field"], 0)
            self.assertTrue(facts["scan_complete"])

    def test_a_seclog_cpu_field_is_detected_under_the_target_grep(self):
        # The measurement this capability exists for. If the real buffer looks
        # like this, an anchor expecting the message immediately after the
        # timestamp would silently count nothing.
        body = (
            b"<6>[    0.000000] [0:      swapper/0:    0] Booting Linux\n"
            b"<5>[    0.100000] [1:            init:    1] init: first stage\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp), node_bytes=body))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertEqual(facts["shape_counts"]["seclog_cpu_field"], 2)
            self.assertTrue(facts["seclog_cpu_field_present"])
            self.assertEqual(
                M.channel_verdict(facts), "RECORDS_CARRY_A_SECLOG_CPU_FIELD"
            )

    def test_records_without_a_prefix_are_counted_separately(self):
        # Continuation lines and a wrapped first record have no prefix; counting
        # them is how "the anchor would miss these" becomes visible.
        body = (
            b"ontinuation of a wrapped record\n"
            b"<6>[    1.000000] a whole record\n"
            b"    indented continuation\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp), node_bytes=body))
            self.assertEqual(result.returncode, 0, result.stderr)
            counts = self.parsed(result)["shape_counts"]
            self.assertEqual(counts["lines_total"], 3)
            self.assertEqual(counts["no_record_prefix"], 2)
            self.assertEqual(counts["priority_timestamp"], 1)

    def test_absent_node_still_emits_every_key(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp), node_kind="absent"))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertEqual(facts["state"], "unavailable")
            self.assertFalse(facts["bounded"])
            self.assertEqual(set(facts["shape_counts"].values()), {0})
            self.assertEqual(M.channel_verdict(facts), "NODE_ABSENT_OR_UNREADABLE")

    def test_symlinked_node_is_refused_without_reading(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp), node_kind="symlink"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.parsed(result)["state"], "indirect")

    def test_oversized_node_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            oversized = self.KERNEL_LOG + b"x" * (M.SCAN_MAXIMUM + 1)
            result = self.run_device_shell(self.fixture(Path(temp), node_bytes=oversized))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertFalse(facts["bounded"])
            self.assertEqual(set(facts["shape_counts"].values()), {0})
            self.assertEqual(M.channel_verdict(facts), "NODE_TOO_LARGE_TO_SCAN")

    def test_consuming_node_fails_closed(self):
        # A node that empties after its first read - the /proc/kmsg shape - must
        # be refused rather than reported as an empty but valid window.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = self.fixture(root)
            node = root / "last_kmsg"
            drain = root / "tools/draining-head"
            drain.parent.mkdir(parents=True, exist_ok=True)
            drain.write_bytes(b"#!" + str(DEVICE_SHELL).encode() + b"\n" +
                              str(DEVICE_BIN / "head").encode() + b' "$@"\n: > ' + str(node).encode() + b"\n")
            drain.chmod(0o755)
            script = script.replace(str(DEVICE_BIN / "head"), str(drain))
            result = self.run_device_shell(script)
            self.assertEqual(result.returncode, 0, result.stderr)
            with self.assertRaises(M.ObservationError):
                self.parsed(result)

    def test_no_log_byte_ever_reaches_stdout(self):
        with tempfile.TemporaryDirectory() as temp:
            marked = self.KERNEL_LOG.replace(b"builder@host", b"SECRET-LOG-BODY-MUST-NOT-APPEAR")
            result = self.run_device_shell(self.fixture(Path(temp), node_bytes=marked))
            self.assertEqual(result.returncode, 0, result.stderr)
            # Only key names and counts may appear; no fragment of the log body.
            for body in (b"SECRET-LOG-BODY-MUST-NOT-APPEAR", b"Linux version",
                         b"init first stage", b"Restarting system", b"<6>[", b"0x9f000000"):
                self.assertNotIn(body, result.stdout)
            self.assertLess(len(result.stdout), 1024)


if __name__ == "__main__":
    unittest.main()
