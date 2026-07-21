#!/usr/bin/env python3
"""Validate the minimal FYG8 PID 1 userspace proof patch host-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_r4w1b_patch_check as shared  # noqa: E402
import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint  # noqa: E402
import s22plus_fyg8_r4w1e_e1_host_contract as e1  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1e0_pid1_userspace_proof_v1"
VERDICT = "PASS_R4W1E0_PID1_USERSPACE_PROOF_HOST_CONTRACT"
TARGET = shared.TARGET
CONFIG = "CONFIG_S22PLUS_FYG8_PID1_USERSPACE_PROOF"
DEFAULT_SOURCE = shared.DEFAULT_SOURCE
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/"
    "s22plus_fyg8_r4w1e0_pid1_userspace_proof.patch"
)
DEFAULT_INIT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_runtime/init"
)
DEFAULT_RUNTIME_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_runtime/runtime-receipt.json"
)
RUNTIME_RECEIPT_SHA256 = (
    "4ab9bae4d974c087fc68dda75d91d08babaeacaaa0f11f56d3b309b0fa42c2be"
)
RUNTIME_TOOL_NAMES = (
    "aarch64-linux-gnu-gcc",
    "aarch64-linux-gnu-strip",
    "aarch64-linux-gnu-readelf",
    "aarch64-linux-gnu-nm",
    "aarch64-linux-gnu-objdump",
    "gcc",
    "file",
    "qemu-aarch64",
)
PATCH_SHA256 = "3a1d680b8878f9db340957f49e37bb5651d118bab683b1db0925f5abe431d447"
PATCHED_FILES = {
    "kernel_platform/common/init/main.c": (
        "ce23d5f2dc7d7922ad3207dad61597fbd9619cdd728cf73b67e2bb4e5ff834e4"
    ),
    "kernel_platform/common/init/Kconfig": (
        "efb76d71da5ae455ec17be1c2bc1e418126be8e99d6cc9e4e268d53fede9900d"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "458b359fbcbb17686f0cfc153cf3fff2387fe0acbc0ab7e3cff722ed06172fa0"
    ),
}
PROBE_ID_PREIMAGE = (
    "S22PLUS_FYG8_R4W1E0_PID1_USERSPACE_PROBE_V1|SM-S906N|g0q|"
    "S906NKSS7FYG8|after=NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK|"
    "prior=1682af0e|date=2026-07-22"
)
PROBE_ID = hashlib.sha256(PROBE_ID_PREIMAGE.encode("ascii")).digest()[:16]
REQUEST = bytes.fromhex(
    "53323251010110000000000064554e8469385878c5bf8d57c44edeeafd118a62"
)
E1_INIT_SHA256 = "c3fd6cc88d8de494421ff2bf0f082d278745fdf9c2a74a2b5edba9fb8ca93627"
RUNTIME_FILES = {
    "workspace/public/src/native-init/s22plus_r4w1e_e1_runtime.c": (
        "d0767ebd1b10a9631c4306fe9d02e21faa3e49afcdb82e66fa77aeb1872e48cf"
    ),
    "workspace/public/src/native-init/s22plus_r4w1e_e1_child.c": (
        "2af86dda0f6c93ee90996d89c9803bd84bab16b909d25b732b69144fe8760e14"
    ),
    "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.c": (
        "9012a764887e3e37436d1396bacf53e63a70a0143941b7f3b8b2bb6255884703"
    ),
    "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.h": (
        "1a720dca985c159266a8dc281131de3c916ea223efec831a132a6d7217b44712"
    ),
}
ENTRY_PREIMAGE = (
    "S22PLUS_FYG8_R4W1E0_KERNEL_PID1_ENTRY|SM-S906N|g0q|S906NKSS7FYG8|"
    f"base-main={shared.BASE_FILES['kernel_platform/common/init/main.c']}|"
    f"init={E1_INIT_SHA256}|"
    "semantics=kernel_execve(/init)==0&&task_pid_nr(current)==1|"
    "layout=r4w1d-exact-45-byte-slot"
)
ENTRY_SHA256 = hashlib.sha256(ENTRY_PREIMAGE.encode("ascii")).hexdigest()
ENTRY_PROOF = f"\n[[S22P1U|{ENTRY_SHA256[:32]}]]\n".encode("ascii")
USERSPACE_PREIMAGE = (
    "S22PLUS_FYG8_R4W1E0_USERSPACE_FIRST_REQUEST|SM-S906N|g0q|"
    f"S906NKSS7FYG8|entry={ENTRY_SHA256[:32]}|request={REQUEST.hex()}|"
    "semantics=pid1-mount-proc-open-write-exact-request|"
    "layout=overwrite-same-45-byte-slot"
)
USERSPACE_SHA256 = hashlib.sha256(USERSPACE_PREIMAGE.encode("ascii")).hexdigest()
USERSPACE_PROOF = f"\n[[S22P1U|{USERSPACE_SHA256[:32]}]]\n".encode("ascii")
PROOF_FAMILY = b"[[S22P1U|"


class CheckError(ValueError):
    pass


@dataclass
class ModelState:
    slot: bytes = b""
    ready: bool = False
    userspace_proven: bool = False
    seed_idx: int = 0
    seed_boot_cnt: int = 0


def model_entry(*, exec_ok: bool, pid: int, magic: int, idx: int, boot: int) -> ModelState:
    payload_size = 0x200000 - 16
    if not exec_ok or pid != 1 or magic != 0x4D474F4C or idx < payload_size:
        return ModelState()
    return ModelState(
        slot=ENTRY_PROOF,
        ready=True,
        seed_idx=idx,
        seed_boot_cnt=boot,
    )


def model_write(
    state: ModelState,
    *,
    pid: int,
    offset: int,
    request: bytes,
    idx: int,
    boot: int,
) -> int:
    if pid != 1:
        return -1
    if not state.ready or state.userspace_proven:
        return -2
    if offset != 0 or len(request) != len(REQUEST):
        return -3
    if request != REQUEST:
        return -4
    if idx != state.seed_idx or boot != state.seed_boot_cnt:
        return -5
    if state.slot != ENTRY_PROOF:
        return -5
    state.slot = USERSPACE_PROOF
    state.userspace_proven = True
    return len(request)


def classify_observation(baseline: bytes, observed: bytes) -> str:
    if PROOF_FAMILY in baseline:
        raise CheckError("pre-candidate retained baseline contains the proof family")
    if observed.count(PROOF_FAMILY) != 1:
        raise CheckError("post-candidate proof family cardinality is not one")
    entry_count = observed.count(ENTRY_PROOF)
    userspace_count = observed.count(USERSPACE_PROOF)
    if (entry_count, userspace_count) == (1, 0):
        return "ENTRY_ONLY"
    if (entry_count, userspace_count) == (0, 1):
        return "USERSPACE_CALLBACK_REACHED"
    raise CheckError("post-candidate proof identity is ambiguous")


def _added_lines(text: str) -> list[str]:
    return [
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _function(text: str, start: str, end: str) -> str:
    try:
        begin = text.index(start)
        finish = text.index(end, begin)
    except ValueError as exc:
        raise CheckError(f"required source boundary missing: {start}") from exc
    return text[begin:finish]


def check_patch(patch: Path) -> dict[str, Any]:
    if patch.is_symlink() or not patch.is_file():
        raise CheckError("R4W1-E0 patch missing or indirect")
    actual = shared.sha256_file(patch)
    if actual != PATCH_SHA256:
        raise CheckError(f"R4W1-E0 patch SHA256 mismatch: {actual}")
    text = patch.read_text(encoding="ascii")
    targets = re.findall(r"^\+\+\+ b/(.+)$", text, flags=re.MULTILINE)
    if set(targets) != set(shared.BASE_FILES) or len(targets) != len(shared.BASE_FILES):
        raise CheckError(f"unexpected patch targets: {targets}")
    added = _added_lines(text)
    added_text = "\n".join(added)
    configs = {
        symbol
        for line in added
        for symbol in re.findall(r"CONFIG_[A-Z0-9_]+", line)
    }
    if configs != {CONFIG}:
        raise CheckError(f"unexpected config symbols: {sorted(configs)}")
    forbidden = (
        "panic(",
        "emergency_restart",
        "kernel_restart",
        "reboot(",
        "filp_open",
        "kernel_write",
        "blkdev_get",
        "submit_bio",
        "ioremap(",
        "of_machine_is_compatible",
        "of_find_compatible_node",
    )
    hits = [token for token in forbidden if token in added_text]
    if hits:
        raise CheckError(f"forbidden operations or new runtime gates: {hits}")
    required = (
        ENTRY_PROOF.decode("ascii").strip(),
        USERSPACE_PROOF.decode("ascii").strip(),
        'proc_create("s22_checkpoint", 0200',
        "task_pid_nr(current) != 1",
        "copy_from_user(request, buffer, sizeof(request))",
        "memcmp(request, s22plus_fyg8_p1u_request, sizeof(request))",
        "seed_idx < payload_size",
        "cursor - S22PLUS_FYG8_P1U_PROOF_SIZE",
        "s22plus_fyg8_p1u_store(head, s22plus_fyg8_p1u_userspace)",
    )
    missing = [token for token in required if token not in added_text]
    if missing:
        raise CheckError(f"required proof tokens missing: {missing}")
    if added_text.count("[[S22P1U|") != 2:
        raise CheckError("proof marker cardinality mismatch")
    initializer = re.search(
        r"s22plus_fyg8_p1u_request\[S22PLUS_FYG8_P1U_REQUEST_SIZE\] = \{"
        r"(.*?)\n\};",
        added_text,
        flags=re.DOTALL,
    )
    if initializer is None:
        raise CheckError("fixed userspace request initializer missing")
    request_bytes = bytes(
        int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]{2})", initializer.group(1))
    )
    if request_bytes != REQUEST:
        raise CheckError("kernel request bytes do not match first E1 request")
    return {
        "path": str(patch),
        "sha256": actual,
        "targets": targets,
        "config": CONFIG,
        "forbidden_hits": hits,
        "verified": True,
    }


def apply_and_check(source: Path, patch: Path) -> dict[str, Any]:
    shared.check_base_files(source)
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1e0-") as temp_name:
        temp = Path(temp_name)
        for relative in shared.BASE_FILES:
            destination = temp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=temp,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise CheckError(f"patch application failed: {completed.stdout[-2000:]}")
        hashes = {
            relative: shared.sha256_file(temp / relative)
            for relative in shared.BASE_FILES
        }
        if hashes != PATCHED_FILES:
            raise CheckError(f"patched file identities mismatch: {hashes}")
        main = (temp / "kernel_platform/common/init/main.c").read_text(
            encoding="ascii"
        )
        entry = _function(
            main,
            "static void s22plus_fyg8_p1u_record_entry",
            "static ssize_t s22plus_fyg8_p1u_write",
        )
        writer = _function(
            main,
            "static ssize_t s22plus_fyg8_p1u_write",
            "static const struct proc_ops s22plus_fyg8_p1u_ops",
        )
        edge = _function(main, "if (ramdisk_execute_command)", "/*\n\t * We try")
        entry_order = (
            'strcmp(init_filename, "/init")',
            "task_pid_nr(current) != 1",
            "seed_idx < payload_size",
            "s22plus_fyg8_p1u_store(head, s22plus_fyg8_p1u_entry)",
        )
        writer_order = (
            "task_pid_nr(current) != 1",
            "!s22plus_fyg8_p1u_state.ready",
            "s22plus_fyg8_p1u_state.userspace_proven",
            "copy_from_user(request, buffer, sizeof(request))",
            "memcmp(request, s22plus_fyg8_p1u_request, sizeof(request))",
            "s22plus_fyg8_p1u_header_unchanged(head)",
            "memcmp(slot, s22plus_fyg8_p1u_entry",
            "s22plus_fyg8_p1u_store(head, s22plus_fyg8_p1u_userspace)",
            "s22plus_fyg8_p1u_state.userspace_proven = true",
        )
        if [entry.index(token) for token in entry_order] != sorted(
            entry.index(token) for token in entry_order
        ):
            raise CheckError("entry proof guard order mismatch")
        if [writer.index(token) for token in writer_order] != sorted(
            writer.index(token) for token in writer_order
        ):
            raise CheckError("userspace proof guard order mismatch")
        expected_edge = (
            "ret = run_init_process(ramdisk_execute_command);\n"
            "\t\tif (!ret) {\n"
            "\t\t\ts22plus_fyg8_p1u_record_entry(ramdisk_execute_command);"
        )
        if expected_edge not in edge or main.count("s22plus_fyg8_p1u_record_entry(") != 3:
            raise CheckError("entry proof is not on the unique exec-success edge")
        return {"patched_files": hashes, "source_semantics": True}


def check_runtime_sources(root: Path) -> dict[str, Any]:
    hashes: dict[str, str] = {}
    for relative, expected in RUNTIME_FILES.items():
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise CheckError(f"runtime source missing or indirect: {relative}")
        actual = shared.sha256_file(path)
        if actual != expected:
            raise CheckError(f"runtime source identity mismatch: {relative}")
        hashes[relative] = actual
    runtime = (root / next(iter(RUNTIME_FILES))).read_text(encoding="ascii")
    client = (
        root / "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.c"
    ).read_text(encoding="ascii")
    start = _function(runtime, "void _start(void)", "\n}")
    start_order = ("sys_getpid() != 1", "s22_r4w1e_checkpoint_client_init", "e1_run();")
    if [start.index(token) for token in start_order] != sorted(
        start.index(token) for token in start_order
    ):
        raise CheckError("PID 1 runtime entry order mismatch")
    e1 = _function(runtime, "static void e1_run(void)", "void _start(void)")
    first_checkpoint = e1.index("E1_REQUIRE(")
    expected_first = (
        "E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());"
    )
    if e1.index(expected_first) != first_checkpoint:
        raise CheckError("first E1 userspace action is not proc mount checkpoint")
    if (
        'result = sys_mount(source, target, fstype, flags, data);' not in runtime
        or '"proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC' not in runtime
    ):
        raise CheckError("proc mount implementation missing")
    if 'sys_openat("/proc/s22_checkpoint", O_WRONLY | O_CLOEXEC)' not in client:
        raise CheckError("checkpoint proc write path mismatch")
    return {"files": hashes, "first_action": "proc-mount-then-exact-checkpoint", "verified": True}


def reproduce_runtime(root: Path) -> tuple[dict[str, Any], bytes, bytes]:
    runtime = e1.read_direct(
        root / "workspace/public/src/native-init/s22plus_r4w1e_e1_runtime.c",
        "E1 runtime",
    )
    child = e1.read_direct(
        root / "workspace/public/src/native-init/s22plus_r4w1e_e1_child.c",
        "E1 child",
    )
    client = e1.read_direct(
        root / "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.c",
        "E1 checkpoint client",
    )
    header = e1.read_direct(
        root / "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.h",
        "E1 checkpoint header",
    )
    loaded_sources = {
        "workspace/public/src/native-init/s22plus_r4w1e_e1_runtime.c": runtime,
        "workspace/public/src/native-init/s22plus_r4w1e_e1_child.c": child,
        "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.c": client,
        "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.h": header,
    }
    loaded_hashes = {
        relative: hashlib.sha256(data).hexdigest()
        for relative, data in loaded_sources.items()
    }
    if loaded_hashes != RUNTIME_FILES:
        raise CheckError("runtime reproduction source identities mismatch")
    tools = e1.require_tools()
    with e1.without_compiler_environment():
        with tempfile.TemporaryDirectory(prefix="s22-r4w1e0-probe-") as probe_dir:
            request_probe = e1.probe_client_request(
                Path(probe_dir), client.decode("ascii"), header, PROBE_ID, tools
            )
        with tempfile.TemporaryDirectory(prefix="s22-r4w1e0-init-a-") as first_dir:
            first = e1.compile_one(
                Path(first_dir), runtime, child, client, header, PROBE_ID, tools
            )
        with tempfile.TemporaryDirectory(prefix="s22-r4w1e0-init-b-") as second_dir:
            second = e1.compile_one(
                Path(second_dir), runtime, child, client, header, PROBE_ID, tools
            )
    if first["init"]["data"] != second["init"]["data"]:
        raise CheckError("R4W1-E0 init two-build reproduction mismatch")
    if first["child"]["data"] != second["child"]["data"]:
        raise CheckError("R4W1-E0 child two-build reproduction mismatch")
    if request_probe["sha256"] != hashlib.sha256(REQUEST).hexdigest():
        raise CheckError("compiled first checkpoint request identity mismatch")
    if request_probe["run_id"] != PROBE_ID.hex():
        raise CheckError("compiled first checkpoint probe ID mismatch")
    init_data = first["init"].pop("data")
    child_data = first["child"].pop("data")
    second["init"].pop("data")
    second["child"].pop("data")
    receipt = {
        "schema": "s22plus_fyg8_r4w1e0_runtime_receipt_v1",
        "probe_id": PROBE_ID.hex(),
        "probe_id_preimage": PROBE_ID_PREIMAGE,
        "sources": {
            relative: digest for relative, digest in RUNTIME_FILES.items()
        },
        "compile_flags": list(e1.COMPILE_FLAGS),
        "tools": {
            name: {
                "name": Path(path).name,
                "sha256": shared.sha256_file(Path(path)),
            }
            for name, path in sorted(tools.items())
        },
        "request_probe": request_probe,
        "init": {
            "size": len(init_data),
            "sha256": hashlib.sha256(init_data).hexdigest(),
        },
        "child": {
            "size": len(child_data),
            "sha256": hashlib.sha256(child_data).hexdigest(),
        },
        "reproduction_a": first,
        "reproduction_b": second,
        "two_build_byte_identical": True,
        "host_only": True,
        "verified": True,
    }
    return receipt, init_data, child_data


def encode_runtime_receipt(receipt: dict[str, Any]) -> bytes:
    return (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("ascii")


def check_runtime_artifact(init: Path, receipt_path: Path) -> dict[str, Any]:
    if init.is_symlink() or not init.is_file():
        raise CheckError("R4W1-E0 init artifact missing or indirect")
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise CheckError("R4W1-E0 runtime receipt missing or indirect")
    artifact = e1.read_direct(init, "R4W1-E0 init artifact")
    artifact_sha256 = hashlib.sha256(artifact).hexdigest()
    if artifact_sha256 != E1_INIT_SHA256:
        raise CheckError(f"R4W1-E0 init SHA256 mismatch: {artifact_sha256}")
    receipt_bytes = e1.read_direct(
        receipt_path, "R4W1-E0 runtime receipt", max_size=1_048_576
    )
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    if receipt_sha256 != RUNTIME_RECEIPT_SHA256:
        raise CheckError(f"R4W1-E0 runtime receipt SHA256 mismatch: {receipt_sha256}")
    try:
        receipt = json.loads(receipt_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckError("R4W1-E0 runtime receipt is not valid JSON") from exc
    required = {
        "schema": "s22plus_fyg8_r4w1e0_runtime_receipt_v1",
        "probe_id": PROBE_ID.hex(),
        "probe_id_preimage": PROBE_ID_PREIMAGE,
        "sources": RUNTIME_FILES,
        "compile_flags": list(e1.COMPILE_FLAGS),
        "two_build_byte_identical": True,
        "host_only": True,
        "verified": True,
    }
    for name, expected in required.items():
        if receipt.get(name) != expected:
            raise CheckError(f"R4W1-E0 runtime receipt {name} mismatch")
    if receipt.get("init") != {"size": len(artifact), "sha256": artifact_sha256}:
        raise CheckError("R4W1-E0 runtime receipt init binding mismatch")
    if receipt.get("request_probe", {}).get("sha256") != hashlib.sha256(REQUEST).hexdigest():
        raise CheckError("R4W1-E0 runtime receipt request mismatch")
    if receipt.get("request_probe", {}).get("run_id") != PROBE_ID.hex():
        raise CheckError("R4W1-E0 runtime receipt probe ID mismatch")
    if sorted(receipt.get("tools", {})) != sorted(RUNTIME_TOOL_NAMES):
        raise CheckError("R4W1-E0 runtime receipt tool inventory mismatch")
    return {
        "path": str(init),
        "size": len(artifact),
        "sha256": artifact_sha256,
        "receipt_path": str(receipt_path),
        "receipt_sha256": receipt_sha256,
        "probe_id": PROBE_ID.hex(),
        "request_probe": receipt["request_probe"],
        "two_build_byte_identical": True,
        "verified": True,
    }


def check_protocol() -> dict[str, Any]:
    expected_request = checkpoint.encode_request(
        "E1", checkpoint.STAGES["PROC_MOUNTED"], run_id=PROBE_ID
    )
    if REQUEST != expected_request:
        raise CheckError("first E1 request identity mismatch")
    if len(ENTRY_PROOF) != 45 or len(USERSPACE_PROOF) != 45:
        raise CheckError("compact proof size mismatch")
    if ENTRY_PROOF == USERSPACE_PROOF or ENTRY_PROOF.count(PROOF_FAMILY) != 1:
        raise CheckError("proof identity or family mismatch")
    if PROBE_ID != bytes.fromhex("64554e8469385878c5bf8d57c44edeea"):
        raise CheckError("probe ID preimage mismatch")
    state = model_entry(
        exec_ok=True,
        pid=1,
        magic=0x4D474F4C,
        idx=0x300000,
        boot=7,
    )
    if state.slot != ENTRY_PROOF or not state.ready:
        raise CheckError("entry model did not publish")
    if model_write(
        state,
        pid=1,
        offset=0,
        request=REQUEST,
        idx=0x300000,
        boot=7,
    ) != len(REQUEST):
        raise CheckError("userspace model did not publish")
    if state.slot != USERSPACE_PROOF or not state.userspace_proven:
        raise CheckError("userspace proof model state mismatch")
    return {
        "entry_proof": ENTRY_PROOF.decode("ascii").strip(),
        "userspace_proof": USERSPACE_PROOF.decode("ascii").strip(),
        "request_hex": REQUEST.hex(),
        "probe_id": PROBE_ID.hex(),
        "same_slot_overwrite": True,
        "entry_observation": classify_observation(b"", ENTRY_PROOF),
        "userspace_observation": classify_observation(b"", USERSPACE_PROOF),
        "positive_semantics": (
            "exact callback request accepted and userspace marker stored; "
            "syscall return and later E1 stages are not proven"
        ),
        "verified": True,
    }


def run(
    source: Path,
    patch: Path,
    init: Path = DEFAULT_INIT,
    runtime_receipt: Path = DEFAULT_RUNTIME_RECEIPT,
) -> dict[str, Any]:
    root = shared.repo_root()
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "patch": check_patch(patch),
        "source": apply_and_check(source, patch),
        "runtime": check_runtime_sources(root),
        "runtime_artifact": check_runtime_artifact(init, runtime_receipt),
        "protocol": check_protocol(),
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "flash": False,
            "live_authorized": False,
        },
        "verdict": VERDICT,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--init", type=Path, default=DEFAULT_INIT)
    parser.add_argument(
        "--runtime-receipt", type=Path, default=DEFAULT_RUNTIME_RECEIPT
    )
    parser.add_argument("--prepare-runtime-dir", type=Path)
    args = parser.parse_args()
    root = shared.repo_root()
    try:
        if args.prepare_runtime_dir is not None:
            output = shared.resolve(root, args.prepare_runtime_dir)
            if output.exists():
                raise CheckError("runtime output directory already exists")
            receipt, init_data, child_data = reproduce_runtime(root)
            output.mkdir(parents=True)
            (output / "init").write_bytes(init_data)
            (output / "s22-e1-child").write_bytes(child_data)
            (output / "runtime-receipt.json").write_bytes(
                encode_runtime_receipt(receipt)
            )
            print(
                json.dumps(
                    {
                        "result": "prepared",
                        "directory": str(output),
                        "init_sha256": receipt["init"]["sha256"],
                        "receipt_sha256": hashlib.sha256(
                            encode_runtime_receipt(receipt)
                        ).hexdigest(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        result = run(
            shared.resolve(root, args.source),
            shared.resolve(root, args.patch),
            shared.resolve(root, args.init),
            shared.resolve(root, args.runtime_receipt),
        )
    except (CheckError, shared.CheckError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"verdict": "BLOCKED_R4W1E0_HOST_CONTRACT", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
