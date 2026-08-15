#!/usr/bin/env python3
"""Build and audit the dormant S20+ N1 Magisk native-canary module.

This is an H0 builder.  It performs no ADB, root, Magisk, reboot, or device
operation, and its output is not live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_native_canary.c"
DEFAULT_OUTPUT = (
    ROOT / "workspace/private/outputs/s20plus_g986n/native_canary_n1_v1"
)
SCHEMA = "s20plus_g986n_native_canary_n1_build_v1"
VERDICT = "PASS_S20PLUS_G986N_NATIVE_CANARY_N1_HOST_BUILD"
MODULE_ID = "s20plus_native_canary"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
STATE_DIR = "/data/adb/s20plus-native-init/n1"
MODULE_FILES = (
    "module.prop",
    "skip_mount",
    "service.sh",
    "bin/s20plus_native_canary",
)
MODULE_MODES = {
    "module.prop": 0o644,
    "skip_mount": 0o644,
    "service.sh": 0o750,
    "bin/s20plus_native_canary": 0o750,
}
TOOLS = {
    "cc": Path("/usr/bin/aarch64-linux-gnu-gcc-15"),
    "strip": Path("/usr/bin/aarch64-linux-gnu-strip"),
    "readelf": Path("/usr/bin/aarch64-linux-gnu-readelf"),
    "nm": Path("/usr/bin/aarch64-linux-gnu-nm"),
    "file": Path("/usr/bin/file"),
    "qemu": Path("/usr/bin/qemu-aarch64"),
}
COMPILE_FLAGS = (
    "-std=c11",
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-fno-ident",
    f"-ffile-prefix-map={ROOT}=.",
    f"-fdebug-prefix-map={ROOT}=.",
    "-Wl,--build-id=none",
    "-Wl,-z,noexecstack",
    "-Wl,-z,relro",
    "-Wl,-z,now",
)


class BuildError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def direct_regular(path: Path, label: str) -> os.stat_result:
    try:
        lst = path.lstat()
        resolved = path.resolve(strict=True)
        st = resolved.stat()
    except OSError as exc:
        raise BuildError(f"{label} is unavailable: {exc}") from exc
    if (
        not stat.S_ISREG(lst.st_mode)
        or not stat.S_ISREG(st.st_mode)
        or stat.S_ISLNK(lst.st_mode)
        or path != resolved
        or lst.st_dev != st.st_dev
        or lst.st_ino != st.st_ino
        or st.st_nlink != 1
    ):
        raise BuildError(f"{label} is not one exact direct regular file")
    return st


def receipt(path: Path, label: str) -> dict[str, Any]:
    st = direct_regular(path, label)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (
            before.st_dev != st.st_dev
            or before.st_ino != st.st_ino
            or before.st_nlink != 1
            or not stat.S_ISREG(before.st_mode)
            or before.st_size < 0
            or before.st_size > 64 * 1024 * 1024
        ):
            raise BuildError(f"{label} changed before it was read")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, before.st_size - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > before.st_size:
                raise BuildError(f"{label} grew while it was read")
            chunks.append(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if (
        size != before.st_size
        or after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
        or after.st_ctime_ns != before.st_ctime_ns
    ):
        raise BuildError(f"{label} changed while it was read")
    data = b"".join(chunks)
    return {
        "size": len(data),
        "sha256": sha256_bytes(data),
    }


def tool_receipts() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, path in TOOLS.items():
        state = receipt(path, f"{name} tool")
        command = [str(path), "--version"]
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=clean_environment(),
            timeout=10,
        )
        if completed.returncode != 0 or len(completed.stdout) > 8192:
            raise BuildError(f"{name} tool version could not be bounded")
        state.update(
            {
                "path": str(path),
                "version_sha256": sha256_bytes(completed.stdout),
                "version_size": len(completed.stdout),
            }
        )
        result[name] = state
    return result


def compiler_closure() -> dict[str, Any]:
    queries = {
        "cc1": "-print-prog-name=cc1",
        "collect2": "-print-prog-name=collect2",
        "assembler": "-print-prog-name=as",
        "linker": "-print-prog-name=ld",
        "crt1": "-print-file-name=crt1.o",
        "crti": "-print-file-name=crti.o",
        "crtn": "-print-file-name=crtn.o",
        "crtbeginT": "-print-file-name=crtbeginT.o",
        "crtend": "-print-file-name=crtend.o",
        "libc": "-print-file-name=libc.a",
        "libc_nonshared": "-print-file-name=libc_nonshared.a",
        "libgcc": "-print-file-name=libgcc.a",
        "libgcc_eh": "-print-file-name=libgcc_eh.a",
    }
    result: dict[str, Any] = {}
    for name, query in queries.items():
        output = run_checked([str(TOOLS["cc"]), query], timeout=10)
        value = output.decode("utf-8", errors="strict").strip()
        if not value or "\n" in value:
            raise BuildError(f"compiler closure query is malformed: {name}")
        path = Path(value).resolve(strict=True)
        state = receipt(path, f"compiler closure {name}")
        state.update({"path": str(path), "query": query})
        result[name] = state
    return result


def python_closure() -> dict[str, Any]:
    executable = Path(sys.executable).resolve(strict=True)
    zipfile_source = Path(zipfile.__file__).resolve(strict=True)
    return {
        "executable": {
            "path": str(executable),
            **receipt(executable, "Python executable"),
        },
        "version": sys.version,
        "version_sha256": sha256_bytes(sys.version.encode("utf-8")),
        "zipfile_source": {
            "path": str(zipfile_source),
            **receipt(zipfile_source, "Python zipfile source"),
        },
    }


def clean_environment() -> dict[str, str]:
    return {
        "HOME": "/nonexistent/s20plus-n1-build",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "SOURCE_DATE_EPOCH": "0",
        "TZ": "UTC",
    }


def run_checked(command: list[str], *, timeout: int = 60) -> bytes:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=clean_environment(),
        timeout=timeout,
    )
    if completed.returncode != 0:
        text = completed.stdout[:4096].decode("utf-8", errors="replace")
        raise BuildError(f"command failed ({completed.returncode}): {text}")
    if len(completed.stdout) > 2 * 1024 * 1024:
        raise BuildError("command output exceeded the H0 bound")
    return completed.stdout


def compile_canary(output: Path, *, host_test: bool = False) -> dict[str, Any]:
    direct_regular(SOURCE, "canary source")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise BuildError("canary output already exists")
    command = [str(TOOLS["cc"]), *COMPILE_FLAGS]
    if host_test:
        command.append("-DS20PLUS_CANARY_HOST_TEST=1")
    command.extend(["-o", str(output), str(SOURCE)])
    run_checked(command)
    run_checked([str(TOOLS["strip"]), "--strip-all", str(output)])
    os.chmod(output, 0o700)
    return audit_elf(output)


def audit_elf(path: Path) -> dict[str, Any]:
    identity = receipt(path, "native canary")
    file_output = run_checked([str(TOOLS["file"]), "-b", str(path)]).decode(
        "ascii", errors="strict"
    )
    readelf = run_checked(
        [str(TOOLS["readelf"]), "-W", "-h", "-l", "-d", str(path)]
    ).decode("ascii", errors="strict")
    undefined_output = run_checked([str(TOOLS["nm"]), "-u", str(path)]).decode(
        "ascii", errors="strict"
    )
    undefined = "\n".join(
        line for line in undefined_output.splitlines() if "no symbols" not in line
    )
    expected_file = (
        "ELF 64-bit LSB executable, ARM aarch64" in file_output
        and "statically linked" in file_output
    )
    if not expected_file:
        raise BuildError("native canary is not a static ELF64 AArch64 executable")
    if "INTERP" in readelf or "NEEDED" in readelf or "Dynamic section" in readelf:
        raise BuildError("native canary contains a dynamic-loader dependency")
    if undefined.strip():
        raise BuildError("native canary contains undefined symbols")
    load_lines = [line for line in readelf.splitlines() if line.lstrip().startswith("LOAD")]
    if not load_lines or any(re.search(r"\bRWE\b", line) for line in load_lines):
        raise BuildError("native canary has an absent or writable-executable LOAD segment")
    entry = re.search(r"Entry point address:\s*(0x[0-9a-fA-F]+)", readelf)
    if entry is None:
        raise BuildError("native canary entry point is missing")
    identity.update(
        {
            "file_output": file_output.strip(),
            "entry_point": entry.group(1).lower(),
            "static": True,
            "pt_interp": False,
            "dt_needed": [],
            "undefined_symbols": [],
            "writable_executable_load": False,
        }
    )
    return identity


def module_prop() -> bytes:
    return (
        "id=s20plus_native_canary\n"
        "name=S20+ Native Canary\n"
        "version=1\n"
        "versionCode=1\n"
        "author=android-native-init-lab\n"
        "description=One-shot late_start native execution canary for SM-G986N IYC2\n"
    ).encode("ascii")


def service_sh() -> bytes:
    return (
        "#!/system/bin/sh\n"
        "MODDIR=${0%/*}\n"
        "i=0\n"
        "while [ \"$i\" -lt 120 ]; do\n"
        "  if [ \"$(getprop sys.boot_completed 2>/dev/null)\" = \"1\" ]; then\n"
        "    exec \"$MODDIR/bin/s20plus_native_canary\"\n"
        "  fi\n"
        "  i=$((i + 1))\n"
        "  sleep 1\n"
        "done\n"
        "exit 0\n"
    ).encode("ascii")


def module_contents(binary: bytes) -> dict[str, bytes]:
    return {
        "module.prop": module_prop(),
        "skip_mount": b"",
        "service.sh": service_sh(),
        "bin/s20plus_native_canary": binary,
    }


def write_module_zip(path: Path, binary: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise BuildError("module ZIP already exists")
    contents = module_contents(binary)
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as archive:
        for name in MODULE_FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | MODULE_MODES[name]) << 16
            archive.writestr(info, contents[name])
    os.chmod(path, 0o600)


def audit_module_zip(path: Path, binary: bytes) -> dict[str, Any]:
    archive_identity = receipt(path, "module ZIP")
    expected = module_contents(binary)
    members: list[dict[str, Any]] = []
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        if tuple(info.filename for info in infos) != MODULE_FILES:
            raise BuildError("module ZIP member order or inventory changed")
        if len({info.filename for info in infos}) != len(MODULE_FILES):
            raise BuildError("module ZIP has duplicate members")
        for info in infos:
            name = info.filename
            mode = info.external_attr >> 16
            data = archive.read(info)
            if (
                name.startswith("/")
                or "\\" in name
                or ".." in Path(name).parts
                or name.endswith("/")
                or not stat.S_ISREG(mode)
                or stat.S_IMODE(mode) != MODULE_MODES[name]
                or info.compress_type != zipfile.ZIP_STORED
                or info.date_time != (1980, 1, 1, 0, 0, 0)
                or info.flag_bits & 0x1
                or info.file_size != len(expected[name])
                or data != expected[name]
            ):
                raise BuildError(f"module ZIP member is not exact: {name}")
            members.append(
                {
                    "name": name,
                    "mode": oct(MODULE_MODES[name]),
                    "size": len(data),
                    "sha256": sha256_bytes(data),
                    "compression": "stored",
                }
            )
    archive_identity["members"] = members
    archive_identity["exact_four_regular_members"] = True
    return archive_identity


def source_safety() -> dict[str, Any]:
    source = SOURCE.read_text(encoding="utf-8")
    forbidden = {
        "generic_process_exec": ("system(", "execve(", "execl(", "posix_spawn("),
        "child_creation": ("fork(", "clone(", "pthread_create("),
        "network": ("socket(", "connect(", "bind(", "listen("),
        "mount_or_namespace": ("mount(", "umount", "unshare(", "setns("),
        "device_control": ("ioctl(", "mknod("),
        "system_control": ("reboot(", "setprop", "ctl.start", "ctl.stop"),
        "debug_or_module": ("ptrace(", "init_module(", "finit_module("),
        "block_path": ("/dev/block",),
    }
    findings = {
        category: [needle for needle in needles if needle in source]
        for category, needles in forbidden.items()
    }
    findings = {key: values for key, values in findings.items() if values}
    if findings:
        raise BuildError(f"native source gained a forbidden surface: {findings}")
    service = service_sh().decode("ascii")
    service_forbidden = (
        "eval", "sh -c", "su ", "magisk ", "adb", "curl", "wget", "&\n",
        "/dev/block", "/system/bin/reboot", "setprop", "resetprop",
    )
    present = [needle for needle in service_forbidden if needle in service]
    if present:
        raise BuildError(f"service script gained a forbidden surface: {present}")
    return {
        "generic_exec": False,
        "children_or_threads": False,
        "network": False,
        "mount_or_namespace": False,
        "device_or_block_access": False,
        "property_or_service_write": False,
        "reboot": False,
        "bounded_boot_wait_seconds": 120,
    }


def render_binding(
    build_result: dict[str, Any], *, run_nonce: str, pre_boot_id_sha256: str
) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{32}", run_nonce):
        raise BuildError("run nonce must be 32 lowercase hex characters")
    if not re.fullmatch(r"[0-9a-f]{64}", pre_boot_id_sha256):
        raise BuildError("pre-boot ID hash must be 64 lowercase hex characters")
    binary = build_result["binary"]
    module = build_result["module_zip"]
    return (
        "schema=s20plus_native_canary_n1_binding_v1\n"
        "target_model=SM-G986N\n"
        "target_device=y2q\n"
        "target_product=y2qksx\n"
        "target_incremental=G986NKSS8IYC2\n"
        f"module_zip_sha256={module['sha256']}\n"
        f"module_zip_size={module['size']}\n"
        f"binary_sha256={binary['sha256']}\n"
        f"binary_size={binary['size']}\n"
        f"run_nonce={run_nonce}\n"
        f"pre_boot_id_sha256={pre_boot_id_sha256}\n"
    ).encode("ascii")


def build(out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.resolve(strict=False)
    if out_dir.exists() or out_dir.is_symlink():
        raise BuildError("output directory already exists; refusing to clobber it")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tools = tool_receipts()
    compiler = compiler_closure()
    python_runtime = python_closure()
    source = receipt(SOURCE, "canary source")
    builder_source = receipt(Path(__file__).resolve(), "N1 builder source")
    safety = source_safety()

    with tempfile.TemporaryDirectory(prefix=".s20plus-n1-a-", dir=out_dir.parent) as first_dir, \
         tempfile.TemporaryDirectory(prefix=".s20plus-n1-b-", dir=out_dir.parent) as second_dir:
        first_root = Path(first_dir)
        second_root = Path(second_dir)
        first_binary = first_root / "s20plus_native_canary"
        second_binary = second_root / "s20plus_native_canary"
        first_audit = compile_canary(first_binary)
        second_audit = compile_canary(second_binary)
        if first_binary.read_bytes() != second_binary.read_bytes():
            raise BuildError("two native canary builds are not byte-identical")
        first_zip = first_root / f"{MODULE_ID}.zip"
        second_zip = second_root / f"{MODULE_ID}.zip"
        write_module_zip(first_zip, first_binary.read_bytes())
        write_module_zip(second_zip, second_binary.read_bytes())
        if first_zip.read_bytes() != second_zip.read_bytes():
            raise BuildError("two module ZIP builds are not byte-identical")
        zip_audit = audit_module_zip(first_zip, first_binary.read_bytes())

        out_dir.mkdir(mode=0o700)
        binary_out = out_dir / "s20plus_native_canary"
        zip_out = out_dir / f"{MODULE_ID}.zip"
        shutil.copyfile(first_binary, binary_out)
        shutil.copyfile(first_zip, zip_out)
        os.chmod(binary_out, 0o700)
        os.chmod(zip_out, 0o600)

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "tier": "H0",
        "live_authority": False,
        "target": TARGET,
        "module_id": MODULE_ID,
        "state_dir": STATE_DIR,
        "source": source,
        "builder_source": builder_source,
        "tools": tools,
        "compiler_closure": compiler,
        "python_closure": python_runtime,
        "compile_flags": list(COMPILE_FLAGS),
        "binary": receipt(binary_out, "published native canary"),
        "binary_audit": first_audit,
        "reproduction_binary": second_audit,
        "module_zip": receipt(zip_out, "published module ZIP"),
        "module_zip_audit": zip_audit,
        "source_safety": safety,
        "two_builds_byte_identical": True,
        "two_zips_byte_identical": True,
        "device_commands": 0,
        "adb_commands": 0,
        "su_commands": 0,
        "install_commands": 0,
        "reboot_commands": 0,
    }
    manifest = out_dir / "build-result.json"
    manifest_bytes = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        written = 0
        while written < len(manifest_bytes):
            amount = os.write(fd, manifest_bytes[written:])
            if amount <= 0:
                raise OSError("short write while publishing build result")
            written += amount
        os.fsync(fd)
    finally:
        os.close(fd)
    dir_fd = os.open(out_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    result["manifest"] = receipt(manifest, "build result")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build(args.out_dir)
    except (BuildError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "REJECTED", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
