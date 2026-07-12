#!/usr/bin/env python3
"""Validate the host-only FYG8 R4W1 retained-init witness source patch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_r4w1_patch_check_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
VERDICT = "PASS_R4W1_HOST_PATCH_CONTRACT"
MARKER_ID = "9ed5923b08c5eedbbdb0aaa6f6a5200c"
MARKER = (
    "\n[[S22R4W1|id="
    + MARKER_ID
    + "|phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)
LOG_BASE = 0x800200000
LOG_SIZE = 0x200000
LOG_MAGIC = 0x4D474F4C
PATCH_SHA256 = "e66962c9e8cc503f9c5e94265816fdc2e96f4920a2d47387c6f1a4d9bbc6b787"
EXPECTED_REVISIONS = (
    "r01",
    "r02",
    "r04",
    "r05",
    "r06",
    "r07",
    "r08",
    "r09",
    "r10",
    "r11",
    "r12",
)
BASE_FILES = {
    "kernel_platform/common/init/main.c": (
        "7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a"
    ),
    "kernel_platform/common/init/Kconfig": (
        "8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493"
    ),
}
PATCHED_FILES = {
    "kernel_platform/common/init/main.c": (
        "195577c773cd8b128e02b9553c7fa58b456ed7a9a39f14a70059281221dd7279"
    ),
    "kernel_platform/common/init/Kconfig": (
        "2e483dcad5fae2d393f4b55e5cf055621c0620908da31745a716aa3fb762bdec"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "beabea909cf577f54b97411385d74ce0e04782ada39d96d3192fca5047248542"
    ),
}
DEFAULT_SOURCE = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/s22plus_fyg8_r4w1_retained_init_witness.patch"
)


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_base_files(source: Path) -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    for relative, expected in BASE_FILES.items():
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise CheckError(f"base file missing or indirect: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise CheckError(f"base SHA256 mismatch for {relative}: {actual}")
        checked.append({"path": relative, "sha256": actual})
    return {"files": checked, "verified": True}


def added_patch_lines(patch_text: str) -> list[str]:
    return [
        line[1:]
        for line in patch_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def check_patch_policy(patch: Path) -> dict[str, Any]:
    if patch.is_symlink() or not patch.is_file():
        raise CheckError("patch missing or indirect")
    actual_sha = sha256_file(patch)
    if actual_sha != PATCH_SHA256:
        raise CheckError(f"patch SHA256 mismatch: {actual_sha}")
    text = patch.read_text(encoding="ascii")
    targets = re.findall(r"^\+\+\+ b/(.+)$", text, flags=re.MULTILINE)
    if set(targets) != set(BASE_FILES) or len(targets) != len(BASE_FILES):
        raise CheckError(f"unexpected patch targets: {targets}")
    added = added_patch_lines(text)
    symbols = {
        symbol
        for line in added
        for symbol in re.findall(r"CONFIG_[A-Z0-9_]+", line)
    }
    if symbols != {"CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"}:
        raise CheckError(f"unexpected added config symbols: {sorted(symbols)}")
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
    )
    added_text = "\n".join(added)
    hits = [token for token in forbidden if token in added_text]
    if hits:
        raise CheckError(f"forbidden added operations: {hits}")
    if MARKER_ID not in added_text:
        raise CheckError("marker ID missing from patch")
    return {
        "path": str(patch),
        "sha256": actual_sha,
        "targets": targets,
        "added_config_symbols": sorted(symbols),
        "forbidden_hits": hits,
        "verified": True,
    }


def apply_patch_to_minimal_tree(source: Path, patch: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1-check-") as temp_name:
        temp = Path(temp_name)
        before: dict[str, bytes] = {}
        for relative in BASE_FILES:
            src = source / relative
            dst = temp / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o644)
            before[relative] = dst.read_bytes()
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
        after = {relative: (temp / relative).read_bytes() for relative in BASE_FILES}
        unchanged = [relative for relative in BASE_FILES if before[relative] == after[relative]]
        if unchanged:
            raise CheckError(f"patch left target unchanged: {unchanged}")
        actual = {
            relative: hashlib.sha256(data).hexdigest()
            for relative, data in after.items()
        }
        if actual != PATCHED_FILES:
            raise CheckError(f"patched file SHA256 mismatch: {actual}")
        return {relative: data.decode("utf-8") for relative, data in after.items()}


def check_patched_sources(patched: dict[str, str]) -> dict[str, Any]:
    main = patched["kernel_platform/common/init/main.c"]
    kconfig = patched["kernel_platform/common/init/Kconfig"]
    defconfig = patched["kernel_platform/common/arch/arm64/configs/gki_defconfig"]
    exact_counts = {
        "marker_id": main.count(MARKER_ID),
        "record_function_definition": main.count(
            "static void s22plus_fyg8_record_init_exec(const char *init_filename)"
        ),
        "record_function_call": main.count(
            "s22plus_fyg8_record_init_exec(ramdisk_execute_command);"
        ),
        "magic_gate": main.count(
            "READ_ONCE(head->magic) != S22PLUS_FYG8_LOG_MAGIC"
        ),
        "publish_barrier": main.count("smp_wmb();"),
        "index_publish": main.count("WRITE_ONCE(head->idx, idx + marker_size);"),
    }
    if any(count != 1 for count in exact_counts.values()):
        raise CheckError(f"patched main.c token cardinality mismatch: {exact_counts}")
    required_main = (
        f"0x{LOG_BASE:x}ULL",
        f"0x{LOG_SIZE:x}U",
        f"0x{LOG_MAGIC:08x}U",
        'strcmp(init_filename, "/init")',
        "task_pid_nr(current) != 1",
        "pos = idx % payload_size;",
        "first = min(marker_size, payload_size - pos);",
    )
    missing_main = [token for token in required_main if token not in main]
    if missing_main:
        raise CheckError(f"patched main.c missing tokens: {missing_main}")
    if kconfig.count("config S22PLUS_FYG8_RETAINED_WITNESS") != 1:
        raise CheckError("witness Kconfig definition cardinality mismatch")
    if kconfig.count("default n") < 1:
        raise CheckError("witness Kconfig does not default off")
    if defconfig.count("CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y") != 1:
        raise CheckError("witness defconfig enable cardinality mismatch")
    return {
        "marker": MARKER.strip(),
        "marker_size": len(MARKER.encode("ascii")),
        "payload_size": LOG_SIZE - 16,
        "patched_files": PATCHED_FILES,
        "exact_counts": exact_counts,
        "required_main_missing": missing_main,
        "verified": True,
    }


def extract_node(text: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\{{(.*?)\n\s*\}};", text, re.DOTALL)
    if not match:
        raise CheckError(f"DT node missing: {name}")
    return match.group(1)


def check_dt_contract(source: Path) -> dict[str, Any]:
    directory = (
        source
        / "kernel_platform/msm-kernel/arch/arm64/boot/dts/samsung/rainbow/g0q"
    )
    files = sorted(directory.glob("g0q_kor_singlex_w00_r*.dts"))
    revisions = tuple(re.search(r"_(r\d+)\.dts$", path.name).group(1) for path in files)
    if revisions != EXPECTED_REVISIONS:
        raise CheckError(f"unexpected g0q DT revisions: {revisions}")
    rows: list[dict[str, Any]] = []
    for path, revision in zip(files, revisions):
        text = path.read_text(encoding="utf-8")
        carveout = extract_node(text, "sec_debug_region_log@8001FF000")
        log_buf = extract_node(text, "samsung,kernel_log_buf")
        requirements = (
            ('compatible = "samsung,carve-out";', carveout),
            ('reg = <0x08 0x1ff000 0x00 0x901000>;', carveout),
            ('compatible = "samsung,kernel_log_buf";', log_buf),
            ('status = "okay";', log_buf),
            ("sec,use-partial_reserved_mem;", log_buf),
            ('reg = <0x08 0x200000 0x00 0x200000>;', log_buf),
            ("sec,strategy = <0x03>;", log_buf),
        )
        missing = [token for token, body in requirements if token not in body]
        if missing:
            raise CheckError(f"DT contract mismatch {revision}: {missing}")
        rows.append({"revision": revision, "path": str(path), "verified": True})
    return {
        "base": f"0x{LOG_BASE:x}",
        "size": LOG_SIZE,
        "revisions": rows,
        "verified": True,
    }


def check_vendor_abi(source: Path) -> dict[str, Any]:
    header = source / (
        "kernel_platform/msm-kernel/include/linux/samsung/debug/sec_log_buf.h"
    )
    main = source / (
        "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/sec_log_buf_main.c"
    )
    last = source / (
        "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
        "sec_log_buf_last_kmsg.c"
    )
    texts = {
        "header": header.read_text(encoding="utf-8"),
        "main": main.read_text(encoding="utf-8"),
        "last_kmsg": last.read_text(encoding="utf-8"),
    }
    required = {
        "header": (
            "#define SEC_LOG_MAGIC\t\t0x4d474f4c",
            "uint32_t boot_cnt;",
            "uint32_t magic;",
            "uint32_t idx;",
            "uint32_t prev_idx;",
            "char buf[];",
        ),
        "main": (
            "DEVICE_BUILDER(__last_kmsg_pull_last_log, NULL)",
            "DEVICE_BUILDER(__log_buf_pull_early_buffer, NULL)",
        ),
        "last_kmsg": (
            "last_kmsg->size = __log_buf_copy_to_buffer(buf);",
            '#define LAST_LOG_BUF_NODE\t\t"last_kmsg"',
        ),
    }
    missing = {
        name: [token for token in tokens if token not in texts[name]]
        for name, tokens in required.items()
    }
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    if missing:
        raise CheckError(f"vendor sec_log_buf ABI mismatch: {missing}")
    return {
        "files": {
            "header": sha256_file(header),
            "main": sha256_file(main),
            "last_kmsg": sha256_file(last),
        },
        "missing": missing,
        "verified": True,
    }


def run_check(source: Path, patch: Path) -> dict[str, Any]:
    base = check_base_files(source)
    patch_policy = check_patch_policy(patch)
    patched = apply_patch_to_minimal_tree(source, patch)
    patched_contract = check_patched_sources(patched)
    dt = check_dt_contract(source)
    vendor = check_vendor_abi(source)
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "base": base,
        "patch": patch_policy,
        "patched_contract": patched_contract,
        "dt_contract": dt,
        "vendor_abi": vendor,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "image_created": False,
            "flash": False,
            "live_authorized": False,
            "security_config_changed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    result = run_check(resolve(root, args.source), resolve(root, args.patch))
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = resolve(root, args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded, encoding="ascii")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CheckError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
