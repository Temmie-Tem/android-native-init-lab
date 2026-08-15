#!/usr/bin/env python3
"""Build, run, and audit the P3.18 dummy_hcd -> real observer control."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import lzma
import os
import re
import select
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p318_cdc_acm_qemu_real_observer_v1"
VERDICT = "PASS_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0"
PASS_LINE = (
    b"P318_QEMU result=PASS "
    b"verdict=PASS_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0 banner_bytes=49"
)
FAIL_LINE_PREFIX = b"P318_QEMU result=FAIL "
TERMINAL_LINE_PREFIX = b"P318_QEMU result="
KERNEL_VERSION = "6.12.94+deb13-arm64"
MODULES = (
    "usb-common",
    "usbcore",
    "configfs",
    "udc-core",
    "libcomposite",
    "dummy_hcd",
    "u_serial",
    "usb_f_acm",
    "cdc-acm",
)
RUNTIME = Path("workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c")
P260_HARNESS = Path("workspace/public/src/native-init/s22plus_fyg8_p260_qemu_harness.c")
INIT_SOURCE = Path("workspace/public/src/native-init/s22plus_fyg8_p318_cdc_acm_qemu_init.c")
CONTROLLER_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_cdc_acm_qemu_e2e.py"
)
GUEST_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_cdc_acm_qemu_guest.py"
)
OBSERVER_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/device_action_cdc_acm_observer_v1.py"
)
SOURCE_PATHS = {
    "controller": CONTROLLER_SOURCE,
    "runtime": RUNTIME,
    "p260_harness": P260_HARNESS,
    "init": INIT_SOURCE,
    "guest": GUEST_SOURCE,
    "observer": OBSERVER_SOURCE,
}
DEFAULT_GUEST_ROOT = Path("workspace/private/tools/generic-arm64-guest/root")
DEFAULT_QEMU_ROOT = Path("workspace/private/tools/qemu-arm64-10.2.1/root")
DEFAULT_PYTHON_INPUT = Path(
    "workspace/private/tools/p318-arm64-python-trixie-20260815-v2"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318_cdc_acm_qemu_e2e"
)
SANDBOX_OUTPUT = Path("/execution")
BWRAP = Path("/usr/bin/bwrap")
BWRAP_VERSION = "bubblewrap 0.11.1"

PYTHON_PACKAGES = {
    "python3.13-minimal_3.13.5-2+deb13u3_arm64.deb": {
        "package": "python3.13-minimal",
        "version": "3.13.5-2+deb13u3",
        "size": 2002540,
        "sha256": "d64a87f3dc9b3b52567cda12096312767b19f8f3995d4051f79a2435d3d994de",
    },
    "libpython3.13-minimal_3.13.5-2+deb13u3_arm64.deb": {
        "package": "libpython3.13-minimal",
        "version": "3.13.5-2+deb13u3",
        "size": 856300,
        "sha256": "c5210fcdcbf293d7ccdb1a0ebb33fad11c87d027af89e6f5bb8cd62ed001defe",
    },
    "libpython3.13-stdlib_3.13.5-2+deb13u3_arm64.deb": {
        "package": "libpython3.13-stdlib",
        "version": "3.13.5-2+deb13u3",
        "size": 1892732,
        "sha256": "88f3f041436676c627672955f39269abff8168196546fc65130aa31165c03981",
    },
    "libc6_2.41-12+deb13u3_arm64.deb": {
        "package": "libc6",
        "version": "2.41-12+deb13u3",
        "size": 2489480,
        "sha256": "ff529924782d3286181188fc265a6a92e7fe28975fb3a925dc0e05c0ca66e52f",
    },
    "libgcc-s1_14.2.0-19_arm64.deb": {
        "package": "libgcc-s1",
        "version": "14.2.0-19",
        "size": 54104,
        "sha256": "1108bc87879833d6d9a145f22a4a15cddb34e065b4b5f4b97bee586adbac2851",
    },
    "libexpat1_2.7.1-2_arm64.deb": {
        "package": "libexpat1",
        "version": "2.7.1-2",
        "size": 93320,
        "sha256": "7f6868227f4893a11123e43b9ed291950b550c7dc209905b2fb871c74678d1bf",
    },
    "zlib1g_1%3a1.3.dfsg+really1.3.1-1+b1_arm64.deb": {
        "package": "zlib1g",
        "version": "1:1.3.dfsg+really1.3.1-1+b1",
        "size": 85116,
        "sha256": "209aa5cf671e97b9eb0410844fa6df4cae2e75b0c72e7802ab6c8ece13e6ddef",
    },
    "libssl3t64_3.5.6-1~deb13u2_arm64.deb": {
        "package": "libssl3t64",
        "version": "3.5.6-1~deb13u2",
        "size": 2760128,
        "sha256": "f7e09a12ccb2d6bd28bcc87a6e2462a0558dcb3cc34d56f90ee86fbd3402d8ba",
    },
}
KEYRING = {
    "filename": "debian-archive-keyring_2025.1ubuntu1_all.deb",
    "size": 187108,
    "sha256": "b5f307b91c4491fc6f83d0a2dbd91a876244363a4910681db0177833656f6037",
}
EXTRACTED_KEYRING = {
    "size": 55918,
    "sha256": "506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017",
}
INRELEASE = {
    "filename": "trixie-InRelease",
    "size": 140416,
    "sha256": "98b25b5cd185c59d34aa6e4c3e9b5b8f01bbe9d104fe2dcfbcd30dc0a14a59ed",
}
PACKAGES_INDEX = {
    "filename": "trixie-main-binary-arm64-Packages",
    "release_path": "main/binary-arm64/Packages",
    "size": 56104035,
    "sha256": "7d45e6f90e5cc4e4f215c4e4965ac2e6076572c9e5cbb5f88dfc880c76002a96",
}
GUEST_PACKAGES_XZ = {
    "filename": "Packages.xz",
    "size": 9607412,
    "sha256": "753da751bbc7a679f48bd1b623ffd4479cb6861c426118284c76eb82909e4908",
}
KERNEL_PACKAGE = {
    "filename": "linux-image-6.12.94+deb13-arm64_6.12.94-1_arm64.deb",
    "repository_filename": (
        "pool/main/l/linux-signed-arm64/"
        "linux-image-6.12.94+deb13-arm64_6.12.94-1_arm64.deb"
    ),
    "package": "linux-image-6.12.94+deb13-arm64",
    "version": "6.12.94-1",
    "architecture": "arm64",
    "size": 92732600,
    "sha256": "72db7fcfb443a4b03448bda98f4e7c1a1fa0d6c21fc57f0b119d704442f8ad49",
}


class ControlError(RuntimeError):
    pass


def complete_console_lines(data: bytes) -> tuple[bytes, ...]:
    """Return only LF-terminated lines, stripping one serial CR."""

    lines = data.split(b"\n")
    complete: list[bytes] = []
    for line in lines[:-1]:
        complete.append(line[:-1] if line.endswith(b"\r") else line)
    return tuple(complete)


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise ControlError("repository root not found")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity_bytes(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": sha256_bytes(data)}


def identity(path: Path) -> dict[str, Any]:
    return identity_bytes(stable_read(path, str(path), 2**31))


def stable_read(path: Path, label: str, maximum: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ControlError(f"{label} unavailable") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= maximum:
        raise ControlError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, name) != getattr(after, name) for name in fields):
        raise ControlError(f"{label} changed while reading")
    return data


def write_snapshot(path: Path, data: bytes, mode: int = 0o444) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise ControlError("snapshot write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, mode)
    if stable_read(path, f"snapshot {path.name}", 2**31) != data:
        raise ControlError("snapshot bytes differ after publication")


def snapshot_file(
    source: Path,
    destination: Path,
    label: str,
    maximum: int,
    mode: int = 0o444,
) -> bytes:
    data = stable_read(source, label, maximum)
    write_snapshot(destination, data, mode)
    return data


def require_receipt(path: Path, expected: dict[str, Any], label: str) -> bytes:
    data = stable_read(path, label, 2**31)
    if type(expected) is not dict or identity_bytes(data) != expected:
        raise ControlError(f"{label} identity differs")
    return data


def strict_json_loads(data: bytes) -> Any:
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise ControlError("preserved result is not UTF-8") from exc

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ControlError(f"preserved result repeats key: {key}")
            value[key] = item
        return value

    def reject_float(value: str) -> Any:
        raise ControlError(f"preserved result contains floating value: {value}")

    def reject_constant(value: str) -> Any:
        raise ControlError(f"preserved result contains non-finite value: {value}")

    try:
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ControlError("preserved result is invalid") from exc


def exact_value(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            exact_value(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            exact_value(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def receipt_shape(value: Any, extra_keys: tuple[str, ...] = ()) -> bool:
    keys = {"size", "sha256", *extra_keys}
    return (
        type(value) is dict
        and set(value) == keys
        and type(value.get("size")) is int
        and value["size"] > 0
        and type(value.get("sha256")) is str
        and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
        and all(type(value.get(key)) is str for key in extra_keys)
    )


def validate_result_shape(value: Any) -> None:
    if type(value) is not dict or set(value) != {
        "schema",
        "verdict",
        "build",
        "console",
        "transport",
        "scope",
    }:
        raise ControlError("preserved result shape differs")
    build = value.get("build")
    if type(build) is not dict or set(build) != {
        "compile_output",
        "config",
        "config_receipt",
        "guest_supply_chain",
        "guest_source_audit",
        "init",
        "init_file",
        "initramfs",
        "kernel",
        "kernel_snapshot",
        "modules",
        "python",
        "python_file",
        "python_supply_chain",
        "qemu",
        "sources",
    }:
        raise ControlError("preserved build shape differs")
    for key in ("config_receipt", "init", "initramfs", "kernel", "python"):
        if not receipt_shape(build.get(key)):
            raise ControlError(f"preserved build receipt shape differs: {key}")
    if not receipt_shape(build.get("kernel_snapshot"), ("relative_path",)):
        raise ControlError("preserved kernel snapshot shape differs")
    if type(build.get("compile_output")) is not str or any(
        type(build.get(key)) is not str for key in ("init_file", "python_file")
    ):
        raise ControlError("preserved build scalar type differs")
    for key in (
        "config",
        "guest_source_audit",
        "guest_supply_chain",
        "modules",
        "python_supply_chain",
        "sources",
    ):
        if type(build.get(key)) is not dict:
            raise ControlError(f"preserved build object differs: {key}")
    qemu = build.get("qemu")
    if type(qemu) is not dict or set(qemu) != {
        "execution_snapshot",
        "launcher_proc_maps",
        "observed_mapped_files",
        "observed_launcher_mapped_files",
        "proc_maps",
        "sandbox",
        "sandbox_mountinfo",
        "source",
    }:
        raise ControlError("preserved QEMU receipt shape differs")
    if not receipt_shape(qemu.get("proc_maps")):
        raise ControlError("preserved QEMU maps receipt shape differs")
    if not receipt_shape(qemu.get("launcher_proc_maps")):
        raise ControlError("preserved bubblewrap maps receipt shape differs")
    if not receipt_shape(qemu.get("sandbox_mountinfo")):
        raise ControlError("preserved sandbox mountinfo receipt shape differs")
    if type(qemu.get("source")) is not dict or type(qemu.get("execution_snapshot")) is not dict:
        raise ControlError("preserved QEMU authority shape differs")
    for key in ("observed_mapped_files", "observed_launcher_mapped_files"):
        observed = qemu.get(key)
        if type(observed) is not dict or not observed or any(
            not receipt_shape(item, ("path",)) for item in observed.values()
        ):
            raise ControlError(f"preserved mapped-file shape differs: {key}")
    if type(qemu.get("sandbox")) is not dict:
        raise ControlError("preserved sandbox state shape differs")
    if not receipt_shape(value.get("console")):
        raise ControlError("preserved console shape differs")
    if type(value.get("transport")) is not dict or type(value.get("scope")) is not dict:
        raise ControlError("preserved result object type differs")


def current_source_data(repo: Path) -> dict[str, bytes]:
    return {
        name: stable_read(repo / path, f"{name} source", 2**20)
        for name, path in SOURCE_PATHS.items()
    }


def function_body(source: bytes, name: str) -> str:
    try:
        text = source.decode("utf-8", "strict")
        tree = ast.parse(text)
    except (UnicodeError, SyntaxError) as exc:
        raise ControlError("guest source does not parse") from exc
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise ControlError(f"guest function multiplicity differs: {name}")
    segment = ast.get_source_segment(text, matches[0])
    if segment is None:
        raise ControlError(f"guest function source unavailable: {name}")
    return segment


def require_ordered_once(body: str, tokens: tuple[str, ...], label: str) -> None:
    position = -1
    for token in tokens:
        if body.count(token) != 1:
            raise ControlError(f"{label} token multiplicity differs: {token}")
        found = body.index(token)
        if found <= position:
            raise ControlError(f"{label} token order differs: {token}")
        position = found


def audit_guest_source(data: bytes) -> dict[str, bool]:
    run_body = function_body(data, "run")
    require_ordered_once(
        run_body,
        (
            "create_gadget(config)",
            "tty_descriptor = open_ttygs0()",
            "write_all(tty_descriptor, banner)",
            "stage=pre-bind-banner status=PASS",
            "persist_session(observer, config)",
            "child = os.fork()",
            "wait_ready(ready_read, child)",
            'write_verify(Path("/config/usb_gadget/g1/UDC"), UDC)',
            "wait_configured()",
            "wait_child(child)",
            "P318_QEMU result=PASS",
            "time.sleep(3600.0)",
        ),
        "guest run",
    )
    child_body = function_body(data, "child_observe")
    require_ordered_once(
        child_body,
        (
            "value = session.observe(",
            "reopened = observer.validate_receipt(",
            'raw = (RUN_DIR / "candidate-observer.raw").read_bytes()',
            'value.get("classification") != "accepted"',
            'reopened.get("accepted") is not True',
            "raw != expected",
            "P318_QEMU observer=PASS",
        ),
        "guest observer",
    )
    return {
        "pre_bind_banner_before_observer_fork": True,
        "actual_observer_and_receipt_reopen_before_pass": True,
        "udc_bind_after_observer_ready": True,
    }


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise ControlError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}"
        )
    return result


def derive_guest_config(runtime_data: bytes, harness_data: bytes) -> dict[str, str]:
    runtime = runtime_data.decode("utf-8", "strict")
    harness = harness_data.decode("utf-8", "strict")
    prefixes = re.findall(r'static const char banner_prefix\[\] = "([^"]+)";', runtime)
    regions = re.findall(
        r"static const uint8_t k_run_id\[16\] = \{(?P<body>.*?)\};",
        harness,
        re.DOTALL,
    )
    octets = re.findall(r"0x([0-9a-fA-F]{2})", regions[0]) if len(regions) == 1 else []
    exact_runtime_tokens = (
        ('{"/config/usb_gadget/g1/idVendor", "0x04e8", "0x04e8"}', 1),
        ('{"/config/usb_gadget/g1/idProduct", "0x6861", "0x6861"}', 1),
        ('"Android Native Init Lab",', 2),
        ('"S22+ E3 ACM",', 2),
    )
    if (
        prefixes != ["S22PLUS-FYG8-E3:"]
        or len(octets) != 16
        or any(runtime.count(token) != count for token, count in exact_runtime_tokens)
    ):
        raise ControlError("P2.60 banner/gadget source authority drifted")
    run_id = bytes(int(value, 16) for value in octets)
    banner = prefixes[0].encode("ascii") + run_id.hex().encode("ascii") + b"\n"
    if len(banner) != 49:
        raise ControlError("derived banner is not 49 bytes")
    return {
        "banner_hex": banner.hex(),
        "manufacturer": "Android Native Init Lab",
        "product": "S22+ E3 ACM",
        "serial": "S22E3" + run_id.hex(),
        "usb_product_id": "6861",
        "usb_vendor_id": "04e8",
    }


def dpkg_field(path: Path, name: str) -> str:
    return run(["dpkg-deb", "-f", str(path), name]).stdout.strip()


def parse_packages_index(data: bytes) -> tuple[dict[str, str], ...]:
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise ControlError("Debian Packages index is not UTF-8") from exc
    records: list[dict[str, str]] = []
    for paragraph in text.split("\n\n"):
        if not paragraph.strip():
            continue
        record: dict[str, str] = {}
        for line in paragraph.splitlines():
            if line.startswith((" ", "\t")):
                continue
            key, separator, value = line.partition(": ")
            if separator:
                record[key] = value
        records.append(record)
    return tuple(records)


def signed_kernel_record(packages_data: bytes) -> dict[str, str]:
    matches = [
        record
        for record in parse_packages_index(packages_data)
        if record.get("Package") == KERNEL_PACKAGE["package"]
        and record.get("Version") == KERNEL_PACKAGE["version"]
        and record.get("Architecture") == KERNEL_PACKAGE["architecture"]
    ]
    if len(matches) != 1:
        raise ControlError("signed kernel package record multiplicity differs")
    record = matches[0]
    expected = {
        "Package": KERNEL_PACKAGE["package"],
        "Version": KERNEL_PACKAGE["version"],
        "Architecture": KERNEL_PACKAGE["architecture"],
        "Filename": KERNEL_PACKAGE["repository_filename"],
        "Size": str(KERNEL_PACKAGE["size"]),
        "SHA256": KERNEL_PACKAGE["sha256"],
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise ControlError("signed kernel package record identity differs")
    return expected


def audit_signed_package_index(source_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    inrelease = source_root / INRELEASE["filename"]
    packages = source_root / PACKAGES_INDEX["filename"]
    inrelease_data = stable_read(inrelease, "Debian InRelease", 2**20)
    packages_data = stable_read(packages, "Debian Packages", 2**27)
    if identity_bytes(inrelease_data) != {
        "size": INRELEASE["size"],
        "sha256": INRELEASE["sha256"],
    }:
        raise ControlError("Debian InRelease identity differs")
    if identity_bytes(packages_data) != {
        "size": PACKAGES_INDEX["size"],
        "sha256": PACKAGES_INDEX["sha256"],
    }:
        raise ControlError("Debian Packages identity differs")

    keyring_deb = source_root / KEYRING["filename"]
    keyring_deb_data = stable_read(keyring_deb, "Debian keyring package", 2**20)
    if identity_bytes(keyring_deb_data) != {
        "size": KEYRING["size"],
        "sha256": KEYRING["sha256"],
    }:
        raise ControlError("Debian archive keyring identity differs")
    with tempfile.TemporaryDirectory(prefix="p318-debian-keyring-") as temporary:
        run(["dpkg-deb", "-x", str(keyring_deb), temporary])
        keyring = Path(temporary) / "usr/share/keyrings/debian-archive-keyring.pgp"
        if identity(keyring) != EXTRACTED_KEYRING:
            raise ControlError("extracted Debian archive keyring identity differs")
        signature = run(["gpgv", "--keyring", str(keyring), str(inrelease)]).stdout
    required_signers = (
        "Debian Archive Automatic Signing Key (13/trixie)",
        "Debian Stable Release Key (13/trixie)",
    )
    if any(signer not in signature for signer in required_signers):
        raise ControlError("Debian InRelease signer set differs")
    require_receipt(keyring_deb, identity_bytes(keyring_deb_data), "Debian keyring package")
    require_receipt(inrelease, identity_bytes(inrelease_data), "Debian InRelease")
    require_receipt(packages, identity_bytes(packages_data), "Debian Packages")

    release_line = (
        f" {PACKAGES_INDEX['sha256']} {PACKAGES_INDEX['size']:8d} "
        f"{PACKAGES_INDEX['release_path']}"
    )
    inrelease_text = inrelease_data.decode("utf-8", "strict")
    if inrelease_text.count(release_line) != 1:
        raise ControlError("Debian Packages index is not bound by InRelease")

    records = parse_packages_index(packages_data)
    signed_records: dict[str, dict[str, str]] = {}
    for filename, expected in PYTHON_PACKAGES.items():
        matches = [
            record
            for record in records
            if record.get("Package") == expected["package"]
            and record.get("Version") == expected["version"]
            and record.get("Architecture") == "arm64"
        ]
        if len(matches) != 1:
            raise ControlError(f"signed package record multiplicity differs: {filename}")
        record = matches[0]
        if (
            record.get("SHA256") != expected["sha256"]
            or record.get("Size") != str(expected["size"])
            or not record.get("Filename", "").startswith("pool/main/")
            or not record.get("Filename", "").endswith("_arm64.deb")
        ):
            raise ControlError(f"signed package record identity differs: {filename}")
        signed_records[filename] = {
            field: record[field]
            for field in ("Package", "Version", "Architecture", "Filename", "Size", "SHA256")
        }
    return (
        {
            "inrelease": identity_bytes(inrelease_data),
            "packages": identity_bytes(packages_data),
            "keyring_deb": identity_bytes(keyring_deb_data),
            "extracted_keyring": EXTRACTED_KEYRING,
            "gpgv_signers_verified": list(required_signers),
            "inrelease_binds_packages": True,
        },
        signed_records,
    )


def audit_python_inputs(root: Path) -> dict[str, Any]:
    deb_root = root / "debs"
    if not deb_root.is_dir() or set(path.name for path in deb_root.iterdir()) != set(PYTHON_PACKAGES):
        raise ControlError("Python package set differs")
    source_root = root / "source"
    expected_source_names = {
        KEYRING["filename"],
        "debootstrap.log",
        INRELEASE["filename"],
        PACKAGES_INDEX["filename"],
    }
    if not source_root.is_dir() or set(path.name for path in source_root.iterdir()) != expected_source_names:
        raise ControlError("Python source evidence set differs")
    signed_index, signed_records = audit_signed_package_index(source_root)
    packages: dict[str, Any] = {}
    for filename, expected in PYTHON_PACKAGES.items():
        path = deb_root / filename
        data = stable_read(path, f"Python package {filename}", 2**24)
        found = identity_bytes(data)
        if found != {"size": expected["size"], "sha256": expected["sha256"]}:
            raise ControlError(f"Python package identity differs: {filename}")
        metadata = {
            "package": dpkg_field(path, "Package"),
            "version": dpkg_field(path, "Version"),
            "architecture": dpkg_field(path, "Architecture"),
        }
        if metadata != {
            "package": expected["package"],
            "version": expected["version"],
            "architecture": "arm64",
        }:
            raise ControlError(f"Python package metadata differs: {filename}")
        require_receipt(path, found, f"Python package {filename}")
        packages[filename] = {**found, **metadata, "signed_record": signed_records[filename]}

    keyring = source_root / KEYRING["filename"]
    keyring_data = stable_read(keyring, "Debian archive keyring", 2**20)
    if identity_bytes(keyring_data) != {
        "size": KEYRING["size"],
        "sha256": KEYRING["sha256"],
    }:
        raise ControlError("Debian archive keyring identity differs")
    log_data = stable_read(source_root / "debootstrap.log", "debootstrap log", 2**20)
    log = log_data.decode("utf-8", "strict")
    required_log = (
        "URL:https://deb.debian.org/debian/dists/trixie/InRelease",
        'Good signature from "Debian Archive Automatic Signing Key (13/trixie)',
        'Good signature from "Debian Stable Release Key (13/trixie)',
        "binary-arm64/by-hash/SHA256/",
    )
    if any(token not in log for token in required_log) or "Cannot check Release signature" in log:
        raise ControlError("Debian source verification log differs")
    for filename in PYTHON_PACKAGES:
        decoded = filename.replace("%3a", ":")
        package = PYTHON_PACKAGES[filename]["package"]
        if package not in log or decoded.rsplit("_arm64.deb", 1)[0] not in log.replace("%3a", ":"):
            raise ControlError(f"package absent from verified source log: {filename}")
    return {
        "packages": packages,
        "archive_keyring": identity_bytes(keyring_data),
        "signed_index": signed_index,
        "debootstrap_log": {"size": len(log_data), "sha256": sha256_bytes(log_data)},
        "release_signature_verified": True,
        "suite": "trixie",
        "architecture": "arm64",
    }


def snapshot_python_inputs(source_root: Path, destination_root: Path) -> None:
    deb_source = source_root / "debs"
    evidence_source = source_root / "source"
    if not deb_source.is_dir() or not evidence_source.is_dir():
        raise ControlError("Python input root is incomplete")
    (destination_root / "debs").mkdir(parents=True)
    (destination_root / "source").mkdir()
    for filename in PYTHON_PACKAGES:
        snapshot_file(
            deb_source / filename,
            destination_root / "debs" / filename,
            f"Python package {filename}",
            2**24,
        )
    for filename, maximum in (
        (KEYRING["filename"], 2**20),
        ("debootstrap.log", 2**20),
        (INRELEASE["filename"], 2**20),
        (PACKAGES_INDEX["filename"], 2**27),
    ):
        snapshot_file(
            evidence_source / filename,
            destination_root / "source" / filename,
            f"Python source evidence {filename}",
            maximum,
        )


def find_module(module_root: Path, name: str) -> Path:
    matches = sorted(module_root.glob(f"**/{name}.ko.xz"))
    if len(matches) != 1:
        raise ControlError(f"expected one {name}.ko.xz, found {len(matches)}")
    return matches[0]


def snapshot_guest_package_inputs(guest_root: Path, destination_root: Path) -> None:
    source_root = guest_root.parent
    deb_root = source_root / "debs"
    deb = deb_root / KERNEL_PACKAGE["filename"]
    if (
        not guest_root.is_dir()
        or not deb_root.is_dir()
        or set(path.name for path in deb_root.iterdir())
        != {KERNEL_PACKAGE["filename"]}
    ):
        raise ControlError("guest kernel package source is incomplete")
    (destination_root / "debs").mkdir(parents=True)
    snapshot_file(
        source_root / GUEST_PACKAGES_XZ["filename"],
        destination_root / GUEST_PACKAGES_XZ["filename"],
        "guest Debian Packages.xz",
        2**24,
    )
    snapshot_file(
        deb,
        destination_root / "debs" / KERNEL_PACKAGE["filename"],
        "guest kernel package",
        2**27,
    )


def audit_guest_package_snapshot(
    snapshot_root: Path,
    loose_guest_root: Path,
    signed_packages_data: bytes,
) -> tuple[dict[str, Any], bytes, dict[str, tuple[bytes, bytes]]]:
    if identity_bytes(signed_packages_data) != {
        "size": PACKAGES_INDEX["size"],
        "sha256": PACKAGES_INDEX["sha256"],
    }:
        raise ControlError("signed Packages authority differs for guest kernel")
    if (
        not snapshot_root.is_dir()
        or set(path.name for path in snapshot_root.iterdir())
        != {GUEST_PACKAGES_XZ["filename"], "debs"}
        or set(path.name for path in (snapshot_root / "debs").iterdir())
        != {KERNEL_PACKAGE["filename"]}
    ):
        raise ControlError("guest kernel execution snapshot shape differs")

    source_root = loose_guest_root.parent
    source_packages_xz = stable_read(
        source_root / GUEST_PACKAGES_XZ["filename"],
        "current guest Debian Packages.xz",
        2**24,
    )
    snapshot_packages_xz = stable_read(
        snapshot_root / GUEST_PACKAGES_XZ["filename"],
        "snapshotted guest Debian Packages.xz",
        2**24,
    )
    if (
        source_packages_xz != snapshot_packages_xz
        or identity_bytes(snapshot_packages_xz)
        != {
            "size": GUEST_PACKAGES_XZ["size"],
            "sha256": GUEST_PACKAGES_XZ["sha256"],
        }
    ):
        raise ControlError("guest Packages.xz source and snapshot differ")
    try:
        decompressed_packages = lzma.decompress(snapshot_packages_xz)
    except lzma.LZMAError as exc:
        raise ControlError("guest Packages.xz cannot be decompressed") from exc
    if decompressed_packages != signed_packages_data:
        raise ControlError("guest Packages.xz differs from signed Packages authority")
    record = signed_kernel_record(signed_packages_data)

    source_deb = stable_read(
        source_root / "debs" / KERNEL_PACKAGE["filename"],
        "current guest kernel package",
        2**27,
    )
    snapshot_deb_path = snapshot_root / "debs" / KERNEL_PACKAGE["filename"]
    snapshot_deb = stable_read(
        snapshot_deb_path,
        "snapshotted guest kernel package",
        2**27,
    )
    expected_deb = {
        "size": KERNEL_PACKAGE["size"],
        "sha256": KERNEL_PACKAGE["sha256"],
    }
    if source_deb != snapshot_deb or identity_bytes(snapshot_deb) != expected_deb:
        raise ControlError("guest kernel package source and snapshot differ")
    metadata = {
        "package": dpkg_field(snapshot_deb_path, "Package"),
        "version": dpkg_field(snapshot_deb_path, "Version"),
        "architecture": dpkg_field(snapshot_deb_path, "Architecture"),
    }
    if metadata != {
        "package": KERNEL_PACKAGE["package"],
        "version": KERNEL_PACKAGE["version"],
        "architecture": KERNEL_PACKAGE["architecture"],
    }:
        raise ControlError("guest kernel package metadata differs")

    modules: dict[str, tuple[bytes, bytes]] = {}
    module_receipts: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="p318-kernel-package-") as temporary:
        extracted = Path(temporary)
        run(["dpkg-deb", "-x", str(snapshot_deb_path), str(extracted)])
        require_receipt(snapshot_deb_path, expected_deb, "snapshotted kernel package")
        kernel_path = extracted / "boot" / f"vmlinuz-{KERNEL_VERSION}"
        kernel_data = stable_read(kernel_path, "extracted guest kernel", 2**27)
        loose_kernel = stable_read(
            loose_guest_root / "boot" / f"vmlinuz-{KERNEL_VERSION}",
            "loose guest kernel",
            2**27,
        )
        if loose_kernel != kernel_data:
            raise ControlError("loose guest kernel differs from signed package")
        extracted_module_root = extracted / "usr/lib/modules" / KERNEL_VERSION
        loose_module_root = loose_guest_root / "usr/lib/modules" / KERNEL_VERSION
        for name in MODULES:
            package_path = find_module(extracted_module_root, name)
            compressed = stable_read(
                package_path,
                f"extracted guest module {name}",
                2**25,
            )
            loose_path = find_module(loose_module_root, name)
            loose_compressed = stable_read(
                loose_path,
                f"loose guest module {name}",
                2**25,
            )
            if loose_compressed != compressed:
                raise ControlError(
                    f"loose guest module differs from signed package: {name}"
                )
            try:
                decompressed = lzma.decompress(compressed)
            except lzma.LZMAError as exc:
                raise ControlError(
                    f"signed guest module cannot be decompressed: {name}"
                ) from exc
            modules[name] = (compressed, decompressed)
            module_receipts[name] = {
                "package_relative_path": str(package_path.relative_to(extracted)),
                "compressed": identity_bytes(compressed),
                "decompressed": identity_bytes(decompressed),
            }

    return (
        {
            "packages_xz": identity_bytes(snapshot_packages_xz),
            "decompressed_packages": identity_bytes(decompressed_packages),
            "decompressed_packages_match_signed_index": True,
            "source_inputs_match_execution_snapshot": True,
            "kernel_package": {
                "deb": identity_bytes(snapshot_deb),
                "metadata": metadata,
                "signed_record": record,
                "snapshot_relative_path": (
                    f"input-snapshots/guest-package/debs/"
                    f"{KERNEL_PACKAGE['filename']}"
                ),
            },
            "kernel": identity_bytes(kernel_data),
            "modules": module_receipts,
            "loose_tree_matches_signed_package": True,
        },
        kernel_data,
        modules,
    )


def build_initramfs(
    *, repo: Path, guest_root: Path, python_input: Path, output: Path
) -> dict[str, Any]:
    if output.exists():
        raise ControlError("output already exists")
    output.mkdir(parents=True)
    rootfs = output / "rootfs"
    rootfs.mkdir()
    snapshot_root = output / "input-snapshots"
    python_snapshot = snapshot_root / "python"
    snapshot_python_inputs(python_input, python_snapshot)
    python_receipt = audit_python_inputs(python_snapshot)
    signed_packages_data = stable_read(
        python_snapshot / "source" / PACKAGES_INDEX["filename"],
        "snapshotted signed Debian Packages",
        2**27,
    )
    guest_package_snapshot = snapshot_root / "guest-package"
    snapshot_guest_package_inputs(guest_root, guest_package_snapshot)
    guest_supply_chain, kernel_data, signed_modules = audit_guest_package_snapshot(
        guest_package_snapshot,
        guest_root,
        signed_packages_data,
    )
    for filename in PYTHON_PACKAGES:
        package = python_snapshot / "debs" / filename
        run(["dpkg-deb", "-x", str(package), str(rootfs)])
        require_receipt(
            package,
            {
                "size": PYTHON_PACKAGES[filename]["size"],
                "sha256": PYTHON_PACKAGES[filename]["sha256"],
            },
            f"snapshotted Python package {filename}",
        )
    # Debian trixie packages target merged-/usr; the minimal package subset does
    # not include base-files, so publish the interpreter's absolute loader path.
    (rootfs / "lib").symlink_to("usr/lib")

    source_data = current_source_data(repo)
    guest_source_audit = audit_guest_source(source_data["guest"])
    config = derive_guest_config(source_data["runtime"], source_data["p260_harness"])
    write_snapshot(
        rootfs / "p318-qemu-config.json",
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode() + b"\n",
    )
    write_snapshot(
        rootfs / "s22plus_fyg8_p318_cdc_acm_qemu_guest.py",
        source_data["guest"],
        0o555,
    )
    write_snapshot(
        rootfs / "device_action_cdc_acm_observer_v1.py",
        source_data["observer"],
    )
    (rootfs / "modules").mkdir()

    compiler = shutil.which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise ControlError("aarch64-linux-gnu-gcc unavailable")
    init = rootfs / "init"
    compile_result = subprocess.run(
        [
            compiler,
            "-static",
            "-O2",
            "-Wall",
            "-Wextra",
            "-o",
            str(init),
            "-x",
            "c",
            "-",
        ],
        input=source_data["init"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if compile_result.returncode != 0:
        raise ControlError(
            "init compilation failed:\n"
            + compile_result.stdout.decode("utf-8", "replace")
        )
    init.chmod(0o755)

    kernel = snapshot_root / "guest" / f"vmlinuz-{KERNEL_VERSION}"
    write_snapshot(kernel, kernel_data)
    module_receipts: dict[str, Any] = {}
    for name in MODULES:
        source_data_bytes, decompressed = signed_modules[name]
        target = rootfs / "modules" / f"{name}.ko"
        write_snapshot(target, decompressed)
        module_receipts[name] = {
            "source": identity_bytes(source_data_bytes),
            "decompressed": identity_bytes(decompressed),
        }

    for path in sorted(rootfs.rglob("*"), reverse=True):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "p318-cdc-acm-qemu-e2e.cpio"
    with initramfs.open("wb") as stream:
        result = subprocess.run(
            [
                "bash",
                "-c",
                "find . -print0 | LC_ALL=C sort -z | cpio --null --reproducible -o -H newc",
            ],
            cwd=rootfs,
            check=False,
            stdout=stream,
            stderr=subprocess.PIPE,
        )
    if result.returncode != 0:
        raise ControlError(f"cpio failed: {result.stderr.decode('utf-8', 'replace')}")
    init_file = run(["file", str(init)]).stdout.strip()
    python_file = run(["file", str(rootfs / "usr/bin/python3.13")]).stdout.strip()
    if "ARM aarch64" not in init_file or "statically linked" not in init_file:
        raise ControlError("init binary identity differs")
    if "ARM aarch64" not in python_file or "dynamically linked" not in python_file:
        raise ControlError("Python binary identity differs")
    if not exact_value(audit_python_inputs(python_snapshot), python_receipt):
        raise ControlError("snapshotted Python inputs changed during build")
    if not exact_value(audit_python_inputs(python_input), python_receipt):
        raise ControlError("Python source inputs changed during build")
    rechecked_guest, rechecked_kernel, rechecked_modules = audit_guest_package_snapshot(
        guest_package_snapshot,
        guest_root,
        signed_packages_data,
    )
    if (
        not exact_value(rechecked_guest, guest_supply_chain)
        or rechecked_kernel != kernel_data
        or rechecked_modules != signed_modules
    ):
        raise ControlError("guest signed-package inputs changed during build")
    return {
        "kernel": identity_bytes(kernel_data),
        "kernel_snapshot": {
            "relative_path": str(kernel.relative_to(output)),
            **identity_bytes(kernel_data),
        },
        "init": identity(init),
        "init_file": init_file.split(": ", 1)[-1],
        "python": identity(rootfs / "usr/bin/python3.13"),
        "python_file": python_file.split(": ", 1)[-1],
        "python_supply_chain": python_receipt,
        "guest_supply_chain": guest_supply_chain,
        "sources": {name: {"size": len(data), "sha256": sha256_bytes(data)} for name, data in source_data.items()},
        "guest_source_audit": guest_source_audit,
        "config": config,
        "config_receipt": identity(rootfs / "p318-qemu-config.json"),
        "modules": module_receipts,
        "initramfs": identity(initramfs),
        "compile_output": compile_result.stdout.decode("utf-8", "replace"),
    }


def qemu_execution_environment(qemu_root: Path) -> dict[str, str]:
    library_root = qemu_root / "usr/lib/x86_64-linux-gnu"
    return {
        "LANG": "C",
        "LC_ALL": "C",
        "LD_LIBRARY_PATH": str(library_root),
        "PATH": "/usr/bin:/bin",
        "QEMU_MODULE_DIR": str(library_root / "qemu-empty"),
        "TZ": "UTC0",
    }


def qemu_command(
    qemu_root: Path,
    output: Path,
    interpreter_name: str,
    info_fd: int | None = None,
) -> tuple[list[str], dict[str, str]]:
    binary = qemu_root / "usr/bin/qemu-system-aarch64"
    launcher = qemu_root / "usr/bin/bwrap"
    library_root = qemu_root / "usr/lib/x86_64-linux-gnu"
    interpreter = library_root / interpreter_name
    module_root = library_root / "qemu-empty"
    if (
        not binary.is_file()
        or not launcher.is_file()
        or not interpreter.is_file()
        or not module_root.is_dir()
        or any(module_root.iterdir())
    ):
        raise ControlError("QEMU execution snapshot unavailable")
    sandbox_qemu_root = SANDBOX_OUTPUT / qemu_root.relative_to(output)
    sandbox_library_root = sandbox_qemu_root / "usr/lib/x86_64-linux-gnu"
    sandbox_binary = sandbox_qemu_root / "usr/bin/qemu-system-aarch64"
    sandbox_interpreter = sandbox_library_root / interpreter_name
    sandbox_kernel = SANDBOX_OUTPUT / "input-snapshots/guest" / f"vmlinuz-{KERNEL_VERSION}"
    sandbox_initramfs = SANDBOX_OUTPUT / "p318-cdc-acm-qemu-e2e.cpio"
    sandbox_arguments = [
        "--unshare-all",
        "--as-pid-1",
        "--die-with-parent",
        "--new-session",
    ]
    if info_fd is not None:
        sandbox_arguments += ["--info-fd", str(info_fd)]
    sandbox_arguments += [
        "--clearenv",
        "--setenv",
        "LANG",
        "C",
        "--setenv",
        "LC_ALL",
        "C",
        "--setenv",
        "TZ",
        "UTC0",
        "--setenv",
        "LD_LIBRARY_PATH",
        str(sandbox_library_root),
        "--setenv",
        "PATH",
        "/nonexistent",
        "--setenv",
        "QEMU_MODULE_DIR",
        str(sandbox_library_root / "qemu-empty"),
        "--ro-bind",
        str(output),
        str(SANDBOX_OUTPUT),
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/etc",
        "--dir",
        "/sys",
        "--dir",
        "/var",
        "--dir",
        "/run",
        "--chdir",
        "/",
        "--",
        str(sandbox_interpreter),
        "--library-path",
        str(sandbox_library_root),
        "--argv0",
        str(sandbox_binary),
        str(sandbox_binary),
        "-M",
        "virt",
        "-cpu",
        "cortex-a57",
        "-smp",
        "2",
        "-m",
        "768M",
        "-display",
        "none",
        "-audio",
        "none",
        "-serial",
        "stdio",
        "-monitor",
        "none",
        "-no-reboot",
        "-no-user-config",
        "-nodefaults",
        "-nic",
        "none",
        "-kernel",
        str(sandbox_kernel),
        "-initrd",
        str(sandbox_initramfs),
        "-append",
        "console=ttyAMA0 rdinit=/init panic=-1 loglevel=6",
    ]
    return (
        [
            str(interpreter),
            "--library-path",
            str(library_root),
            "--argv0",
            str(launcher),
            str(launcher),
            *sandbox_arguments,
        ],
        qemu_execution_environment(qemu_root),
    )


def qemu_source_environment(qemu_root: Path) -> dict[str, str]:
    library_root = qemu_root / "usr/lib/x86_64-linux-gnu"
    return {
        "LANG": "C",
        "LC_ALL": "C",
        "LD_LIBRARY_PATH": str(library_root),
        "PATH": "/usr/bin:/bin",
        "QEMU_MODULE_DIR": str(library_root / "qemu"),
        "TZ": "UTC0",
    }


def loader_closure(
    binary: Path, environment: dict[str, str], label: str
) -> dict[str, dict[str, Any]]:
    output = run(["ldd", str(binary)], env=environment).stdout
    closure: dict[str, dict[str, Any]] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("linux-vdso.so.1 "):
            continue
        indirect = re.fullmatch(r"(?P<name>\S+) => (?P<path>/\S+) \(0x[0-9a-f]+\)", line)
        direct = re.fullmatch(r"(?P<path>/\S+) \(0x[0-9a-f]+\)", line)
        if "not found" in line or (indirect is None and direct is None):
            raise ControlError(f"{label} loader closure line differs: {line}")
        match = indirect or direct
        assert match is not None
        resolved = Path(match.group("path")).resolve(strict=True)
        if not resolved.is_file() or resolved.is_symlink():
            raise ControlError(f"{label} loader closure is not a regular file")
        name = indirect.group("name") if indirect is not None else resolved.name
        if name in closure:
            raise ControlError(f"{label} loader closure name repeats")
        closure[name] = {"path": str(resolved), **identity(resolved)}
    if not closure:
        raise ControlError(f"{label} loader closure is empty")
    return closure


def qemu_loader_closure(qemu_root: Path) -> dict[str, dict[str, Any]]:
    binary = qemu_root / "usr/bin/qemu-system-aarch64"
    return loader_closure(binary, qemu_source_environment(qemu_root), "QEMU")


def qemu_authority(qemu_root: Path) -> dict[str, Any]:
    binary = qemu_root / "usr/bin/qemu-system-aarch64"
    library_root = qemu_root / "usr/lib/x86_64-linux-gnu"
    if not binary.is_file() or not library_root.is_dir():
        raise ControlError("QEMU authority is unavailable")
    environment = qemu_source_environment(qemu_root)
    version = run([str(binary), "--version"], env=environment).stdout.splitlines()
    if not version or version[0] != "QEMU emulator version 10.2.1 (Debian 1:10.2.1+ds-1ubuntu3.1)":
        raise ControlError("QEMU version differs")
    if not BWRAP.is_file():
        raise ControlError("bubblewrap sandbox launcher is unavailable")
    bwrap_version = run([str(BWRAP), "--version"], env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}).stdout.strip()
    if bwrap_version != BWRAP_VERSION:
        raise ControlError("bubblewrap version differs")
    return {
        "binary": {"path": str(binary.resolve(strict=True)), **identity(binary)},
        "version": version[0],
        "loader_closure": qemu_loader_closure(qemu_root),
        "explicit_external_data_directory": False,
        "ambient_environment_inherited": False,
        "external_module_directory_used": False,
        "sandbox_launcher": {
            "binary": {"path": str(BWRAP.resolve(strict=True)), **identity(BWRAP)},
            "version": bwrap_version,
            "loader_closure": loader_closure(
                BWRAP,
                {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                "bubblewrap",
            ),
        },
    }


def prepare_qemu_snapshot(
    qemu_root: Path, output: Path
) -> tuple[dict[str, Any], Path]:
    source = qemu_authority(qemu_root)
    execution_root = output / "input-snapshots" / "qemu"
    binary_target = execution_root / "usr/bin/qemu-system-aarch64"
    binary_source = Path(source["binary"]["path"])
    binary_data = snapshot_file(
        binary_source,
        binary_target,
        "QEMU binary",
        2**28,
        0o555,
    )
    if identity_bytes(binary_data) != {
        "size": source["binary"]["size"],
        "sha256": source["binary"]["sha256"],
    }:
        raise ControlError("QEMU binary changed before snapshot")

    launcher_source = source["sandbox_launcher"]["binary"]
    launcher_target = execution_root / "usr/bin/bwrap"
    launcher_data = snapshot_file(
        Path(launcher_source["path"]),
        launcher_target,
        "bubblewrap sandbox launcher",
        2**24,
        0o555,
    )
    if identity_bytes(launcher_data) != {
        "size": launcher_source["size"],
        "sha256": launcher_source["sha256"],
    }:
        raise ControlError("bubblewrap changed before snapshot")

    library_root = execution_root / "usr/lib/x86_64-linux-gnu"
    snapshot_libraries: dict[str, dict[str, Any]] = {}
    interpreter_names: list[str] = []
    qemu_loader_names = tuple(sorted(source["loader_closure"]))
    launcher_loader_names = tuple(
        sorted(source["sandbox_launcher"]["loader_closure"])
    )
    merged_libraries: dict[str, dict[str, Any]] = {}
    for closure in (
        source["loader_closure"],
        source["sandbox_launcher"]["loader_closure"],
    ):
        for name, expected in closure.items():
            prior = merged_libraries.get(name)
            if prior is not None and not exact_value(prior, expected):
                raise ControlError(f"loader name resolves to different bytes: {name}")
            merged_libraries[name] = expected
    for name, expected in sorted(merged_libraries.items()):
        if Path(name).name != name:
            raise ControlError("execution loader name is not a basename")
        target = library_root / name
        data = snapshot_file(
            Path(expected["path"]),
            target,
            f"execution loader input {name}",
            2**28,
            0o555 if name.startswith("ld-linux-") else 0o444,
        )
        found = identity_bytes(data)
        if found != {"size": expected["size"], "sha256": expected["sha256"]}:
            raise ControlError(f"execution loader input changed before snapshot: {name}")
        snapshot_libraries[name] = {
            "path": str(SANDBOX_OUTPUT / target.relative_to(output)),
            **found,
        }
        if name.startswith("ld-linux-"):
            interpreter_names.append(name)
    if len(interpreter_names) != 1:
        raise ControlError("QEMU interpreter multiplicity differs")
    (library_root / "qemu-empty").mkdir()

    snapshot = {
        "root": str(SANDBOX_OUTPUT / execution_root.relative_to(output)),
        "binary": {
            "path": str(SANDBOX_OUTPUT / binary_target.relative_to(output)),
            **identity_bytes(binary_data),
        },
        "sandbox_launcher": {
            "path": str(SANDBOX_OUTPUT / launcher_target.relative_to(output)),
            **identity_bytes(launcher_data),
        },
        "loader_closure": snapshot_libraries,
        "qemu_loader_names": list(qemu_loader_names),
        "sandbox_launcher_loader_names": list(launcher_loader_names),
        "interpreter_name": interpreter_names[0],
        "module_directory_empty": True,
    }
    interpreter = library_root / snapshot["interpreter_name"]
    version_environment = qemu_execution_environment(execution_root)
    version = run(
        [
            str(interpreter),
            "--library-path",
            str(library_root),
            "--argv0",
            str(binary_target),
            str(binary_target),
            "--version",
        ],
        env=version_environment,
    ).stdout.splitlines()
    if not version or version[0] != source["version"]:
        raise ControlError("snapshotted QEMU version differs")
    launcher_version = run(
        [
            str(interpreter),
            "--library-path",
            str(library_root),
            "--argv0",
            str(launcher_target),
            str(launcher_target),
            "--version",
        ],
        env=version_environment,
    ).stdout.strip()
    if launcher_version != source["sandbox_launcher"]["version"]:
        raise ControlError("snapshotted bubblewrap version differs")
    return {"source": source, "execution_snapshot": snapshot}, execution_root


def mapped_regular_files(
    maps_data: bytes, output: Path
) -> dict[str, dict[str, Any]]:
    try:
        lines = maps_data.decode("utf-8", "strict").splitlines()
    except UnicodeError as exc:
        raise ControlError("QEMU maps are not UTF-8") from exc
    mapped: dict[str, dict[str, Any]] = {}
    for line in lines:
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or not fields[5].startswith("/"):
            continue
        if fields[5].endswith(" (deleted)"):
            raise ControlError("QEMU mapped a deleted file")
        raw_path = Path(fields[5])
        try:
            if raw_path == SANDBOX_OUTPUT or SANDBOX_OUTPUT in raw_path.parents:
                relative = raw_path.relative_to(SANDBOX_OUTPUT)
                resolved = (output / relative).resolve(strict=True)
                logical = str(raw_path)
            elif raw_path == output or output in raw_path.parents:
                relative = raw_path.relative_to(output)
                resolved = raw_path.resolve(strict=True)
                logical = str(SANDBOX_OUTPUT / relative)
            else:
                resolved = raw_path.resolve(strict=True)
                logical = str(resolved)
        except OSError as exc:
            raise ControlError("QEMU mapped path cannot be reopened") from exc
        if not resolved.is_file():
            continue
        key = logical
        found = {"path": logical, **identity(resolved)}
        if key in mapped and mapped[key] != found:
            raise ControlError("QEMU mapped file identity changed")
        mapped[key] = found
    if not mapped:
        raise ControlError("QEMU mapped-file closure is empty")
    return mapped


def capture_process_maps(pid: int, output: Path) -> bytes:
    path = Path("/proc") / str(pid) / "maps"
    for _ in range(3):
        first = path.read_bytes()
        second = path.read_bytes()
        if first == second:
            mapped_regular_files(first, output)
            return first
    raise ControlError("QEMU process maps changed during capture")


def audit_qemu_mapped_closure(
    declared: dict[str, Any], maps_data: bytes, output: Path
) -> dict[str, dict[str, Any]]:
    return audit_mapped_closure(
        declared,
        maps_data,
        output,
        binary_key="binary",
        loader_names_key="qemu_loader_names",
        label="QEMU",
    )


def audit_mapped_closure(
    declared: dict[str, Any],
    maps_data: bytes,
    output: Path,
    *,
    binary_key: str,
    loader_names_key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    mapped = mapped_regular_files(maps_data, output)
    binary = declared.get(binary_key)
    libraries = declared.get("loader_closure")
    loader_names = declared.get(loader_names_key)
    if (
        type(binary) is not dict
        or type(libraries) is not dict
        or type(loader_names) is not list
        or any(type(name) is not str for name in loader_names)
        or not set(loader_names).issubset(libraries)
    ):
        raise ControlError(f"{label} execution snapshot declaration differs")
    required = {binary.get("path")} | {
        libraries[name].get("path")
        for name in loader_names
        if name in libraries and type(libraries[name]) is dict
    }
    if None in required or not required or set(mapped) != required:
        raise ControlError(f"{label} actual maps omit declared loader closure")
    for value in [binary, *(libraries[name] for name in loader_names)]:
        path = value["path"]
        if not exact_value(mapped[path], value):
            raise ControlError(f"{label} mapped identity differs from snapshot")
    return mapped


def audit_launcher_mapped_closure(
    declared: dict[str, Any], maps_data: bytes, output: Path
) -> dict[str, dict[str, Any]]:
    return audit_mapped_closure(
        declared,
        maps_data,
        output,
        binary_key="sandbox_launcher",
        loader_names_key="sandbox_launcher_loader_names",
        label="bubblewrap",
    )


def stable_proc_read(path: Path, label: str) -> bytes:
    for _ in range(5):
        try:
            first = path.read_bytes()
            second = path.read_bytes()
        except OSError as exc:
            raise ControlError(f"{label} unavailable") from exc
        if first == second and first:
            return first
    raise ControlError(f"{label} changed during capture")


def audit_sandbox_mountinfo(data: bytes) -> dict[str, Any]:
    try:
        lines = data.decode("utf-8", "strict").splitlines()
    except UnicodeError as exc:
        raise ControlError("sandbox mountinfo is not UTF-8") from exc
    mounts: dict[str, dict[str, Any]] = {}
    for line in lines:
        fields = line.split()
        if "-" not in fields or len(fields) < 10:
            raise ControlError("sandbox mountinfo line differs")
        separator = fields.index("-")
        if separator + 2 >= len(fields):
            raise ControlError("sandbox mountinfo separator differs")
        mountpoint = fields[4]
        if mountpoint in mounts:
            raise ControlError("sandbox mountpoint repeats")
        mounts[mountpoint] = {
            "filesystem": fields[separator + 1],
            "read_only": "ro" in fields[5].split(","),
        }
    expected_points = {
        "/",
        "/execution",
        "/proc",
        "/dev",
        "/dev/null",
        "/dev/zero",
        "/dev/full",
        "/dev/random",
        "/dev/urandom",
        "/dev/tty",
        "/dev/pts",
        "/tmp",
    }
    if set(mounts) != expected_points:
        raise ControlError("sandbox mountpoint set differs")
    if (
        mounts["/"]["filesystem"] != "tmpfs"
        or mounts["/proc"]["filesystem"] != "proc"
        or mounts["/dev"]["filesystem"] != "tmpfs"
        or mounts["/tmp"]["filesystem"] != "tmpfs"
        or mounts["/execution"]["read_only"] is not True
    ):
        raise ControlError("sandbox mount semantics differ")
    return {
        "mountpoint_count": len(mounts),
        "execution_read_only": True,
        "root_tmpfs": True,
        "isolated_procfs": True,
        "minimal_dev": True,
        "tmp_is_tmpfs": True,
    }


def capture_sandbox_state(
    pid: int, output: Path
) -> tuple[bytes, dict[str, Any]]:
    proc = Path("/proc") / str(pid)
    root = proc / "root"
    for _ in range(100):
        try:
            empty = {
                name: tuple(sorted(path.name for path in (root / name).iterdir()))
                for name in ("etc", "sys", "var", "run")
            }
            execution_stat = (root / "execution").stat()
            output_stat = output.stat()
            if (
                all(not entries for entries in empty.values())
                and (execution_stat.st_dev, execution_stat.st_ino)
                == (output_stat.st_dev, output_stat.st_ino)
            ):
                break
        except OSError:
            pass
        time.sleep(0.02)
    else:
        raise ControlError("QEMU sandbox root did not become ready")

    mount_namespace = os.readlink(proc / "ns/mnt")
    network_namespace = os.readlink(proc / "ns/net")
    if (
        mount_namespace == os.readlink("/proc/self/ns/mnt")
        or network_namespace == os.readlink("/proc/self/ns/net")
        or (root / "usr").exists()
    ):
        raise ControlError("QEMU sandbox namespace isolation differs")
    absent = (
        "etc/gnutls/config",
        "etc/libnl/classid",
        "etc/localtime",
        "etc/selinux/config",
        "sys/bus/nd/devices",
        "var/lib/crypto-config/profiles/current/gnutls.conf",
    )
    if any((root / path).exists() for path in absent):
        raise ControlError("QEMU sandbox exposes an ambient configuration input")
    mountinfo = stable_proc_read(proc / "mountinfo", "QEMU sandbox mountinfo")
    mount_audit = audit_sandbox_mountinfo(mountinfo)
    return mountinfo, {
        **mount_audit,
        "empty_configuration_directories": ["/etc", "/run", "/sys", "/var"],
        "ambient_configuration_paths_absent": [f"/{path}" for path in absent],
        "execution_bind_matches_output_inode": True,
        "mount_namespace_isolated": True,
        "network_namespace_isolated": True,
        "host_root_usr_absent": True,
        "host_kernel_runtime_interfaces_byte_frozen": False,
    }


def read_bwrap_info(descriptor: int, deadline: float) -> dict[str, int]:
    chunks: list[bytes] = []
    while time.monotonic() < deadline:
        readable, _, _ = select.select([descriptor], [], [], 0.1)
        if not readable:
            continue
        chunk = os.read(descriptor, 4096)
        if not chunk:
            break
        chunks.append(chunk)
    value = strict_json_loads(b"".join(chunks))
    expected_keys = {
        "child-pid",
        "cgroup-namespace",
        "ipc-namespace",
        "mnt-namespace",
        "net-namespace",
        "pid-namespace",
        "uts-namespace",
    }
    if (
        type(value) is not dict
        or set(value) != expected_keys
        or any(type(value[key]) is not int or value[key] <= 0 for key in expected_keys)
    ):
        raise ControlError("bubblewrap child identity differs")
    return value


def audit_qemu_execution_snapshot(
    snapshot: dict[str, Any], output: Path
) -> dict[str, Any]:
    if type(snapshot) is not dict or set(snapshot) != {
        "root",
        "binary",
        "sandbox_launcher",
        "loader_closure",
        "qemu_loader_names",
        "sandbox_launcher_loader_names",
        "interpreter_name",
        "module_directory_empty",
    }:
        raise ControlError("QEMU execution snapshot shape differs")
    local_root = (output / "input-snapshots/qemu").resolve(strict=True)
    expected_root = SANDBOX_OUTPUT / "input-snapshots/qemu"
    if snapshot.get("root") != str(expected_root):
        raise ControlError("QEMU execution snapshot root differs")
    binary_path = local_root / "usr/bin/qemu-system-aarch64"
    binary = snapshot.get("binary")
    if type(binary) is not dict or binary.get("path") != str(
        expected_root / "usr/bin/qemu-system-aarch64"
    ):
        raise ControlError("QEMU execution binary declaration differs")
    require_receipt(
        binary_path,
        {"size": binary.get("size"), "sha256": binary.get("sha256")},
        "QEMU execution binary",
    )
    launcher_path = local_root / "usr/bin/bwrap"
    launcher = snapshot.get("sandbox_launcher")
    if type(launcher) is not dict or launcher.get("path") != str(
        expected_root / "usr/bin/bwrap"
    ):
        raise ControlError("bubblewrap execution declaration differs")
    require_receipt(
        launcher_path,
        {"size": launcher.get("size"), "sha256": launcher.get("sha256")},
        "bubblewrap execution binary",
    )
    libraries = snapshot.get("loader_closure")
    if type(libraries) is not dict or not libraries:
        raise ControlError("QEMU execution loader closure differs")
    library_root = local_root / "usr/lib/x86_64-linux-gnu"
    sandbox_library_root = expected_root / "usr/lib/x86_64-linux-gnu"
    for name, receipt in libraries.items():
        if type(name) is not str or Path(name).name != name or type(receipt) is not dict:
            raise ControlError("QEMU execution loader entry differs")
        path = library_root / name
        if receipt.get("path") != str(sandbox_library_root / name):
            raise ControlError("QEMU execution loader path differs")
        require_receipt(
            path,
            {"size": receipt.get("size"), "sha256": receipt.get("sha256")},
            f"QEMU execution loader {name}",
        )
    interpreter = snapshot.get("interpreter_name")
    if (
        type(interpreter) is not str
        or interpreter not in libraries
        or not interpreter.startswith("ld-linux-")
    ):
        raise ControlError("QEMU execution interpreter differs")
    qemu_names = snapshot.get("qemu_loader_names")
    launcher_names = snapshot.get("sandbox_launcher_loader_names")
    if (
        type(qemu_names) is not list
        or type(launcher_names) is not list
        or qemu_names != sorted(qemu_names)
        or launcher_names != sorted(launcher_names)
        or not set(qemu_names).issubset(libraries)
        or not set(launcher_names).issubset(libraries)
    ):
        raise ControlError("execution loader-name partitions differ")
    empty_modules = library_root / "qemu-empty"
    if (
        snapshot.get("module_directory_empty") is not True
        or not empty_modules.is_dir()
        or any(empty_modules.iterdir())
    ):
        raise ControlError("QEMU execution module directory differs")
    return snapshot


def run_qemu(
    *, qemu_root: Path, output: Path, timeout_sec: int, interpreter_name: str
) -> tuple[bytes, bytes, bytes, bytes, dict[str, Any], str]:
    info_read, info_write = os.pipe()
    command, environment = qemu_command(
        qemu_root,
        output,
        interpreter_name,
        info_write,
    )
    try:
        process = subprocess.Popen(
            command,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            pass_fds=(info_write,),
        )
    finally:
        os.close(info_write)
    assert process.stdout is not None
    chunks: list[bytes] = []
    observed = b""
    deadline = time.monotonic() + timeout_sec
    verdict = "TIMEOUT_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0"
    maps_data = b""
    launcher_maps_data = b""
    mountinfo_data = b""
    sandbox_state: dict[str, Any] = {}
    try:
        info = read_bwrap_info(info_read, min(deadline, time.monotonic() + 5.0))
        qemu_pid = info["child-pid"]
        launcher_maps_data = capture_process_maps(process.pid, output)
        mountinfo_data, sandbox_state = capture_sandbox_state(qemu_pid, output)
        sandbox_state["child_pid_from_bwrap_info"] = True
        while time.monotonic() < deadline:
            readable, _, _ = select.select([process.stdout.fileno()], [], [], 1.0)
            if not readable:
                if process.poll() is not None:
                    break
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            print(chunk.decode("utf-8", "replace"), end="")
            chunks.append(chunk)
            observed += chunk
            complete = complete_console_lines(observed)
            terminals = [
                line for line in complete if line.startswith(TERMINAL_LINE_PREFIX)
            ]
            if terminals:
                verdict = (
                    VERDICT
                    if terminals == [PASS_LINE]
                    else "FAIL_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0"
                )
                maps_data = capture_process_maps(qemu_pid, output)
                break
    finally:
        os.close(info_read)
        process.terminate()
        try:
            tail, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            tail, _ = process.communicate(timeout=5)
        if tail:
            print(tail.decode("utf-8", "replace"), end="")
            chunks.append(tail)
    return (
        b"".join(chunks),
        maps_data,
        launcher_maps_data,
        mountinfo_data,
        sandbox_state,
        verdict,
    )


def audit_console(log_data: bytes, config: dict[str, str]) -> dict[str, Any]:
    log_data.decode("utf-8", "strict")
    lines = complete_console_lines(log_data)
    trailing = b"" if log_data.endswith(b"\n") else log_data.rsplit(b"\n", 1)[-1]
    control_prefixes = (TERMINAL_LINE_PREFIX, b"P318_QEMU observer=")
    if trailing and any(
        trailing.startswith(prefix) or prefix.startswith(trailing)
        for prefix in control_prefixes
    ):
        raise ControlError("QEMU E2E console has an incomplete control tail")
    if not isinstance(config, dict) or set(config) != {
        "banner_hex",
        "manufacturer",
        "product",
        "serial",
        "usb_product_id",
        "usb_vendor_id",
    }:
        raise ControlError("QEMU E2E config differs")
    try:
        banner = bytes.fromhex(config["banner_hex"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ControlError("QEMU E2E banner config differs") from exc
    required = (
        b"P318_QEMU stage=pre-bind-banner status=PASS banner_bytes=49",
        b"P318_QEMU stage=dummy-configured status=PASS",
        (
            b"P318_QEMU observer=PASS classification=accepted banner_bytes=49 "
            + f"banner_sha256={sha256_bytes(banner)}".encode("ascii")
        ),
        PASS_LINE,
    )
    if any(lines.count(token) != 1 for token in required):
        raise ControlError("QEMU E2E console markers differ")
    terminals = tuple(
        line for line in lines if line.startswith(TERMINAL_LINE_PREFIX)
    )
    if terminals != (PASS_LINE,) or log_data.count(PASS_LINE) != 1:
        raise ControlError("QEMU E2E terminal marker multiplicity differs")
    if any(
        line.startswith((b"P318_QEMU observer=FAIL", FAIL_LINE_PREFIX))
        for line in lines
    ):
        raise ControlError("QEMU E2E console contains failure")
    if b"Kernel panic" in log_data:
        raise ControlError("QEMU E2E console contains kernel panic")
    module_lines = tuple(
        line for line in lines if line.startswith(b"P318_QEMU module=")
    )
    expected_module_lines = tuple(
        f"P318_QEMU module={name} status=PASS".encode("ascii")
        for name in MODULES
    )
    if module_lines != expected_module_lines:
        raise ControlError("QEMU E2E exact module sequence differs")
    return {
        "banner_size": len(banner),
        "banner_sha256": sha256_bytes(banner),
        "pre_bind_queue_before_observer_process": True,
        "dummy_hcd_transport": True,
        "real_python_selector_open_read_receipt": True,
        "terminal_complete_line": True,
        "accepted": True,
    }


def execute(
    *, repo: Path, guest_root: Path, qemu_root: Path, python_input: Path, output: Path, timeout_sec: int
) -> dict[str, Any]:
    build = build_initramfs(
        repo=repo,
        guest_root=guest_root,
        python_input=python_input,
        output=output,
    )
    qemu_receipt, qemu_execution_root = prepare_qemu_snapshot(qemu_root, output)
    audit_qemu_execution_snapshot(qemu_receipt["execution_snapshot"], output)
    build["qemu"] = qemu_receipt
    (
        log_data,
        maps_data,
        launcher_maps_data,
        mountinfo_data,
        sandbox_state,
        verdict,
    ) = run_qemu(
        qemu_root=qemu_execution_root,
        output=output,
        timeout_sec=timeout_sec,
        interpreter_name=qemu_receipt["execution_snapshot"]["interpreter_name"],
    )
    write_snapshot(output / "qemu-console.log", log_data)
    if not maps_data:
        raise ControlError("QEMU mapped-file receipt is absent")
    write_snapshot(output / "qemu-proc-maps.log", maps_data)
    write_snapshot(output / "bwrap-proc-maps.log", launcher_maps_data)
    write_snapshot(output / "qemu-mountinfo.log", mountinfo_data)
    build["qemu"]["proc_maps"] = identity_bytes(maps_data)
    build["qemu"]["observed_mapped_files"] = audit_qemu_mapped_closure(
        build["qemu"]["execution_snapshot"], maps_data, output
    )
    build["qemu"]["launcher_proc_maps"] = identity_bytes(launcher_maps_data)
    build["qemu"]["observed_launcher_mapped_files"] = audit_launcher_mapped_closure(
        build["qemu"]["execution_snapshot"], launcher_maps_data, output
    )
    build["qemu"]["sandbox_mountinfo"] = identity_bytes(mountinfo_data)
    if not exact_value(audit_sandbox_mountinfo(mountinfo_data), {
        key: sandbox_state[key]
        for key in (
            "execution_read_only",
            "isolated_procfs",
            "minimal_dev",
            "mountpoint_count",
            "root_tmpfs",
            "tmp_is_tmpfs",
        )
    }):
        raise ControlError("QEMU sandbox mount audit changed before publication")
    build["qemu"]["sandbox"] = sandbox_state
    transport = audit_console(log_data, build["config"]) if verdict == VERDICT else {}
    result = {
        "schema": SCHEMA,
        "verdict": verdict,
        "build": build,
        "console": {"size": len(log_data), "sha256": sha256_bytes(log_data)},
        "transport": transport,
        "scope": {
            "device_actions": 0,
            "actual_s22_usb": False,
            "actual_root_udev_guard": False,
            "dummy_hcd_to_real_python_end_to_end": verdict == VERDICT,
            "poll_packbits_47_48_qualified_by_this_control": False,
            "live_authority": False,
        },
    }
    write_snapshot(
        output / "result.json",
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return audit_current_output(
        repo=repo,
        guest_root=guest_root,
        qemu_root=qemu_root,
        python_input=python_input,
        output=output,
    )


def audit_preserved(
    *, result_data: bytes, log_data: bytes, current_sources: dict[str, bytes]
) -> dict[str, Any]:
    value = strict_json_loads(result_data)
    validate_result_shape(value)
    if (
        type(value.get("schema")) is not str
        or value["schema"] != SCHEMA
        or type(value.get("verdict")) is not str
        or value["verdict"] != VERDICT
    ):
        raise ControlError("preserved result authority differs")
    build = value.get("build")
    sources = build.get("sources")
    if type(sources) is not dict or set(sources) != set(SOURCE_PATHS):
        raise ControlError("preserved source receipts absent")
    if set(current_sources) != set(SOURCE_PATHS):
        raise ControlError("current source set differs")
    for name, data in current_sources.items():
        if not exact_value(
            sources.get(name), {"size": len(data), "sha256": sha256_bytes(data)}
        ):
            raise ControlError(f"preserved source differs: {name}")
    expected_config = derive_guest_config(
        current_sources["runtime"], current_sources["p260_harness"]
    )
    if not exact_value(build.get("config"), expected_config):
        raise ControlError("preserved derived config differs")
    if not exact_value(
        build.get("guest_source_audit"), audit_guest_source(current_sources["guest"])
    ):
        raise ControlError("preserved guest source audit differs")
    console = value.get("console")
    if not exact_value(
        console, {"size": len(log_data), "sha256": sha256_bytes(log_data)}
    ):
        raise ControlError("preserved console receipt differs")
    transport = audit_console(log_data, build.get("config"))
    if not exact_value(transport, value.get("transport")):
        raise ControlError("preserved transport result differs")
    scope = value.get("scope")
    expected_scope = {
        "actual_root_udev_guard": False,
        "actual_s22_usb": False,
        "device_actions": 0,
        "dummy_hcd_to_real_python_end_to_end": True,
        "live_authority": False,
        "poll_packbits_47_48_qualified_by_this_control": False,
    }
    if not exact_value(scope, expected_scope):
        raise ControlError("preserved scope differs")
    return value


def audit_current_output(
    *,
    repo: Path,
    guest_root: Path,
    qemu_root: Path,
    python_input: Path,
    output: Path,
) -> dict[str, Any]:
    result_data = stable_read(output / "result.json", "QEMU result", 2**20)
    log_data = stable_read(output / "qemu-console.log", "QEMU console", 2**20)
    value = audit_preserved(
        result_data=result_data,
        log_data=log_data,
        current_sources=current_source_data(repo),
    )
    build = value["build"]
    current_python = audit_python_inputs(python_input)
    if not exact_value(build.get("python_supply_chain"), current_python):
        raise ControlError("preserved Python supply chain differs")
    python_snapshot = output / "input-snapshots/python"
    if not exact_value(audit_python_inputs(python_snapshot), current_python):
        raise ControlError("preserved Python execution snapshot differs")
    signed_packages_data = stable_read(
        python_snapshot / "source" / PACKAGES_INDEX["filename"],
        "preserved signed Debian Packages",
        2**27,
    )
    guest_supply, signed_kernel, signed_modules = audit_guest_package_snapshot(
        output / "input-snapshots/guest-package",
        guest_root,
        signed_packages_data,
    )
    if not exact_value(build.get("guest_supply_chain"), guest_supply):
        raise ControlError("preserved guest signed-package supply chain differs")

    qemu = build["qemu"]
    if not exact_value(qemu.get("source"), qemu_authority(qemu_root)):
        raise ControlError("preserved QEMU source authority differs")
    snapshot = audit_qemu_execution_snapshot(qemu["execution_snapshot"], output)
    maps_data = stable_read(output / "qemu-proc-maps.log", "QEMU process maps", 2**20)
    if not exact_value(qemu.get("proc_maps"), identity_bytes(maps_data)):
        raise ControlError("preserved QEMU process maps receipt differs")
    observed = audit_qemu_mapped_closure(snapshot, maps_data, output)
    if not exact_value(qemu.get("observed_mapped_files"), observed):
        raise ControlError("preserved QEMU mapped-file closure differs")
    launcher_maps_data = stable_read(
        output / "bwrap-proc-maps.log", "bubblewrap process maps", 2**20
    )
    if not exact_value(
        qemu.get("launcher_proc_maps"), identity_bytes(launcher_maps_data)
    ):
        raise ControlError("preserved bubblewrap process maps receipt differs")
    launcher_observed = audit_launcher_mapped_closure(
        snapshot, launcher_maps_data, output
    )
    if not exact_value(
        qemu.get("observed_launcher_mapped_files"), launcher_observed
    ):
        raise ControlError("preserved bubblewrap mapped-file closure differs")
    mountinfo_data = stable_read(
        output / "qemu-mountinfo.log", "QEMU sandbox mountinfo", 2**20
    )
    if not exact_value(
        qemu.get("sandbox_mountinfo"), identity_bytes(mountinfo_data)
    ):
        raise ControlError("preserved sandbox mountinfo receipt differs")
    mount_audit = audit_sandbox_mountinfo(mountinfo_data)
    expected_sandbox = {
        **mount_audit,
        "ambient_configuration_paths_absent": [
            "/etc/gnutls/config",
            "/etc/libnl/classid",
            "/etc/localtime",
            "/etc/selinux/config",
            "/sys/bus/nd/devices",
            "/var/lib/crypto-config/profiles/current/gnutls.conf",
        ],
        "child_pid_from_bwrap_info": True,
        "empty_configuration_directories": ["/etc", "/run", "/sys", "/var"],
        "execution_bind_matches_output_inode": True,
        "host_kernel_runtime_interfaces_byte_frozen": False,
        "host_root_usr_absent": True,
        "mount_namespace_isolated": True,
        "network_namespace_isolated": True,
    }
    if not exact_value(qemu.get("sandbox"), expected_sandbox):
        raise ControlError("preserved QEMU sandbox state differs")

    rootfs = output / "rootfs"
    expected_config_data = (
        json.dumps(build["config"], sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )
    if stable_read(
        rootfs / "p318-qemu-config.json", "rootfs QEMU config", 4096
    ) != expected_config_data:
        raise ControlError("preserved rootfs config content differs")
    current_artifacts = {
        "kernel": identity_bytes(signed_kernel),
        "init": identity(rootfs / "init"),
        "python": identity(rootfs / "usr/bin/python3.13"),
        "config_receipt": identity(rootfs / "p318-qemu-config.json"),
        "initramfs": identity(output / "p318-cdc-acm-qemu-e2e.cpio"),
    }
    for name, found in current_artifacts.items():
        if not exact_value(build.get(name), found):
            raise ControlError(f"preserved artifact differs: {name}")
    kernel_snapshot = build["kernel_snapshot"]
    expected_kernel_relative = f"input-snapshots/guest/vmlinuz-{KERNEL_VERSION}"
    if kernel_snapshot.get("relative_path") != expected_kernel_relative:
        raise ControlError("preserved kernel snapshot path differs")
    kernel_snapshot_data = require_receipt(
        output / expected_kernel_relative,
        {"size": kernel_snapshot.get("size"), "sha256": kernel_snapshot.get("sha256")},
        "guest kernel execution snapshot",
    )
    if not exact_value(identity_bytes(kernel_snapshot_data), build["kernel"]):
        raise ControlError("guest kernel source and execution snapshot differ")
    source_copies = {
        "guest": rootfs / "s22plus_fyg8_p318_cdc_acm_qemu_guest.py",
        "observer": rootfs / "device_action_cdc_acm_observer_v1.py",
    }
    for name, path in source_copies.items():
        if not exact_value(identity(path), build["sources"][name]):
            raise ControlError(f"preserved rootfs source differs: {name}")

    modules = build.get("modules")
    if not isinstance(modules, dict) or set(modules) != set(MODULES):
        raise ControlError("preserved module set differs")
    for name in MODULES:
        source_data, decompressed = signed_modules[name]
        expected = {
            "source": identity_bytes(source_data),
            "decompressed": identity_bytes(decompressed),
        }
        if not exact_value(modules.get(name), expected):
            raise ControlError(f"preserved module authority differs: {name}")
        if not exact_value(identity(rootfs / "modules" / f"{name}.ko"), expected["decompressed"]):
            raise ControlError(f"preserved rootfs module differs: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--guest-root", type=Path, default=DEFAULT_GUEST_ROOT)
    parser.add_argument("--qemu-root", type=Path, default=DEFAULT_QEMU_ROOT)
    parser.add_argument("--python-input", type=Path, default=DEFAULT_PYTHON_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.timeout_sec <= 600:
        raise ControlError("timeout outside 30..600 seconds")
    root = args.repo.resolve()
    resolve = lambda path: path if path.is_absolute() else root / path
    paths = {
        "guest_root": resolve(args.guest_root),
        "qemu_root": resolve(args.qemu_root),
        "python_input": resolve(args.python_input),
        "output": resolve(args.output),
    }
    result = (
        audit_current_output(repo=root, **paths)
        if args.audit_only
        else execute(repo=root, timeout_sec=args.timeout_sec, **paths)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == VERDICT else 1


if __name__ == "__main__":
    raise SystemExit(main())
