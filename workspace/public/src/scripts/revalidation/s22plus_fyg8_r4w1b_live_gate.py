#!/usr/bin/env python3
"""One-shot FYG8 R4W1-B direct-PID1 retained-witness live gate.

Offline qualification is inert.  Connected read-only and live modes are
separately policy-gated.  The live path may transfer one exact boot-only
candidate, then must restore the exact Magisk boot and classify the first
rollback boot's byte-identical /proc/last_kmsg reads.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import shlex
import subprocess
import sys
import tarfile
import tempfile
import termios
import time
from pathlib import Path
from typing import Any

import s22plus_boot_only_live_core as core
import s22plus_fyg8_r3c0_live_gate as transport


SCHEMA = "s22plus_fyg8_r4w1b_live_gate_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1b_live_gate.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1b_live_gate.py")
CORE_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_boot_only_live_core.py"
)
CORE_TEST_RELATIVE = Path("tests/test_s22plus_boot_only_live_core.py")
STATIC_CHECKER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1b_candidate_static_checker.py"
)
STATIC_CHECKER_TEST_RELATIVE = Path(
    "tests/test_s22plus_fyg8_r4w1b_candidate_static_checker.py"
)
BUILDER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1b_candidate.py"
)
BUILD_PRIMITIVE_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_boot_slice.py"
)
CHECK_PRIMITIVE_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_boot_verify.py"
)
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_FYG8_R4W1B_AGENTS_EXCEPTION_DRAFT_2026-07-19.md"
)
POLICY_MARKER = "S22+ FYG8 R4W1-B direct-PID1 retained witness boot-only live gate"
CONNECTED_ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1B_CONNECTED_POLICY_STATE=ACTIVE"
LIVE_ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1B_POLICY_STATE=ACTIVE"
CONNECTED_ACK_TOKEN = "S22PLUS-FYG8-R4W1B-CONNECTED-READ-ONLY-DRY-RUN"
LIVE_ACK_TOKEN = "S22PLUS-FYG8-R4W1B-DIRECT-PID1-LIVE"
ROLLBACK_ACK_TOKEN = "S22PLUS-FYG8-R4W1B-MAGISK-ROLLBACK-FROM-DOWNLOAD"
NORMAL_DOWNLOAD_CONFIRMATION = "S22PLUS-FYG8-R4W1B-NORMAL-DOWNLOAD-CONFIRMED"

EXPECTED_CANDIDATE_BOOT_SIZE = 100_663_296
EXPECTED_CANDIDATE_BOOT_SHA256 = (
    "69690e6832bab2a422979054b51ad279222c14cbc369517433b55a785ed3d44d"
)
EXPECTED_CANDIDATE_LZ4_SIZE = 27_055_052
EXPECTED_CANDIDATE_LZ4_SHA256 = (
    "be2265ae72c584553945a82cdabc1ce36cc59cf6ee065c9675b97df9fc209c9a"
)
EXPECTED_CANDIDATE_AP_SIZE = 27_064_361
EXPECTED_CANDIDATE_AP_SHA256 = (
    "ae26340d69f7208ae3a8c0d135e3f65317b4d16b539d4e19c1613b7f15f0f2c5"
)
EXPECTED_MANIFEST_SIZE = 4_150
EXPECTED_MANIFEST_SHA256 = (
    "46c29171bfe640fb81b4dc36b8f342364c73055274145f413f29e0c8e36c65b0"
)
EXPECTED_STATIC_RESULT_SIZE = 30_004
EXPECTED_STATIC_RESULT_SHA256 = (
    "969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47"
)
EXPECTED_STATIC_CHECKER_SHA256 = (
    "922b05eaffd1b17d33f69376564cbeab008c0e84b8cb2a34464aad8f5896d0b4"
)
EXPECTED_STATIC_CHECKER_TEST_SHA256 = (
    "d0eb08ddb90c8569f858367f04d601eb4db59cc879bed8ceb157e7bc3b06105f"
)
EXPECTED_BUILDER_SHA256 = (
    "3d7b0cdcf5584c034589b713a85e15eb302932093b3721e8e65ee42242edf388"
)
EXPECTED_BUILD_PRIMITIVE_SHA256 = (
    "dd2bdcb42d12a4453eaeb8f81208c801c990536e7516d8bdeacc0b8a92e663e1"
)
EXPECTED_CHECK_PRIMITIVE_SHA256 = (
    "ebf2f0941324cf4e6204ab4526125e7b3b66356672bb10ad40f6625ab4563f17"
)
EXPECTED_TRANSPORT_SHA256 = (
    "f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4"
)
EXPECTED_STATIC_SCHEMA = "s22plus_fyg8_r4w1b_candidate_static_checker_v1"
EXPECTED_STATIC_VERDICT = "PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT"

EXPECTED_MAGISK_BOOT_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
EXPECTED_VENDOR_BOOT_SHA256 = (
    "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"
)
EXPECTED_DTBO_SHA256 = (
    "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
)
EXPECTED_RECOVERY_SHA256 = (
    "93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4"
)
EXPECTED_MAGISK_AP_SHA256 = (
    "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
)
EXPECTED_STOCK_AP_SHA256 = (
    "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94"
)
EXPECTED_ODIN_SIZE = 3_746_744
EXPECTED_ODIN_SHA256 = (
    "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
)
EXPECTED_FULL_FIRMWARE_SHA256 = (
    "f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8"
)
EXPECTED_MAGISK_AP_SIZE = 23_367_721
EXPECTED_STOCK_AP_SIZE = 100_669_481
EXPECTED_FULL_FIRMWARE_SIZE = 9_680_091_538
EXPECTED_STATIC_CHECKER_SIZE = 25_565
EXPECTED_STATIC_CHECKER_TEST_SIZE = 5_930
EXPECTED_BUILDER_SIZE = 14_597
EXPECTED_BUILD_PRIMITIVE_SIZE = 8_739
EXPECTED_CHECK_PRIMITIVE_SIZE = 26_866
EXPECTED_TRANSPORT_SIZE = 35_401

MARKER = (
    b"\n[[S22R4W1B|id=36dc5462adedcf136176f2ddcfee08a8|"
    b"phase=DIRECT_INIT_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)
MARKER_FAMILY = b"[[S22R4W1B|"
HISTORICAL_FAMILY = b"[[S22R4W1|"
FYG8_BANNER = b"5.10.226-android12-9-30958166-abS906NKSS7FYG8"
EXPECTED_BIND = (
    "/sys/bus/platform/drivers/samsung,kernel_log_buf/"
    "8.samsung,kernel_log_buf"
)
PSTORE_PATHS = (
    "/sys/fs/pstore/console-ramoops",
    "/sys/fs/pstore/console-ramoops-0",
)
MAX_OBSERVER_BYTES = 64 * 1024 * 1024
ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/\d+/\d+")

DEFAULT_CANDIDATE_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/reproduction-c"
)
DEFAULT_CANDIDATE_BOOT = DEFAULT_CANDIDATE_DIR / "boot.img"
DEFAULT_CANDIDATE_LZ4 = DEFAULT_CANDIDATE_DIR / "boot.img.lz4"
DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_DIR / "odin4/AP.tar.md5"
DEFAULT_MANIFEST = DEFAULT_CANDIDATE_DIR / "manifest.json"
DEFAULT_STATIC_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/static-check-result.json"
)
DEFAULT_MAGISK_AP = transport.DEFAULT_MAGISK_ROLLBACK_AP
DEFAULT_STOCK_AP = transport.DEFAULT_STOCK_ROLLBACK_AP
DEFAULT_FULL_FIRMWARE = Path(
    "workspace/private/inputs/firmware/"
    "SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac.zip"
)
DEFAULT_ODIN = transport.DEFAULT_ODIN
RUN_ROOT = Path("workspace/private/runs")
CONNECTED_PASS_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1b_connected_read_only_pass.json"
)
CONSUMED_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1b_live_exception_consumed.json"
)


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    return transport.repo_root()


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (root / value).resolve()


def helper_sha256(root: Path) -> str:
    return core.sha256_file(root / SCRIPT_RELATIVE)


def test_sha256(root: Path) -> str:
    return core.sha256_file(root / TEST_RELATIVE)


def core_sha256(root: Path) -> str:
    return core.sha256_file(root / CORE_RELATIVE)


def core_test_sha256(root: Path) -> str:
    return core.sha256_file(root / CORE_TEST_RELATIVE)


def require_identity(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise GateError(f"{label} is missing or indirect: {path}")
    receipt = core.hash_stable_file(path)
    if receipt != {"size": size, "sha256": digest}:
        raise GateError(f"{label} identity mismatch: {receipt}")
    return receipt


def require_sha(path: Path, digest: str, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise GateError(f"{label} is missing or indirect: {path}")
    receipt = core.hash_stable_file(path)
    if receipt["sha256"] != digest:
        raise GateError(f"{label} SHA mismatch: {receipt['sha256']}")
    return receipt


def tar_members(path: Path) -> list[str]:
    with tarfile.open(path) as archive:
        members = archive.getmembers()
    if any(not member.isfile() for member in members):
        raise GateError(f"AP contains a non-regular member: {path}")
    return [member.name for member in members]


def classify_marker(payload: bytes) -> dict[str, Any]:
    return core.classify_marker_family(
        payload,
        exact_marker=MARKER,
        family_prefix=MARKER_FAMILY,
        historical_family=HISTORICAL_FAMILY,
    )


def run_fresh_static_checker(root: Path, odin: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1b-live-static-") as temporary:
        output = Path(temporary) / "result.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(root / STATIC_CHECKER_RELATIVE),
                "--odin",
                str(odin),
                "--out",
                str(output),
            ],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
            check=False,
        )
        if completed.returncode != 0 or completed.stderr:
            raise GateError(
                f"fresh static checker failed rc={completed.returncode}: "
                f"{completed.stderr.strip()}"
            )
        receipt = require_identity(
            output,
            EXPECTED_STATIC_RESULT_SIZE,
            EXPECTED_STATIC_RESULT_SHA256,
            "fresh static result",
        )
        try:
            data = json.loads(output.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise GateError("fresh static result is invalid JSON") from exc
        if (
            data.get("schema") != EXPECTED_STATIC_SCHEMA
            or data.get("verdict") != EXPECTED_STATIC_VERDICT
            or data.get("blockers") != []
        ):
            raise GateError("fresh static result contract mismatch")
        return {**receipt, "schema": data["schema"], "verdict": data["verdict"]}


def verify_artifacts(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    odin = resolve(root, args.odin)
    identities = {
        "candidate_boot": require_identity(
            resolve(root, args.candidate_boot),
            EXPECTED_CANDIDATE_BOOT_SIZE,
            EXPECTED_CANDIDATE_BOOT_SHA256,
            "candidate raw boot",
        ),
        "candidate_lz4": require_identity(
            resolve(root, args.candidate_lz4),
            EXPECTED_CANDIDATE_LZ4_SIZE,
            EXPECTED_CANDIDATE_LZ4_SHA256,
            "candidate LZ4",
        ),
        "candidate_ap": require_identity(
            resolve(root, args.candidate_ap),
            EXPECTED_CANDIDATE_AP_SIZE,
            EXPECTED_CANDIDATE_AP_SHA256,
            "candidate AP",
        ),
        "manifest": require_identity(
            resolve(root, args.manifest),
            EXPECTED_MANIFEST_SIZE,
            EXPECTED_MANIFEST_SHA256,
            "candidate manifest",
        ),
        "static_result": require_identity(
            resolve(root, args.static_result),
            EXPECTED_STATIC_RESULT_SIZE,
            EXPECTED_STATIC_RESULT_SHA256,
            "pinned static result",
        ),
        "magisk_rollback_ap": require_sha(
            resolve(root, args.magisk_ap), EXPECTED_MAGISK_AP_SHA256, "Magisk rollback AP"
        ),
        "stock_cleanup_ap": require_sha(
            resolve(root, args.stock_ap), EXPECTED_STOCK_AP_SHA256, "stock cleanup AP"
        ),
        "odin": require_identity(
            odin, EXPECTED_ODIN_SIZE, EXPECTED_ODIN_SHA256, "Odin4"
        ),
        "full_firmware": require_sha(
            resolve(root, args.full_firmware),
            EXPECTED_FULL_FIRMWARE_SHA256,
            "full FYG8 stock firmware",
        ),
    }
    for label, path in (
        ("candidate AP", resolve(root, args.candidate_ap)),
        ("Magisk rollback AP", resolve(root, args.magisk_ap)),
        ("stock cleanup AP", resolve(root, args.stock_ap)),
    ):
        if tar_members(path) != ["boot.img.lz4"]:
            raise GateError(f"{label} is not exactly boot-only")
    source_pins = {
        "static_checker": require_sha(
            root / STATIC_CHECKER_RELATIVE,
            EXPECTED_STATIC_CHECKER_SHA256,
            "R4W1-B static checker",
        ),
        "static_checker_test": require_sha(
            root / STATIC_CHECKER_TEST_RELATIVE,
            EXPECTED_STATIC_CHECKER_TEST_SHA256,
            "R4W1-B static checker test",
        ),
        "builder": require_sha(
            root / BUILDER_RELATIVE, EXPECTED_BUILDER_SHA256, "R4W1-B builder"
        ),
        "build_primitive": require_sha(
            root / BUILD_PRIMITIVE_RELATIVE,
            EXPECTED_BUILD_PRIMITIVE_SHA256,
            "boot-slice primitive",
        ),
        "check_primitive": require_sha(
            root / CHECK_PRIMITIVE_RELATIVE,
            EXPECTED_CHECK_PRIMITIVE_SHA256,
            "boot verification primitive",
        ),
        "transport": require_sha(
            root / Path(transport.__file__).relative_to(root),
            EXPECTED_TRANSPORT_SHA256,
            "R3C0 transport source",
        ),
    }
    fresh = run_fresh_static_checker(root, odin)
    return {
        "target": TARGET,
        "identities": identities,
        "source_pins": source_pins,
        "fresh_static_checker": fresh,
        "ap_members": ["boot.img.lz4"],
    }


def verify_recovery_artifacts(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    odin = resolve(root, args.odin)
    result = {
        "magisk_rollback_ap": require_sha(
            resolve(root, args.magisk_ap), EXPECTED_MAGISK_AP_SHA256, "Magisk rollback AP"
        ),
        "stock_cleanup_ap": require_sha(
            resolve(root, args.stock_ap), EXPECTED_STOCK_AP_SHA256, "stock cleanup AP"
        ),
        "odin": require_identity(
            odin, EXPECTED_ODIN_SIZE, EXPECTED_ODIN_SHA256, "Odin4"
        ),
    }
    for label, path in (
        ("Magisk rollback AP", resolve(root, args.magisk_ap)),
        ("stock cleanup AP", resolve(root, args.stock_ap)),
    ):
        if tar_members(path) != ["boot.img.lz4"]:
            raise GateError(f"{label} is not exactly boot-only")
    return result


def policy_required_values(root: Path) -> tuple[str, ...]:
    return (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        helper_sha256(root),
        test_sha256(root),
        str(CORE_RELATIVE),
        core_sha256(root),
        core_test_sha256(root),
        CONNECTED_ACK_TOKEN,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        NORMAL_DOWNLOAD_CONFIRMATION,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_STATIC_RESULT_SHA256,
        EXPECTED_STATIC_CHECKER_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_AP_SHA256,
        EXPECTED_FULL_FIRMWARE_SHA256,
        EXPECTED_VENDOR_BOOT_SHA256,
    )


def parse_live_connected_evidence_binding(text: str) -> dict[str, Any]:
    pattern = re.compile(
        r"The load-bearing connected PASS record is\s+"
        r"`(?P<pass_path>[^`]+)`,\s+created at `(?P<created_at>[^`]+)`, size\s+"
        r"`(?P<pass_size>[1-9][0-9]*)`, SHA256\s+"
        r"`(?P<pass_sha>[0-9a-f]{64})`\. It binds connected result\s+"
        r"`(?P<result_path>[^`]+)`, size `(?P<result_size>[1-9][0-9]*)`, SHA256\s+"
        r"`(?P<result_sha>[0-9a-f]{64})`\."
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise GateError("R4W1-B live policy lacks one exact connected evidence binding")
    values = matches[0].groupdict()
    if values["pass_path"] != str(CONNECTED_PASS_STATE):
        raise GateError("R4W1-B live policy connected PASS path mismatch")
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
        values["created_at"],
    ):
        raise GateError("R4W1-B live policy connected timestamp is not canonical UTC")
    result_path = Path(values["result_path"])
    if (
        not re.fullmatch(r"[A-Za-z0-9._/-]+", values["result_path"])
        or result_path.is_absolute()
        or str(result_path) != values["result_path"]
        or ".." in result_path.parts
        or tuple(result_path.parts[:3]) != ("workspace", "private", "runs")
        or len(result_path.parts) < 5
        or result_path.name != "result.json"
    ):
        raise GateError("R4W1-B live policy connected result path is not canonical")
    return {
        "pass_path": values["pass_path"],
        "created_at_utc": values["created_at"],
        "pass_size": int(values["pass_size"]),
        "pass_sha256": values["pass_sha"],
        "result_path": values["result_path"],
        "result_size": int(values["result_size"]),
        "result_sha256": values["result_sha"],
    }


def policy_active(root: Path, *, connected: bool) -> bool:
    sentinel = CONNECTED_ACTIVE_SENTINEL if connected else LIVE_ACTIVE_SENTINEL
    try:
        text = (root / "AGENTS.md").read_text(encoding="utf-8")
    except OSError:
        return False
    active_line = re.compile(rf"(?m)^\s*`?{re.escape(sentinel)}`?\s*$")
    if len(active_line.findall(text)) != 1:
        return False
    if not all(value in text for value in policy_required_values(root)):
        return False
    if not connected:
        try:
            parse_live_connected_evidence_binding(text)
        except GateError:
            return False
    return True


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if path.is_symlink() or not path.is_file():
        raise GateError("R4W1-B policy draft is missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "DRAFT_INACTIVE",
        CONNECTED_ACTIVE_SENTINEL,
        LIVE_ACTIVE_SENTINEL,
        *policy_required_values(root),
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise GateError(f"R4W1-B policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": core.sha256_file(path),
        "helper_sha256": helper_sha256(root),
        "test_sha256": test_sha256(root),
        "core_sha256": core_sha256(root),
        "core_test_sha256": core_test_sha256(root),
        "connected_active": policy_active(root, connected=True),
        "live_active": policy_active(root, connected=False),
    }


def remote_text(serial: str, command: str, *, root: bool = False) -> str:
    return transport.adb_shell(serial, command, root=root, timeout=90).strip()


def sha256_output(value: str, label: str) -> str:
    fields = value.split()
    if not fields or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
        raise GateError(f"malformed remote SHA output: {label}")
    return fields[0]


def strict_odin_devices(odin: Path, log_path: Path, label: str) -> list[str]:
    result = transport.run([odin, "-l"], timeout=10.0)
    output = (result.stdout or "") + (result.stderr or "")
    raw_devices = sorted(set(ODIN_DEVICE_RE.findall(output)))
    devices = [device for device in raw_devices if Path(device).exists()]
    stale_devices = [device for device in raw_devices if device not in devices]
    transport.append_log(
        log_path,
        f"[{core.utc_now()}] {label} strict odin4 -l "
        f"rc={result.returncode} devices={devices} stale={stale_devices}",
    )
    transport.append_log(log_path, output)
    if result.returncode != 0:
        raise GateError(f"Odin enumeration failed rc={result.returncode}: {label}")
    if stale_devices:
        raise GateError(f"Odin enumeration returned stale endpoints: {stale_devices}")
    return devices


def current_android_exact(odin: Path, log_path: Path) -> tuple[str, dict[str, str]]:
    serial, values = transport.current_android()
    vendor_boot = sha256_output(
        remote_text(
            serial,
            "sha256sum /dev/block/by-name/vendor_boot",
            root=True,
        ),
        "vendor_boot",
    )
    if vendor_boot != EXPECTED_VENDOR_BOOT_SHA256:
        raise GateError("Android vendor_boot identity mismatch")
    if values.get("boot_sha256") != EXPECTED_MAGISK_BOOT_SHA256:
        raise GateError("Android Magisk boot identity mismatch")
    if values.get("dtbo_sha256") != EXPECTED_DTBO_SHA256:
        raise GateError("Android DTBO identity mismatch")
    if values.get("recovery_sha256") != EXPECTED_RECOVERY_SHA256:
        raise GateError("Android recovery identity mismatch")
    devices = strict_odin_devices(odin, log_path, "r4w1b-android-no-odin")
    if devices:
        raise GateError(f"Android state has Odin endpoint: {devices}")
    values["vendor_boot_sha256"] = vendor_boot
    return serial, values


def pstore_console_absent(serial: str) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for path in PSTORE_PATHS:
        quoted = shlex.quote(path)
        value = remote_text(
            serial, f"if test -e {quoted}; then echo present; else echo absent; fi"
        )
        if value not in {"present", "absent"}:
            raise GateError(f"ambiguous pstore state: {path}")
        result[path] = value == "absent"
    if not all(result.values()):
        raise GateError(f"pstore console would shadow retained observer: {result}")
    return result


def connected_preflight(
    root: Path, run_dir: Path, odin: Path
) -> tuple[str, dict[str, Any]]:
    if (root / CONSUMED_STATE).exists() or (root / CONSUMED_STATE).is_symlink():
        raise GateError("R4W1-B candidate exception is already consumed")
    serial, android = current_android_exact(odin, run_dir / "connected.log")
    state = remote_text(
        serial,
        "printf 'osrelease='; cat /proc/sys/kernel/osrelease; "
        "grep '^sec_log_buf ' /proc/modules; "
        f"test -L {shlex.quote(EXPECTED_BIND)} && echo bind_ok=1 || echo bind_ok=0; "
        "stat -c '%n:%s:%a' /proc/ap_klog /proc/last_kmsg",
        root=True,
    )
    required = (
        f"osrelease={transport.EXPECTED_RELEASE}",
        "sec_log_buf ",
        " Live ",
        "bind_ok=1",
        "/proc/ap_klog:",
        "/proc/last_kmsg:",
    )
    missing = [value for value in required if value not in state]
    if missing:
        raise GateError(f"retained observer baseline mismatch: {missing}")
    captures: dict[str, Any] = {}
    for name, command, read_count in (
        ("ap_klog", "cat /proc/ap_klog", 1),
        ("last_kmsg", "cat /proc/last_kmsg", 2),
    ):
        receipts: list[dict[str, Any]] = []
        payloads: list[bytes] = []
        for index in range(read_count):
            suffix = f"_{index + 1}" if read_count > 1 else ""
            path = run_dir / f"baseline_{name}{suffix}.bin"
            receipts.append(
                core.capture_adb_exec_out(
                    serial,
                    command,
                    path,
                    root=True,
                    timeout=120,
                    maximum=MAX_OBSERVER_BYTES,
                )
            )
            payload = core.read_stable_file(path, maximum=MAX_OBSERVER_BYTES)
            if not payload:
                raise GateError(f"baseline observer is empty: {name}")
            payloads.append(payload)
            if read_count > 1:
                time.sleep(0.25)
        byte_identical = all(payload == payloads[0] for payload in payloads[1:])
        if not byte_identical:
            raise GateError(f"baseline observer reads are not byte-identical: {name}")
        marker = classify_marker(payloads[0])
        if not marker["baseline_absent"] or marker["integrity_issue"]:
            raise GateError(f"R4W1-B marker family contaminates baseline {name}")
        captures[name] = {
            "reads": receipts,
            "read_count": read_count,
            "byte_identical": byte_identical,
            "read_to_eof": all(receipt["read_to_eof"] for receipt in receipts),
            "stderr_bytes": sum(receipt["stderr_bytes"] for receipt in receipts),
            "bytes": len(payloads[0]),
            "sha256": core.sha256_bytes(payloads[0]),
            "marker": marker,
        }
    summary = {
        "target": TARGET,
        "android": android,
        "sec_log_buf_live": True,
        "bind": EXPECTED_BIND,
        "pstore_console_absent": pstore_console_absent(serial),
        "observers": captures,
        "one_shot_consumed": False,
        "no_odin_endpoint": True,
        "device_writes": False,
    }
    core.durable_write_json(run_dir / "connected_preflight.json", summary)
    return serial, summary


def validate_connected_result_contract(
    result: Any,
    *,
    root: Path | None = None,
    result_path: Path | None = None,
    expected_artifacts: dict[str, Any] | None = None,
) -> dict[Path, bytes]:
    if (root is None) != (result_path is None):
        raise GateError("R4W1-B connected receipt validation context is incomplete")
    if not isinstance(result, dict):
        raise GateError("R4W1-B connected result is not an object")
    result_expected = {
        "schema": SCHEMA,
        "mode": "connected-read-only-dry-run",
        "target": TARGET,
        "device_contact": True,
        "device_writes": False,
        "reboot": False,
        "download_transition": False,
        "odin_transfer": False,
        "flash": False,
        "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
    }
    if any(result.get(key) != value for key, value in result_expected.items()):
        raise GateError("R4W1-B connected result contract mismatch")
    artifacts = result.get("artifacts")
    expected_identities = {
        "candidate_boot": {
            "size": EXPECTED_CANDIDATE_BOOT_SIZE,
            "sha256": EXPECTED_CANDIDATE_BOOT_SHA256,
        },
        "candidate_lz4": {
            "size": EXPECTED_CANDIDATE_LZ4_SIZE,
            "sha256": EXPECTED_CANDIDATE_LZ4_SHA256,
        },
        "candidate_ap": {
            "size": EXPECTED_CANDIDATE_AP_SIZE,
            "sha256": EXPECTED_CANDIDATE_AP_SHA256,
        },
        "manifest": {
            "size": EXPECTED_MANIFEST_SIZE,
            "sha256": EXPECTED_MANIFEST_SHA256,
        },
        "static_result": {
            "size": EXPECTED_STATIC_RESULT_SIZE,
            "sha256": EXPECTED_STATIC_RESULT_SHA256,
        },
        "magisk_rollback_ap": {
            "size": EXPECTED_MAGISK_AP_SIZE,
            "sha256": EXPECTED_MAGISK_AP_SHA256,
        },
        "stock_cleanup_ap": {
            "size": EXPECTED_STOCK_AP_SIZE,
            "sha256": EXPECTED_STOCK_AP_SHA256,
        },
        "odin": {"size": EXPECTED_ODIN_SIZE, "sha256": EXPECTED_ODIN_SHA256},
        "full_firmware": {
            "size": EXPECTED_FULL_FIRMWARE_SIZE,
            "sha256": EXPECTED_FULL_FIRMWARE_SHA256,
        },
    }
    expected_sources = {
        "static_checker": {
            "size": EXPECTED_STATIC_CHECKER_SIZE,
            "sha256": EXPECTED_STATIC_CHECKER_SHA256,
        },
        "static_checker_test": {
            "size": EXPECTED_STATIC_CHECKER_TEST_SIZE,
            "sha256": EXPECTED_STATIC_CHECKER_TEST_SHA256,
        },
        "builder": {"size": EXPECTED_BUILDER_SIZE, "sha256": EXPECTED_BUILDER_SHA256},
        "build_primitive": {
            "size": EXPECTED_BUILD_PRIMITIVE_SIZE,
            "sha256": EXPECTED_BUILD_PRIMITIVE_SHA256,
        },
        "check_primitive": {
            "size": EXPECTED_CHECK_PRIMITIVE_SIZE,
            "sha256": EXPECTED_CHECK_PRIMITIVE_SHA256,
        },
        "transport": {"size": EXPECTED_TRANSPORT_SIZE, "sha256": EXPECTED_TRANSPORT_SHA256},
    }
    expected_fresh = {
        "size": EXPECTED_STATIC_RESULT_SIZE,
        "sha256": EXPECTED_STATIC_RESULT_SHA256,
        "schema": EXPECTED_STATIC_SCHEMA,
        "verdict": EXPECTED_STATIC_VERDICT,
    }
    if (
        not isinstance(artifacts, dict)
        or artifacts.get("target") != TARGET
        or artifacts.get("identities") != expected_identities
        or artifacts.get("source_pins") != expected_sources
        or artifacts.get("fresh_static_checker") != expected_fresh
        or artifacts.get("ap_members") != ["boot.img.lz4"]
    ):
        raise GateError("R4W1-B connected artifact contract mismatch")
    if expected_artifacts is not None and artifacts != expected_artifacts:
        raise GateError("R4W1-B connected artifacts differ from fresh live artifacts")
    baseline = result.get("baseline")
    if not isinstance(baseline, dict):
        raise GateError("R4W1-B connected result baseline is missing")
    if (
        baseline.get("target") != TARGET
        or baseline.get("device_writes") is not False
        or baseline.get("one_shot_consumed") is not False
        or baseline.get("no_odin_endpoint") is not True
        or baseline.get("sec_log_buf_live") is not True
        or baseline.get("bind") != EXPECTED_BIND
    ):
        raise GateError("R4W1-B connected baseline contract mismatch")
    android = baseline.get("android")
    expected_android = {
        "model": "SM-S906N",
        "device": "g0q",
        "bootloader": "S906NKSS7FYG8",
        "incremental": "S906NKSS7FYG8",
        "boot_completed": "1",
        "bootanim": "stopped",
        "verified_boot_state": "orange",
        "root": "uid=0(root)",
        "boot_sha256": EXPECTED_MAGISK_BOOT_SHA256,
        "dtbo_sha256": EXPECTED_DTBO_SHA256,
        "recovery_sha256": EXPECTED_RECOVERY_SHA256,
        "vendor_boot_sha256": EXPECTED_VENDOR_BOOT_SHA256,
    }
    if android != expected_android:
        raise GateError("R4W1-B connected Android baseline contract mismatch")
    observers = baseline.get("observers")
    if not isinstance(observers, dict) or set(observers) != {"ap_klog", "last_kmsg"}:
        raise GateError("R4W1-B connected observer contract mismatch")
    expected_names = {
        "ap_klog": ["baseline_ap_klog.bin"],
        "last_kmsg": ["baseline_last_kmsg_1.bin", "baseline_last_kmsg_2.bin"],
    }
    reopened_payloads: dict[Path, bytes] = {}
    for name, observer in observers.items():
        if (
            not isinstance(observer, dict)
            or observer.get("read_to_eof") is not True
            or observer.get("stderr_bytes") != 0
            or type(observer.get("bytes")) is not int
            or observer["bytes"] <= 0
            or observer["bytes"] > MAX_OBSERVER_BYTES
            or not re.fullmatch(r"[0-9a-f]{64}", str(observer.get("sha256", "")))
        ):
            raise GateError("R4W1-B connected observer receipt mismatch")
        marker = observer.get("marker")
        if (
            not isinstance(marker, dict)
            or marker.get("baseline_absent") is not True
            or marker.get("integrity_issue") is not False
            or marker.get("acceptance_present") is not False
            or marker.get("exact_count") != 0
            or marker.get("exact_record_count") != 0
            or marker.get("family_count") != 0
            or marker.get("foreign_count") != 0
            or marker.get("delimiter_mismatch_count") != 0
            or marker.get("partial_at_head") is not False
            or marker.get("partial_at_tail") is not False
            or marker.get("unterminated_offsets") != []
        ):
            raise GateError("R4W1-B connected marker baseline mismatch")
        expected_reads = 2 if name == "last_kmsg" else 1
        reads = observer.get("reads")
        if (
            observer.get("read_count") != expected_reads
            or observer.get("byte_identical") is not True
            or not isinstance(reads, list)
            or len(reads) != expected_reads
        ):
            raise GateError("R4W1-B connected observer rehearsal mismatch")
        read_identities: list[dict[str, Any]] = []
        for index, read in enumerate(reads):
            if (
                not isinstance(read, dict)
                or read.get("read_to_eof") is not True
                or read.get("returncode") != 0
                or read.get("stderr_bytes") != 0
                or type(read.get("bytes")) is not int
                or read["bytes"] <= 0
                or read["bytes"] > MAX_OBSERVER_BYTES
                or not re.fullmatch(r"[0-9a-f]{64}", str(read.get("sha256", "")))
            ):
                raise GateError("R4W1-B connected observer read receipt mismatch")
            receipt_path = Path(str(read.get("path", "")))
            if not receipt_path.is_absolute() or receipt_path.name != expected_names[name][index]:
                raise GateError("R4W1-B connected observer path mismatch")
            identity = {"size": read["bytes"], "sha256": read["sha256"]}
            if root is not None and result_path is not None:
                if receipt_path.is_symlink() or not receipt_path.is_file():
                    raise GateError("R4W1-B connected observer is missing or indirect")
                reopened = receipt_path.resolve()
                if reopened.parent != result_path.resolve().parent:
                    raise GateError("R4W1-B connected observer escaped its result directory")
                payload = core.read_stable_file(reopened, maximum=MAX_OBSERVER_BYTES)
                if {"size": len(payload), "sha256": core.sha256_bytes(payload)} != identity:
                    raise GateError("R4W1-B connected observer file identity mismatch")
                if classify_marker(payload) != marker:
                    raise GateError("R4W1-B connected observer marker semantics mismatch")
                reopened_payloads[reopened] = payload
            read_identities.append(identity)
        if (
            observer["bytes"] != read_identities[0]["size"]
            or observer["sha256"] != read_identities[0]["sha256"]
            or any(identity != read_identities[0] for identity in read_identities[1:])
        ):
            raise GateError("R4W1-B connected observer summary/receipt mismatch")
    pstore = baseline.get("pstore_console_absent")
    if not isinstance(pstore, dict) or set(pstore) != set(PSTORE_PATHS) or not all(
        value is True for value in pstore.values()
    ):
        raise GateError("R4W1-B connected pstore contract mismatch")
    return reopened_payloads


def validate_connected_pass(
    root: Path,
    *,
    expected_artifacts: dict[str, Any] | None = None,
    require_policy_identity: bool = False,
) -> dict[str, Any]:
    path = root / CONNECTED_PASS_STATE
    if path.is_symlink() or not path.is_file():
        raise GateError("R4W1-B connected read-only PASS record is missing")
    pass_payload = core.read_stable_file(path, maximum=1024 * 1024)
    pass_identity = {"size": len(pass_payload), "sha256": core.sha256_bytes(pass_payload)}
    try:
        record = json.loads(pass_payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("R4W1-B connected PASS record is invalid") from exc
    expected = {
        "schema": "s22plus_fyg8_r4w1b_connected_pass_v1",
        "target": TARGET,
        "helper_sha256": helper_sha256(root),
        "test_sha256": test_sha256(root),
        "core_sha256": core_sha256(root),
        "core_test_sha256": core_test_sha256(root),
        "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
        "device_writes": False,
    }
    if (
        not isinstance(record, dict)
        or set(record) != {
            "schema",
            "target",
            "created_at_utc",
            "helper_sha256",
            "test_sha256",
            "core_sha256",
            "core_test_sha256",
            "result_path",
            "result_sha256",
            "verdict",
            "device_writes",
        }
        or any(record.get(key) != value for key, value in expected.items())
        or not isinstance(record.get("created_at_utc"), str)
        or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
            str(record.get("created_at_utc", "")),
        )
        or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("result_sha256", "")))
    ):
        raise GateError("R4W1-B connected PASS record contract mismatch")
    result_text = record["result_path"]
    if not isinstance(result_text, str):
        raise GateError("R4W1-B connected PASS result path is not text")
    result_relative = Path(result_text)
    if (
        not re.fullmatch(r"[A-Za-z0-9._/-]+", result_text)
        or result_relative.is_absolute()
        or str(result_relative) != result_text
        or ".." in result_relative.parts
        or tuple(result_relative.parts[:3]) != ("workspace", "private", "runs")
        or len(result_relative.parts) < 5
        or result_relative.name != "result.json"
    ):
        raise GateError("R4W1-B connected PASS result path is not canonical")
    unresolved_result_path = root / result_relative
    if unresolved_result_path.is_symlink() or not unresolved_result_path.is_file():
        raise GateError("R4W1-B connected result is missing or indirect")
    result_path = unresolved_result_path.resolve()
    run_root = resolve(root, RUN_ROOT)
    if not result_path.is_relative_to(run_root):
        raise GateError("connected PASS result path is outside private runs")
    result_payload = core.read_stable_file(result_path, maximum=8 * 1024 * 1024)
    result_identity = {
        "size": len(result_payload),
        "sha256": core.sha256_bytes(result_payload),
    }
    if result_identity["sha256"] != record["result_sha256"]:
        raise GateError("R4W1-B connected result differs from PASS record")
    if require_policy_identity:
        binding = parse_live_connected_evidence_binding(
            (root / "AGENTS.md").read_text(encoding="utf-8")
        )
        if (
            binding["pass_path"] != str(CONNECTED_PASS_STATE)
            or binding["created_at_utc"] != record["created_at_utc"]
            or binding["pass_size"] != pass_identity["size"]
            or binding["pass_sha256"] != pass_identity["sha256"]
            or binding["result_path"] != record["result_path"]
            or binding["result_size"] != result_identity["size"]
            or binding["result_sha256"] != result_identity["sha256"]
        ):
            raise GateError("R4W1-B connected evidence differs from live policy binding")
    try:
        result = json.loads(result_payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("R4W1-B connected result is invalid") from exc
    raw_payloads = validate_connected_result_contract(
        result,
        root=root,
        result_path=result_path,
        expected_artifacts=expected_artifacts,
    )
    if (
        core.read_stable_file(path, maximum=1024 * 1024) != pass_payload
        or core.read_stable_file(result_path, maximum=8 * 1024 * 1024) != result_payload
        or any(
            core.read_stable_file(raw_path, maximum=MAX_OBSERVER_BYTES) != payload
            for raw_path, payload in raw_payloads.items()
        )
    ):
        raise GateError("R4W1-B connected evidence changed during validation")
    return record


def connected_dry_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root, connected=True):
        raise GateError("R4W1-B connected read-only policy is inactive")
    if args.ack != CONNECTED_ACK_TOKEN:
        raise GateError("R4W1-B connected acknowledgement mismatch")
    if (root / CONNECTED_PASS_STATE).exists() or (root / CONNECTED_PASS_STATE).is_symlink():
        raise GateError("R4W1-B connected read-only PASS state already exists")
    run_dir = core.allocate_run_dir(root, RUN_ROOT, "s22plus-r4w1b-connected", args.run_dir)
    odin = resolve(root, args.odin)
    _, baseline = connected_preflight(root, run_dir, odin)
    result = {
        "schema": SCHEMA,
        "mode": "connected-read-only-dry-run",
        "target": TARGET,
        "artifacts": artifacts,
        "baseline": baseline,
        "device_contact": True,
        "device_writes": False,
        "reboot": False,
        "download_transition": False,
        "odin_transfer": False,
        "flash": False,
        "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
    }
    result_path = run_dir / "result.json"
    core.durable_write_json(result_path, result)
    record = {
        "schema": "s22plus_fyg8_r4w1b_connected_pass_v1",
        "target": TARGET,
        "created_at_utc": core.utc_now(),
        "helper_sha256": helper_sha256(root),
        "test_sha256": test_sha256(root),
        "core_sha256": core_sha256(root),
        "core_test_sha256": core_test_sha256(root),
        "result_path": str(result_path.relative_to(root)),
        "result_sha256": core.sha256_file(result_path),
        "verdict": result["verdict"],
        "device_writes": False,
    }
    core.durable_create_json(root / CONNECTED_PASS_STATE, record)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"]}, indent=2))
    return 0


def consume_exception(root: Path, run_dir: Path) -> None:
    core.durable_create_json(
        root / CONSUMED_STATE,
        {
            "schema": "s22plus_fyg8_r4w1b_consumed_v1",
            "target": TARGET,
            "reason": "candidate_flash_start",
            "consumed_at_utc": core.utc_now(),
            "run_dir": str(run_dir.relative_to(root)),
            "helper_sha256": helper_sha256(root),
            "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
            "static_result_sha256": EXPECTED_STATIC_RESULT_SHA256,
        },
    )


def require_consumed_for_rollback(root: Path) -> dict[str, Any]:
    path = root / CONSUMED_STATE
    if path.is_symlink() or not path.is_file():
        raise GateError("rollback requires a valid consumed R4W1-B run")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("R4W1-B consumed state is invalid") from exc
    expected = {
        "schema": "s22plus_fyg8_r4w1b_consumed_v1",
        "target": TARGET,
        "reason": "candidate_flash_start",
        "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        "static_result_sha256": EXPECTED_STATIC_RESULT_SHA256,
    }
    if any(state.get(key) != value for key, value in expected.items()):
        raise GateError("R4W1-B consumed state contract mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(state.get("helper_sha256", ""))):
        raise GateError("R4W1-B consumed helper identity is malformed")
    run_dir = resolve(root, Path(str(state.get("run_dir", ""))))
    if not run_dir.is_relative_to(resolve(root, RUN_ROOT)) or not run_dir.is_dir():
        raise GateError("R4W1-B consumed run directory is invalid")
    return state


def observe_raw_park(seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    time.sleep(seconds)
    return {
        "bounded": True,
        "requested_sec": seconds,
        "elapsed_sec": round(time.monotonic() - started, 6),
        "candidate_adb_required": False,
        "host_rdx_command": False,
        "meaning": "raw-park observation close; not Android readiness or marker proof",
    }


def wait_for_one_odin(
    odin: Path, log_path: Path, label: str, seconds: int
) -> str | None:
    deadline = time.monotonic() + seconds
    while True:
        devices = strict_odin_devices(odin, log_path, label)
        if len(devices) == 1:
            return devices[0]
        if len(devices) > 1:
            raise GateError(f"ambiguous Odin endpoints: {devices}")
        if time.monotonic() >= deadline:
            return None
        time.sleep(1)


def wait_for_strict_odin_absence(
    odin: Path, log_path: Path, label: str, seconds: int
) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        devices = strict_odin_devices(odin, log_path, label)
        if not devices:
            transport.append_log(log_path, f"{label}_strict_odin_absent=1")
            return True
        if len(devices) > 1:
            raise GateError(f"ambiguous Odin endpoints while waiting for disconnect: {devices}")
        if time.monotonic() >= deadline:
            transport.append_log(
                log_path, f"{label}_strict_odin_absent=0 still_present={devices}"
            )
            return False
        time.sleep(1)


def prepare_fresh_confirmation_input() -> int:
    try:
        descriptor = sys.stdin.fileno()
    except (OSError, ValueError) as exc:
        raise GateError("normal Download confirmation input is unavailable") from exc
    if os.isatty(descriptor):
        try:
            termios.tcflush(descriptor, termios.TCIFLUSH)
        except OSError as exc:
            raise GateError("normal Download TTY input could not be flushed") from exc
    else:
        try:
            prebuffered, _, _ = select.select([descriptor], [], [], 0)
        except (OSError, ValueError) as exc:
            raise GateError("normal Download confirmation input is unavailable") from exc
        if prebuffered:
            raise GateError("prebuffered normal Download confirmation is not fresh")
    return descriptor


def read_fresh_confirmation(timeout_sec: float, *, descriptor: int | None = None) -> str:
    if timeout_sec <= 0:
        raise GateError("normal Download confirmation window expired")
    if descriptor is None:
        descriptor = prepare_fresh_confirmation_input()
    deadline = time.monotonic() + timeout_sec
    payload = bytearray()
    while b"\n" not in payload:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GateError("normal Download confirmation timed out")
        ready, _, _ = select.select([descriptor], [], [], remaining)
        if not ready:
            raise GateError("normal Download confirmation timed out")
        chunk = os.read(descriptor, 256)
        if not chunk:
            raise GateError("normal Download confirmation was not provided")
        payload.extend(chunk)
        if len(payload) > 256:
            raise GateError("normal Download confirmation is oversized")
    line, separator, trailing = bytes(payload).partition(b"\n")
    if separator != b"\n" or trailing:
        raise GateError("normal Download confirmation has trailing input")
    try:
        return line.removesuffix(b"\r").decode("ascii")
    except UnicodeDecodeError as exc:
        raise GateError("normal Download confirmation is not ASCII") from exc


def confirm_normal_download(timeout_sec: float) -> None:
    descriptor = prepare_fresh_confirmation_input()
    print(
        "Confirm on the device that RDX has been exited and the screen is normal "
        "Samsung Download mode. Type the exact confirmation token to permit rollback.",
        flush=True,
    )
    if (
        read_fresh_confirmation(timeout_sec, descriptor=descriptor)
        != NORMAL_DOWNLOAD_CONFIRMATION
    ):
        raise GateError("normal Download confirmation mismatch")


def require_unchanged_odin_endpoint(
    odin: Path,
    log_path: Path,
    expected_device: str,
    *,
    label: str,
) -> str:
    devices = strict_odin_devices(odin, log_path, label)
    if devices != [expected_device]:
        raise GateError(
            f"Odin endpoint changed before rollback transfer: "
            f"expected {[expected_device]}, observed {devices}"
        )
    return expected_device


def wait_magisk_android_exact(
    odin: Path, log_path: Path, seconds: int
) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + seconds
    last_error = "no Android observation"
    while time.monotonic() < deadline:
        try:
            return current_android_exact(odin, log_path)
        except (GateError, transport.GateError, subprocess.SubprocessError, OSError) as exc:
            last_error = str(exc)
            time.sleep(2)
    raise GateError(f"exact Magisk Android did not return: {last_error}")


def flash_rollback_exact(
    root: Path,
    args: argparse.Namespace,
    odin: Path,
    device: str,
    log_path: Path,
) -> str:
    try:
        transport.flash_exact(
            odin,
            resolve(root, args.magisk_ap),
            device,
            log_path,
            "r4w1b-magisk-rollback",
        )
        return "magisk"
    except transport.GateError:
        devices = strict_odin_devices(odin, log_path, "r4w1b-stock-cleanup")
        if devices != [device]:
            raise
        transport.flash_exact(
            odin,
            resolve(root, args.stock_ap),
            devices[0],
            log_path,
            "r4w1b-stock-cleanup",
        )
        return "stock"


def collect_first_rollback_last_kmsg(
    serial: str, run_dir: Path
) -> dict[str, Any]:
    paths = [run_dir / "rollback_last_kmsg_1.bin", run_dir / "rollback_last_kmsg_2.bin"]
    receipts = []
    for path in paths:
        receipts.append(
            core.capture_adb_exec_out(
                serial,
                "cat /proc/last_kmsg",
                path,
                root=True,
                timeout=120,
                maximum=MAX_OBSERVER_BYTES,
            )
        )
        time.sleep(0.25)
    first = core.read_stable_file(paths[0], maximum=MAX_OBSERVER_BYTES)
    second = core.read_stable_file(paths[1], maximum=MAX_OBSERVER_BYTES)
    if not first or not second:
        raise GateError("rollback last_kmsg is empty")
    if first != second:
        raise GateError("rollback last_kmsg reads are not byte-identical")
    marker = classify_marker(first)
    result = {
        "reads": receipts,
        "byte_identical": True,
        "read_to_eof": True,
        "bytes": len(first),
        "sha256": core.sha256_bytes(first),
        "marker": marker,
        "fyg8_banner_count": first.count(FYG8_BANNER),
        "candidate_banner_is_not_unique": True,
        "ring_binding": (
            "exact R4W1-B marker binds a positive ring to the candidate; marker "
            "absence cannot distinguish exec rejection from retention loss or an "
            "intervening kernel boot"
        ),
        "load_bearing": True,
    }
    core.durable_write_json(run_dir / "rollback_last_kmsg.json", result)
    return result


def classify_verdict(
    *,
    rollback_target: str,
    rollback_ok: bool,
    candidate_transfer_ok: bool,
    observer: dict[str, Any] | None,
) -> tuple[str, int]:
    if rollback_target != "magisk" or not rollback_ok:
        return "FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED", 20
    if observer is None:
        return "FAIL_R4W1B_OBSERVER_CAPTURE", 21
    marker = observer["marker"]
    if marker["integrity_issue"]:
        return "FAIL_R4W1B_MARKER_INTEGRITY", 22
    if not candidate_transfer_ok:
        if marker["acceptance_present"]:
            return "FAIL_R4W1B_MARKER_INTEGRITY", 23
        return "FAIL_R4W1B_CANDIDATE_TRANSFER_AND_ROLLED_BACK", 24
    if marker["acceptance_present"]:
        return "PASS_R4W1B_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK", 0
    return "NO_PROOF_R4W1B_EXEC_OR_TRANSITION_UNRESOLVED", 32


def finish_failed(
    run_dir: Path,
    timeline_path: Path,
    timeline: list[dict[str, str]],
    result: dict[str, Any],
    *,
    verdict: str,
    error: str,
    semantics: dict[str, str],
    rc: int = 20,
) -> int:
    result["verdict"] = verdict
    result["error"] = error
    result.setdefault("timeline_phase_semantics", {}).update(semantics)
    core.append_remaining_events(timeline_path, timeline)
    core.durable_write_json(run_dir / "result.json", result)
    return rc


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root, connected=False):
        raise GateError("R4W1-B live policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("R4W1-B live acknowledgement mismatch")
    validate_connected_pass(
        root,
        expected_artifacts=artifacts,
        require_policy_identity=True,
    )
    if (root / CONSUMED_STATE).exists() or (root / CONSUMED_STATE).is_symlink():
        raise GateError("R4W1-B candidate exception is already consumed")
    run_dir = core.allocate_run_dir(root, RUN_ROOT, "s22plus-r4w1b-live", args.run_dir)
    timeline_path = run_dir / "timeline.json"
    timeline: list[dict[str, str]] = []
    log_path = run_dir / "live.log"
    odin = resolve(root, args.odin)
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "live",
        "target": TARGET,
        "artifacts": artifacts,
        "candidate_flash_attempted": False,
        "candidate_transfer_ok": False,
        "verdict": "INCOMPLETE",
    }
    core.append_event(timeline_path, timeline, "live_session_start")
    try:
        serial, baseline = connected_preflight(root, run_dir, odin)
        result["baseline"] = baseline
        core.durable_write_json(run_dir / "result.json", result)
        reboot = transport.run(["adb", "-s", serial, "reboot", "download"], timeout=20)
        if reboot.returncode != 0:
            raise GateError("baseline Android failed to request Download mode")
        device = wait_for_one_odin(
            odin, log_path, "r4w1b-candidate-download", args.download_wait_sec
        )
        if device is None:
            raise GateError("normal Download endpoint did not appear before candidate")
    except (GateError, core.LiveCoreError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        return finish_failed(
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict="FAIL_R4W1B_PRECONSUMPTION_NO_CANDIDATE_FLASH",
            error=str(exc),
            semantics={
                "candidate_flash_start": "pre-consumption failure; no candidate flash",
                "candidate_flash_done": "no candidate transfer",
                "candidate_boot_ready": "no candidate raw-park observation",
                "rollback_flash_start": "no consumed candidate; no rollback",
                "rollback_flash_done": "no rollback transfer",
                "rollback_boot_ready": "baseline boot was not replaced",
                "live_session_end": "pre-consumption run ended fail-closed",
            },
            rc=1,
        )

    core.append_event(timeline_path, timeline, "candidate_flash_start")
    try:
        consume_exception(root, run_dir)
        result["candidate_flash_attempted"] = True
        core.durable_write_json(run_dir / "result.json", result)
        transport.flash_exact(
            odin,
            resolve(root, args.candidate_ap),
            device,
            log_path,
            "r4w1b-candidate",
        )
        result["candidate_transfer_ok"] = True
    except (GateError, core.LiveCoreError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        result["candidate_transfer_error"] = str(exc)
    core.append_event(timeline_path, timeline, "candidate_flash_done")
    core.durable_write_json(run_dir / "result.json", result)

    if result["candidate_transfer_ok"]:
        try:
            disconnected = wait_for_strict_odin_absence(
                odin, log_path, "r4w1b-candidate-disconnect", args.disconnect_wait_sec
            )
            if disconnected is not True:
                raise GateError("candidate Odin endpoint did not disconnect; raw park refused")
            result["candidate_odin_disconnected"] = disconnected
            result["candidate_observation"] = observe_raw_park(args.park_wait_sec)
        except (GateError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
            result["candidate_observation"] = {"error": str(exc), "bounded": True}
    else:
        result["candidate_observation"] = {
            "bounded": True,
            "meaning": "candidate transfer failed; no raw-park proof",
        }
    core.append_event(timeline_path, timeline, "candidate_boot_ready")
    core.durable_write_json(run_dir / "result.json", result)

    print(
        "Candidate observation is closed. Physically exit any RDX screen and enter "
        "normal Samsung Download mode for mandatory rollback.",
        flush=True,
    )
    try:
        transition_started = time.monotonic()
        rollback_device = wait_for_one_odin(
            odin, log_path, "r4w1b-mandatory-rollback", args.transition_wait_sec
        )
        if rollback_device is None:
            raise GateError("normal Download endpoint did not appear for rollback")
        remaining = args.transition_wait_sec - (time.monotonic() - transition_started)
        confirm_normal_download(remaining)
        core.append_event(timeline_path, timeline, "rollback_flash_start")
        rollback_device = require_unchanged_odin_endpoint(
            odin,
            log_path,
            rollback_device,
            label="r4w1b-mandatory-rollback-revalidate",
        )
    except (GateError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        return finish_failed(
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict="FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
            error=str(exc),
            semantics={
                "rollback_flash_start": "no confirmed normal Download target; no rollback",
                "rollback_flash_done": "no rollback transfer",
                "rollback_boot_ready": "rollback Android not observed",
                "live_session_end": "rollback-from-download recovery required",
            },
        )

    try:
        rollback_target = flash_rollback_exact(
            root, args, odin, rollback_device, log_path
        )
    except (GateError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        return finish_failed(
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict="FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
            error=str(exc),
            semantics={
                "rollback_flash_done": "rollback transfer failed",
                "rollback_boot_ready": "rollback Android not observed",
                "live_session_end": "attended recovery remains required",
            },
        )
    core.append_event(timeline_path, timeline, "rollback_flash_done")
    result["rollback_target"] = rollback_target
    observer = None
    rollback_ok = False
    final: dict[str, str] | None = None
    try:
        if rollback_target != "magisk":
            raise GateError("stock cleanup cannot satisfy R4W1-B rollback")
        serial, final = wait_magisk_android_exact(
            odin, log_path, args.android_wait_sec
        )
        rollback_ok = True
        core.append_event(timeline_path, timeline, "rollback_boot_ready")
        observer = collect_first_rollback_last_kmsg(serial, run_dir)
    except (GateError, core.LiveCoreError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        result["rollback_health_or_observer_error"] = str(exc)
        if len(timeline) == 6:
            core.append_event(timeline_path, timeline, "rollback_boot_ready")
    verdict, rc = classify_verdict(
        rollback_target=rollback_target,
        rollback_ok=rollback_ok,
        candidate_transfer_ok=bool(result["candidate_transfer_ok"]),
        observer=observer,
    )
    result.update(
        {
            "final": final,
            "rollback_ok": rollback_ok,
            "rollback_last_kmsg": observer,
            "verdict": verdict,
        }
    )
    core.append_event(timeline_path, timeline, "live_session_end")
    core.durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def rollback_from_download(root: Path, args: argparse.Namespace) -> int:
    if args.ack != ROLLBACK_ACK_TOKEN:
        raise GateError("R4W1-B rollback acknowledgement mismatch")
    require_consumed_for_rollback(root)
    run_dir = core.allocate_run_dir(root, RUN_ROOT, "s22plus-r4w1b-rollback", args.run_dir)
    timeline_path = run_dir / "timeline.json"
    timeline: list[dict[str, str]] = []
    log_path = run_dir / "rollback.log"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "target": TARGET,
        "verdict": "INCOMPLETE",
        "timeline_phase_semantics": {
            "candidate_flash_start": "recovery-only; no candidate flash",
            "candidate_flash_done": "recovery-only; no candidate transfer",
            "candidate_boot_ready": "operator entered Download before recovery session",
        },
    }
    for name in core.TIMELINE_NAMES[:4]:
        core.append_event(timeline_path, timeline, name)
    core.durable_write_json(run_dir / "result.json", result)
    odin = resolve(root, args.odin)
    try:
        transition_started = time.monotonic()
        devices = strict_odin_devices(odin, log_path, "r4w1b-recovery")
        if len(devices) != 1:
            raise GateError(f"recovery requires exactly one Odin endpoint: {devices}")
        remaining = args.transition_wait_sec - (time.monotonic() - transition_started)
        confirm_normal_download(remaining)
        core.append_event(timeline_path, timeline, "rollback_flash_start")
        device = require_unchanged_odin_endpoint(
            odin,
            log_path,
            devices[0],
            label="r4w1b-recovery-revalidate",
        )
    except (GateError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        return finish_failed(
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict="FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
            error=str(exc),
            semantics={
                "rollback_flash_start": "no confirmed normal Download target",
                "rollback_flash_done": "no rollback transfer",
                "rollback_boot_ready": "rollback Android not observed",
                "live_session_end": "attended recovery remains required",
            },
        )
    try:
        target = flash_rollback_exact(root, args, odin, device, log_path)
        core.append_event(timeline_path, timeline, "rollback_flash_done")
        if target != "magisk":
            raise GateError("stock cleanup did not restore Magisk baseline")
        _, final = wait_magisk_android_exact(odin, log_path, args.android_wait_sec)
        core.append_event(timeline_path, timeline, "rollback_boot_ready")
        verdict = "PASS_R4W1B_MAGISK_ROLLBACK_FROM_DOWNLOAD"
        rc = 0
    except (GateError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
        return finish_failed(
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict="FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
            error=str(exc),
            semantics={
                "rollback_flash_done": "rollback transfer or target did not verify",
                "rollback_boot_ready": "exact Magisk Android not verified",
                "live_session_end": "attended recovery remains required",
            },
        )
    result.update({"rollback_target": target, "final": final, "verdict": verdict})
    core.append_event(timeline_path, timeline, "live_session_end")
    core.durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--connected-read-only-dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--candidate-boot", type=Path, default=DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-lz4", type=Path, default=DEFAULT_CANDIDATE_LZ4)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--static-result", type=Path, default=DEFAULT_STATIC_RESULT)
    parser.add_argument("--magisk-ap", type=Path, default=DEFAULT_MAGISK_AP)
    parser.add_argument("--stock-ap", type=Path, default=DEFAULT_STOCK_AP)
    parser.add_argument("--full-firmware", type=Path, default=DEFAULT_FULL_FIRMWARE)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--download-wait-sec", type=int, default=120)
    parser.add_argument("--disconnect-wait-sec", type=int, default=30)
    parser.add_argument("--park-wait-sec", type=int, default=30)
    parser.add_argument("--transition-wait-sec", type=int, default=120)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    return parser


def validate_runtime_args(args: argparse.Namespace) -> None:
    for label, value, maximum in (
        ("download wait", args.download_wait_sec, 300),
        ("disconnect wait", args.disconnect_wait_sec, 120),
        ("park wait", args.park_wait_sec, 90),
        ("transition wait", args.transition_wait_sec, 120),
        ("Android wait", args.android_wait_sec, 600),
    ):
        if value < 1 or value > maximum:
            raise GateError(f"{label} must be between 1 and {maximum} seconds")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        validate_runtime_args(args)
        if args.rollback_from_download:
            verify_recovery_artifacts(root, args)
            return rollback_from_download(root, args)
        artifacts = verify_artifacts(root, args)
        policy = verify_policy_draft(root)
        if args.offline_check:
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "mode": "offline-check",
                        "target": TARGET,
                        "artifacts": artifacts,
                        "policy": policy,
                        "connected_pass_present": (root / CONNECTED_PASS_STATE).is_file(),
                        "candidate_consumed": (root / CONSUMED_STATE).exists(),
                        "device_contact": False,
                        "device_writes": False,
                        "flash": False,
                        "verdict": "PASS_R4W1B_LIVE_GATE_OFFLINE_CHECK",
                    },
                    indent=2,
                )
            )
            return 0
        if args.connected_read_only_dry_run:
            return connected_dry_run(root, args, artifacts)
        if args.live:
            return live_run(root, args, artifacts)
        raise GateError("no mode selected")
    except (
        GateError,
        core.LiveCoreError,
        transport.GateError,
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
