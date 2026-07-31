#!/usr/bin/env python3
"""Materialize one fresh observer-keyed Phase 2 A90 rootfs.

The input is the exact clean deterministic Phase 2B ext4 image.  The output is
one new-inode private copy containing exactly one fresh per-run SSH public key.
This host-only tool cannot contact a device, stage an image, flash, reboot, or
grant candidate/F1 authority.  A failed run directory is retained and is never
reused.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_phase2_display_v1_rootfs as phase2  # noqa: E402


PRIVATE_ROOT = REPO_ROOT / "workspace" / "private"
PRIVATE_RUN_BASE = PRIVATE_ROOT / "runs" / "server-distro"
CLEAN_IMAGE = (
    PRIVATE_ROOT
    / "outputs"
    / "a90-phase2-display-v1-ab-07-return-epoch-diagnostics"
    / "A"
    / "phase2-display-v1.img"
)
CLEAN_RECEIPT = (
    PRIVATE_ROOT
    / "outputs"
    / "a90-phase2-display-v1-ab-07-return-epoch-diagnostics"
    / "ab-receipt.json"
)
CLEAN_IMAGE_SHA256 = (
    "394fc9e3db303ea41e48139a6f57b6559ddd868412d6b7b217d2765276e4d55c"
)
CLEAN_RECEIPT_SHA256 = (
    "dfd1bd121800a7e97a855c1c92af1dab21bcd77f84786d26bfaa024ce932abf7"
)
IMAGE_BYTES = 2 * 1024 * 1024 * 1024
FILESYSTEM_LABEL = "PHASE2DISPLAYV1"
RUN_ID_RE = re.compile(
    r"^a90-v3406-debian-display-f1-(?P<date>[0-9]{8})-(?P<sequence>[0-9]{2})$"
)
PUBLIC_KEY_RE = re.compile(
    rb"^ssh-ed25519 [A-Za-z0-9+/]+={0,3}(?: [^\r\n]*)?\n$"
)
KEY_PATH = "observer-key"
KEYED_IMAGE_PATH = "phase2-display-v1-keyed.img"
SUMMARY_PATH = "keyed-rootfs-summary.json"
AUTHORIZED_KEYS = "/root/.ssh/authorized_keys"
ABSENT_RUNTIME_PATHS = (
    "/etc/dropbear/dropbear_ed25519_host_key",
    "/run/a90-native-display-release",
    "/run/a90-display/ready",
    "/run/a90-display/failure",
    "/run/a90-display/presenter.log",
    "/run/a90-display/launcher.pid",
)
SCHEMA = "a90-phase2d-keyed-rootfs-v1"
PASS_DECISION = "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS"


class ContractError(RuntimeError):
    """Raised when the per-run keying contract is not exact."""


def sha256_file(path: Path) -> str:
    return phase2.sha256_file(path)


def utc_now() -> str:
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def require_regular(
    path: Path,
    *,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    private: bool = False,
) -> os.stat_result:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ContractError(f"not a regular non-symlink file: {path}")
    if private and info.st_mode & 0o077:
        raise ContractError(f"private file permissions are too broad: {path}")
    if expected_size is not None and info.st_size != expected_size:
        raise ContractError(
            f"size mismatch for {path}: expected={expected_size} actual={info.st_size}"
        )
    if expected_sha256 is not None:
        actual = sha256_file(path)
        if actual != expected_sha256:
            raise ContractError(
                f"sha256 mismatch for {path}: "
                f"expected={expected_sha256} actual={actual}"
            )
    return info


def debugfs_path_absent(image: Path, target: str) -> bool:
    return phase2.debugfs_stat(image, target) is None


def read_ext4_label(image: Path) -> str:
    with image.open("rb") as stream:
        stream.seek(1024 + 0x38)
        if stream.read(2) != b"\x53\xef":
            raise ContractError("clean image is not ext4")
        stream.seek(1024 + 0x78)
        raw = stream.read(16)
    try:
        return raw.split(b"\0", 1)[0].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError("ext4 label is not ASCII") from exc


def audit_clean_base() -> dict[str, Any]:
    image_info = require_regular(
        CLEAN_IMAGE,
        expected_size=IMAGE_BYTES,
        expected_sha256=CLEAN_IMAGE_SHA256,
        private=True,
    )
    require_regular(
        CLEAN_RECEIPT,
        expected_sha256=CLEAN_RECEIPT_SHA256,
        private=True,
    )
    try:
        receipt = json.loads(CLEAN_RECEIPT.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("clean A/B receipt is not valid JSON") from exc
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != "a90-phase2-display-v1-ab-receipt"
        or receipt.get("profile") != "phase2-display-v1"
        or receipt.get("image_byte_identical") is not True
        or receipt.get("candidate_authority") is not False
        or receipt.get("device_action") is not False
        or receipt.get("flash") is not False
        or receipt.get("A", {}).get("image", {}).get("sha256")
        != CLEAN_IMAGE_SHA256
        or receipt.get("B", {}).get("image", {}).get("sha256")
        != CLEAN_IMAGE_SHA256
    ):
        raise ContractError("clean A/B receipt semantics are not exact")
    if read_ext4_label(CLEAN_IMAGE) != FILESYSTEM_LABEL:
        raise ContractError("clean ext4 label mismatch")
    root_ssh = phase2.debugfs_stat(CLEAN_IMAGE, "/root/.ssh")
    if root_ssh != {"mode": 0o700, "uid": 0, "gid": 0, "size": 4096}:
        raise ContractError("clean root SSH directory metadata mismatch")
    for target in (AUTHORIZED_KEYS, *ABSENT_RUNTIME_PATHS):
        if not debugfs_path_absent(CLEAN_IMAGE, target):
            raise ContractError(f"clean image unexpectedly contains {target}")
    return {
        "image": CLEAN_IMAGE,
        "image_size": image_info.st_size,
        "image_sha256": CLEAN_IMAGE_SHA256,
        "image_inode": image_info.st_ino,
        "image_device": image_info.st_dev,
        "receipt": CLEAN_RECEIPT,
        "receipt_sha256": CLEAN_RECEIPT_SHA256,
    }


def validate_run_id(run_id: str) -> str:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("run ID is not the exact Phase 2 display F1 form")
    return run_id


def exact_run_dir(run_id: str) -> Path:
    validate_run_id(run_id)
    return (PRIVATE_RUN_BASE / run_id).resolve()


def run(
    command: list[str],
    *,
    timeout: float = 300.0,
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env={**os.environ, "LC_ALL": "C", "LANG": "C", "TZ": "UTC"},
    )
    if result.returncode != 0:
        raise ContractError(
            f"host command failed rc={result.returncode}: {command!r}"
        )
    return result


def generate_observer_key(run_dir: Path) -> tuple[Path, Path]:
    private_key = run_dir / KEY_PATH
    public_key = run_dir / f"{KEY_PATH}.pub"
    if private_key.exists() or public_key.exists():
        raise ContractError("observer key path is not absent")
    run(
        [
            "ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "",
            "-f",
            str(private_key),
        ],
        timeout=60.0,
    )
    private_info = require_regular(private_key, private=True)
    public_info = require_regular(public_key)
    if private_info.st_mode & 0o777 != 0o600:
        raise ContractError("observer private key mode is not 0600")
    if public_info.st_mode & 0o022:
        raise ContractError("observer public key is group/world writable")
    public_bytes = public_key.read_bytes()
    if PUBLIC_KEY_RE.fullmatch(public_bytes) is None:
        raise ContractError("observer public key is not one exact Ed25519 line")
    return private_key, public_key


def copy_clean_image(base: dict[str, Any], run_dir: Path) -> Path:
    output = run_dir / KEYED_IMAGE_PATH
    if output.exists() or output.is_symlink():
        raise ContractError("keyed image path is not absent")
    run(
        [
            "cp",
            "--reflink=never",
            "--sparse=always",
            "--preserve=mode",
            str(base["image"]),
            str(output),
        ],
        timeout=600.0,
    )
    output.chmod(0o600)
    output_info = require_regular(
        output,
        expected_size=base["image_size"],
        expected_sha256=base["image_sha256"],
        private=True,
    )
    if (
        output_info.st_dev == base["image_device"]
        and output_info.st_ino == base["image_inode"]
    ):
        raise ContractError("keyed image did not receive a new inode")
    return output


def normalize_after_keying(image: Path) -> None:
    for field in ("atime", "ctime", "mtime", "crtime"):
        phase2.debugfs(
            image,
            f"set_inode_field /root/.ssh {field} 0",
            writable=True,
        )
    commands = "\n".join(
        (
            "set_current_time 1",
            f"set_super_value volume_name {FILESYSTEM_LABEL}",
            "set_super_value mtime 0",
            "set_super_value lastcheck 0",
            "",
        )
    ).encode("ascii")
    phase2.run(
        ["debugfs", "-w", image],
        timeout=60.0,
        input_bytes=commands,
    )


def insert_observer_key(image: Path, public_key: Path) -> dict[str, Any]:
    if not debugfs_path_absent(image, AUTHORIZED_KEYS):
        raise ContractError("authorized_keys is not absent before keying")
    record = phase2.replace_ext4_file(
        image,
        public_key,
        AUTHORIZED_KEYS,
        mode=0o600,
        uid=0,
        gid=0,
    )
    normalize_after_keying(image)
    return record


def validate_keyed_image(
    base: dict[str, Any],
    image: Path,
    public_key: Path,
) -> dict[str, Any]:
    info = require_regular(
        image,
        expected_size=IMAGE_BYTES,
        private=True,
    )
    if info.st_dev == base["image_device"] and info.st_ino == base["image_inode"]:
        raise ContractError("keyed image aliases the clean source inode")
    auth = phase2.debugfs_stat(image, AUTHORIZED_KEYS)
    expected_auth = {
        "mode": 0o600,
        "uid": 0,
        "gid": 0,
        "size": public_key.stat().st_size,
    }
    if auth != expected_auth:
        raise ContractError(
            f"authorized_keys metadata mismatch: {auth} != {expected_auth}"
        )
    public_sha = sha256_file(public_key)
    if hashlib.sha256(phase2.debugfs_cat(image, AUTHORIZED_KEYS)).hexdigest() != public_sha:
        raise ContractError("authorized_keys content mismatch")
    if read_ext4_label(image) != FILESYSTEM_LABEL:
        raise ContractError("keying changed the ext4 label")
    for target in ABSENT_RUNTIME_PATHS:
        if not debugfs_path_absent(image, target):
            raise ContractError(f"keyed image unexpectedly contains {target}")
    fsck = phase2.run(
        ["e2fsck", "-fn", image],
        timeout=300.0,
        check=False,
    )
    if fsck.returncode != 0:
        raise ContractError("keyed image failed read-only e2fsck")
    image_sha = sha256_file(image)
    if image_sha == base["image_sha256"]:
        raise ContractError("keyed image hash did not change")
    if sha256_file(base["image"]) != base["image_sha256"]:
        raise ContractError("clean source changed during keying")
    return {
        "path": str(image),
        "size": info.st_size,
        "sha256": image_sha,
        "inode": info.st_ino,
        "device": info.st_dev,
        "new_inode": True,
        "filesystem": "ext4",
        "filesystem_label": FILESYSTEM_LABEL,
        "authorized_keys": record_for_authorized_key(auth, public_sha),
        "e2fsck_read_only_rc": fsck.returncode,
        "runtime_paths_absent": list(ABSENT_RUNTIME_PATHS),
    }


def record_for_authorized_key(
    metadata: dict[str, int],
    public_sha256: str,
) -> dict[str, Any]:
    return {
        "target": AUTHORIZED_KEYS,
        **metadata,
        "sha256": public_sha256,
        "root_owned_mode_0600": True,
    }


def write_private_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    body = (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def source_contract_issues(source: str) -> tuple[str, ...]:
    issues: list[str] = []
    validator_start = source.find("\ndef source_contract_issues(")
    build_start = source.find("\ndef build(", validator_start + 1)
    if validator_start < 0 or build_start < 0:
        return ("keying source validator boundary is missing",)
    subject = source[:validator_start] + source[build_start:]
    required = (
        '"cp",\n            "--reflink=never",\n            "--sparse=always"',
        'if output.exists() or output.is_symlink():',
        'raise ContractError("keyed image path is not absent")',
        'if private_key.exists() or public_key.exists():',
        'phase2.replace_ext4_file(',
        'mode=0o600,\n        uid=0,\n        gid=0,',
        '["e2fsck", "-fn", image]',
        'if sha256_file(base["image"]) != base["image_sha256"]:',
        '"candidate_authority": False',
        '"device_contact": False',
        '"rootfs_staged": False',
        '"flash": False',
        '"reboot": False',
    )
    for token in required:
        if token not in subject:
            issues.append(f"keying source contract missing: {token!r}")
    for forbidden in (
        "--reflink=auto",
        "adb ",
        "fastboot",
        "native_init_flash",
        "--execute-approved-stage",
        "rm -f",
        "unlink(",
    ):
        if forbidden in subject:
            issues.append(f"keying source contains forbidden token: {forbidden!r}")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        issues.append("keying source is not valid Python")
        return tuple(issues)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    exact_guards = {
        "generate_observer_key": (
            "private_key.exists() or public_key.exists()",
        ),
        "copy_clean_image": (
            "output.exists() or output.is_symlink()",
            (
                "output_info.st_dev == base['image_device'] and "
                "output_info.st_ino == base['image_inode']"
            ),
        ),
        "build": (
            "run_dir.exists() or run_dir.is_symlink()",
        ),
    }
    for function_name, expected_tests in exact_guards.items():
        function = functions.get(function_name)
        actual_tests = (
            {
                ast.unparse(node.test)
                for node in ast.walk(function)
                if isinstance(node, ast.If)
            }
            if function is not None
            else set()
        )
        for expected in expected_tests:
            if expected not in actual_tests:
                issues.append(
                    "keying AST guard missing: "
                    f"{function_name}: {expected}"
                )
    return tuple(issues)


def build(run_id: str) -> dict[str, Any]:
    run_id = validate_run_id(run_id)
    source = Path(__file__).read_text(encoding="utf-8")
    issues = source_contract_issues(source)
    if issues:
        raise ContractError("; ".join(issues))
    base = audit_clean_base()
    run_dir = exact_run_dir(run_id)
    if run_dir.exists() or run_dir.is_symlink():
        raise ContractError("run directory must be absent and is never reusable")
    run_dir.mkdir(mode=0o700)
    private_key, public_key = generate_observer_key(run_dir)
    image = copy_clean_image(base, run_dir)
    inserted = insert_observer_key(image, public_key)
    keyed = validate_keyed_image(base, image, public_key)
    if inserted["sha256"] != keyed["authorized_keys"]["sha256"]:
        raise ContractError("inserted and reopened authorized key hashes differ")
    summary = {
        "schema": SCHEMA,
        "decision": PASS_DECISION,
        "created_utc": utc_now(),
        "run_id": run_id,
        "materializer": {
            "path": str(Path(__file__).resolve()),
            "size": Path(__file__).stat().st_size,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "source": {
            "path": str(base["image"]),
            "size": base["image_size"],
            "sha256": base["image_sha256"],
            "inode": base["image_inode"],
            "device": base["image_device"],
            "receipt_path": str(base["receipt"]),
            "receipt_sha256": base["receipt_sha256"],
            "unchanged": True,
        },
        "observer": {
            "private_key_path": str(private_key),
            "private_key_sha256": sha256_file(private_key),
            "public_key_path": str(public_key),
            "public_key_sha256": sha256_file(public_key),
            "algorithm": "ssh-ed25519",
            "single_run": True,
        },
        "keyed_image": keyed,
        "candidate_authority": False,
        "f1_authorized": False,
        "live_authority": False,
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
        "reboot": False,
    }
    write_private_json_exclusive(run_dir / SUMMARY_PATH, summary)
    return summary


def audit_payload() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    issues = source_contract_issues(source)
    base = audit_clean_base()
    return {
        "schema": SCHEMA,
        "mode": "host-only-audit",
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "clean_image_sha256": base["image_sha256"],
        "clean_receipt_sha256": base["receipt_sha256"],
        "contract_issues": list(issues),
        "ready_for_private_materialization": not issues,
        "candidate_authority": False,
        "f1_authorized": False,
        "live_authority": False,
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
        "reboot": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = audit_payload() if args.audit_only else build(args.run_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-phase2d-keyed-rootfs: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
