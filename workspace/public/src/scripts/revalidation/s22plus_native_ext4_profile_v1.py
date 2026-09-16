"""Fixed native ext4 filesystem profile and raw superblock validation; H0 only."""
from __future__ import annotations

import hashlib
import re
import struct
import uuid

import s22plus_root_console_v1 as wire
import s22plus_native_gpt_profile_v1 as gpt
from s22plus_native_records_v3 import read, require, verify

SCHEMA = "s22plus-native-ext4-v1"
BLOCK_SIZE = 4096
FIRST_LBA = 12_115_456
LAST_LBA = 62_305_023
BLOCK_COUNT = LAST_LBA - FIRST_LBA + 1
SIZE_BYTES = BLOCK_COUNT * BLOCK_SIZE
LABEL = "S22DEBIAN"
INODE_SIZE = 256
INODE_RATIO = 65536
FEATURES = (
    "has_journal", "ext_attr", "dir_index", "filetype", "extent", "64bit",
    "flex_bg", "sparse_super", "large_file", "huge_file", "dir_nlink",
    "extra_isize", "metadata_csum",
)
COMPAT = 0x0000002C
INCOMPAT = 0x000002C2
RO_COMPAT = 0x0000046B
WITNESS_NAME = ".s22-native-ext4-witness-v1"
WITNESS = (b"S22PLUS_NATIVE_EXT4_V1\n" +
           bytes((i * 17 + 31) & 255 for i in range(4096)))[:4096]
WITNESS_SHA256 = hashlib.sha256(WITNESS).hexdigest()
READER_PROFILE = "thermal-v3-reconnect-ufs-drain-ext4-reader-v1"
INITIALIZER_PROFILE = "thermal-v3-reconnect-ufs-drain-ext4-initialize-v1"
PROFILES = (READER_PROFILE, INITIALIZER_PROFILE)
SELECTIONS = ("filesystem-inspect", "filesystem-initialize", "filesystem-verify")
RESULT = re.compile(
    rb"FS1_RESULT mode=([0-2]) status=([01]) last=([0-9]+) failed=([0-9]+) errno=([0-9]+) "
    rb"formatted=([01]) mounted=([01]) witness=([01]) synced=([01]) unmounted=([01]) "
    rb"cleanup_attempted=([01]) cleanup_failed=([01]) cleanup_errno=([0-9]+) "
    rb"helper_reaped=([01]) helper_status=([0-9]+) blocks=([0-9]+)")
CHECKER_STDERR = b"e2fsck 1.47.2 (1-Jan-2025)\n"

# An explicit empty feature baseline prevents a future distro mke2fs.conf from
# enabling orphan_file, casefold, encryption, quota or another undeclared feature.
CONFIG = b"""[defaults]
base_features = sparse_super
default_mntopts = acl,user_xattr
blocksize = 4096
inode_size = 256
inode_ratio = 65536
enable_periodic_fsck = 0
[fs_types]
ext4 = {
    features = extent
}
s22root = {
    inode_ratio = 65536
}
"""


def formatter_argv(executable: str, device: str, fs_uuid: str,
                   *, blocks: int = BLOCK_COUNT) -> list[str]:
    """H0 command constructor; live callers must supply the sealed constants."""
    if str(uuid.UUID(fs_uuid)) != fs_uuid or type(blocks) is not int or blocks < 8192:
        raise ValueError("invalid ext4 qualification geometry or UUID")
    return [executable, "-q", "-t", "ext4", "-T", "s22root", "-b", str(BLOCK_SIZE),
            "-I", str(INODE_SIZE), "-i", str(INODE_RATIO), "-m", "0",
            "-e", "remount-ro", "-L", LABEL, "-U", fs_uuid,
            "-O", "none," + ",".join(FEATURES),
            "-E", "nodiscard,lazy_itable_init=0,lazy_journal_init=0,root_owner=0:0",
            device, str(blocks)]


def crc32c(data: bytes) -> int:
    value = 0xFFFFFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x82F63B78 if value & 1 else 0)
    return value


def superblock(raw: bytes, fs_uuid: str, *, blocks: int = BLOCK_COUNT) -> dict:
    """Validate the primary superblock only; this is not complete fsck proof."""
    if type(raw) is not bytes or len(raw) != 1024:
        raise ValueError("ext4 superblock must be exactly 1024 bytes")
    u16 = lambda offset: struct.unpack_from("<H", raw, offset)[0]
    u32 = lambda offset: struct.unpack_from("<I", raw, offset)[0]
    actual_blocks = u32(4) | u32(0x150) << 32
    fields = {
        "magic": u16(0x38) == 0xEF53,
        "blocks": actual_blocks == blocks,
        "first_data_block": u32(0x14) == 0,
        "block_size": u32(0x18) == 2 and u32(0x1C) == 2,
        "inode_size": u16(0x58) == INODE_SIZE,
        "revision": u32(0x48) == 0 and u32(0x4C) == 1,
        "clean": u16(0x3A) == 1 and u32(0xE8) == 0 and u32(0x194) == 0,
        "error_behavior": u16(0x3C) == 2,
        "features": (u32(0x5C), u32(0x60), u32(0x64)) == (COMPAT, INCOMPAT, RO_COMPAT),
        "uuid": raw[0x68:0x78] == uuid.UUID(fs_uuid).bytes,
        "label": raw[0x78:0x88] == LABEL.encode().ljust(16, b"\0"),
        "internal_journal": u32(0xE0) == 8 and u32(0xE4) == 0 and raw[0xD0:0xE0] == bytes(16),
        "descriptor_size": u16(0xFE) == 64,
        "checksum_type": raw[0x175] == 1,
        "checksum": u32(0x3FC) == crc32c(raw[:0x3FC]),
    }
    rejected = [key for key, valid in fields.items() if not valid]
    if rejected:
        raise ValueError("ext4 superblock differs: " + ", ".join(rejected))
    return {"status": "PASS_PROFILE_SUPERBLOCK_ONLY", "block_size": BLOCK_SIZE,
            "block_count": actual_blocks, "inode_size": INODE_SIZE,
            "features": list(FEATURES), "clean": True,
            "sha256": hashlib.sha256(raw).hexdigest(), "complete_filesystem_proved": False}


def decode(stdout: bytes, stderr: bytes, selection: str) -> dict:
    """Accept complete fixed positive evidence only; retain negatives in raw capture."""
    if selection not in SELECTIONS or type(stdout) is not bytes or type(stderr) is not bytes:
        raise ValueError("filesystem proof types differ")
    if len(stdout) > 32768 or len(stderr) > 8192 or not stdout.endswith(b"\n"):
        raise ValueError("filesystem proof is truncated or oversized")
    lines = stdout.splitlines()
    if not lines or RESULT.fullmatch(lines[-1]) is None:
        raise ValueError("complete filesystem result is absent")
    values = tuple(map(int, RESULT.fullmatch(lines[-1]).groups()))
    mode = SELECTIONS.index(selection)
    wanted = ((0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, BLOCK_COUNT)
              if mode == 0 else
              (mode, 0, 9, 0, 0, int(mode == 1), 1, 1, int(mode == 1), 1, 0, 0, 0, 1, 0, BLOCK_COUNT))
    if values != wanted:
        raise ValueError("filesystem command did not prove the selected complete outcome")
    if stderr != (b"" if mode == 0 else CHECKER_STDERR):
        raise ValueError("unexpected filesystem tool diagnostics")
    position = 0
    tool_rows = []
    steps = [1] if mode == 0 else list(range(1, 10)) if mode == 1 else [1, 3, 4, 5, 6, 8, 9]
    for step in steps:
        if step in (2, 4):
            tool = b"format" if step == 2 else b"check"
            if position >= len(lines) or lines[position] != b"FS1_TOOL_BEGIN tool=" + tool:
                raise ValueError("filesystem tool start differs")
            position += 1; start = position
            end = b"FS1_TOOL_END tool=" + tool + b" status=0 reaped=1"
            while position < len(lines) and lines[position] != end:
                if lines[position].startswith(b"FS1_"):
                    raise ValueError("unexpected filesystem record inside tool output")
                position += 1
            if position == len(lines):
                raise ValueError("filesystem tool has no successful reaped terminal")
            output = b"\n".join(lines[start:position])
            if tool == b"format" and output:
                raise ValueError("quiet formatter produced unexpected output")
            if tool == b"check":
                expected = [b"Pass 1: Checking inodes, blocks, and sizes",
                            b"Pass 2: Checking directory structure",
                            b"Pass 3: Checking directory connectivity",
                            b"Pass 4: Checking reference counts",
                            b"Pass 5: Checking group summary information"]
                actual = lines[start:position]
                summary = re.fullmatch(rb"S22DEBIAN: ([0-9]+)/([0-9]+) files \(([0-9]+\.[0-9])% non-contiguous\), ([0-9]+)/([0-9]+) blocks",
                                       actual[-1]) if actual else None
                if len(actual) != 6 or actual[:5] != expected or summary is None:
                    raise ValueError("filesystem checker summary differs")
                used, total, _, allocated, blocks = summary.groups()
                if int(used) != (11 if mode == 1 else 12) or not int(used) <= int(total) or \
                        int(blocks) != BLOCK_COUNT or not 0 < int(allocated) < BLOCK_COUNT:
                    raise ValueError("filesystem checker geometry or fixed-file count differs")
            tool_rows.append(dict(tool=tool.decode(), stdout_sha256=hashlib.sha256(output).hexdigest()))
            position += 1
        if position >= len(lines) or lines[position] != f"FS1_STEP step={step} errno=0".encode():
            raise ValueError("filesystem stage order or outcome differs")
        position += 1
    if position != len(lines) - 1:
        raise ValueError("filesystem proof has extra records")
    return dict(status="PASS_PARTITION_BINDING" if mode == 0 else
                "PASS_INITIALIZED_WRITTEN_CLEAN_UNMOUNT" if mode == 1 else
                "PASS_READONLY_WITNESS_CLEAN_UNMOUNT", selection=selection,
                block_count=BLOCK_COUNT, witness_sha256=None if mode == 0 else WITNESS_SHA256,
                formatted=mode == 1, clean_unmounted=mode != 0, tools=tool_rows,
                fresh_boot_proved=False)


def image_binding(image):
    """Validate only fixed private data; no H0 builders enter the live closure."""
    value = read(verify(image['filesystem']['binding']))
    require(value['schema'] == 's22plus-native-ext4-binding-h0-v1' and value['active'] is False and
            (value['block_size'], value['block_count'], value['size_bytes'], value['features'], value['witness_sha256']) ==
            (BLOCK_SIZE, BLOCK_COUNT, SIZE_BYTES, list(FEATURES), WITNESS_SHA256) and
            image['filesystem']['initialize'] is (image['profile'] == INITIALIZER_PROFILE),
            'filesystem image declaration differs')
    require(str(uuid.UUID(value['filesystem_uuid'])) == value['filesystem_uuid'], 'filesystem UUID differs')
    sealed = gpt.vectors(image['gpt']); shape = gpt.geometry(sealed, 'proposed')
    require(image['gpt']['proposal'] == value['layout_proposal'] and
            verify(value['expected_gpt']).read_bytes() == sealed['proposed'] and
            shape['userdata_sectors'] == 67108864 and shape['native_first_lba'] == FIRST_LBA and
            shape['native_sectors'] * 512 == SIZE_BYTES,
            'filesystem layout is outside the exact retained Android32 extent')
    return value


class Profile:
    RESULT_KEY = "filesystem"
    SETTLE_SECONDS = 0

    def __init__(self, image, selection):
        if selection not in SELECTIONS or image["profile"] not in PROFILES or \
                re.fullmatch(r"[0-9a-f]{32}", image["run_id_hex"]) is None:
            raise ValueError("filesystem image or command selection differs")
        self.selection = selection
        self.MUTATES = selection == "filesystem-initialize"
        if (image["profile"] == INITIALIZER_PROFILE) != self.MUTATES:
            raise ValueError("filesystem command is outside the compiled image role")
        self.OBSERVATION_SECONDS = 60 if selection == "filesystem-inspect" else 300
        self.ADMISSION_SECONDS = 17 if selection == "filesystem-inspect" else 245
        command = "exec /s22-fs " + selection.removeprefix("filesystem-") + " " + image["run_id_hex"]
        self.BODY = wire.command(command.encode(), cwd=b"/s22-root-work",
                                 timeout_ms=15000 if selection == "filesystem-inspect" else 240000)

    def project(self, stdout, stderr, terminal, *, requested):
        result = dict(schema=SCHEMA, status="NO_PROOF", selection=self.selection, requested=requested,
                      stdout=dict(size=len(stdout), sha256=hashlib.sha256(stdout).hexdigest()),
                      stderr=dict(size=len(stderr), sha256=hashlib.sha256(stderr).hexdigest()),
                      grants_device_authority=False)
        if not requested:
            return dict(result, reason="ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT")
        if terminal is None or terminal[:4] != (5, 0, 0, 0) or terminal[4] != len(stdout) + len(stderr) or terminal[5] != 0:
            return dict(result, reason="FILESYSTEM_COMMAND_DID_NOT_COMPLETE_SUCCESSFULLY")
        try:
            proof = decode(stdout, stderr, self.selection)
        except ValueError as error:
            return dict(result, reason=str(error))
        return dict(result, **proof)
