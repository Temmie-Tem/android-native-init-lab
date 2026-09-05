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
                  "linux_version": "1", "init_records": "42",
                  "terminal_marker": "1", "sec_log_marker": "3",
                  "candidate_banner": "0"}
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

    def test_readable_channel_with_userspace_and_a_terminal_record(self):
        facts = M.parse_root(self.transcript())
        self.assertTrue(facts["channel_readable"])
        self.assertTrue(facts["carries_terminal_record"])
        self.assertTrue(facts["scan_complete"])
        self.assertTrue(facts["size_matches_recorded_observation"])
        self.assertEqual(facts["window_sha256"], "a" * 64)
        self.assertIs(facts["log_contents_emitted"], False)
        self.assertEqual(
            M.channel_verdict(facts),
            "CHANNEL_READABLE_WITH_USERSPACE_AND_TERMINAL_RECORD",
        )

    def test_nothing_in_the_result_claims_retention_or_a_boot_identity(self):
        # The window may hold a wrapped older record, so readability is not
        # retention and no verdict may name which boot produced it.
        facts = M.parse_root(self.transcript())
        self.assertNotIn("is_completed_prior_boot", facts)
        self.assertNotIn("channel_proved", facts)
        self.assertNotIn("PRIOR_BOOT", M.channel_verdict(facts))
        self.assertNotIn("PROVEN", M.channel_verdict(facts))

    def test_absent_node_is_not_a_channel(self):
        facts = M.parse_root(self.unscanned())
        self.assertFalse(facts["channel_readable"])
        self.assertEqual(M.channel_verdict(facts), "CHANNEL_ABSENT")

    def test_terminal_record_absence_is_reported_without_denying_readability(self):
        facts = M.parse_root(self.transcript(terminal_marker="0"))
        self.assertTrue(facts["channel_readable"])
        self.assertFalse(facts["carries_terminal_record"])
        self.assertEqual(
            M.channel_verdict(facts),
            "CHANNEL_READABLE_WITH_USERSPACE_NO_TERMINAL_RECORD",
        )

    def test_candidate_banner_is_the_only_predicate_that_names_a_boot(self):
        facts = M.parse_root(self.transcript(candidate_banner="1"))
        self.assertTrue(facts["carries_candidate_banner"])
        self.assertEqual(facts["candidate_banner_count"], 1)
        self.assertEqual(M.channel_verdict(facts), "CANDIDATE_BANNER_OBSERVED_EXACTLY_ONCE")

    def test_repeated_candidate_banner_is_reported_not_folded_away(self):
        # More than one banner means the window spans more than one candidate
        # boot, which this lane never authorizes.
        facts = M.parse_root(self.transcript(candidate_banner="2"))
        self.assertFalse(facts["carries_candidate_banner"])
        self.assertEqual(facts["candidate_banner_count"], 2)
        self.assertEqual(M.channel_verdict(facts), "CANDIDATE_BANNER_REPEATED_UNEXPECTEDLY")

    def test_absent_banner_does_not_claim_a_boot(self):
        facts = M.parse_root(self.transcript())
        self.assertFalse(facts["carries_candidate_banner"])
        self.assertNotIn("CANDIDATE_BANNER", M.channel_verdict(facts))

    def test_userspace_absence_is_distinguished(self):
        facts = M.parse_root(self.transcript(init_records="0"))
        self.assertFalse(facts["channel_readable"])
        self.assertEqual(M.channel_verdict(facts), "CHANNEL_PRESENT_NO_USERSPACE_RECORDS")

    def test_not_a_kernel_log_is_distinguished(self):
        facts = M.parse_root(self.transcript(linux_version="0"))
        self.assertFalse(facts["channel_readable"])
        self.assertEqual(M.channel_verdict(facts), "CHANNEL_PRESENT_NOT_A_KERNEL_LOG")

    def test_truncated_scan_is_refused_rather_than_counted_as_zero(self):
        # A short read that a pipeline turned into a successful digest.
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.transcript(scanned=str(M.OBSERVED_SIZE - 1)))

    def test_growth_past_the_cap_is_refused(self):
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.transcript(meta_after=f"{M.OBSERVED_SIZE + 4096}:1"))

    def test_bound_must_follow_from_the_observed_node(self):
        # Combinations the shell cannot produce must not parse.
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.transcript(bounded="no", window="none", recheck="none",
                                         scanned="-1", meta_after="0:0",
                                         linux_version="0", init_records="0",
                                         terminal_marker="0", sec_log_marker="0"))
        with self.assertRaises(M.ObservationError):
            M.parse_root(self.unscanned(state="regular", meta=f"{M.OBSERVED_SIZE}:1"))

    def test_inconsistent_transcripts_are_refused(self):
        cases = [
            {"state": "unavailable", "bounded": "yes"},          # absent node reporting a scan
            {"bounded": "no", "window": "a" * 64 + "  -"},       # unscanned window with a digest
            {"recheck": "b" * 64 + "  -"},                       # node consumed or grew between passes
            {"recheck": "none"},                                 # scanned window without a recheck
            {"bounded": "no", "window": "none"},                 # unscanned window with hits
            {"meta": f"{M.OBSERVED_SIZE}:2"},                    # not a direct regular file
            {"window": "zz"},                                    # malformed digest
            {"state": "elsewhere"},                              # undeclared state
            {"linux_version": "-1"},                             # malformed count
            {"meta": "not-metadata"},                            # malformed metadata
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

    def test_complete_script_proves_the_channel_on_the_device_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertTrue(facts["channel_readable"])
            self.assertTrue(facts["scan_complete"])
            self.assertEqual(facts["predicate_counts"]["linux_version"], 1)
            self.assertEqual(facts["predicate_counts"]["init_records"], 2)
            self.assertEqual(facts["predicate_counts"]["terminal_marker"], 1)
            self.assertEqual(
                M.channel_verdict(facts),
                "CHANNEL_READABLE_WITH_USERSPACE_AND_TERMINAL_RECORD",
            )

    def test_extended_alternation_actually_matches_under_the_target_toybox(self):
        # The portability fix: each alternative must match on its own, proving
        # -E alternation is honoured by the target's grep rather than the host's.
        for tail, expected in ((b"<5>[ 1.0] reboot: Restarting system\n", 1),
                               (b"<5>[ 1.0] reboot: Power down\n", 1),
                               (b"<5>[ 1.0] Power down\n", 1),
                               (b"<5>[ 1.0] nothing terminal here\n", 0)):
            with self.subTest(tail=tail), tempfile.TemporaryDirectory() as temp:
                body = self.KERNEL_LOG.replace(b"<5>[  600.000000] reboot: Restarting system\n", b"") + tail
                result = self.run_device_shell(self.fixture(Path(temp), node_bytes=body))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.parsed(result)["predicate_counts"]["terminal_marker"], expected)

    def test_candidate_banner_is_found_under_the_target_grep(self):
        # The banner as /dev/kmsg actually renders it: a priority and timestamp
        # prefix, then the exact string the candidate's PID1 writes.
        planted = (
            b"<6>[    1.234567] " + M.CANDIDATE_BANNER.encode() + b"\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(
                self.fixture(Path(temp), node_bytes=self.KERNEL_LOG + planted)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertEqual(facts["predicate_counts"]["candidate_banner"], 1)
            self.assertTrue(facts["carries_candidate_banner"])
            self.assertEqual(
                M.channel_verdict(facts), "CANDIDATE_BANNER_OBSERVED_EXACTLY_ONCE"
            )
            # Even the banner never reaches stdout; only its count does.
            self.assertNotIn(M.CANDIDATE_BANNER.encode(), result.stdout)

    def test_quoted_candidate_banner_is_not_counted(self):
        # The banner is the one predicate that names a boot, so an unanchored
        # match on it would be the worst possible false positive: a userspace
        # record quoting the string must not read as the candidate having run.
        quoted = (
            b'<6>[   12.0] init: starting service "log ' + M.CANDIDATE_BANNER.encode() + b'"\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(
                self.fixture(Path(temp), node_bytes=self.KERNEL_LOG + quoted)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertEqual(facts["predicate_counts"]["candidate_banner"], 0)
            self.assertFalse(facts["carries_candidate_banner"])

    def test_anchoring_rejects_a_quoted_marker_in_a_userspace_record(self):
        # An unanchored substring match would count this. The record prefix
        # anchor is what makes the count mean "a kernel record", not "the bytes
        # appear somewhere in the window".
        quoted = (
            b'<6>[   12.0] init: property_set("sys.powerctl", "reboot: Restarting system")\n'
            b'<6>[   13.0] healthd: charger says Power down soon\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            body = self.KERNEL_LOG.replace(
                b"<5>[  600.000000] reboot: Restarting system\n", b""
            ) + quoted
            result = self.run_device_shell(self.fixture(Path(temp), node_bytes=body))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertEqual(facts["predicate_counts"]["terminal_marker"], 0)
            self.assertFalse(facts["carries_terminal_record"])

    def test_absent_node_still_emits_every_key(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_device_shell(self.fixture(Path(temp), node_kind="absent"))
            self.assertEqual(result.returncode, 0, result.stderr)
            facts = self.parsed(result)
            self.assertEqual(facts["state"], "unavailable")
            self.assertFalse(facts["bounded"])
            self.assertEqual(set(facts["predicate_counts"].values()), {0})
            self.assertEqual(M.channel_verdict(facts), "CHANNEL_ABSENT")

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
            self.assertEqual(set(facts["predicate_counts"].values()), {0})

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
