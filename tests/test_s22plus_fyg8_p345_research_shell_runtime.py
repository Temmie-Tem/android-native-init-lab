from __future__ import annotations

import os
from pathlib import Path
import hashlib
import hmac
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p344_open_read_branch_runtime as p344  # noqa: E402
import s22plus_fyg8_p345_readonly_child as child  # noqa: E402
import s22plus_fyg8_p345_research_shell_runtime as runtime  # noqa: E402


class P345ResearchShellRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_path = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p344/"
            "stock-candidate-build-v1-20260905-01/stock-sources/"
            "s22plus_fyg8_p290_e3_runtime.inc.c"
        )
        self.source = self.source_path.read_bytes()
        self.key = p344.predecessor._materialized_key(self.source)
        self.nonce = bytes(range(1, 33))

    def test_wire_constants_and_cancel_tag_are_exactly_bound(self) -> None:
        self.assertEqual(runtime.P345_RUN_ID_HEX, "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a")
        self.assertEqual(runtime.P335_RUN_ID, runtime.P345_RUN_ID)
        for prefix in (
            "P328", "P329", "P330", "P331", "P332", "P333", "P334",
            "P335", "P336", "P337", "P338", "P339", "P340", "P341",
            "P342", "P343", "P344",
        ):
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID"), runtime.P345_RUN_ID)
            self.assertEqual(
                getattr(runtime, f"{prefix}_RUN_ID_HEX"), runtime.P345_RUN_ID_HEX
            )
        self.assertEqual(
            runtime.P344_PREDECESSOR_RUN_ID_HEX,
            p344.P344_RUN_ID_HEX,
        )
        self.assertEqual(runtime.FRAME_CANCEL, 5)
        self.assertEqual(runtime.FRAME_CANCEL_ACK, 0x88)
        self.assertEqual(runtime.P345_CANCEL_SEQUENCE, 4)
        self.assertEqual(runtime.P345_CANCELLED_FLAG, 0x08)
        self.assertEqual(runtime.P345_CANCEL_PAYLOAD_SIZE, 32)
        self.assertEqual(
            runtime.AUTH_DOMAIN_CANCEL,
            b"S22PLUS-FYG8-P345-AUTH-CANCEL-v1",
        )
        expected = hmac.new(
            self.key,
            runtime.AUTH_DOMAIN_CANCEL
            + runtime.P345_RUN_ID
            + self.nonce
            + struct.pack("<I", 4),
            hashlib.sha256,
        ).digest()
        self.assertEqual(runtime.cancel_tag(self.key, self.nonce), expected)
        self.assertEqual(
            runtime.cancel_tag(self.key, runtime.P345_RUN_ID, self.nonce), expected
        )
        frame = runtime.encode_cancel_frame(self.key, self.nonce)
        self.assertEqual(len(frame), 48)
        self.assertEqual(runtime.HEADER.unpack(frame[:16])[1:5], (1, 5, 32, 4))
        for bad in (
            lambda: runtime.cancel_tag(self.key, b"\0" * 32),
            lambda: runtime.cancel_tag(self.key, self.nonce, sequence=3),
            lambda: runtime.cancel_tag(self.key, b"\0" * 32),
        ):
            with self.assertRaises(runtime.RuntimeIdentityError):
                bad()

    def test_ack_and_completion_preserve_command_outcome(self) -> None:
        ack0 = runtime.encode_frame(
            runtime.FRAME_CANCEL_ACK,
            4,
            struct.pack("<I", runtime.P345_CANCEL_STATUS_CONSUMED),
        )
        ack1 = runtime.encode_frame(
            runtime.FRAME_CANCEL_ACK,
            4,
            struct.pack("<I", runtime.P345_CANCEL_STATUS_ALREADY_COMPLETED),
        )
        self.assertTrue(runtime.decode_cancel_ack(ack0)["active"])
        self.assertTrue(runtime.decode_cancel_ack(ack1)["already_completed"])

        completed = runtime.EXIT.pack(0, 0, 0, 0, 7)
        self.assertEqual(
            runtime.completion_state(completed, 0)["outcome"], "completed"
        )
        self.assertEqual(
            runtime.completion_state(completed, 0, ack1)["outcome"], "completed"
        )
        failed = runtime.EXIT.pack(0, 17, 0, 3, 8)
        self.assertEqual(
            runtime.completion_state(failed, 3)["outcome"], "command-failed"
        )
        timed_out = runtime.EXIT.pack(1, -1, 9, 0, 9)
        self.assertEqual(
            runtime.completion_state(timed_out, 0)["outcome"], "timeout"
        )
        truncated = runtime.EXIT.pack(2, 0, 0, 4, 10)
        self.assertEqual(
            runtime.completion_state(truncated, 4)["outcome"], "truncated"
        )
        cancelled = runtime.EXIT.pack(8, 7, 0, 4, 11)
        value = runtime.completion_state(cancelled, 4, ack0)
        self.assertEqual(value["outcome"], "cancelled")
        self.assertTrue(value["terminal_proved"])
        self.assertFalse(value["transport_uncertain"])
        with self.assertRaises(runtime.RuntimeIdentityError):
            runtime.completion_state(cancelled, 4)
        with self.assertRaises(runtime.RuntimeIdentityError):
            runtime.decode_cancel_ack(ack0[:-1] + b"\1")

    def test_helper_transform_preserves_fixed_commands_and_adds_cancel_path(self) -> None:
        fixture_child = runtime.fixture_child_source()
        helper = runtime.build_helper(fixture_child)
        self.assertIn(b"#define P345_FRAME_CANCEL 5U", helper)
        self.assertIn(b"#define P345_FRAME_CANCEL_ACK 0x88U", helper)
        self.assertIn(b"p345_auth_domain_cancel", helper)
        self.assertIn(b"p345_enter_readonly_child(void)", helper)
        self.assertIn(b"p345_try_read_cancel", helper)
        self.assertIn(b"p345_framed_console(", helper)
        self.assertIn(b"p345_exec_command(", helper)
        self.assertIn(b"sequence == 4U", helper)
        self.assertIn(b"p345_command_valid", helper)
        self.assertNotIn(b"p328_exec_command(", helper)
        self.assertNotIn(b"p335_command_valid(", helper)
        self.assertNotIn(b"P345_CANCEL_ACK_FLAG", helper)

        transformed = runtime.transform_runtime_include(
            self.source, self.key, child=fixture_child
        )
        receipt = runtime.validate_transform(
            self.source,
            transformed,
            auth_key_sha256=runtime.auth_key_sha256(self.key),
            child=fixture_child,
        )
        self.assertEqual(
            receipt["changed_anchors"],
            [
                "p344_child_drain_deadline",
                "p345_readonly_child_sequence_4",
                "p345_authenticated_cancel",
            ],
        )
        self.assertEqual(receipt["predecessor_run_id"], p344.P344_RUN_ID_HEX)
        self.assertEqual(receipt["run_id_hex"], runtime.P345_RUN_ID_HEX)
        self.assertNotIn(runtime.P344_COMMAND, transformed)
        self.assertIn(runtime._c_string(runtime.P345_COMMAND), transformed)
        self.assertNotIn(p344.P344_ENTRY, transformed)
        self.assertIn(runtime.P345_ENTRY, transformed)
        self.assertEqual(transformed.count(runtime.P345_ENTRY), 1)
        with self.assertRaises(runtime.RuntimeIdentityError):
            runtime.validate_transform(
                self.source,
                transformed[:-1] + b"0",
                auth_key_sha256=runtime.auth_key_sha256(self.key),
                child=fixture_child,
            )

    def test_actual_child_source_and_setup_failure_diagnostic_are_bound(self) -> None:
        self.assertEqual(runtime.child_source(), child.CHILD_SOURCE)
        helper = runtime.build_helper()
        self.assertEqual(helper.count(b"p345_enter_readonly_child(void)"), 1)
        self.assertEqual(helper.count(b"p345_enter_readonly_child()"), 1)
        self.assertEqual(helper.count(b"P345_READONLY_CHILD_SETUP_FAILED"), 1)
        start, end = runtime._function_slice(
            helper, b"static long p345_exec_command("
        )
        body = helper[start:end]
        self.assertLess(
            body.index(b"sys_close(tty_fd)"),
            body.index(b"p345_enter_readonly_child()"),
        )
        self.assertLess(
            body.index(b"p345_enter_readonly_child()"),
            body.index(b"char *const argv[]"),
        )
        self.assertIn(b"p345_report_child_setup_failure(child_setup)", body)
        self.assertEqual(runtime.audit_binding()["child_source"], child.SOURCE_IDENTITY)
        self.assertEqual(runtime.SOURCE_IDENTITY, runtime.P344_SOURCE_IDENTITY)

    def test_actual_child_transform_aarch64_syntax_compiles(self) -> None:
        compiler = shutil.which("aarch64-linux-gnu-gcc")
        if compiler is None:
            self.skipTest("aarch64-linux-gnu-gcc is unavailable")
        transformed = runtime.transform_runtime_include(self.source, self.key)
        source_root = self.source_path.parent
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            for path in source_root.iterdir():
                if not path.is_file():
                    continue
                target = output_root / path.name
                shutil.copyfile(path, target)
                target.chmod(0o600)
            (output_root / "s22plus_fyg8_p290_e3_runtime.inc.c").write_bytes(
                transformed
            )
            run_id_define = "{" + ",".join(
                f"0x{value:02x}" for value in runtime.P345_RUN_ID
            ) + "}"
            command = [
                compiler,
                "-nostdlib",
                "-ffreestanding",
                "-fno-builtin",
                "-fno-stack-protector",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fsyntax-only",
                "-DS22PLUS_FYG8_P233_PROFILE=3",
                f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={run_id_define}",
                "-I",
                str(output_root),
                "-I",
                str(ROOT / "workspace/public/src/native-init"),
                str(output_root / "s22plus_fyg8_p290_e3_runtime.c"),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env={
                    **os.environ,
                    "LANG": "C",
                    "LC_ALL": "C",
                    "SOURCE_DATE_EPOCH": "0",
                },
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_console_accepts_late_cancel_after_normal_seq4_exit(self) -> None:
        helper = runtime.build_helper(runtime.fixture_child_source())
        names = (
            "p345_command_valid",
            "p345_cancel_tag_valid",
            "p345_write_cancel_ack",
            "p345_framed_console",
        )
        functions = []
        for name in names:
            declaration = f"static int {name}(".encode("ascii")
            if name in {"p345_write_cancel_ack", "p345_framed_console"}:
                declaration = f"static long {name}(".encode("ascii")
            start, end = runtime._function_slice(helper, declaration)
            functions.append(helper[start:end].decode("ascii"))

        prefix = r"""
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define EAGAIN 11
#define EIO 5
#define P260_EPROTO 71
#define P260_EINTR 4
#define P328_MAGIC_0 0x53U
#define P328_MAGIC_1 0x33U
#define P328_MAGIC_2 0x32U
#define P328_MAGIC_3 0x38U
#define P328_FRAME_VERSION 1U
#define P328_FRAME_OPEN 1U
#define P328_FRAME_EXEC 2U
#define P328_FRAME_CLOSE 3U
#define P328_FRAME_READY 0x81U
#define P328_FRAME_DATA 0x82U
#define P328_FRAME_EXIT 0x83U
#define P328_FRAME_DONE 0x84U
#define P328_FRAME_CHALLENGE 0x85U
#define P328_FRAME_AUTH 0x86U
#define P328_FRAME_BOOT_ID 0x87U
#define P335_FRAME_BOOT_ID 0x87U
#define P328_FRAME_CANCEL 5U
#define P328_FRAME_CANCEL_ACK 0x88U
#define P345_FRAME_CANCEL 5U
#define P345_FRAME_CANCEL_ACK 0x88U
#define P345_CANCEL_SEQUENCE 4U
#define P345_CANCEL_STATUS_CONSUMED 0U
#define P345_CANCEL_STATUS_ALREADY_COMPLETED 1U
#define P345_CANCEL_STATUS_NONE 0xffU
#define P345_CANCEL_PAYLOAD_SIZE 32U
#define P345_CANCEL_NONE 0U
#define P345_CANCEL_PENDING 1U
#define P345_CANCEL_VALID 2U
#define P345_CANCELLED_FLAG 0x08U
#define P328_HEADER_SIZE 16U
#define P328_MAX_PAYLOAD 1055U
#define P328_MAX_COMMAND 1023U
#define P328_AUTH_TAG_SIZE 32U
#define P328_NONCE_SIZE 32U
#define P335_BOOT_ID_SIZE 16U
#define P335_BOOT_ID_SEQUENCE 2U
#define P335_COMMANDS_PER_SESSION 3U
#define P339_OPEN_READ_BRANCH_HEADER_READ_ERRNO 0U
#define P339_OPEN_READ_BRANCH_HEADER_VALIDATION 1U
#define P339_OPEN_READ_BRANCH_OPEN_SEMANTIC 4U
#define P339_DIAG_OPEN_READ_BRANCH 0x3390U
#define P339_DIAG_OPEN_HEADER_WORD_0 0x3391U
#define P339_DIAG_OPEN_HEADER_WORD_1 0x3392U
#define P339_DIAG_OPEN_HEADER_WORD_2 0x3393U
#define P339_DIAG_OPEN_HEADER_WORD_3 0x3394U
#define P330_DIAG_OPEN_PARSED 0x3301U
#define P330_DIAG_RNG 0x3302U
#define P330_RNG_EAGAIN_RETRY_LIMIT 3U
#define S22PLUS_P318_BANNER_WRITTEN 1
static const uint8_t p328_run_id_bytes[16] = {0};
static const char p328_auth_domain_open[] = "open";
static const char p328_auth_domain_ready[] = "ready";
static const char p328_auth_domain_exec[] = "exec";
static const char p328_auth_domain_close[] = "close";
static const char p335_auth_domain_boot_id[] = "boot";
static const char p345_auth_domain_cancel[] = "cancel";
static const char p335_command_1[] = "/bin/busybox id";
static const char p335_command_3[] =
    "/bin/busybox echo P328-NONCE c345f1e0a90b5e6d7c8a9b0c1d2e3f0a";
struct s22plus_p318_banner_result { int outcome; };
struct input_frame {
    uint8_t type;
    uint32_t sequence;
    uint16_t length;
    uint8_t payload[P328_MAX_PAYLOAD];
};
static struct input_frame inputs[7];
static size_t input_count, input_index;
static uint8_t output_types[32];
static uint32_t output_sequences[32];
static uint32_t output_ack_status;
static size_t output_count;
static long p328_read_frame(
    int fd, uint8_t *type, uint32_t *sequence, uint8_t *payload,
    uint16_t *length, uint8_t *header, uint8_t *branch,
    uint8_t *open_seen) {
    (void)fd;
    if (input_index >= input_count) return -EIO;
    struct input_frame *frame = &inputs[input_index++];
    *type = frame->type;
    *sequence = frame->sequence;
    *length = frame->length;
    memcpy(payload, frame->payload, frame->length);
    if (header != NULL) memset(header, 0, P328_HEADER_SIZE);
    if (branch != NULL) *branch = P339_OPEN_READ_BRANCH_HEADER_READ_ERRNO;
    if (open_seen != NULL) *open_seen = 1U;
    return 0;
}
static long p330_write_diagnostic(int fd, uint32_t stage, int32_t code) {
    (void)fd; (void)stage; (void)code; return 0;
}
static struct s22plus_p318_banner_result
s22plus_p318_banner_attempt(int fd) {
    (void)fd;
    return (struct s22plus_p318_banner_result){S22PLUS_P318_BANNER_WRITTEN};
}
static long p328_getrandom_nonce(uint8_t nonce[P328_NONCE_SIZE]) {
    for (size_t index = 0; index < P328_NONCE_SIZE; ++index)
        nonce[index] = (uint8_t)(index + 1U);
    return 0;
}
static void p282_poll_delay(void) {}
static void p328_hmac_message(
    uint8_t digest[P328_AUTH_TAG_SIZE], const char *domain,
    size_t domain_size, const uint8_t *run_id, const uint8_t *nonce,
    uint32_t sequence, int include_sequence, const uint8_t *command,
    size_t command_size) {
    (void)domain; (void)domain_size; (void)run_id; (void)nonce;
    (void)sequence; (void)include_sequence; (void)command;
    (void)command_size;
    memset(digest, 0, P328_AUTH_TAG_SIZE);
}
static int p328_constant_time_equal(
    const uint8_t *left, const uint8_t *right, size_t size) {
    (void)left; (void)right; (void)size; return 1;
}
static int p260_bytes_equal(
    const char *left, const char *right, size_t size) {
    return memcmp(left, right, size) == 0;
}
static uint32_t p328_load_le32(const uint8_t *value) {
    return (uint32_t)value[0] | ((uint32_t)value[1] << 8)
        | ((uint32_t)value[2] << 16) | ((uint32_t)value[3] << 24);
}
static void p328_store_le32(uint8_t *value, uint32_t input) {
    value[0] = (uint8_t)input; value[1] = (uint8_t)(input >> 8);
    value[2] = (uint8_t)(input >> 16); value[3] = (uint8_t)(input >> 24);
}
static long p328_write_frame(
    int fd, uint8_t type, uint32_t sequence,
    const uint8_t *payload, uint16_t length) {
    (void)fd;
    if (output_count < sizeof(output_types)) {
        output_types[output_count] = type;
        output_sequences[output_count] = sequence;
        ++output_count;
    }
    if (type == P345_FRAME_CANCEL_ACK && length == 4U)
        output_ack_status = p328_load_le32(payload);
    return 0;
}
static long p345_exec_command(
    int fd, uint32_t sequence, const uint8_t *input,
    uint16_t input_length, const uint8_t nonce[P328_NONCE_SIZE],
    uint8_t *cancel_status) {
    (void)fd; (void)input; (void)input_length; (void)nonce;
    if (cancel_status != NULL) *cancel_status = P345_CANCEL_STATUS_NONE;
    uint8_t exit_payload[24] = {0};
    return p328_write_frame(
        fd, P328_FRAME_EXIT, sequence, exit_payload,
        (uint16_t)sizeof(exit_payload));
}
"""
        main = r"""
static void add_input(
    size_t index, uint8_t type, uint32_t sequence,
    const uint8_t *payload, uint16_t length) {
    inputs[index].type = type;
    inputs[index].sequence = sequence;
    inputs[index].length = length;
    memcpy(inputs[index].payload, payload, length);
}
int main(void) {
    uint8_t open_payload[16] = {0};
    uint8_t tag[32] = {0};
    uint8_t exec3[32 + sizeof(p335_command_1) - 1U];
    uint8_t exec4[32 + 11U];
    uint8_t exec5[32 + sizeof(p335_command_3) - 1U];
    uint8_t boot_id[16] = {0};
    memcpy(exec3 + 32, p335_command_1, sizeof(p335_command_1) - 1U);
    memcpy(exec4 + 32, "printf p345", 11U);
    memcpy(exec5 + 32, p335_command_3, sizeof(p335_command_3) - 1U);
    memset(exec3, 0, 32); memset(exec5, 0, 32);
    add_input(0, P328_FRAME_OPEN, 0, open_payload, sizeof(open_payload));
    add_input(1, P328_FRAME_AUTH, 1, tag, sizeof(tag));
    add_input(2, P328_FRAME_EXEC, 3, exec3, sizeof(exec3));
    add_input(3, P328_FRAME_EXEC, 4, exec4, sizeof(exec4));
    add_input(4, P345_FRAME_CANCEL, 4, tag, sizeof(tag));
    add_input(5, P328_FRAME_EXEC, 5, exec5, sizeof(exec5));
    add_input(6, P328_FRAME_CLOSE, 6, tag, sizeof(tag));
    input_count = 7;
    uint8_t open_seen = 0;
    long result = p345_framed_console(5, boot_id, &open_seen);
    long seq4_exit = -1, ack = -1, seq5_exit = -1;
    for (size_t index = 0; index < output_count; ++index) {
        if (output_types[index] == P328_FRAME_EXIT
            && output_sequences[index] == 4U && seq4_exit < 0)
            seq4_exit = (long)index;
        if (output_types[index] == P345_FRAME_CANCEL_ACK)
            ack = (long)index;
        if (output_types[index] == P328_FRAME_EXIT
            && output_sequences[index] == 5U && seq5_exit < 0)
            seq5_exit = (long)index;
    }
    return result == 0 && open_seen == 1U && seq4_exit >= 0
        && ack == seq4_exit + 1L && output_ack_status == 1U
        && seq5_exit == ack + 1L ? 0 : 20;
}
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "console_fixture.c"
            source.write_text(prefix + "\n".join(functions) + main)
            native = root / "console_fixture"
            build = subprocess.run(
                [
                    "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-function", "-O2", str(source), "-o", str(native),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run(
                [str(native)], capture_output=True, text=True, timeout=2
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_actual_cancel_kills_and_reaps_without_fabricating_status(self) -> None:
        helper = runtime.build_helper(runtime.fixture_child_source())
        names = (
            "p345_report_child_setup_failure",
            "p345_command_valid",
            "p345_cancel_tag_valid",
            "p345_try_read_cancel",
            "p345_write_cancel_ack",
            "p345_enter_readonly_child",
            "p345_exec_command",
        )
        functions = []
        for name in names:
            for kind in ("int", "long", "void"):
                declaration = f"static {kind} {name}(".encode("ascii")
                try:
                    start, end = runtime._function_slice(helper, declaration)
                except runtime.RuntimeIdentityError:
                    continue
                functions.append(helper[start:end].decode("ascii"))
                break
            else:
                self.fail(f"missing transformed C function {name}")

        prefix = r"""
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#define EAGAIN 11
#define EIO 5
#define EINVAL 22
#define ETIMEDOUT 110
#define SIGKILL 9
#define WNOHANG 1
#define O_CLOEXEC 0U
#define O_NONBLOCK 0U
#define O_RDONLY 0U
#define P260_EPROTO 71
#define P260_EINTR 4
#define P328_ECHILD 10
#define P328_MAX_COMMAND 1023U
#define P328_MAX_PAYLOAD 1055U
#define P328_MAX_OUTPUT 131072U
#define P328_COMMAND_TIMEOUT_SEC 15LL
#define P328_HEADER_SIZE 16U
#define P328_AUTH_TAG_SIZE 32U
#define P328_NONCE_SIZE 32U
#define P328_FRAME_VERSION 1U
#define P328_MAGIC_0 0x53U
#define P328_MAGIC_1 0x33U
#define P328_MAGIC_2 0x32U
#define P328_MAGIC_3 0x38U
#define P328_FRAME_DATA 0x82U
#define P328_FRAME_EXIT 0x83U
#define P328_FRAME_CANCEL 5U
#define P328_FRAME_CANCEL_ACK 0x88U
#define P345_FRAME_CANCEL 5U
#define P345_FRAME_CANCEL_ACK 0x88U
#define P345_CANCEL_SEQUENCE 4U
#define P345_CANCEL_STATUS_CONSUMED 0U
#define P345_CANCEL_STATUS_ALREADY_COMPLETED 1U
#define P345_CANCEL_STATUS_NONE 0xffU
#define P345_CANCEL_PAYLOAD_SIZE 32U
#define P345_CANCEL_NONE 0U
#define P345_CANCEL_PENDING 1U
#define P345_CANCEL_VALID 2U
#define P345_CANCELLED_FLAG 0x08U
#define P328_FLAG_TIMEOUT 0x01U
#define P328_FLAG_TRUNCATED 0x02U
#define P328_FLAG_EXEC_FAILURE 0x04U
static const uint8_t p328_run_id_bytes[16] = {0};
static const char p345_auth_domain_cancel[] =
    "S22PLUS-FYG8-P345-AUTH-CANCEL-v1";
static const char p335_command_1[] = "/bin/busybox id";
static const char p335_command_3[] =
    "/bin/busybox echo P328-NONCE c345f1e0a90b5e6d7c8a9b0c1d2e3f0a";
struct timespec64 { int64_t tv_sec, tv_nsec; };
static long ticks;
static int partial_mode, direct_killed, killed;
static uint8_t cancel_input[64];
static size_t cancel_offset, cancel_length;
static int frame_count, frame_types[4], exit_flags, exit_code, exit_signal;
static uint32_t ack_status;
static long p282_deadline_after(long seconds, struct timespec64 *deadline) {
    deadline->tv_sec = ticks + seconds;
    deadline->tv_nsec = 0;
    return 0;
}
static int p282_deadline_expired(const struct timespec64 *deadline) {
    return ticks >= deadline->tv_sec;
}
static void p282_poll_delay(void) { ++ticks; }
static long p241_clock_gettime(struct timespec64 *value) {
    value->tv_sec = ticks;
    value->tv_nsec = 0;
    return 0;
}
static long sys_pipe2(int fds[2], int flags) {
    (void)flags; fds[0] = 3; fds[1] = 4; return 0;
}
static long sys_close(int fd) { (void)fd; return 0; }
static long sys_write(int fd, const void *buffer, size_t size) {
    (void)fd; (void)buffer; return (long)size;
}
static long sys_clone(void) { return 42; }
static long sys_kill(long pid, int sig) {
    (void)sig;
    if (pid == 42) direct_killed = 1;
    if (pid < 0) killed = 1;
    return 0;
}
static long sys_wait4(long pid, int *status, int options) {
    (void)status; (void)options;
    if (pid < 0) return -P328_ECHILD;
    return partial_mode || killed ? pid : 0;
}
static long sys_read(int fd, void *buffer, size_t size) {
    if (fd != 5) return -EAGAIN;
    if (cancel_offset == cancel_length) return -EAGAIN;
    size_t remaining = cancel_length - cancel_offset;
    if (size > remaining) size = remaining;
    memcpy(buffer, cancel_input + cancel_offset, size);
    cancel_offset += size;
    return (long)size;
}
static long sys_openat(const char *path, int flags, int mode) {
    (void)path; (void)flags; (void)mode; return 0;
}
static long sys_execve(const char *path, char *const argv[], char *const envp[]) {
    (void)path; (void)argv; (void)envp; return -1;
}
static long sys_dup3(int source, int target, int flags) {
    (void)source; (void)flags; return target;
}
static long syscall6(long a, long b, long c, long d, long e, long f, long g) {
    (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; (void)g; return 0;
}
static void sys_exit(int code) { (void)code; }
static long p260_write_all(int fd, const char *value, size_t size, long timeout) {
    (void)fd; (void)value; (void)size; (void)timeout; return 0;
}
static int p260_bytes_equal(const char *left, const char *right, size_t size) {
    return memcmp(left, right, size) == 0;
}
static int p328_constant_time_equal(
    const uint8_t *left, const uint8_t *right, size_t size) {
    return memcmp(left, right, size) == 0;
}
static void p328_hmac_message(
    uint8_t digest[32], const char *domain, size_t domain_size,
    const uint8_t *run_id, const uint8_t *nonce, uint32_t sequence,
    int include_sequence, const uint8_t *command, size_t command_size) {
    (void)domain; (void)domain_size; (void)run_id; (void)nonce;
    (void)sequence; (void)include_sequence; (void)command; (void)command_size;
    memset(digest, 0xaa, 32);
}
static uint16_t p328_load_le16(const uint8_t *value) {
    return (uint16_t)value[0] | ((uint16_t)value[1] << 8);
}
static uint32_t p328_load_le32(const uint8_t *value) {
    return (uint32_t)value[0] | ((uint32_t)value[1] << 8)
        | ((uint32_t)value[2] << 16) | ((uint32_t)value[3] << 24);
}
static void p328_store_le32(uint8_t *value, uint32_t input) {
    value[0] = (uint8_t)input; value[1] = (uint8_t)(input >> 8);
    value[2] = (uint8_t)(input >> 16); value[3] = (uint8_t)(input >> 24);
}
static void p328_store_le64(uint8_t *value, uint64_t input) {
    for (int index = 0; index < 8; ++index)
        value[index] = (uint8_t)(input >> (8 * index));
}
static uint32_t p328_frame_crc(
    const uint8_t *header, const uint8_t *payload, size_t size) {
    (void)header; (void)payload; (void)size; return 0;
}
static long p328_write_frame(
    int fd, uint8_t type, uint32_t sequence,
    const uint8_t *payload, uint16_t length) {
    (void)fd; (void)sequence;
    if (frame_count < 4) frame_types[frame_count++] = type;
    if (type == P328_FRAME_EXIT) {
        memcpy(&exit_flags, payload, 4);
        memcpy(&exit_code, payload + 4, 4);
        memcpy(&exit_signal, payload + 8, 4);
    } else if (type == P345_FRAME_CANCEL_ACK) {
        memcpy(&ack_status, payload, 4);
    }
    (void)length;
    return 0;
}
static uint64_t p328_elapsed_ms(
    const struct timespec64 *start, const struct timespec64 *finish) {
    (void)start; (void)finish; return 0;
}
static long p328_reap_after_kill(long pid, int *status) {
    (void)pid; *status = 7 << 8; return 0;
}
static long p328_cleanup_process_group(long pid) { (void)pid; return 0; }
static long p328_setsid(void) { return 0; }
static long p328_dup_to(int source, int target) {
    (void)source; return target;
}
"""
        main = r"""
int main(int argc, char **argv) {
    (void)argv;
    partial_mode = argc > 1;
    uint8_t nonce[32] = {1};
    uint8_t header[16] = {
        'S', '3', '2', '8', 1, 5, 32, 0, 4, 0, 0, 0, 0, 0, 0, 0
    };
    memset(cancel_input, 0xaa, sizeof(cancel_input));
    memcpy(cancel_input, header, sizeof(header));
    cancel_length = argc > 1 ? 8 : 48;
    uint8_t cancel_status = 255;
    long result = p345_exec_command(
        5, 4, (const uint8_t *)"x", 1, nonce, &cancel_status);
    if (argc > 1)
        return result == -P260_EPROTO && frame_count == 0 ? 0 : 10;
    return result == 0
        && cancel_status == P345_CANCEL_STATUS_CONSUMED
        && direct_killed
        && killed
        && frame_count == 2
        && frame_types[0] == P328_FRAME_EXIT
        && frame_types[1] == P345_FRAME_CANCEL_ACK
        && exit_flags == P345_CANCELLED_FLAG
        && exit_code == 7
        && exit_signal == 0
        && ack_status == P345_CANCEL_STATUS_CONSUMED ? 0 : 11;
}
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "cancel_fixture.c"
            source.write_text(prefix + "\n".join(functions) + main)
            native = root / "cancel_fixture"
            build = subprocess.run(
                [
                    "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-function", "-O2", str(source), "-o", str(native),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            arm = shutil.which("aarch64-linux-gnu-gcc")
            if arm is not None:
                subprocess.run(
                    [
                        arm, "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-Wno-unused-function", "-O2", "-c", str(source),
                        "-o", str(root / "cancel_fixture.aarch64.o"),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                description = subprocess.check_output(
                    ["file", str(root / "cancel_fixture.aarch64.o")],
                    text=True,
                )
                self.assertIn("ARM aarch64", description)
            self.assertEqual(
                subprocess.run([str(native)], timeout=2).returncode, 0
            )
            self.assertEqual(
                subprocess.run([str(native), "partial"], timeout=2).returncode, 0
            )


if __name__ == "__main__":
    unittest.main()
