"""Host-only P3.45 child-boundary source, seam and ash smoke tests."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s22plus_fyg8_p345_readonly_child as child


HARNESS_PREFIX = r'''
#include <stddef.h>
#include <stdint.h>

static long syscall6(long nr, long a0, long a1, long a2,
                     long a3, long a4, long a5) {
    (void)a0; (void)a1; (void)a2; (void)a3; (void)a4; (void)a5;
    /* A native fixture deliberately lacks the target namespace capability. */
    return nr == 97 ? -38 : -1;
}
static long sys_openat(const char *path, int flags, unsigned int mode) {
    (void)path; (void)flags; (void)mode; return -2;
}
static long sys_close(int fd) { (void)fd; return 0; }
static long sys_read(int fd, void *buffer, size_t size) {
    (void)fd; (void)buffer; (void)size; return 0;
}
static long sys_write(int fd, const void *buffer, size_t size) {
    (void)fd; (void)buffer; (void)size; return -1;
}
static long sys_mount(const char *source, const char *target,
                      const char *fstype, unsigned long flags,
                      const char *data) {
    (void)source; (void)target; (void)fstype; (void)flags; (void)data;
    return -1;
}
'''
HARNESS_MAIN = r'''
int main(void) {
    return p345_enter_readonly_child() == 0 ? 2 : 0;
}
'''

HOST_FILTER_PREFIX = r'''
#include <sys/syscall.h>
#include <unistd.h>
static long syscall6(long nr, long a0, long a1, long a2,
                     long a3, long a4, long a5) {
    return syscall(nr, a0, a1, a2, a3, a4, a5);
}
static long sys_openat(const char *path, int flags, unsigned int mode) {
    (void)path; (void)flags; (void)mode; return -2;
}
static long sys_close(int fd) { (void)fd; return 0; }
static long sys_read(int fd, void *buffer, size_t size) {
    (void)fd; (void)buffer; (void)size; return 0;
}
static long sys_write(int fd, const void *buffer, size_t size) {
    (void)fd; (void)buffer; (void)size; return -1;
}
static long sys_mount(const char *source, const char *target,
                      const char *fstype, unsigned long flags,
                      const char *data) {
    (void)source; (void)target; (void)fstype; (void)flags; (void)data;
    return -1;
}
'''
HOST_FILTER_MAIN = r'''
int main(void) {
    (void)&p345_enter_readonly_child;
    if (p345_prctl(P345_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) return 10;
    if (p345_install_filter() != 0) return 11;
    long readable = syscall6(
        P345_NR_OPENAT, P345_AT_FDCWD, (long)(uintptr_t)"/proc/self/cmdline",
        P345_O_RDONLY, 0, 0, 0);
    if (readable < 0) return 12;
    long denied = syscall6(
        P345_NR_OPENAT, P345_AT_FDCWD, (long)(uintptr_t)"/tmp/p345-create",
        P345_O_WRONLY | P345_O_CREAT, 0600, 0, 0);
    if (denied != -P345_EPERM) return 13;
    return 0;
}
'''


class P345ReadonlyChildTests(unittest.TestCase):
    def test_audit_is_fixed_h0_and_finite(self):
        metadata = child.audit()
        self.assertEqual(metadata["api"], "p345_enter_readonly_child(void)")
        self.assertTrue(metadata["fixed_no_input"])
        self.assertTrue(metadata["host_only"])
        self.assertFalse(metadata["device_contact"])
        self.assertFalse(metadata["runtime_behavior_unchanged"])
        self.assertFalse(metadata["validator_only"])
        self.assertFalse(metadata["f1_ready"])
        self.assertEqual(metadata["closes_inherited_fds_above"], 2)
        self.assertEqual(metadata["seccomp_default"], "ERRNO(EPERM)")
        self.assertEqual(metadata["unsupported_syscall_policy"], "fail-closed-before-ash")
        self.assertEqual(metadata["process_view"], [])
        self.assertEqual(
            [item["view"] for item in metadata["snapshot_files"]],
            [
                "/proc/meminfo",
                "/proc/cpuinfo",
                "/proc/uptime",
                "/proc/version",
                "/proc/mounts",
                "/sys/class/udc/a600000.dwc3/state",
            ],
        )
        self.assertIn("processes", metadata["catalog"])
        self.assertIn("/proc/*/fd", metadata["forbidden_view_entries"])
        self.assertIn("network", metadata["denied_categories"])
        self.assertIn(
            "clone-no-namespace-flags-process-limit-bound",
            metadata["allowed_syscalls"],
        )

    def test_fragment_is_fixed_no_input_and_contains_boundary_controls(self):
        source = child.child_source()
        self.assertEqual(source, child.CHILD_SOURCE)
        self.assertEqual(source.count(b"p345_enter_readonly_child(void)"), 1)
        for marker in (
            b"P345_NR_UNSHARE",
            b"P345_NR_CLOSE_RANGE",
            b"P345_NR_SETGROUPS",
            b"P345_NR_SETRESUID",
            b"P345_NR_SETRESGID",
            b"P345_NR_CAPSET",
            b"P345_PR_SET_NO_NEW_PRIVS",
            b"P345_NR_SECCOMP",
            b"P345_SECCOMP_RET_ERRNO",
            b"P345_O_WRITE_MASK",
            b"P345_BUSYBOX_SOURCE \"/bin/busybox\"",
            b"/proc/meminfo",
            b"/proc/cpuinfo",
            b"/proc/uptime",
            b"/proc/version",
            b"/proc/mounts",
            b"/sys/class/udc/a600000.dwc3/state",
        ):
            self.assertIn(marker, source)
        self.assertNotIn(b"/proc/*/fd", source)
        self.assertNotIn(b"/proc/kcore", source)

    def test_fixed_hook_is_after_tty_close_and_before_argv(self):
        original = (
            b"        (void)sys_close(tty_fd);\n"
            b"        char *const argv[] = {"
        )
        transformed = child.integrate_child_source(b"prefix\n" + original + b"suffix")
        self.assertEqual(transformed.count(child.P345_INTEGRATION_HOOK), 1)
        self.assertLess(
            transformed.index(b"sys_close(tty_fd)"),
            transformed.index(b"p345_enter_readonly_child()"),
        )
        self.assertLess(
            transformed.index(b"p345_enter_readonly_child()"),
            transformed.index(b"char *const argv[]"),
        )
        self.assertEqual(child.validate_integration(transformed), transformed)
        with self.assertRaises(child.P345ChildSourceError):
            child.integrate_child_source(transformed)
        with self.assertRaises(child.P345ChildSourceError):
            child.integrate_child_source(b"tty close only")
        with self.assertRaises(child.P345ChildSourceError):
            child.validate_integration(original)

    def test_native_fixture_fails_closed_before_ash_when_unshare_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "p345_fixture.c"
            source.write_text(HARNESS_PREFIX + child.child_source().decode("ascii") + HARNESS_MAIN)
            executable = root / "p345_fixture"
            build = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    str(source),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, timeout=2)
            self.assertEqual(result.returncode, 0)

    def test_native_seccomp_filter_rejects_write_open_flags(self):
        """Exercise the filter itself with host syscall numbers only."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "p345_filter_fixture.c"
            source.write_text(
                "#include <stddef.h>\n#include <stdint.h>\n"
                + HOST_FILTER_PREFIX
                + child.child_source().decode("ascii")
                + HOST_FILTER_MAIN
            )
            executable = root / "p345_filter_fixture"
            definitions = [
                "-DP345_AUDIT_ARCH=0xc000003eU",
                "-DP345_NR_SECCOMP=317",
                "-DP345_NR_PRCTL=157",
                "-DP345_NR_OPENAT=257",
                "-DP345_NR_READ=0",
                "-DP345_NR_WRITE=1",
                "-DP345_NR_CLOSE=3",
                "-DP345_NR_EXIT=60",
                "-DP345_NR_EXIT_GROUP=231",
            ]
            build = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-D_GNU_SOURCE",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    *definitions,
                    str(source),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, timeout=2)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_arm64_object_compiles_when_toolchain_is_available(self):
        compiler = shutil.which("aarch64-linux-gnu-gcc")
        if compiler is None:
            self.skipTest("aarch64-linux-gnu-gcc is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "p345_fixture.c"
            source.write_text(HARNESS_PREFIX + child.child_source().decode("ascii") + HARNESS_MAIN)
            object_file = root / "p345_fixture.o"
            build = subprocess.run(
                [
                    compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    "-c",
                    str(source),
                    "-o",
                    str(object_file),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            description = subprocess.check_output(["file", str(object_file)], text=True)
            self.assertIn("ARM aarch64", description)

    def test_native_busybox_ash_pipeline_substitution_and_nonzero_exit(self):
        busybox = Path("/bin/busybox")
        if not busybox.exists():
            self.skipTest("static BusyBox is unavailable")
        pipeline = subprocess.run(
            [str(busybox), "ash", "-c", "printf '%s\\n' alpha beta | tr a-z A-Z; printf '<%s>\\n' \"$(printf nested)\""],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(pipeline.returncode, 0, pipeline.stderr)
        self.assertEqual(pipeline.stdout, "ALPHA\nBETA\n<nested>\n")
        failed = subprocess.run(
            [str(busybox), "ash", "-c", "false; exit $?"],
            capture_output=True,
            check=False,
        )
        self.assertEqual(failed.returncode, 1)

    def test_native_busybox_readonly_directory_rejects_creation(self):
        busybox = Path("/bin/busybox")
        if not busybox.exists():
            self.skipTest("static BusyBox is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            view = Path(directory) / "view"
            view.mkdir()
            view.chmod(stat.S_IRUSR | stat.S_IXUSR)
            try:
                attempted = subprocess.run(
                    [str(busybox), "ash", "-c", ": > blocked; printf should-not-run"],
                    cwd=view,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(attempted.returncode, 0)
                self.assertFalse((view / "blocked").exists())
            finally:
                view.chmod(stat.S_IRWXU)


if __name__ == "__main__":
    unittest.main()
