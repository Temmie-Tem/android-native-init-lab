"""Hostile tests for the S20+ P0 direct-PID1 minimal download-request candidate.

The three consumed ACM candidates could not distinguish "/init never ran" from
"the gadget chain failed silently", because their only evidence lived at the end
of a configfs/UDC/ttyGS0 chain. This candidate's evidence is a download-mode
request, so the properties that matter are: the reduction is real and cannot
silently regrow, the request cannot be gated behind the best-effort banner, and
the binary is inert anywhere but as PID1.
"""
import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_min_init.c"
CC = shutil.which("aarch64-linux-gnu-gcc")
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


V4 = load("build_s20plus_g986n_p0_pid1_min_h0")
TEXT = SOURCE.read_text()


def executable_text():
    """Source with comments stripped, so prose cannot satisfy a structural check."""
    without_block = re.sub(r"/\*.*?\*/", "", TEXT, flags=re.S)
    return "\n".join(line.split("//", 1)[0] for line in without_block.splitlines())


class SourceShapeTests(unittest.TestCase):
    def test_pid1_gate_precedes_every_effect(self):
        body = executable_text()
        start = body.index("void _start(void) {", body.index("#else"))
        gate = body.index("p0_getpid() != 1", start)
        for effect in ("p0_banner_best_effort()", "p0_request_download()"):
            self.assertLess(gate, body.index(effect, start), f"{effect} precedes the PID1 gate")

    def test_download_request_is_not_gated_behind_the_banner(self):
        # The banner is best effort. If the request could only be reached on the
        # banner's success path, a failed mknod or open would silently destroy
        # the candidate's only primary evidence - the exact failure mode the ACM
        # chain had.
        body = executable_text()
        start = body.index("void _start(void) {", body.index("#else"))
        tail = body[start:]
        banner = tail.index("p0_banner_best_effort()")
        request = tail.index("p0_request_download()")
        self.assertLess(banner, request)
        between = tail[banner + len("p0_banner_best_effort()"):request]
        for branching in (r"\bif\b", r"\bwhile\b", r"\bfor\b", r"\breturn\b", r"\?", r"&&", r"\|\|"):
            self.assertIsNone(re.search(branching, between), f"branching {branching} between banner and request")

    def test_banner_helper_discards_every_result_except_the_open(self):
        helper = TEXT[TEXT.index("static void p0_banner_best_effort"):]
        helper = helper[: helper.index("\n}\n") + 3]
        # Only the open may be inspected, and only to skip the write.
        self.assertEqual(helper.count("if ("), 1)
        self.assertIn("if (descriptor < 0)", helper)
        for call in ("NR_MKDIRAT", "NR_MKNODAT", "NR_WRITE", "NR_CLOSE"):
            index = helper.index(call)
            # A call may span lines, so look back to the start of the statement.
            statement = max(helper.rfind(";", 0, index), helper.rfind("{", 0, index)) + 1
            self.assertIn("(void)", helper[statement:index], f"{call} result is not discarded")

    def test_banner_writes_once_and_is_not_retried(self):
        helper = TEXT[TEXT.index("static void p0_banner_best_effort"):]
        helper = helper[: helper.index("\n}\n") + 3]
        self.assertEqual(helper.count("NR_WRITE"), 1)
        for looping in ("for (", "while ("):
            self.assertNotIn(looping, helper)

    def test_kmsg_node_needs_no_sysfs_lookup(self):
        # The ACM candidate had to read /sys/class/tty/ttyGS0/dev to learn the
        # major:minor, so its banner depended on a driver having bound first.
        self.assertIn("#define P0_KMSG_MAJOR 1U", TEXT)
        self.assertIn("#define P0_KMSG_MINOR 11U", TEXT)
        self.assertNotIn("/sys/class", executable_text())


class BuilderPolicyTests(unittest.TestCase):
    def test_forbidden_strings_cover_the_whole_acm_chain(self):
        acm_source = (ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_acm_init.c").read_text()
        for marker in ("a600000.dwc3", "/config/usb_gadget", "acm.usb0", "/dev/ttyGS0", "/sys/class/tty/ttyGS0/dev"):
            self.assertIn(marker, acm_source, "the ACM candidate no longer carries this marker")
            self.assertIn(marker.encode(), V4.FORBIDDEN_STRINGS, f"builder does not forbid {marker}")

    def test_forbidden_syscalls_include_exit_group_and_the_acm_surface(self):
        self.assertEqual(V4.FORBIDDEN_RUNTIME_SYSCALLS["exit_group"], 94)
        self.assertEqual(V4.FORBIDDEN_RUNTIME_SYSCALLS["mount"], 40)
        self.assertFalse(set(V4.EXPECTED_RUNTIME_SYSCALLS) & set(V4.FORBIDDEN_RUNTIME_SYSCALLS))

    def test_expected_syscalls_are_exactly_the_declared_surface(self):
        self.assertEqual(
            sorted(V4.EXPECTED_RUNTIME_SYSCALLS.items()),
            sorted({"mknodat": 33, "mkdirat": 34, "openat": 56, "close": 57,
                    "write": 64, "nanosleep": 101, "reboot": 142, "getpid": 172}.items()),
        )

    def test_builder_declares_the_reboot_honestly(self):
        # The one property that differs from the ACM candidate must not be
        # under-declared in the manifest the reviewer reads.
        text = Path(V4.__file__).read_text()
        self.assertIn('"reboot_syscall": True', text)
        self.assertIn('"reboot_target": "download"', text)
        self.assertIn('"dwell_before_reboot": False', text)
        self.assertIn('"usb_gadget_configured": False', text)


class ContractBindingTests(unittest.TestCase):
    SECTION = "## S20+ P0 PID1 Minimal Download-Request F1 candidate"

    def section(self):
        text = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text()
        self.assertEqual(text.count(self.SECTION + "\n"), 1)
        return text.split(self.SECTION + "\n", 1)[1].split("\n## ", 1)[0]

    def prose(self):
        """Section with line wrapping collapsed, so a hard wrap cannot hide a claim."""
        return " ".join(self.section().split())

    def test_section_pins_the_current_source_and_builder(self):
        # Committed inputs, so this drift guard always runs. A source or builder
        # edit that does not re-pin the section fails here rather than reaching
        # a reviewer as a stale identity.
        body = self.section()
        for path in (SOURCE, Path(V4.__file__).resolve()):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertIn(digest, body, f"section does not pin the current {path.name}")

    def test_section_is_not_active_and_declares_the_reboot(self):
        body = self.prose()
        self.assertIn("NOT ACTIVE", body)
        # While the owner still observes the consumed candidate's ACM banner, the
        # section must say so: a run would otherwise record NO_PROOF even on a
        # PID1 that executed and reached Download.
        self.assertIn("OBSERVATION REPLACEMENT PENDING", body)
        self.assertIn("The observation replacement is not done.", body)
        self.assertIn("must not be activated", body)
        # The one property that differs from every previous P0 candidate must be
        # stated in the section, not left to the manifest.
        self.assertIn("issues a reboot syscall and requests a mode transition", body)
        self.assertIn("mandatory resident-Magisk rollback", body)
        self.assertIn("There is no dwell.", body)

    def test_section_inherits_rather_than_restates_the_f1_machinery(self):
        body = self.prose()
        self.assertIn("## P0 PID1 ACM Odin boot-only F1", body)
        self.assertIn("by reference", body)
        self.assertIn("Only the boot partition is a payload", body)


@unittest.skipUnless(TOOLCHAIN, "aarch64 cross toolchain or qemu-aarch64 is unavailable")
class CompiledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory()
        work = Path(cls._temp.name)
        cls.binary = work / "init"
        subprocess.run([CC, *V4.acm.COMPILE_FLAGS, SOURCE, "-o", cls.binary], check=True, timeout=180)
        subprocess.run([STRIP, "--strip-all", cls.binary], check=True, timeout=60)
        cls.objdump = subprocess.run([OBJDUMP, "-d", cls.binary], check=True, capture_output=True, timeout=60).stdout.decode()
        cls.bytes = cls.binary.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def test_selftest_passes_under_qemu(self):
        with tempfile.TemporaryDirectory() as temp:
            selftest = Path(temp) / "selftest"
            subprocess.run([CC, *V4.acm.COMPILE_FLAGS, "-Wno-unused-function",
                            "-DS20PLUS_P0_MIN_SELFTEST_ONLY=1", SOURCE, "-o", selftest], check=True, timeout=180)
            self.assertEqual(subprocess.run([QEMU, selftest], timeout=30).returncode, 0)

    def test_compiled_syscall_surface_is_exact(self):
        for name, number in V4.EXPECTED_RUNTIME_SYSCALLS.items():
            self.assertTrue(V4.acm.syscall_load_present(self.objdump, number), f"missing {name}")
        for name, number in V4.FORBIDDEN_RUNTIME_SYSCALLS.items():
            self.assertFalse(V4.acm.syscall_load_present(self.objdump, number), f"present {name}")

    def test_compiled_binary_proves_the_reduction(self):
        for required in V4.REQUIRED_STRINGS:
            self.assertIn(required, self.bytes)
        for forbidden in V4.FORBIDDEN_STRINGS:
            self.assertNotIn(forbidden, self.bytes)

    def test_binary_is_small_and_reproducible(self):
        self.assertLess(len(self.bytes), 4 * 1024)
        with tempfile.TemporaryDirectory() as temp:
            again = Path(temp) / "again"
            subprocess.run([CC, *V4.acm.COMPILE_FLAGS, SOURCE, "-o", again], check=True, timeout=180)
            subprocess.run([STRIP, "--strip-all", again], check=True, timeout=60)
            self.assertEqual(again.read_bytes(), self.bytes)

    def test_binary_is_inert_when_it_is_not_pid1(self):
        # Executed anywhere but as PID1 it must park, never reach the reboot.
        # A timeout here is the pass condition; an exit is not.
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([QEMU, self.binary], capture_output=True, timeout=5)


if __name__ == "__main__":
    unittest.main()
