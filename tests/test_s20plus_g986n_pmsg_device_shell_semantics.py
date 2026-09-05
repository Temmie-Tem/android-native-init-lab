"""Device-shell semantics for the S20+ PMSG warm-reboot marker scripts.

The V1 trial passed 21/21 hostile tests and still failed on the device at the
descriptor-pin check, because every producer fixture executed the generated
script through the host shell. Host `sh` keeps `exec`-opened descriptors across
`exec`; Android's mksh marks descriptors above 2 close-on-exec, so an exec'd
helper cannot see `/proc/self/fd/N`.

The shape guards always run. The dynamic tests execute the *complete* generated
scripts — `set -eu` prelude included, probe, writer and reader — through the
target's own shell and toybox binaries from the retained stock ramdisk extract
under qemu-aarch64, and are skipped when that private extract or qemu is absent.
"""
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_pmsg_warm_reboot_d1.py"
DEVICE_SHELL_ROOT = ROOT / "workspace/private/work/s20plus-twrp-y2q-h0-20260831/ramdisk-stock-iyc2"
DEVICE_SHELL = DEVICE_SHELL_ROOT / "system/bin/sh"
DEVICE_BIN = DEVICE_SHELL_ROOT / "system/bin"
QEMU = shutil.which("qemu-aarch64")

# Helpers the extract provides as real aarch64 toybox binaries. Anything else
# the generated scripts touch is synthesized by the reused host fixture.
DEVICE_TOOLS = ("stat", "cat", "printf", "head", "grep", "wc", "sha256sum", "readlink")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load("_s20_pmsg_shell", RUNNER)
# The V1 suite owns the fixture that satisfies the shared health guard.
V1 = load("_s20_pmsg_v1_tests", ROOT / "tests/test_s20plus_g986n_pmsg_warm_reboot_d1.py")


def executable_lines(script):
    return [line for line in script.splitlines() if not line.lstrip().startswith("#")]


def pmsg_owned(script):
    """The part this runner generates, after the shared root-health guard.

    The guard is pinned, consumed bytes shared with the root-health D0 lane;
    its own bare `printf` is recorded in the target contract and deferred to
    that runner's next version bump.
    """
    guard = M.health.ROOT_READ_SCRIPT
    if not script.startswith(guard):
        raise AssertionError("generated script no longer starts with the shared guard")
    return script[len(guard):]


class ShapeTests(unittest.TestCase):
    def scripts(self):
        bound = M.make_binding(V1.observation())
        return {
            "probe": M.probe_script(bound),
            "write": M.write_script(bound),
            "read": M.read_script(bound, V1.NEW),
        }

    def test_generated_scripts_never_address_descriptors_through_proc_self(self):
        # /proc/self names the exec'd helper, not the shell that pinned the
        # descriptor. Every generated reference must go through /proc/$$.
        for name, script in self.scripts().items():
            with self.subTest(script=name):
                body = "\n".join(executable_lines(script))
                self.assertNotIn("/proc/self/fd/", body)
                self.assertIn("/proc/$$/fd/", body)

    def test_no_pmsg_owned_command_resolves_through_path(self):
        # A root-privileged script must not depend on PATH for any helper.
        bare = re.compile(r"(?<![/\w-])(printf|head|grep|wc|stat|cat|id|getprop|readlink|getenforce|sha256sum)\b")
        for name, script in self.scripts().items():
            with self.subTest(script=name):
                for line in executable_lines(pmsg_owned(script)):
                    self.assertIsNone(bare.search(line), f"PATH-resolved helper in {name}: {line.strip()}")

    def test_writer_pins_before_deriving_the_write_descriptor(self):
        script = M.write_script(M.make_binding(V1.observation()))
        pin = script.index("exec 3< /dev/pmsg0")
        derive = script.index("exec 4> /proc/$$/fd/3")
        write = script.index("/system/bin/printf '\\n%s\\n'")
        self.assertLess(pin, derive)
        self.assertLess(derive, write)
        self.assertNotIn("> /dev/pmsg0", script)
        self.assertIn("[ ! -L /dev/pmsg0 ] && [ -c /dev/pmsg0 ]", script)

    def test_probe_shares_the_writer_pin_and_writes_nothing(self):
        bound = M.make_binding(V1.observation())
        prelude = M.pin_prelude(bound)
        self.assertIn(prelude, M.probe_script(bound))
        self.assertIn(prelude, M.write_script(bound))
        self.assertNotIn(M.marker_line(bound), M.probe_script(bound))
        self.assertNotIn(">&4", M.probe_script(bound).split(prelude, 1)[1])


@unittest.skipUnless(QEMU and DEVICE_SHELL.exists(), "qemu-aarch64 or the private stock ramdisk extract is unavailable")
class DeviceShellTests(unittest.TestCase):
    def device_fixture(self, root, script, **kwargs):
        """Reuse the V1 host fixture, then swap in the target's own binaries."""
        _, mapping = V1.MarkerTests().shell_fixture(root, script, **kwargs)
        for name in DEVICE_TOOLS:
            mapping["/system/bin/" + name] = str(DEVICE_BIN / name)
        # Synthesized stubs must run under the target shell, not the host's.
        for path in list(mapping.values()):
            node = Path(path)
            if node.is_file() and os.access(node, os.X_OK) and node.read_bytes().startswith(b"#!/bin/sh\n"):
                node.write_bytes(node.read_bytes().replace(b"#!/bin/sh\n", b"#!" + str(DEVICE_SHELL).encode() + b"\n", 1))
        pattern = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
        return pattern.sub(lambda match: mapping[match.group()], script), mapping

    def run_device_shell(self, script):
        env = dict(os.environ, QEMU_LD_PREFIX=str(DEVICE_SHELL_ROOT))
        return subprocess.run(
            [QEMU, str(DEVICE_SHELL), "-c", script],
            capture_output=True, cwd=str(DEVICE_SHELL_ROOT), env=env, timeout=120,
        )

    def test_fixture_is_the_targets_own_mksh(self):
        result = self.run_device_shell('echo "$KSH_VERSION"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"MIRBSD KSH", result.stdout)

    def test_complete_probe_script_passes_on_the_device_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            bound = M.make_binding(V1.observation())
            script, _ = self.device_fixture(Path(temp), M.probe_script(bound))
            result = self.run_device_shell(script)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(M.parse_probe((result.returncode, result.stdout, result.stderr))["writable"])

    def test_complete_writer_script_passes_and_emits_the_exact_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            bound = M.make_binding(V1.observation())
            script, _ = self.device_fixture(Path(temp), M.write_script(bound))
            result = self.run_device_shell(script)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(M.parse_write((result.returncode, result.stdout, result.stderr), bound)["returned"])
            self.assertNotIn(M.marker_line(bound).encode(), result.stdout)

    def test_complete_reader_script_matches_exactly_once_on_the_device_shell(self):
        cases = [("one", "scanned", 1), ("duplicate", "scanned", 2), ("substring", "scanned", 0), ("missing", "unavailable", 0)]
        for kind, state, count in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                bound = M.make_binding(V1.observation())
                script, mapping = self.device_fixture(root, M.read_script(bound, V1.NEW), boot="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
                node = Path(mapping["/sys/fs/pstore/pmsg-ramoops-0"])
                node.unlink()
                marker = M.marker_bytes(bound)
                if kind == "one":
                    node.write_bytes(b"PRIVATE-LOG\x00\xff" + marker + b"other")
                elif kind == "duplicate":
                    node.write_bytes(marker * 2)
                elif kind == "substring":
                    node.write_bytes(b"prefix" + marker[1:])
                result = self.run_device_shell(script)
                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = M.parse_read((result.returncode, result.stdout, result.stderr))
                self.assertEqual((parsed["state"], parsed["matches"]), (state, count))
                self.assertNotIn(b"PRIVATE-LOG", result.stdout)
                self.assertNotIn(M.marker_line(bound).encode(), result.stdout)

    def test_proc_self_regression_fails_exactly_as_the_v1_trial_did(self):
        # Reverting to /proc/self must fail here, not on the device. This is the
        # exact failure the consumed V1 trial produced.
        with tempfile.TemporaryDirectory() as temp:
            bound = M.make_binding(V1.observation())
            reverted = M.write_script(bound).replace("/proc/$$/", "/proc/self/")
            script, _ = self.device_fixture(Path(temp), reverted)
            result = self.run_device_shell(script)
            self.assertEqual(result.returncode, 65)
            self.assertNotIn(b"S20PMSG_WRITE_V1", result.stdout)
            self.assertIn(b"/proc/self/fd/3", result.stderr)
            self.assertIn(b"No such file or directory", result.stderr)

    def test_host_shell_cannot_observe_this_difference(self):
        # Why the V1 suite passed: the host shell accepts both shapes, so a
        # host-only fixture constrains nothing about the target.
        with tempfile.TemporaryDirectory() as temp:
            bound = M.make_binding(V1.observation())
            script, _ = V1.MarkerTests().shell_fixture(Path(temp), M.write_script(bound))
            for candidate in (script, script.replace("/proc/$$/", "/proc/self/")):
                result = subprocess.run(["/bin/sh", "-c", candidate], capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(b"S20PMSG_WRITE_V1;returned=1;", result.stdout)


if __name__ == "__main__":
    unittest.main()
