#!/usr/bin/env python3
"""Build the candidate-bound P2.34 E1A init and child reproducibly."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p233_e1_static_checker as p233  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_userspace_build_v1"
VERDICT = "PASS_P234_E1A_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = candidate_contract.TARGET
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p234/userspace")
CHILD_TOKEN = b"S22PLUS_R4W1E_E1_CHILD_OK:4c3e58c0785b\n"
CHILD_EXIT = 23
FORBIDDEN_MODULE_NAMES = (
    "smem.ko",
    "minidump.ko",
    "qcom-scm.ko",
    "qcom_wdt_core.ko",
    "gh_virt_wdt.ko",
)
COMPILER_ENVIRONMENT_KEYS = (
    "AS",
    "BFD_PLUGIN",
    "C_INCLUDE_PATH",
    "COMPILER_PATH",
    "CPATH",
    "CPLUS_INCLUDE_PATH",
    "DEPENDENCIES_OUTPUT",
    "GCC_COMPARE_DEBUG",
    "GCC_EXEC_PREFIX",
    "LD",
    "LDEMULATION",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "LIBRARY_PATH",
    "OBJC_INCLUDE_PATH",
    "SUNPRO_DEPENDENCIES",
)
COMPILE_FLAGS = (
    "-nostdlib",
    "-static",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables",
    "-ffunction-sections",
    "-fdata-sections",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-Wl,--build-id=none",
    "-Wl,--gc-sections",
    "-Wl,-e,_start",
    "-Wl,-z,noexecstack",
)
TOOL_NAMES = (
    "aarch64-linux-gnu-gcc",
    "aarch64-linux-gnu-strip",
    "aarch64-linux-gnu-readelf",
    "aarch64-linux-gnu-nm",
    "file",
    "qemu-aarch64",
)


class BuildError(ValueError):
    pass


def require_tools() -> dict[str, str]:
    resolved = {name: shutil.which(name) for name in TOOL_NAMES}
    missing = [name for name, path in resolved.items() if path is None]
    if missing:
        raise BuildError(f"required P2.34 userspace tools missing: {missing}")
    return {name: str(path) for name, path in resolved.items()}


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _run(
    command: list[str | Path], *, cwd: Path, label: str, allow: int = 0
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for key in COMPILER_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    environment.update({"LANG": "C", "LC_ALL": "C", "SOURCE_DATE_EPOCH": "0"})
    completed = subprocess.run(
        [str(value) for value in command],
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    if completed.returncode != allow:
        detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        raise BuildError(f"{label} failed rc={completed.returncode}: {detail[-2000:]}")
    return completed


def _compile_once(
    root: Path,
    directory: Path,
    run_id: bytes,
    tools: dict[str, str],
) -> dict[str, Any]:
    init_path = directory / "init"
    child_path = directory / "s22-e1-child"
    include = root / "workspace/public/src/native-init"
    define = p233._run_id_define(run_id)
    _run(
        [
            tools["aarch64-linux-gnu-gcc"],
            *COMPILE_FLAGS,
            "-DS22PLUS_FYG8_P233_PROFILE=1",
            f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}",
            "-I",
            include,
            root / p233.DEFAULT_RUNTIME,
            root / p233.DEFAULT_CLIENT,
            "-o",
            init_path,
        ],
        cwd=root,
        label="compile P2.34 E1A init",
    )
    _run(
        [
            tools["aarch64-linux-gnu-gcc"],
            *COMPILE_FLAGS,
            root / p233.DEFAULT_CHILD,
            "-o",
            child_path,
        ],
        cwd=root,
        label="compile P2.34 child",
    )
    outputs: dict[str, Any] = {}
    for name, path in (("init", init_path), ("child", child_path)):
        file_text = _run(
            [tools["file"], "-b", path], cwd=root, label=f"file {name}"
        ).stdout.decode("utf-8", "replace")
        readelf = _run(
            [tools["aarch64-linux-gnu-readelf"], "-W", "-h", "-l", path],
            cwd=root,
            label=f"readelf {name}",
        ).stdout.decode("utf-8", "replace")
        undefined = _run(
            [tools["aarch64-linux-gnu-nm"], "-u", path],
            cwd=root,
            label=f"nm undefined {name}",
        ).stdout
        symbols = _run(
            [tools["aarch64-linux-gnu-nm"], "-n", path],
            cwd=root,
            label=f"nm {name}",
        ).stdout.decode("ascii", "replace")
        stack = [line for line in readelf.splitlines() if "GNU_STACK" in line]
        if (
            "ELF 64-bit LSB executable, ARM aarch64" not in file_text
            or "statically linked" not in file_text
            or "INTERP" in readelf
            or "DYNAMIC" in readelf
            or len(stack) != 1
            or " RWE " in stack[0]
            or undefined.strip()
            or len(re.findall(r"\bT _start$", symbols, re.MULTILINE)) != 1
        ):
            raise BuildError(f"P2.34 {name} static ELF contract mismatch")
        outputs[name] = {"static_aarch64": True}
    for path in (init_path, child_path):
        _run(
            [tools["aarch64-linux-gnu-strip"], "-s", path],
            cwd=root,
            label=f"strip {path.name}",
        )
    for name, path in (("init", init_path), ("child", child_path)):
        data = path.read_bytes()
        outputs[name].update({"data": data, **receipt(data)})
    init_data = outputs["init"]["data"]
    child_data = outputs["child"]["data"]
    forbidden_ids = (
        p233.model.model_run_id("E1A"),
        p233.SOURCE_CHECK_RUN_IDS["E1A"],
    )
    module_counts = {
        name: init_data.count(name.encode("ascii"))
        for name in FORBIDDEN_MODULE_NAMES
    }
    if (
        init_data.count(run_id) != 1
        or init_data.count(b"/proc/s22_checkpoint") != 1
        or init_data.count(b"/s22-e1-child") != 1
        or init_data.count(CHILD_TOKEN) != 1
        or any(init_data.count(value) for value in forbidden_ids)
        or any(module_counts.values())
        or child_data.count(CHILD_TOKEN) != 1
    ):
        raise BuildError("P2.34 E1A candidate identity or closure mismatch")
    child_run = _run(
        [tools["qemu-aarch64"], child_path],
        cwd=root,
        label="execute P2.34 child",
        allow=CHILD_EXIT,
    )
    if child_run.stdout != CHILD_TOKEN or child_run.stderr:
        raise BuildError("P2.34 child token/exit behavior mismatch")
    outputs["init"]["module_string_counts"] = module_counts
    outputs["child"]["qemu_exit"] = child_run.returncode
    for row in outputs.values():
        row.pop("data")
    return outputs


def build_userspace(args: argparse.Namespace) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    output = candidate_contract.intent.resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"P2.34 userspace output already exists: {output}")
    exact_contract = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, args.source),
        candidate_contract.intent.resolve(root, args.intent),
        candidate_contract.intent.resolve(root, args.patch),
    )
    if exact_contract["profile"] != "E1A":
        raise BuildError("P2.34 userspace builder accepts only E1A")
    run_id = bytes.fromhex(exact_contract["run_id"])
    tools = require_tools()
    source_result = p233.audit_sources(
        p233.read_direct(root / p233.DEFAULT_CLIENT, "checkpoint client"),
        p233.read_direct(root / p233.DEFAULT_RUNTIME, "runtime wrapper"),
        p233.read_direct(root / p233.DEFAULT_LEGACY_RUNTIME, "legacy runtime"),
        p233.read_direct(root / p233.DEFAULT_HEADER, "checkpoint header"),
        p233.read_direct(root / p233.DEFAULT_CHILD, "child"),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s22-p234-userspace-a-") as first_name:
        first_dir = Path(first_name)
        first = _compile_once(root, first_dir, run_id, tools)
        first_bytes = {
            "init": (first_dir / "init").read_bytes(),
            "child": (first_dir / "s22-e1-child").read_bytes(),
        }
    with tempfile.TemporaryDirectory(prefix="s22-p234-userspace-b-") as second_name:
        second_dir = Path(second_name)
        second = _compile_once(root, second_dir, run_id, tools)
        second_bytes = {
            "init": (second_dir / "init").read_bytes(),
            "child": (second_dir / "s22-e1-child").read_bytes(),
        }
    if first_bytes != second_bytes or first != second:
        raise BuildError("P2.34 userspace two-build reproducibility mismatch")
    result = {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "candidate_contract": exact_contract,
        "source_contract": source_result,
        "run_id": exact_contract["run_id"],
        "profile": "E1A",
        "compile_flags": list(COMPILE_FLAGS),
        "outputs": first,
        "two_build_byte_identical": True,
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "boot_image_created": False,
            "candidate_packaged": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as name:
        staging = Path(name)
        (staging / "init").write_bytes(first_bytes["init"])
        (staging / "s22-e1-child").write_bytes(first_bytes["child"])
        (staging / "init").chmod(0o755)
        (staging / "s22-e1-child").chmod(0o755)
        (staging / "userspace-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="ascii",
        )
        os.replace(staging, output)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_userspace(parse_args(argv))
    except (
        BuildError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        p233.CheckError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
