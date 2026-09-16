"""ARM64 filesystem core/endpoint checks over private regular-file fixtures."""
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s22plus_native_ext4_profile_v1 as profile

UUID = "11111111-2222-4333-8444-555555555555"
NATIVE = ROOT / "workspace/public/src/native-init"


def superblock_fixture(blocks=profile.BLOCK_COUNT):
    """Independent fixed ext4 field fixture; actual formatter is tested separately."""
    raw = bytearray(1024)
    for offset, value in ((4, blocks & 0xFFFFFFFF), (0x150, blocks >> 32),
                          (0x18, 2), (0x1C, 2), (0x4C, 1), (0x5C, 0x2C),
                          (0x60, 0x2C2), (0x64, 0x46B), (0xE0, 8)):
        struct.pack_into("<I", raw, offset, value)
    for offset, value in ((0x38, 0xEF53), (0x3A, 1), (0x3C, 2), (0x58, 256), (0xFE, 64)):
        struct.pack_into("<H", raw, offset, value)
    raw[0x68:0x78] = uuid.UUID(UUID).bytes
    raw[0x78:0x88] = b"S22DEBIAN".ljust(16, b"\0")
    raw[0x175] = 1
    return checksum(raw)


def checksum(raw):
    raw = bytearray(raw)
    struct.pack_into("<I", raw, 0x3FC, profile.crc32c(raw[:0x3FC]))
    return bytes(raw)


HARNESS = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
/* Only fixture ownership is synthesized. Flags, paths, offsets, data, ELF
 * pinning and file metadata otherwise use actual ARM64 libc/syscalls. */
static int h0_fstat(int fd, struct stat *st) {
    int rc = fstat(fd, st);
    if (!rc) { st->st_uid = 0; st->st_gid = 0; }
    return rc;
}
#define fstat h0_fstat
#define main fs1_unused_device_main
#include "s22plus_native_ext4_v1.c"
#undef main
#undef fstat

struct fake { unsigned fail, count[10], calls, order[16]; };
static int fake_step(void *context, enum fs1_step step, enum fs1_mode mode) {
    struct fake *f = context;
    assert(step >= FS1_BIND && step <= FS1_FINAL && f->calls < 16);
    if (mode == FS1_VERIFY) assert(step != FS1_FORMAT && step != FS1_SYNC);
    f->count[step]++; f->order[f->calls++] = step;
    return f->fail == (unsigned)step ? EIO : 0;
}
static void fake_record(void *context, enum fs1_step step, int error) {
    (void)context; (void)step; (void)error;
}
static void transaction_faults(void) {
    struct fs1_result r;
    for (unsigned failure = 0; failure <= FS1_FINAL; ++failure) {
        struct fake f = {.fail = failure}; struct fs1_io io = {&f, fake_step, fake_record};
        int rc = fs1_execute(FS1_INITIALIZE, &io, &r);
        assert((rc != 0) == (failure != 0));
        assert(f.count[FS1_FORMAT] <= 1 && f.count[FS1_FILE] <= 1 && f.count[FS1_UNMOUNT] <= 1);
        if (failure && failure <= FS1_MOUNT) assert(!f.count[FS1_FILE] && !f.count[FS1_UNMOUNT]);
        if (failure == FS1_FILE || failure == FS1_SYNC) {
            assert(f.count[FS1_UNMOUNT] == 1 && r.cleanup_attempted && r.unmounted);
            assert(!f.count[FS1_FINAL]);
        }
        if (failure == FS1_UNMOUNT) assert(!r.unmounted && !f.count[FS1_FINAL]);
        if (!failure) assert(r.formatted && r.witness_verified && r.synchronized && r.unmounted);
    }
    struct fake f = {0}; struct fs1_io io = {&f, fake_step, fake_record};
    assert(!fs1_execute(FS1_VERIFY, &io, &r));
    assert(!f.count[FS1_FORMAT] && !f.count[FS1_SYNC] && r.witness_verified && r.unmounted);
    memset(&f, 0, sizeof(f));
    assert(!fs1_execute(FS1_INSPECT, &io, &r) && f.calls == 1 && f.order[0] == FS1_BIND);
    memset(&f, 0, sizeof(f));
    assert(fs1_execute((enum fs1_mode)9, &io, &r) && f.calls == 0);
}
int main(int argc, char **argv) {
    assert(argc == 3);
    transaction_faults();
    int sb = open(argv[1], O_RDONLY | O_NOFOLLOW | O_CLOEXEC); assert(sb >= 0);
    uint8_t raw[1024]; assert(read(sb, raw, sizeof(raw)) == sizeof(raw)); assert(!close(sb));
    assert(fs1_superblock(raw, sizeof(raw), fs1_uuid, FS1_BLOCKS));
    uint8_t wrong[16]; memcpy(wrong, fs1_uuid, 16); wrong[0] ^= 1;
    assert(!fs1_superblock(raw, sizeof(raw), wrong, FS1_BLOCKS));
    assert(!fs1_superblock(raw, sizeof(raw) - 1, fs1_uuid, FS1_BLOCKS));
    assert(!fs1_superblock(raw, sizeof(raw), fs1_uuid, FS1_BLOCKS - 1));
    uint8_t witness[FS1_BLOCK]; fs1_witness(witness);
    int directory = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC); assert(directory >= 0);
    assert(fcntl(directory, F_GETFD) & FD_CLOEXEC);
    int fd = openat(directory, "witness", O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    assert(fd >= 0 && write(fd, witness, sizeof(witness)) == sizeof(witness));
    assert(!fsync(fd) && !fsync(directory));
    uint8_t readback[FS1_BLOCK]; assert(pread(fd, readback, sizeof(readback), 0) == sizeof(readback));
    assert(!memcmp(witness, readback, sizeof(witness)));
    errno = 0;
    assert(openat(directory, "witness", O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW, 0600) < 0 && errno == EEXIST);
    errno = 0; assert(openat(directory, "witness", O_RDONLY | O_DIRECTORY) < 0 && errno == ENOTDIR);
    assert(!symlinkat("witness", directory, "link"));
    errno = 0; assert(openat(directory, "link", O_RDONLY | O_NOFOLLOW) < 0 && errno == ELOOP);
    assert(!close(fd));
    char path[PATH_MAX]; assert(snprintf(path, sizeof(path), "%s/witness", argv[2]) > 0);
    uint8_t expected_hash[32] = {@WITNESS_HASH@};
    fd = fs1_pin_file(path, FS1_BLOCK, expected_hash, false); assert(fd >= 0); assert(!close(fd));
    expected_hash[0] ^= 1; assert(fs1_pin_file(path, FS1_BLOCK, expected_hash, false) < 0);
    expected_hash[0] ^= 1;
    assert(!linkat(directory, "witness", directory, "hardlink", 0));
    assert(fs1_pin_file(path, FS1_BLOCK, expected_hash, false) < 0);
    assert(!unlinkat(directory, "hardlink", 0));
    fd = openat(directory, "sparse", O_RDWR | O_CREAT | O_EXCL | O_CLOEXEC, 0600); assert(fd >= 0);
    assert(!ftruncate(fd, (off_t)FS1_BYTES));
    off_t high = (off_t)(FS1_BYTES - FS1_BLOCK);
    assert(high > INT32_MAX && pwrite(fd, witness, sizeof(witness), high) == sizeof(witness));
    assert(pread(fd, readback, sizeof(readback), high) == sizeof(readback));
    assert(!memcmp(witness, readback, sizeof(witness)) && !close(fd));
    assert(!close(directory));
    puts("PASS ARM64 flags offsets pins witness and no-retry transaction faults; no device mount exercised");
    return 0;
}
'''


class SuperblockTests(unittest.TestCase):
    def test_profile_accepts_clean_exact_geometry(self):
        self.assertEqual(profile.superblock(superblock_fixture(), UUID)["block_count"], profile.BLOCK_COUNT)

    def test_rejects_dirty_recovery_and_unselected_features_even_with_valid_checksum(self):
        for offset, value in ((0x60, 0x2C6), (0x5C, 0x102C), (0x64, 0x46F),
                              (0xE4, 1), (0xE8, 1), (0x194, 1), (4, 1234)):
            with self.subTest(offset=offset, value=value):
                raw = bytearray(superblock_fixture()); struct.pack_into("<I", raw, offset, value)
                with self.assertRaises(ValueError): profile.superblock(checksum(raw), UUID)

    def test_rejects_checksum_uuid_short_and_dirty_state(self):
        raw = superblock_fixture()
        for value, identity in ((raw[:-1], UUID), (raw, "22222222-2222-4333-8444-555555555555"),
                                (raw[:100] + bytes([raw[100] ^ 1]) + raw[101:], UUID)):
            with self.assertRaises(ValueError): profile.superblock(value, identity)
        dirty = bytearray(raw);struct.pack_into("<H", dirty, 0x3A, 0)
        with self.assertRaises(ValueError): profile.superblock(checksum(dirty), UUID)

    def test_formatter_profile_is_explicit_and_has_no_discard_or_population(self):
        argv = profile.formatter_argv("/s22-fs-mke2fs", "/fixed/native", UUID)
        self.assertEqual(argv[-1], str(profile.BLOCK_COUNT))
        self.assertEqual(argv[argv.index("-O") + 1], "none," + ",".join(profile.FEATURES))
        self.assertIn("nodiscard,lazy_itable_init=0,lazy_journal_init=0,root_owner=0:0", argv)
        self.assertFalse(set(("-F", "-d", "-c", "-z", "-S")) & set(argv))


@unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc") and shutil.which("qemu-aarch64"),
                     "ARM64 toolchain and QEMU required")
class Arm64Tests(unittest.TestCase):
    def test_real_flags_high_offsets_pins_and_fault_paths(self):
        temporary = ROOT / "workspace/private/tmp";temporary.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="s22-ext4-h0-", dir=temporary) as name:
            out = Path(name)
            seal = "#define FS1_ALLOW_FORMAT 0\nstatic const char fs1_run_id[]=\"h0\";\n"
            seal += 'static const char fs1_uuid_text[]="' + UUID + '";\n'
            seal += "static const uint8_t fs1_uuid[16]={" + ",".join(map(str, uuid.UUID(UUID).bytes)) + "};\n"
            seal += "static const uint8_t fs1_sealed_gpt[FS1_GPT_BYTES]={0};\n"
            for part in ("formatter", "checker", "config"):
                seal += "static const uint64_t fs1_" + part + "_size=1;\n"
                seal += "static const uint8_t fs1_" + part + "_sha256[32]={0};\n"
            (out / "s22plus_native_ext4_seal_v1.h").write_text(seal)
            code = HARNESS.replace("@WITNESS_HASH@", ",".join(map(str, bytes.fromhex(profile.WITNESS_SHA256))))
            (out / "harness.c").write_text(code);(out / "superblock.bin").write_bytes(superblock_fixture())
            subprocess.run(["aarch64-linux-gnu-gcc", "-static", "-Os", "-std=c11", "-Wall", "-Wextra",
                            "-Werror", "-Wno-unused-function", "-I", str(out), "-I", str(NATIVE),
                            str(out / "harness.c"), "-o", str(out / "harness")],
                           check=True, capture_output=True, timeout=60)
            result = subprocess.run(["qemu-aarch64", str(out / "harness"), str(out / "superblock.bin"), str(out)],
                                    check=True, capture_output=True, timeout=30)
            self.assertIn(b"PASS ARM64", result.stdout)
            self.assertEqual((out / "witness").read_bytes(), profile.WITNESS)


if __name__ == "__main__":
    unittest.main()
