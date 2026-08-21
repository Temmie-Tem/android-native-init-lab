#!/usr/bin/env python3

import argparse
import hashlib
import importlib.util
import json
import os
import posixpath
import re
import shutil
import shlex
import socket
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from a90ctl import ProtocolResult, run_cmdv1_command


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
OWNER_NATIVE_SERIAL = "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
OWNER_BRIDGE_PYTHON = "/usr/bin/python3.14"
OWNER_BRIDGE_SCRIPT = (
    Path(__file__).resolve().parents[5]
    / "workspace/public/src/scripts/revalidation/a90_bridge.py"
)
OWNER_SERIAL_REDACTION_PATH = (
    Path(__file__).resolve().parents[5]
    / "workspace/public/src/scripts/server-distro/a90_serial_redaction_v1.py"
)
OWNER_LSUSB = "/usr/bin/lsusb"
OWNER_ADB = "/usr/bin/adb"
OWNER_ADB_ROLE_NATIVE = "NATIVE_NO_RECOVERY"
OWNER_ADB_ROLE_RECOVERY = "BOUND_RECOVERY_PRESENT"
OWNER_USB_VENDOR = "04e8"
OWNER_NATIVE_PRODUCT = "6861"
OWNER_RECOVERY_PRODUCT = "6860"
OWNER_ADB_ATTRIBUTE_RE = re.compile(
    r"^(?:usb|product|model|device|transport_id):[!-~]+$"
)
OWNER_SERIAL_BRIDGE_SCRIPT = (
    Path(__file__).resolve().parents[5]
    / "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py"
)
DEFAULT_REMOTE_IMAGE = "/tmp/native_init_boot.img"
TWRP_SYSTEM_VERSION = "3.7.0_12-0"
TWRP_SYSTEM_SCRIPT = "/system/bin/rebootsystem.sh"
TWRP_SYSTEM_SCRIPT_SIZE = 89
TWRP_SYSTEM_SCRIPT_SHA256 = (
    "3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07"
)
TWRP_SYSTEM_REBOOT_COMMAND = (
    f"test \"$(twrp --version)\" = '{TWRP_SYSTEM_VERSION}' && "
    f"test ! -L {TWRP_SYSTEM_SCRIPT} && "
    f"test \"$(stat -c '%F|%a|%u|%g|%s|%h' {TWRP_SYSTEM_SCRIPT})\" = "
    f"'regular file|755|0|0|{TWRP_SYSTEM_SCRIPT_SIZE}|1' && "
    f"test \"$(sha256sum {TWRP_SYSTEM_SCRIPT} | cut -d' ' -f1)\" = "
    f"'{TWRP_SYSTEM_SCRIPT_SHA256}' && "
    "exec twrp reboot"
)
TWRP_IDENTITY_CHECK_COMMAND = TWRP_SYSTEM_REBOOT_COMMAND.removesuffix(
    "exec twrp reboot"
).rstrip(" &&")
OWNER_RECEIPT_SCHEMA = "a90-f1-owner-effect-receipt-v1"
OWNER_RECEIPT_MODE = "A90_F1_OWNER_EFFECT_RECEIPT_V1"
OWNER_OUTCOMES = (
    "PRE_WRITE_FAILURE",
    "WRITE_OR_READBACK_UNCLASSIFIED",
    "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
    "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
)
BOOT_READBACK_BLOCK_SIZE = 4096
ANDROID_BOOT_MAGIC = b"ANDROID!"
INPUT_MODE_ENV = "A90CTL_INPUT_MODE"
INPUT_CHAR_DELAY_ENV = "A90CTL_INPUT_CHAR_DELAY_SEC"
DEFAULT_SELF_WRITE_STAGING_DIR = "/mnt/sdext/a90/flash-staging"
SELF_WRITE_ALLOWED_STAGING_DIRS = (
    "/mnt/sdext/a90/flash-staging",
    "/cache/a90-runtime/flash-staging",
)
SELF_WRITE_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SELF_WRITE_POLICY_BLOCK = (
    "experimental self-write live path is blocked unless --self-write-live-authorized "
    "selects the bounded v2321 F4-live mode; production/default fast-flash remains "
    "gated by AGENTS.md and design section 12.1"
)


def _load_exact_serial_redaction():
    name = "a90_serial_redaction_v1"
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(getattr(existing, "__file__", "")).resolve() != OWNER_SERIAL_REDACTION_PATH:
            raise RuntimeError("serial redaction module path is not exact")
        return existing
    spec = importlib.util.spec_from_file_location(name, OWNER_SERIAL_REDACTION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("serial redaction module import failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    if Path(module.__file__).resolve() != OWNER_SERIAL_REDACTION_PATH:
        raise RuntimeError("serial redaction module path changed")
    return module


serial_redaction = _load_exact_serial_redaction()

# design section 12.1 F4-live amendment (2026-07-02): the only authorized live self-write
# candidate is the v2321 rollback image driven with boot-flash-f3 self-rollback semantics, so
# both the success path and any restore path converge on the clean rollback checkpoint.
SELF_WRITE_F4_LIVE_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
SELF_WRITE_F4_LIVE_VERSION = "0.9.285"
SELF_WRITE_MODES = {
    "f2": {
        "command": "boot-flash-f2",
        "token": "BOOT-FLASH-F2-BOOT-CANDIDATE",
        "success_marker": "result=ok target-written-ready-to-reboot",
    },
    "f3": {
        "command": "boot-flash-f3",
        "token": "BOOT-FLASH-F3-SELF-ROLLBACK",
        "success_marker": "result=ok rollback-written-ready-to-reboot",
    },
}


@dataclass
class OwnerEffectState:
    """In-process stage facts used only by the fixed owner receipt mode."""

    write_started: bool = False
    boot_written_readback_exact: bool = False
    system_return_attempted: bool = False
    system_return_command_ok: bool = False
    system_return_confirmed: bool = False

    def outcome(self) -> str:
        if not self.write_started:
            return "PRE_WRITE_FAILURE"
        if not self.boot_written_readback_exact:
            return "WRITE_OR_READBACK_UNCLASSIFIED"
        if not self.system_return_attempted or not self.system_return_command_ok:
            return "WRITE_OR_READBACK_UNCLASSIFIED"
        if self.system_return_confirmed:
            return "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
        return "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN"

    def payload(self) -> dict[str, object]:
        return {
            "schema": OWNER_RECEIPT_SCHEMA,
            "mode": OWNER_RECEIPT_MODE,
            "outcome": self.outcome(),
            "writeStarted": self.write_started,
            "bootWrittenReadbackExact": self.boot_written_readback_exact,
            "systemReturnAttempted": self.system_return_attempted,
            "systemReturnCommandOk": self.system_return_command_ok,
            "systemReturnConfirmed": self.system_return_confirmed,
        }


OWNER_EFFECT_STATE: OwnerEffectState | None = None
OWNER_SERIAL_REDACTOR = None


def _owner_redactor():
    global OWNER_SERIAL_REDACTOR
    if OWNER_EFFECT_STATE is None:
        return None
    if OWNER_SERIAL_REDACTOR is None:
        OWNER_SERIAL_REDACTOR = serial_redaction.SerialRedactor()
    return OWNER_SERIAL_REDACTOR


def _owner_register_serial_hash(digest: str | None) -> None:
    redactor = _owner_redactor()
    if redactor is not None and digest is not None:
        redactor.register_hash(digest)


def _owner_register_serial(value: str) -> None:
    redactor = _owner_redactor()
    if redactor is not None:
        redactor.register_secret(value)


def _owner_redact_text(value: object) -> str:
    redactor = _owner_redactor()
    return str(value) if redactor is None else redactor.text(value)


def _owner_redact_bytes(value: bytes) -> bytes:
    redactor = _owner_redactor()
    return value if redactor is None else redactor.bytes(value)


def _emit_owner_receipt(state: OwnerEffectState) -> None:
    """Emit exactly one canonical JSON object and no prose on stdout."""
    raw = json.dumps(
        state.payload(),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    sys.stdout.write(raw)
    sys.stdout.flush()


def owner_stdout(*args: object, **kwargs: object) -> None:
    """Keep the fixed owner stdout channel reserved for its receipt."""
    if OWNER_EFFECT_STATE is None:
        print(*args, **kwargs)


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(
        f"[native-init-flash {timestamp}] {_owner_redact_text(message)}",
        file=sys.stderr,
        flush=True,
    )


def _owner_json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise RuntimeError("owner bridge preflight JSON has duplicate keys")
        value[key] = item
    return value


def _owner_bridge_preflight(args: argparse.Namespace) -> dict[str, object]:
    """Revalidate the fixed managed bridge immediately before Native recovery."""
    if args.bridge_host != DEFAULT_HOST or args.bridge_port != DEFAULT_PORT:
        raise RuntimeError("owner bridge preflight requires the fixed bridge endpoint")
    result = subprocess.run(
        [
            OWNER_BRIDGE_PYTHON,
            str(OWNER_BRIDGE_SCRIPT),
            "preflight",
            "--device", OWNER_NATIVE_SERIAL,
            "--device-glob", OWNER_NATIVE_SERIAL,
            "--pin-selected-realpath",
            "--json",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0 or result.stderr:
        raise RuntimeError("fixed owner bridge preflight command failed")
    try:
        value = json.loads(
            result.stdout.decode("utf-8"),
            object_pairs_hook=_owner_json_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RuntimeError(f"non-finite bridge preflight value: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as exc:
        raise RuntimeError("fixed owner bridge preflight JSON is invalid") from exc
    if type(value) is not dict:
        raise RuntimeError("fixed owner bridge preflight is not an object")
    candidates = value.get("serial_candidates")
    selected_realpath = value.get("selected_realpath")
    pids = value.get("port_pids")
    sockets = value.get("port_sockets")
    socket_inodes = value.get("port_socket_inodes")
    processes = value.get("processes")
    metadata = value.get("metadata")
    command = metadata.get("command") if type(metadata) is dict else None
    process_cmdline = (
        shlex.split(processes[0].get("cmdline"))
        if type(processes) is list
        and len(processes) == 1
        and type(processes[0]) is dict
        and type(processes[0].get("cmdline")) is str
        else None
    )
    command_options = (
        dict(zip(command[2::2], command[3::2]))
        if type(command) is list
        and len(command) == 14
        and all(type(item) is str for item in command)
        and all(item.startswith("--") for item in command[2::2])
        and len(set(command[2::2])) == 6
        else None
    )
    if (
        value.get("wrapper_contract") != 1
        or value.get("bridge_process") != "running"
        or value.get("port_listening") is not True
        or value.get("ambiguous") is not False
        or value.get("selected_device") != OWNER_NATIVE_SERIAL
        or type(selected_realpath) is not str
        or re.fullmatch(r"/dev/ttyACM[0-9]+", selected_realpath) is None
        or type(candidates) is not list
        or len(candidates) != 1
        or type(candidates[0]) is not dict
        or candidates[0].get("path") != OWNER_NATIVE_SERIAL
        or candidates[0].get("realpath") != selected_realpath
        or candidates[0].get("exists") is not True
        or value.get("listen_host") != DEFAULT_HOST
        or value.get("listen_port") != DEFAULT_PORT
        or type(pids) is not list
        or len(pids) != 1
        or type(pids[0]) is not int
        or pids[0] <= 0
        or type(socket_inodes) is not list
        or len(socket_inodes) != 1
        or type(socket_inodes[0]) is not str
        or not socket_inodes[0].isdigit()
        or type(sockets) is not list
        or len(sockets) != 1
        or type(sockets[0]) is not dict
        or sockets[0].get("address") != DEFAULT_HOST
        or sockets[0].get("port") != DEFAULT_PORT
        or sockets[0].get("inode") != socket_inodes[0]
        or type(processes) is not list
        or len(processes) != 1
        or type(processes[0]) is not dict
        or processes[0].get("pid") != pids[0]
        or processes[0].get("managed") is not True
        or processes[0].get("port_match") is not True
        or type(metadata) is not dict
        or metadata.get("pid") != pids[0]
        or metadata.get("device") != OWNER_NATIVE_SERIAL
        or metadata.get("device_glob") != OWNER_NATIVE_SERIAL
        or metadata.get("pin_selected_realpath") is not True
        or metadata.get("effective_expect_realpath") != selected_realpath
        or type(metadata.get("started_at")) is not str
        or not metadata.get("started_at")
        or process_cmdline != command
        or command_options is None
        or command[:2] != ["/usr/bin/python3", str(OWNER_SERIAL_BRIDGE_SCRIPT)]
        or command_options.get("--host") != DEFAULT_HOST
        or command_options.get("--port") != str(DEFAULT_PORT)
        or command_options.get("--device") != OWNER_NATIVE_SERIAL
        or command_options.get("--device-glob") != OWNER_NATIVE_SERIAL
        or command_options.get("--expect-realpath") != selected_realpath
        or type(command_options.get("--capture")) is not str
        or value.get("bridge_probe") not in {"connected-no-immediate-error", "data"}
    ):
        raise RuntimeError("fixed owner bridge preflight identity is not exact")
    receipt_sha256 = hashlib.sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    generation_sha256 = hashlib.sha256(
        json.dumps(
            {
                "bridgePid": pids[0],
                "selectedRealpath": selected_realpath,
                "socketInodes": socket_inodes,
                "command": command,
                "startedAt": metadata.get("started_at"),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    log(f"owner bridge preflight receipt={receipt_sha256} generation={generation_sha256}")
    return {"receiptSha256": receipt_sha256, "generationSha256": generation_sha256}


OWNER_LSUSB_LINE_RE = re.compile(
    rb"^Bus [0-9]{3} Device [0-9]{3}: ID [0-9a-f]{4}:[0-9a-f]{4} .+$"
)


def _owner_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _owner_parse_usb_rows(raw: bytes) -> list[tuple[str, str, str]]:
    lines = raw.splitlines()
    if not lines or any(OWNER_LSUSB_LINE_RE.fullmatch(line) is None for line in lines):
        raise RuntimeError("fixed lsusb inventory is malformed")
    rows = []
    for line in lines:
        match = OWNER_LSUSB_LINE_RE.fullmatch(line)
        assert match is not None
        prefix = line.split(b" ID ", 1)[1]
        vendor_product, description = prefix.split(b" ", 1)
        vendor, product = vendor_product.split(b":", 1)
        rows.append((vendor.decode("ascii"), product.decode("ascii"), description.decode("utf-8")))
    return rows


def _owner_usb_inventory_sha256(
    expected_role: str,
) -> str:
    """Capture one strict, complete fixed lsusb output without device effects."""
    process = subprocess.Popen(
        [OWNER_LSUSB],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired as exc:
            try:
                os.killpg(process.pid, 9)
            except ProcessLookupError:
                pass
            process.wait()
            raise RuntimeError("fixed lsusb inventory timed out") from exc
        if process.returncode != 0 or stderr or not stdout:
            raise RuntimeError("fixed lsusb inventory producer failed")
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            raise RuntimeError("fixed lsusb inventory producer survived") from exc
        else:
            raise RuntimeError("fixed lsusb inventory producer survived")
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, 9)
            except ProcessLookupError:
                pass
    if len(stdout) > 1 << 20:
        raise RuntimeError("fixed lsusb inventory is oversized")
    rows = _owner_parse_usb_rows(stdout)
    samsung = [row for row in rows if row[0] == OWNER_USB_VENDOR]
    if len(samsung) != 1:
        raise RuntimeError("fixed USB inventory requires exactly one Samsung endpoint")
    expected_product = (
        OWNER_NATIVE_PRODUCT
        if expected_role == OWNER_ADB_ROLE_NATIVE
        else OWNER_RECOVERY_PRODUCT
        if expected_role == OWNER_ADB_ROLE_RECOVERY
        else None
    )
    if expected_product is None or samsung[0][1] != expected_product:
        raise RuntimeError("fixed USB role is not exact")
    digest = hashlib.sha256(stdout).hexdigest()
    log(f"owner USB inventory receipt={digest}")
    return digest


def _owner_parse_adb_rows(raw: bytes) -> list[tuple[str, str, tuple[str, ...]]]:
    try:
        lines = raw.decode("ascii").replace("\r", "").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError("fixed ADB inventory is malformed") from exc
    if not lines or lines[0] != "List of devices attached":
        raise RuntimeError("fixed ADB inventory header is malformed")
    rows = []
    seen = set()
    for line in lines[1:]:
        if not line:
            continue
        fields = line.split(None, 2)
        if len(fields) < 2 or not re.fullmatch(r"[!-~]{1,256}", fields[0]) or fields[0] in seen:
            raise RuntimeError("fixed ADB inventory endpoint is malformed")
        serial, state = fields[0], fields[1]
        rest = fields[2] if len(fields) == 3 else ""
        if state == "no" and rest.startswith("permissions"):
            state, rest = "no permissions", rest[len("permissions"):].lstrip()
        if state not in {"device", "recovery", "offline", "unauthorized", "no permissions"}:
            raise RuntimeError("fixed ADB inventory state is malformed")
        attrs = tuple(sorted(rest.split())) if rest else ()
        if any(OWNER_ADB_ATTRIBUTE_RE.fullmatch(item) is None for item in attrs):
            raise RuntimeError("fixed ADB inventory attribute is malformed")
        _owner_register_serial(serial)
        seen.add(serial)
        rows.append((serial, state, attrs))
    return rows


def _owner_adb_inventory_sha256(
    expected_serial_sha256: str,
    expected_role: str,
) -> str:
    """Capture and attribute one fixed raw ``adb devices -l`` inventory."""
    if (
        type(expected_serial_sha256) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected_serial_sha256) is None
        or expected_role not in {OWNER_ADB_ROLE_NATIVE, OWNER_ADB_ROLE_RECOVERY}
    ):
        raise RuntimeError("fixed owner ADB inventory binding is not exact")
    process = subprocess.Popen(
        [OWNER_ADB, "devices", "-l"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired as exc:
            try:
                os.killpg(process.pid, 9)
            except ProcessLookupError:
                pass
            process.wait()
            raise RuntimeError("fixed ADB inventory timed out") from exc
        if process.returncode != 0 or stderr or not stdout or not stdout.endswith(b"\n"):
            raise RuntimeError("fixed ADB inventory producer failed")
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            raise RuntimeError("fixed ADB inventory producer survived") from exc
        else:
            raise RuntimeError("fixed ADB inventory producer survived")
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, 9)
            except ProcessLookupError:
                pass
    if len(stdout) > 1 << 20:
        raise RuntimeError("fixed ADB inventory is oversized")
    rows = _owner_parse_adb_rows(stdout)
    recovery_rows = [item for item in rows if item[1] == "recovery"]
    matching_rows = [
        item for item in rows
        if hashlib.sha256(item[0].encode("utf-8")).hexdigest()
        == expected_serial_sha256
    ]
    if expected_role == OWNER_ADB_ROLE_NATIVE:
        exact = len(rows) == 0
    else:
        exact = (
            len(rows) == 1
            and len(recovery_rows) == 1
            and len(matching_rows) == 1
            and recovery_rows[0][:2] == matching_rows[0][:2]
        )
    if not exact:
        raise RuntimeError("fixed ADB inventory role is not exact")
    digest = hashlib.sha256(stdout).hexdigest()
    log(f"owner ADB inventory receipt={digest} role={expected_role}")
    return digest


def _owner_pre_native_recovery_gate(args: argparse.Namespace) -> None:
    """Rebind the initial Native/foreign epoch immediately before bridge use."""
    if args.owner_expect_adb_role != OWNER_ADB_ROLE_NATIVE:
        raise RuntimeError("pre-recovery owner role is not Native")
    usb_digest = _owner_usb_inventory_sha256(
        OWNER_ADB_ROLE_NATIVE,
    )
    if usb_digest != args.owner_expect_usb_inventory_sha256:
        raise RuntimeError("owner USB inventory changed before Native recovery")
    adb_digest = _owner_adb_inventory_sha256(
        args.expect_recovery_serial_sha256,
        OWNER_ADB_ROLE_NATIVE,
    )
    if adb_digest != args.owner_expect_adb_inventory_sha256:
        raise RuntimeError("owner ADB inventory changed before Native recovery")


@contextmanager
def phase_timer(name: str):
    started = time.monotonic()
    ok = False
    try:
        yield
        ok = True
    finally:
        elapsed = time.monotonic() - started
        log(f"phase.native_init_flash.{name}.elapsed_sec={elapsed:.3f} ok={int(ok)}")


def run_command(args: list[str],
                *,
                check: bool = True,
                capture: bool = False) -> subprocess.CompletedProcess:
    log("+ " + shlex.join(args))
    if capture:
        return subprocess.run(
            args,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    kwargs: dict[str, object] = {}
    if OWNER_EFFECT_STATE is not None:
        # The owner receipt is the sole stdout producer.  Child command prose
        # must not be mixed into its strict machine envelope.
        kwargs["stdout"] = subprocess.DEVNULL
    return subprocess.run(args, check=check, **kwargs)


def adb_base(adb: str, serial: str | None) -> list[str]:
    base = [adb]
    if serial:
        base.extend(["-s", serial])
    return base


def quote_remote_path(path: str, *, label: str) -> str:
    if not path.startswith("/") or "\x00" in path:
        raise RuntimeError(f"{label} must be an absolute remote path")
    return shlex.quote(path)


def parse_adb_devices(output: str) -> list[tuple[str, str]]:
    devices: list[tuple[str, str]] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices"):
            continue

        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    for device_serial, _state in devices:
        _owner_register_serial(device_serial)
    return devices


def parse_adb_devices_strict(output: str) -> list[tuple[str, str]]:
    lines = output.splitlines()
    if not lines or lines[0].strip() != "List of devices attached":
        raise RuntimeError("ADB inventory header is missing or malformed")
    devices: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_line in lines[1:]:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[0] in seen:
            raise RuntimeError("ADB inventory contains a malformed or duplicate endpoint")
        seen.add(parts[0])
        devices.append((parts[0], parts[1]))
    for device_serial, _state in devices:
        _owner_register_serial(device_serial)
    return devices


def adb_devices(adb: str, *, strict: bool = False) -> list[tuple[str, str]]:
    result = subprocess.run(
        [adb, "devices"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if strict:
        if result.returncode != 0 or result.stderr:
            raise RuntimeError("ADB inventory command failed or wrote stderr")
        return parse_adb_devices_strict(result.stdout)
    return parse_adb_devices(result.stdout)


def adb_state(adb: str, serial: str, *, strict: bool = False) -> str | None:
    for device_serial, state in adb_devices(adb, strict=strict):
        if device_serial == serial:
            return state
    return None


def wait_for_adb_state(adb: str,
                       serial: str | None,
                       wanted_states: set[str],
                       timeout_sec: float,
                       *,
                       require_unique: bool = False,
                       strict_inventory: bool = False) -> tuple[str, str]:
    deadline = time.monotonic() + timeout_sec
    last_devices: list[tuple[str, str]] = []

    while time.monotonic() < deadline:
        last_devices = adb_devices(adb, strict=strict_inventory)
        if require_unique and len(last_devices) > 1:
            rendered = ", ".join(
                f"{device_serial}:{state}" for device_serial, state in last_devices
            )
            raise RuntimeError(f"ADB arrival is ambiguous: {rendered}")
        for device_serial, state in last_devices:
            if serial and device_serial != serial:
                continue
            if state in wanted_states:
                log(f"ADB ready: {device_serial} {state}")
                return device_serial, state
        time.sleep(1.0)

    rendered = ", ".join(f"{device_serial}:{state}" for device_serial, state in last_devices) or "<none>"
    raise RuntimeError(f"ADB state timeout; wanted={sorted(wanted_states)} last={rendered}")


def wait_for_adb_disconnect(
    adb: str,
    serial: str,
    timeout_sec: float,
    *,
    strict_inventory: bool = False,
) -> bool:
    deadline = time.monotonic() + timeout_sec

    while time.monotonic() < deadline:
        if adb_state(adb, serial, strict=strict_inventory) is None:
            return True
        time.sleep(0.5)

    return False


def wait_for_new_recovery_adb(
    adb: str,
    baseline: list[tuple[str, str]],
    timeout_sec: float,
    *,
    expected_serial_sha256: str,
) -> tuple[str, str]:
    """Bind one recovery arrival while every pre-existing endpoint stays exact."""
    baseline_set = set(baseline)
    if len(baseline_set) != len(baseline) or any(
        state == "recovery" for _serial, state in baseline
    ):
        raise RuntimeError("ADB baseline is not a valid foreign-endpoint baseline")
    deadline = time.monotonic() + timeout_sec
    last_devices = baseline
    while time.monotonic() < deadline:
        last_devices = adb_devices(adb, strict=True)
        current_set = set(last_devices)
        if not baseline_set.issubset(current_set):
            raise RuntimeError("pre-existing ADB endpoint changed during A90 recovery arrival")
        arrivals = current_set - baseline_set
        if len(arrivals) > 1:
            raise RuntimeError("ADB recovery arrival is ambiguous")
        if len(arrivals) == 1:
            serial, state = next(iter(arrivals))
            if state == "recovery":
                observed = hashlib.sha256(serial.encode("utf-8")).hexdigest()
                if observed != expected_serial_sha256:
                    raise RuntimeError("new recovery endpoint is not the bound A90")
                log(f"ADB ready: {serial} {state}")
                return serial, state
        time.sleep(1.0)
    rendered = ", ".join(
        f"{device_serial}:{state}" for device_serial, state in last_devices
    ) or "<none>"
    raise RuntimeError(f"ADB recovery arrival timeout; last={rendered}")


def bind_present_recovery_or_native_baseline(
    adb: str,
    *,
    expected_serial_sha256: str,
) -> tuple[list[tuple[str, str]], tuple[str, str] | None]:
    """Bind an existing A90 recovery endpoint or a clean Native baseline.

    The returned baseline never contains the bound recovery endpoint.  A
    caller may therefore either use the returned recovery endpoint directly,
    or send the one Native recovery command and wait for one new arrival over
    the unchanged baseline.  A foreign/ambiguous recovery endpoint is a stop,
    never a reason to select by caller-provided serial.
    """
    devices = adb_devices(adb, strict=True)
    recovery = [item for item in devices if item[1] == "recovery"]
    if len(recovery) > 1:
        raise RuntimeError("ADB recovery baseline is ambiguous")
    if not recovery:
        return devices, None
    serial, state = recovery[0]
    observed = hashlib.sha256(serial.encode("utf-8")).hexdigest()
    if observed != expected_serial_sha256:
        raise RuntimeError("present recovery endpoint is not the bound A90")
    baseline = [item for item in devices if item != recovery[0]]
    log(f"ADB ready: {serial} {state} (already present and bound)")
    return baseline, recovery[0]


def wait_for_adb_baseline_restored(
    adb: str,
    recovery_serial: str,
    baseline: list[tuple[str, str]],
    timeout_sec: float,
) -> bool:
    """Require only the causally bound A90 recovery endpoint to disappear."""
    baseline_set = set(baseline)
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        current = set(adb_devices(adb, strict=True))
        if current == baseline_set:
            return True
        if not baseline_set.issubset(current):
            raise RuntimeError("pre-existing ADB endpoint changed during A90 recovery exit")
        extras = current - baseline_set
        if any(serial != recovery_serial for serial, _state in extras):
            raise RuntimeError("foreign ADB endpoint appeared during A90 recovery exit")
        time.sleep(0.5)
    return False


def local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_sha256(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise RuntimeError(f"{label} must be a 64-character hex SHA256")
    return normalized


def file_contains(path: Path, needle: bytes) -> bool:
    if not needle:
        return True

    overlap = max(len(needle) - 1, 0)
    previous = b""
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            data = previous + chunk
            if needle in data:
                return True
            previous = data[-overlap:] if overlap else b""

    return False


def inspect_local_image(args: argparse.Namespace) -> tuple[Path, str, int]:
    image_path = Path(args.boot_image)
    try:
        image_stat = image_path.lstat()
    except FileNotFoundError:
        raise FileNotFoundError(image_path)
    if not stat.S_ISREG(image_stat.st_mode):
        raise RuntimeError(f"boot image is not a regular file: {image_path}")
    if image_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError(f"boot image is group/world writable: {image_path}")

    image_size = image_stat.st_size
    if image_size <= 0:
        raise RuntimeError(f"boot image is empty: {image_path}")
    if image_size % BOOT_READBACK_BLOCK_SIZE != 0:
        raise RuntimeError(
            f"boot image size is not {BOOT_READBACK_BLOCK_SIZE}-byte aligned: "
            f"{image_size}"
        )

    if getattr(args, "expect_android_magic", False):
        with image_path.open("rb") as fp:
            magic = fp.read(len(ANDROID_BOOT_MAGIC))
        if magic != ANDROID_BOOT_MAGIC:
            raise RuntimeError("local image does not start with Android boot magic")
        log("local image starts with Android boot magic")

    if args.expect_version:
        needle = args.expect_version.encode()
        if not file_contains(image_path, needle):
            raise RuntimeError(
                f"expected version marker not found in local image before reboot: "
                f"{args.expect_version}"
            )
        log(f"local image contains expected marker: {args.expect_version}")

    local_hash = local_sha256(image_path)
    if args.expect_sha256 and local_hash != args.expect_sha256:
        raise RuntimeError(
            f"local image sha256 mismatch: expected={args.expect_sha256} actual={local_hash}"
        )
    log(f"local image size: {image_size}")
    log(f"local image sha256: {local_hash}")
    return image_path, local_hash, image_size


def validate_self_write_staging_dir(path: str) -> str:
    if "\x00" in path or not path.startswith("/"):
        raise RuntimeError("--self-write-staging-dir must be an absolute device path")
    normalized = posixpath.normpath(path)
    if normalized != path.rstrip("/"):
        raise RuntimeError("--self-write-staging-dir must be normalized")
    if normalized not in SELF_WRITE_ALLOWED_STAGING_DIRS:
        allowed = ", ".join(SELF_WRITE_ALLOWED_STAGING_DIRS)
        raise RuntimeError(f"--self-write-staging-dir must be one of: {allowed}")
    return normalized


def self_write_remote_image_path(args: argparse.Namespace, image_path: Path) -> str:
    staging_dir = validate_self_write_staging_dir(args.self_write_staging_dir)
    basename = image_path.name
    if not basename or not SELF_WRITE_SAFE_BASENAME_RE.fullmatch(basename):
        raise RuntimeError(f"unsafe self-write remote image basename: {basename!r}")
    return posixpath.join(staging_dir, basename)


def build_experimental_self_write_plan(args: argparse.Namespace,
                                       image_path: Path,
                                       local_hash: str,
                                       image_size: int) -> dict[str, object]:
    if not args.expect_sha256:
        raise RuntimeError("experimental self-write requires --expect-sha256")
    if not args.expect_version:
        raise RuntimeError("experimental self-write requires --expect-version")
    if args.allow_unpinned_image:
        raise RuntimeError("experimental self-write does not allow --allow-unpinned-image")
    if not args.expect_android_magic:
        raise RuntimeError("experimental self-write requires --expect-android-magic")

    mode = getattr(args, "self_write_mode", "f2") or "f2"
    if mode not in SELF_WRITE_MODES:
        raise RuntimeError(f"unknown --self-write-mode: {mode!r}")
    mode_spec = SELF_WRITE_MODES[mode]
    live_authorized = bool(getattr(args, "self_write_live_authorized", False))
    remote_image = self_write_remote_image_path(args, image_path)
    tcpctl_script = "workspace/public/src/scripts/revalidation/tcpctl_host.py"
    return {
        "mode": "experimental-self-write",
        "self_write_mode": mode,
        "policy_state": (
            "f4-live-authorized" if live_authorized else "plan-only-live-blocked"
        ),
        "policy_block": SELF_WRITE_POLICY_BLOCK,
        "local_image": str(image_path),
        "local_sha256": local_hash,
        "image_size": image_size,
        "expected_version": args.expect_version,
        "remote_image": remote_image,
        "staging_dir": posixpath.dirname(remote_image),
        "preflight_commands": [
            "version",
            "status",
            "selftest",
            "pstore summary",
        ],
        "stage_command": [
            "python3",
            tcpctl_script,
            "--bridge-host",
            args.bridge_host,
            "--bridge-port",
            str(args.bridge_port),
            "--device-binary",
            remote_image,
            "install",
            "--install-control-channel",
            "tcpctl",
            "--local-binary",
            str(image_path),
        ],
        "source_plan_command": [
            "boot-flash-plan",
            remote_image,
            local_hash,
            args.expect_version,
        ],
        "self_write_command": [
            mode_spec["command"],
            mode_spec["token"],
            remote_image,
            local_hash,
            args.expect_version,
        ],
        "self_write_success_marker": mode_spec["success_marker"],
        "system_reboot_command": ["reboot"],
        "required_timeline_events": [
            "candidate_flash_start",
            "candidate_flash_done",
            "candidate_boot_ready",
            "live_session_start",
            "live_session_end",
            "rollback_flash_start",
            "rollback_flash_done",
            "rollback_boot_ready",
        ],
        "fallback_path": "native_init_flash.py rollback to v2321 through checked helper/TWRP",
    }


def selfwrite_cmdv1(args: argparse.Namespace,
                    command: list[str],
                    timeout_sec: float | None = None) -> ProtocolResult:
    result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        timeout_sec if timeout_sec is not None else args.bridge_timeout,
        command,
    )
    owner_stdout(result.text, end="" if result.text.endswith("\n") else "\n")
    return result


def selfwrite_hide_settle(args: argparse.Namespace, settle_sec: float) -> None:
    output = bridge_command(
        args.bridge_host,
        args.bridge_port,
        "hide",
        args.bridge_timeout,
        markers=(b"[busy]", b"[done]", b"[err]"),
    )
    owner_stdout(output, end="")
    time.sleep(settle_sec)


VERSION_FIELD_RE = re.compile(r"(?m)^version:\s*(\S+)")


def parse_native_version_field(text: str) -> str | None:
    match = VERSION_FIELD_RE.search(text)
    return match.group(1) if match else None


def wait_for_native_version(args: argparse.Namespace,
                            expect_version: str,
                            overall_timeout: float,
                            poll_interval: float = 3.0) -> str:
    deadline = time.monotonic() + overall_timeout
    last = ""
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            result = run_cmdv1_command(
                args.bridge_host,
                args.bridge_port,
                min(20.0, max(2.0, remaining)),
                ["version"],
            )
            # require a clean cmdv1 result AND an exact-field version match so a partial
            # reconnect, an error frame, or the pre-reboot image is never mistaken for the
            # self-written target.
            if result.rc == 0 and result.status == "ok":
                observed = parse_native_version_field(result.text)
                if observed == expect_version:
                    owner_stdout(result.text, end="" if result.text.endswith("\n") else "\n")
                    return result.text
                last = f"observed version field={observed!r}"
            else:
                last = f"rc={result.rc} status={result.status}"
        except Exception as exc:  # noqa: BLE001 - device is re-enumerating; keep polling
            last = str(exc)
        time.sleep(poll_interval)
    raise RuntimeError(
        f"native init did not report exact version {expect_version} within {overall_timeout:.0f}s; "
        f"last={last!r}"
    )


def run_self_write_live(args: argparse.Namespace,
                        plan: dict[str, object],
                        image_path: Path,
                        local_hash: str,
                        image_size: int) -> int:
    # design section 12.1 F4-live amendment: only the v2321 rollback image with f3 semantics.
    if args.self_write_mode != "f3":
        raise RuntimeError(
            "F4-live is authorized only for --self-write-mode f3 (self-rollback to v2321)"
        )
    if (local_hash.lower() != SELF_WRITE_F4_LIVE_SHA256
            or args.expect_version != SELF_WRITE_F4_LIVE_VERSION):
        raise RuntimeError(
            "F4-live candidate must be the v2321 rollback image "
            f"(sha256 {SELF_WRITE_F4_LIVE_SHA256}, version {SELF_WRITE_F4_LIVE_VERSION})"
        )

    success_marker = str(plan["self_write_success_marker"])
    events: list[dict[str, object]] = []

    def emit(name: str) -> None:
        events.append({
            "event": name,
            "monotonic": round(time.monotonic(), 3),
            "wallclock": time.strftime("%H:%M:%S"),
        })
        log(f"self-write event: {name}")

    result: dict[str, object] = {
        "mode": "experimental-self-write-live",
        "self_write_mode": args.self_write_mode,
        "policy_state": "f4-live-authorized",
        "candidate": str(image_path),
        "candidate_sha256": local_hash,
        "candidate_version": args.expect_version,
        "events": events,
    }

    emit("preflight_start")
    # the auto-menu (autohud) can re-assert on idle and returns rc=-16 status=busy for commands
    # that are not menu-allowed (e.g. pstore, boot-flash-plan); hide/settle before each such group.
    selfwrite_hide_settle(args, settle_sec=args.menu_settle_sec)
    for name in ("version", "status", "selftest"):
        r = selfwrite_cmdv1(args, [name])
        verify_cmdv1_result(r, name)
        if name == "selftest" and "fail=0" not in r.text:
            raise RuntimeError("preflight selftest did not report fail=0")
    pstore = selfwrite_cmdv1(args, ["pstore", "summary"])
    verify_cmdv1_result(pstore, "pstore summary")
    if "entries=0" not in pstore.text:
        raise RuntimeError("preflight pstore summary did not report entries=0")
    emit("preflight_ok")

    emit("candidate_stage_start")
    stage_start = time.monotonic()
    if getattr(args, "self_write_skip_stage", False):
        # transport-independent path: the candidate is already present in the approved staging
        # root; the device-side boot-flash-plan below re-verifies its SHA/version/header and fails
        # closed on any mismatch before any write, so skipping the tcpctl push is safe.
        log("skip-stage: assuming candidate already staged; boot-flash-plan will verify SHA/version")
        result["staged"] = "skipped-preexisting"
    else:
        run_command([str(part) for part in plan["stage_command"]])
        result["staged"] = "tcpctl"
    emit("candidate_stage_done")

    if getattr(args, "self_write_skip_source_plan", False):
        # boot-flash-f3 re-validates the candidate SHA/version/header itself before any write
        # (expected_sha_match / version_marker_found), so the separate read-only boot-flash-plan
        # pre-check is redundant on the fast path and is skipped to save a command + a settle.
        log("skip-source-plan: boot-flash-f3 re-verifies candidate SHA/version before writing")
        result["source_plan"] = "skipped-redundant"
    else:
        selfwrite_hide_settle(args, settle_sec=args.menu_settle_sec)
        emit("source_plan_start")
        source = selfwrite_cmdv1(
            args,
            [str(part) for part in plan["source_plan_command"]],
            timeout_sec=max(args.bridge_timeout, 300.0),
        )
        verify_cmdv1_result(source, "boot-flash-plan")
        for needle in ("result=ok source-plan-only", "expected_sha_match=1", "version_marker_found=1"):
            if needle not in source.text:
                raise RuntimeError(f"source-plan did not report {needle!r}")
        emit("source_plan_done")

    # boot-flash-f3 is CMD_DANGEROUS; hide/settle any active menu before dispatch.
    selfwrite_hide_settle(args, settle_sec=args.menu_settle_sec)
    emit("self_write_start")
    self_write = selfwrite_cmdv1(
        args,
        [str(part) for part in plan["self_write_command"]],
        timeout_sec=max(args.self_write_timeout, args.bridge_timeout),
    )
    verify_cmdv1_result(self_write, "boot-flash-f3")
    for needle in (success_marker, "target_full_match=1", "reboot_required=1"):
        if needle not in self_write.text:
            raise RuntimeError(f"self-write did not report {needle!r}")
    self_flash_elapsed = time.monotonic() - stage_start
    result["self_flash_elapsed_sec"] = round(self_flash_elapsed, 3)
    emit("self_write_done")

    # host-controlled reboot into the self-written v2321 (reboot is CMD_DANGEROUS|CMD_NO_DONE).
    selfwrite_hide_settle(args, settle_sec=args.menu_settle_sec)
    emit("system_reboot_requested")
    try:
        reboot_out = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "reboot",
            30.0,
            markers=(b"[busy]", b"[err]", b"reboot"),
        )
        owner_stdout(reboot_out, end="")
    except RuntimeError as exc:
        # CMD_NO_DONE: the device drops the link instead of returning a marker.
        log(f"reboot returned no clean marker (expected for CMD_NO_DONE): {exc}")

    emit("rollback_boot_wait")
    verify_start = time.monotonic()
    wait_for_native_version(args, SELF_WRITE_F4_LIVE_VERSION, overall_timeout=args.reboot_timeout,
                            poll_interval=args.reboot_poll_interval_sec)
    final_selftest = run_cmdv1_command(
        args.bridge_host, args.bridge_port, args.bridge_timeout, ["selftest"]
    )
    owner_stdout(final_selftest.text, end="" if final_selftest.text.endswith("\n") else "\n")
    verify_cmdv1_result(final_selftest, "selftest")
    if "fail=0" not in final_selftest.text:
        raise RuntimeError("post-reboot v2321 selftest did not report fail=0")
    result["reboot_boot_elapsed_sec"] = round(time.monotonic() - verify_start, 3)
    emit("rollback_boot_ready")

    result["status"] = "ok"
    owner_stdout(json.dumps(result, indent=2, sort_keys=True))

    runs_dir = Path("workspace/private/runs/self-dd")
    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
        out_path = runs_dir / f"f4-live-{time.strftime('%Y%m%d-%H%M%S')}.json"
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
        log(f"self-write result written to {out_path}")
    except OSError as exc:
        log(f"could not write self-write result json: {exc}")
    return 0


def run_experimental_self_write(args: argparse.Namespace,
                                image_path: Path,
                                local_hash: str,
                                image_size: int) -> int:
    plan = build_experimental_self_write_plan(args, image_path, local_hash, image_size)
    owner_stdout(json.dumps(plan, indent=2, sort_keys=True))
    if args.self_write_plan_only:
        return 0
    if not getattr(args, "self_write_live_authorized", False):
        raise RuntimeError(SELF_WRITE_POLICY_BLOCK)
    return run_self_write_live(args, plan, image_path, local_hash, image_size)


@contextmanager
def sealed_local_image_copy(image_path: Path, expected_hash: str, expected_size: int):
    with tempfile.TemporaryDirectory(prefix="native-init-flash-") as temp_dir:
        sealed_path = Path(temp_dir) / "boot.img"
        open_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(image_path, open_flags)
        try:
            source_stat = os.fstat(fd)
            if not stat.S_ISREG(source_stat.st_mode):
                raise RuntimeError(f"boot image changed to a non-regular file: {image_path}")
            if source_stat.st_size != expected_size:
                raise RuntimeError(
                    f"boot image size changed before push: expected={expected_size} "
                    f"actual={source_stat.st_size}"
                )
            with os.fdopen(os.dup(fd), "rb") as source, sealed_path.open("xb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
        finally:
            os.close(fd)
        os.chmod(sealed_path, 0o600)
        sealed_size = sealed_path.stat().st_size
        sealed_hash = local_sha256(sealed_path)
        if sealed_size != expected_size:
            raise RuntimeError(f"sealed image size mismatch: expected={expected_size} actual={sealed_size}")
        if sealed_hash != expected_hash:
            raise RuntimeError(f"sealed image sha256 mismatch: expected={expected_hash} actual={sealed_hash}")
        log(f"sealed local image copy: {sealed_path}")
        yield sealed_path


def remote_sha256(adb: str, serial: str | None, remote_path: str) -> str:
    remote = quote_remote_path(remote_path, label="remote image")
    command = adb_base(adb, serial) + [
        "shell",
        f"sha256sum {remote} 2>/dev/null || toybox sha256sum {remote}",
    ]
    result = run_command(command, capture=True)
    first_field = result.stdout.strip().split()[0]
    if len(first_field) != 64:
        raise RuntimeError(
            "unexpected remote sha256 output: "
            + _owner_redact_text(repr(result.stdout))
        )
    return first_field


def remote_boot_prefix_sha256(adb: str,
                              serial: str | None,
                              boot_block: str,
                              image_size: int) -> str:
    count = image_size // BOOT_READBACK_BLOCK_SIZE
    block = quote_remote_path(boot_block, label="boot block")
    command = adb_base(adb, serial) + [
        "shell",
        (
            f"dd if={block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} "
            "2>/dev/null | sha256sum 2>/dev/null || "
            f"dd if={block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} "
            "2>/dev/null | toybox sha256sum"
        ),
    ]
    result = run_command(command, capture=True)
    first_field = result.stdout.strip().split()[0]
    if len(first_field) != 64:
        raise RuntimeError(
            "unexpected boot prefix sha256 output: "
            + _owner_redact_text(repr(result.stdout))
        )
    return first_field


def bridge_command(host: str,
                   port: int,
                   command: str,
                   timeout_sec: float,
                   markers: tuple[bytes, ...] = (b"[done]", b"[err]"),
                   retry_transport: bool = True) -> str:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0) as sock:
                sock.settimeout(0.25)
                wire_command = command
                input_mode = os.environ.get(INPUT_MODE_ENV)
                double_input = input_mode == "double"
                if double_input:
                    wire_command = "".join(ch * 2 for ch in command)
                prefix = "" if input_mode in {"double", "slow"} else "\n"
                payload = prefix + wire_command + "\n"
                if input_mode == "slow":
                    delay = float(os.environ.get(INPUT_CHAR_DELAY_ENV, "0.02"))
                    for ch in payload:
                        sock.sendall(ch.encode())
                        time.sleep(delay)
                else:
                    sock.sendall(payload.encode())
                data = bytearray()
                read_deadline = time.monotonic() + 5.0
                while time.monotonic() < read_deadline:
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    data.extend(chunk)
                    if any(marker in data for marker in markers):
                        time.sleep(0.2)
                        try:
                            data.extend(sock.recv(8192))
                        except socket.timeout:
                            pass
                        return data.decode("utf-8", errors="replace")
        except OSError as exc:
            last_error = exc

        if not retry_transport:
            raise RuntimeError(
                f"bridge command outcome uncertain after one send for {command!r}: "
                f"{last_error}"
            )

        time.sleep(1.0)

    raise RuntimeError(f"bridge command timeout for {command!r}: {last_error}")


def reboot_native_to_recovery(args: argparse.Namespace) -> None:
    log("requesting recovery from native init bridge")
    if (
        args.require_empty_adb_baseline
        or args.require_stable_adb_baseline
        or getattr(args, "reuse_bound_recovery_or_from_native", False)
    ):
        if getattr(args, "owner_fixed_bridge_preflight", False):
            _owner_bridge_preflight(args)
        output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "recovery",
            args.bridge_timeout,
            markers=(b"recovery:", b"[err]", b"[busy]"),
            retry_transport=False,
        )
        owner_stdout(output, end="")
        if "[busy]" in output or "[err]" in output:
            raise RuntimeError(
                "native recovery command failed; minimal one-shot mode does not resend"
            )
        return
    for attempt in range(1, 4):
        output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "recovery",
            args.bridge_timeout,
            markers=(b"recovery:", b"[err]", b"[busy]"),
        )
        owner_stdout(output, end="")

        if "[busy]" not in output:
            return

        log(f"native init menu is active; requesting hide before recovery attempt={attempt}")
        hide_output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "hide",
            args.bridge_timeout,
            markers=(b"[busy]", b"[done]", b"[err]"),
        )
        owner_stdout(hide_output, end="")
        time.sleep(3.0)

    raise RuntimeError("native init recovery command stayed busy after hide retries")


def flash_boot_image(args: argparse.Namespace,
                     serial: str,
                     image_path: Path,
                     local_hash: str,
                     image_size: int) -> None:
    expected_readback_hash = args.expect_readback_sha256 or local_hash
    remote = quote_remote_path(args.remote_image, label="remote image")
    block = quote_remote_path(args.boot_block, label="boot block")

    if getattr(args, "owner_expect_usb_inventory_sha256", None) is not None:
        identity = run_command(
            adb_base(args.adb, serial) + ["shell", TWRP_IDENTITY_CHECK_COMMAND],
            check=False,
            capture=True,
        )
        if identity.returncode != 0 or identity.stdout or identity.stderr:
            raise RuntimeError("fixed TWRP identity changed before boot push")

    with phase_timer("adb_push"):
        run_command(adb_base(args.adb, serial) + ["push", str(image_path), args.remote_image])

    with phase_timer("remote_sha256"):
        remote_hash = remote_sha256(args.adb, serial, args.remote_image)
    log(f"remote image sha256: {remote_hash}")
    if remote_hash != local_hash:
        raise RuntimeError("remote sha256 mismatch after adb push")

    flash_cmd = (
        f"dd if={remote} of={block} "
        "bs=4M conv=fsync && sync"
    )
    if OWNER_EFFECT_STATE is not None:
        OWNER_EFFECT_STATE.write_started = True
    with phase_timer("boot_dd_write"):
        run_command(adb_base(args.adb, serial) + ["shell", flash_cmd])

    with phase_timer("boot_readback_sha256"):
        boot_prefix_hash = remote_boot_prefix_sha256(args.adb, serial, args.boot_block, image_size)
    log(f"boot block prefix sha256: {boot_prefix_hash}")
    if boot_prefix_hash != expected_readback_hash:
        raise RuntimeError("boot block prefix sha256 mismatch after flash")
    if OWNER_EFFECT_STATE is not None:
        OWNER_EFFECT_STATE.boot_written_readback_exact = True


def reboot_twrp_to_system(
    args: argparse.Namespace,
    serial: str,
    *,
    adb_baseline: list[tuple[str, str]] | None = None,
) -> None:
    time.sleep(1.0)

    minimal_single_shot = (
        args.require_empty_adb_baseline
        or args.require_stable_adb_baseline
        or getattr(args, "reuse_bound_recovery_or_from_native", False)
    )
    reboot_command = (
        TWRP_SYSTEM_REBOOT_COMMAND
        if (
            args.require_stable_adb_baseline
            or getattr(args, "reuse_bound_recovery_or_from_native", False)
        )
        else "twrp reboot"
    )
    attempts = 1 if minimal_single_shot else 3
    for attempt in range(1, attempts + 1):
        if OWNER_EFFECT_STATE is not None:
            OWNER_EFFECT_STATE.system_return_attempted = True
        log(f"requesting system boot through TWRP no-argument reboot attempt={attempt}")
        result = run_command(
            adb_base(args.adb, serial)
            + ["shell", reboot_command],
            check=False,
            capture=True,
        )
        output = (result.stdout + result.stderr).strip()
        if output:
            for line in output.splitlines():
                log(f"twrp reboot: {line}")

        if OWNER_EFFECT_STATE is not None:
            if result.returncode != 0:
                raise RuntimeError(
                    f"TWRP System-return command failed with rc={result.returncode}"
                )
            OWNER_EFFECT_STATE.system_return_command_ok = True

        if (
            args.require_stable_adb_baseline
            or getattr(args, "reuse_bound_recovery_or_from_native", False)
        ):
            if adb_baseline is None:
                raise RuntimeError("stable ADB baseline is missing at recovery exit")
            disconnected = wait_for_adb_baseline_restored(
                args.adb, serial, adb_baseline, 8.0
            )
        else:
            disconnected = wait_for_adb_disconnect(
                args.adb,
                serial,
                8.0,
                strict_inventory=args.require_empty_adb_baseline,
            )
        if disconnected:
            if OWNER_EFFECT_STATE is not None:
                OWNER_EFFECT_STATE.system_return_confirmed = True
            return

        if minimal_single_shot:
            raise RuntimeError(
                "TWRP reboot outcome uncertain; minimal one-shot mode does not resend"
            )
        log("TWRP recovery ADB is still present after reboot request; retrying")
        time.sleep(2.0)

    raise RuntimeError("TWRP reboot did not leave recovery ADB")


def verify_native_init(args: argparse.Namespace) -> str:
    if args.verify_protocol == "selftest":
        return verify_native_init_selftest(args)
    if args.verify_protocol == "raw":
        return verify_native_init_raw(args)

    try:
        return verify_native_init_cmdv1(args)
    except RuntimeError as exc:
        if args.verify_protocol == "cmdv1":
            raise
        if "A90P1 END marker not found" not in str(exc):
            raise
        log(f"cmdv1 verify unavailable; falling back to raw version check: {exc}")
        return verify_native_init_raw(args)


def verify_native_init_selftest(args: argparse.Namespace) -> str:
    result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["selftest"],
    )
    owner_stdout(result.text, end="" if result.text.endswith("\n") else "\n")
    verify_cmdv1_result(result, "selftest")
    if "fail=0" not in result.text:
        raise RuntimeError("native selftest did not report fail=0")
    version_text = ""
    if args.expect_version:
        version_result = run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            args.bridge_timeout,
            ["version"],
        )
        owner_stdout(version_result.text, end="" if version_result.text.endswith("\n") else "\n")
        verify_cmdv1_result(version_result, "version")
        if args.expect_version not in version_result.text:
            raise RuntimeError(f"expected version marker not found: {args.expect_version}")
        version_text = version_result.text
    log("cmdv1 verify passed: selftest rc=0 status=ok fail=0")
    return result.text + version_text


def verify_native_init_raw(args: argparse.Namespace) -> str:
    output = bridge_command(
        args.bridge_host,
        args.bridge_port,
        "version",
        args.bridge_timeout,
        markers=(b"[done] version", b"[err] version"),
    )
    owner_stdout(output, end="")
    if args.expect_version and args.expect_version not in output:
        raise RuntimeError(f"expected version marker not found: {args.expect_version}")
    return output


def verify_cmdv1_result(result: ProtocolResult, command: str) -> None:
    if result.rc != 0 or result.status != "ok":
        raise RuntimeError(
            f"cmdv1 {command} failed rc={result.rc} status={result.status}\n"
            f"{result.text}"
        )


def verify_native_init_cmdv1(args: argparse.Namespace) -> str:
    version_result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["version"],
    )
    owner_stdout(version_result.text, end="" if version_result.text.endswith("\n") else "\n")
    verify_cmdv1_result(version_result, "version")
    if args.expect_version and args.expect_version not in version_result.text:
        raise RuntimeError(f"expected version marker not found: {args.expect_version}")

    status_result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["status"],
    )
    owner_stdout(status_result.text, end="" if status_result.text.endswith("\n") else "\n")
    verify_cmdv1_result(status_result, "status")

    log("cmdv1 verify passed: version/status rc=0 status=ok")
    return version_result.text + status_result.text


def adb_shell_text(adb: str,
                   serial: str | None,
                   shell_command: str,
                   *,
                   check: bool = False) -> str:
    result = run_command(
        adb_base(adb, serial) + ["shell", shell_command],
        check=check,
        capture=True,
    )
    return (result.stdout + result.stderr).strip()


def verify_android_adb(args: argparse.Namespace) -> str:
    serial, state = wait_for_adb_state(
        args.adb,
        args.serial,
        {"device"},
        args.android_timeout,
    )
    if state != "device":
        raise RuntimeError(f"expected Android device ADB state, got {state}")

    deadline = time.monotonic() + args.android_timeout
    last_props = ""
    while time.monotonic() < deadline:
        sys_boot_completed = adb_shell_text(args.adb, serial, "getprop sys.boot_completed")
        dev_bootcomplete = adb_shell_text(args.adb, serial, "getprop dev.bootcomplete")
        last_props = (
            f"sys.boot_completed={sys_boot_completed!r} "
            f"dev.bootcomplete={dev_bootcomplete!r}"
        )
        if sys_boot_completed == "1" or dev_bootcomplete == "1":
            log(f"Android boot-complete observed: {last_props}")
            break
        time.sleep(2.0)
    else:
        raise RuntimeError(f"Android boot-complete timeout: {last_props}")

    root_text = ""
    if args.android_root_check:
        root_text = adb_shell_text(args.adb, serial, "su -c id", check=False)
        if "uid=0" not in root_text:
            raise RuntimeError(
                "Android root check failed: " + _owner_redact_text(repr(root_text))
            )
        log("Android root check passed: su -c id contains uid=0")

    _owner_register_serial(serial)
    summary = f"android_adb serial={_owner_redact_text(serial)} {last_props}"
    if root_text:
        summary += f" root={_owner_redact_text(root_text)}"
    owner_stdout(summary)
    return summary


def verify_post_flash_target(args: argparse.Namespace) -> str:
    if args.post_flash_target == "native-init":
        return verify_native_init(args)
    if args.post_flash_target == "android-adb":
        return verify_android_adb(args)
    raise RuntimeError(f"unknown post-flash target: {args.post_flash_target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flash a native init boot image from TWRP and verify it through the serial bridge."
    )
    parser.add_argument("boot_image", nargs="?", help="boot image to flash")
    parser.add_argument("--adb", default="adb", help="adb executable to use")
    parser.add_argument("--serial", help="ADB serial to target")
    parser.add_argument("--remote-image", default=DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--boot-block", default="/dev/block/by-name/boot")
    parser.add_argument("--bridge-host", default=DEFAULT_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--recovery-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-timeout", type=float, default=180.0)
    parser.add_argument("--expect-version", help="string expected in the native init version output")
    parser.add_argument("--expect-sha256", help="expected SHA256 of the local boot image")
    parser.add_argument(
        "--expect-readback-sha256",
        help="expected SHA256 of the flashed boot block prefix; defaults to --expect-sha256",
    )
    parser.add_argument(
        "--allow-unpinned-image",
        action="store_true",
        help="allow flashing without --expect-sha256; intended only for explicit local experiments",
    )
    parser.add_argument(
        "--verify-protocol",
        choices=("auto", "cmdv1", "raw", "selftest"),
        default="auto",
        help="post-boot verification method; auto tries cmdv1 first and falls back to raw version",
    )
    parser.add_argument(
        "--from-native",
        action="store_true",
        help="first ask the currently running native init shell to reboot to recovery",
    )
    parser.add_argument(
        "--require-empty-adb-baseline",
        action="store_true",
        help="before a from-native request require zero ADB endpoints, then accept only one recovery arrival",
    )
    parser.add_argument(
        "--require-stable-adb-baseline",
        action="store_true",
        help="bind all pre-existing non-recovery ADB endpoints unchanged and accept only one new recovery arrival",
    )
    parser.add_argument(
        "--reuse-bound-recovery-or-from-native",
        action="store_true",
        help=(
            "rollback-only minimal mode: use one already-present recovery "
            "endpoint only when its serial hash matches, otherwise bind the "
            "non-recovery baseline and send Native recovery once"
        ),
    )
    parser.add_argument(
        "--owner-receipt-mode",
        choices=(OWNER_RECEIPT_MODE,),
        help=(
            "fixed A90 owner mode: emit one strict effect-stage receipt; "
            "the owner, not prose or a generic return code, classifies return uncertainty"
        ),
    )
    parser.add_argument(
        "--owner-fixed-bridge-preflight",
        action="store_true",
        help="owner-only rollback mode: revalidate the exact Native bridge before recovery",
    )
    parser.add_argument(
        "--owner-expect-usb-inventory-sha256",
        help="owner-only rollback binding: exact raw lsusb inventory digest",
    )
    parser.add_argument(
        "--owner-expect-adb-inventory-sha256",
        help="owner-only rollback binding: exact raw adb devices -l digest",
    )
    parser.add_argument(
        "--owner-expect-adb-role",
        choices=(OWNER_ADB_ROLE_NATIVE, OWNER_ADB_ROLE_RECOVERY),
        help="owner-only rollback binding: exact A90 ADB endpoint role",
    )
    parser.add_argument(
        "--expect-recovery-serial-sha256",
        help="SHA256 of the sole A90 recovery ADB serial; raw serial stays outside tracked inputs",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="only verify the selected --post-flash-target without flashing",
    )
    parser.add_argument(
        "--post-flash-target",
        choices=("native-init", "android-adb"),
        default="native-init",
        help="post-reboot verification target; native-init keeps the historical serial bridge check",
    )
    parser.add_argument(
        "--android-timeout",
        type=float,
        default=300.0,
        help="timeout for Android ADB device and boot-complete checks when --post-flash-target=android-adb",
    )
    parser.add_argument(
        "--android-root-check",
        action="store_true",
        help="after Android boot-complete, require 'adb shell su -c id' to report uid=0",
    )
    parser.add_argument(
        "--expect-android-magic",
        action="store_true",
        help="require the local image to start with the Android boot image magic before flashing",
    )
    parser.add_argument(
        "--experimental-self-write",
        action="store_true",
        help="prepare the post-F3 self-write host path; live writes are fail-closed until F4 is authorized",
    )
    parser.add_argument(
        "--self-write-plan-only",
        action="store_true",
        help="with --experimental-self-write, print the self-write plan and perform no device action",
    )
    parser.add_argument(
        "--self-write-staging-dir",
        default=DEFAULT_SELF_WRITE_STAGING_DIR,
        help="approved device staging directory for the experimental self-write path",
    )
    parser.add_argument(
        "--self-write-mode",
        choices=("f2", "f3"),
        default="f2",
        help="self-write device command: f2 boot-candidate or f3 self-rollback (F4-live requires f3)",
    )
    parser.add_argument(
        "--self-write-live-authorized",
        action="store_true",
        help="explicit opt-in for the design section 12.1 F4-live validation; live self-write "
             "stays fail-closed without this flag and is restricted to the v2321 rollback image",
    )
    parser.add_argument(
        "--self-write-skip-stage",
        action="store_true",
        help="skip the tcpctl candidate staging step and rely on the device-side boot-flash-plan "
             "SHA/version/header re-verification of an already-staged candidate",
    )
    parser.add_argument(
        "--self-write-timeout",
        type=float,
        default=600.0,
        help="cmdv1 timeout for the long boot-flash-f2/f3 full-partition self-write command",
    )
    parser.add_argument(
        "--reboot-timeout",
        type=float,
        default=240.0,
        help="timeout to wait for native init to re-enumerate and report the expected version",
    )
    parser.add_argument(
        "--reboot-poll-interval-sec",
        type=float,
        default=0.5,
        help="poll granularity while waiting for native init to re-enumerate after reboot",
    )
    parser.add_argument(
        "--menu-settle-sec",
        type=float,
        default=3.0,
        help="settle delay after hide before dispatching a DANGEROUS self-write/reboot command; "
             "the auto-menu hide is async (returns 'hide requested') so <3s risks a redraw race "
             "that corrupts the next cmdv1 frame",
    )
    parser.add_argument(
        "--self-write-skip-source-plan",
        action="store_true",
        help="skip the redundant read-only boot-flash-plan pre-check; boot-flash-f3 re-verifies "
             "the candidate SHA/version/header itself before any write",
    )
    return parser.parse_args()


def main() -> int:
    global OWNER_EFFECT_STATE, OWNER_SERIAL_REDACTOR
    args = parse_args()
    OWNER_EFFECT_STATE = (
        OwnerEffectState() if args.owner_receipt_mode == OWNER_RECEIPT_MODE else None
    )
    OWNER_SERIAL_REDACTOR = None
    if OWNER_EFFECT_STATE is not None and args.verify_only:
        raise SystemExit("owner receipt mode requires one boot transfer, not --verify-only")
    args.expect_sha256 = normalize_sha256(args.expect_sha256, label="--expect-sha256")
    args.expect_readback_sha256 = normalize_sha256(
        args.expect_readback_sha256,
        label="--expect-readback-sha256",
    )
    args.expect_recovery_serial_sha256 = normalize_sha256(
        args.expect_recovery_serial_sha256,
        label="--expect-recovery-serial-sha256",
    )
    _owner_register_serial_hash(args.expect_recovery_serial_sha256)
    args.owner_expect_usb_inventory_sha256 = normalize_sha256(
        args.owner_expect_usb_inventory_sha256,
        label="--owner-expect-usb-inventory-sha256",
    )
    args.owner_expect_adb_inventory_sha256 = normalize_sha256(
        args.owner_expect_adb_inventory_sha256,
        label="--owner-expect-adb-inventory-sha256",
    )
    strict_modes = sum(
        bool(value)
        for value in (
            args.require_empty_adb_baseline,
            args.require_stable_adb_baseline,
            args.reuse_bound_recovery_or_from_native,
        )
    )
    if strict_modes > 1:
        raise SystemExit("ADB baseline modes are mutually exclusive")
    if (
        args.require_empty_adb_baseline or args.require_stable_adb_baseline
    ) and (not args.from_native or args.serial):
        raise SystemExit(
            "strict ADB baseline mode requires --from-native and forbids a caller-selected serial"
        )
    if args.require_stable_adb_baseline and not args.expect_recovery_serial_sha256:
        raise SystemExit(
            "--require-stable-adb-baseline requires --expect-recovery-serial-sha256"
        )
    if args.expect_recovery_serial_sha256 and not args.require_stable_adb_baseline:
        if not args.reuse_bound_recovery_or_from_native:
            raise SystemExit(
                "--expect-recovery-serial-sha256 requires one bound recovery mode"
            )
    if args.reuse_bound_recovery_or_from_native:
        if args.from_native or args.serial:
            raise SystemExit(
                "--reuse-bound-recovery-or-from-native selects its own fixed recovery path"
            )
        if not args.expect_recovery_serial_sha256:
            raise SystemExit(
                "--reuse-bound-recovery-or-from-native requires --expect-recovery-serial-sha256"
            )
    if args.owner_fixed_bridge_preflight and (
        args.owner_receipt_mode != OWNER_RECEIPT_MODE
        or not args.reuse_bound_recovery_or_from_native
    ):
        raise SystemExit(
            "--owner-fixed-bridge-preflight requires owner receipt rollback mode"
        )
    if args.owner_expect_usb_inventory_sha256 is not None and (
        args.owner_receipt_mode != OWNER_RECEIPT_MODE
        or not args.reuse_bound_recovery_or_from_native
    ):
        raise SystemExit(
            "--owner-expect-usb-inventory-sha256 requires owner receipt rollback mode"
        )
    if (
        (args.owner_expect_adb_inventory_sha256 is None)
        != (args.owner_expect_adb_role is None)
    ):
        raise SystemExit("owner ADB inventory digest and role must be supplied together")
    if args.owner_expect_adb_inventory_sha256 is not None and (
        args.owner_receipt_mode != OWNER_RECEIPT_MODE
        or not args.reuse_bound_recovery_or_from_native
        or args.adb != OWNER_ADB
        or args.owner_expect_usb_inventory_sha256 is None
    ):
        raise SystemExit(
            "--owner-expect-adb-inventory-sha256 requires the fixed owner rollback mode"
        )
    if args.owner_expect_usb_inventory_sha256 is not None and (
        args.owner_expect_adb_inventory_sha256 is None
        or args.owner_expect_adb_role is None
    ):
        raise SystemExit("owner USB inventory binding requires the ADB role binding")
    if args.owner_fixed_bridge_preflight and args.owner_expect_usb_inventory_sha256 is None:
        raise SystemExit(
            "--owner-fixed-bridge-preflight requires the owner USB inventory binding"
        )
    if args.owner_expect_usb_inventory_sha256 is not None and not args.owner_fixed_bridge_preflight:
        raise SystemExit(
            "owner USB inventory binding requires --owner-fixed-bridge-preflight"
        )
    if args.owner_fixed_bridge_preflight and args.owner_expect_adb_inventory_sha256 is None:
        raise SystemExit(
            "--owner-fixed-bridge-preflight requires the owner ADB inventory binding"
        )

    with phase_timer("total"):
        if args.verify_only:
            with phase_timer(f"verify_{args.post_flash_target.replace('-', '_')}"):
                verify_post_flash_target(args)
            if OWNER_EFFECT_STATE is not None:
                _emit_owner_receipt(OWNER_EFFECT_STATE)
            return 0

        if not args.boot_image:
            raise SystemExit("boot_image is required unless --verify-only is used")
        if not args.expect_sha256 and not args.allow_unpinned_image:
            raise SystemExit("refusing to flash without --expect-sha256")
        if args.allow_unpinned_image:
            log("unsafe override active: flashing without caller-pinned expected sha256")

        with phase_timer("inspect_local_image"):
            image_path, local_hash, image_size = inspect_local_image(args)

        if args.experimental_self_write:
            with phase_timer("experimental_self_write"):
                return run_experimental_self_write(args, image_path, local_hash, image_size)

        # In the explicit owner receipt mode, bind the complete raw USB
        # inventory before even opening ADB inventory or dispatching the
        # Native bridge.  The backend's digest is only a pre-effect join;
        # this second fixed capture closes the gap between backend inventory
        # and the first possible device command.  Legacy mode deliberately
        # does not run this producer or accept its argv.
        if args.owner_expect_usb_inventory_sha256 is not None:
            observed_usb_inventory_sha256 = _owner_usb_inventory_sha256(
                args.owner_expect_adb_role,
            )
            if observed_usb_inventory_sha256 != args.owner_expect_usb_inventory_sha256:
                raise RuntimeError("owner USB inventory digest mismatch")
            observed_adb_inventory_sha256 = _owner_adb_inventory_sha256(
                args.expect_recovery_serial_sha256,
                args.owner_expect_adb_role,
            )
            if observed_adb_inventory_sha256 != args.owner_expect_adb_inventory_sha256:
                raise RuntimeError("owner ADB inventory digest mismatch")

        adb_baseline: list[tuple[str, str]] | None = None
        bound_recovery: tuple[str, str] | None = None
        if args.reuse_bound_recovery_or_from_native:
            adb_baseline, bound_recovery = bind_present_recovery_or_native_baseline(
                args.adb,
                expected_serial_sha256=args.expect_recovery_serial_sha256,
            )
            if args.owner_expect_adb_inventory_sha256 is not None:
                baseline_adb_inventory_sha256 = _owner_adb_inventory_sha256(
                    args.expect_recovery_serial_sha256,
                    args.owner_expect_adb_role,
                )
                if baseline_adb_inventory_sha256 != args.owner_expect_adb_inventory_sha256:
                    raise RuntimeError("owner ADB inventory digest changed before effect")
        if args.from_native:
            if args.require_empty_adb_baseline:
                adb_baseline = adb_devices(args.adb, strict=True)
                if adb_baseline:
                    rendered = ", ".join(
                        f"{device_serial}:{state}"
                        for device_serial, state in adb_baseline
                    )
                    raise RuntimeError(f"ADB baseline is not empty: {rendered}")
            elif args.require_stable_adb_baseline:
                adb_baseline = adb_devices(args.adb, strict=True)
                if any(state == "recovery" for _serial, state in adb_baseline):
                    raise RuntimeError("ADB baseline already contains a recovery endpoint")
            if args.owner_expect_usb_inventory_sha256 is not None:
                _owner_pre_native_recovery_gate(args)
            with phase_timer("native_to_recovery"):
                reboot_native_to_recovery(args)
        elif args.reuse_bound_recovery_or_from_native and bound_recovery is None:
            if args.owner_expect_usb_inventory_sha256 is not None:
                _owner_pre_native_recovery_gate(args)
            with phase_timer("native_to_recovery"):
                reboot_native_to_recovery(args)

        with phase_timer("wait_recovery_adb"):
            if bound_recovery is not None:
                serial, state = bound_recovery
            elif (
                args.require_stable_adb_baseline
                or args.reuse_bound_recovery_or_from_native
            ):
                if adb_baseline is None:
                    raise RuntimeError("stable ADB baseline was not captured")
                serial, state = wait_for_new_recovery_adb(
                    args.adb,
                    adb_baseline,
                    args.recovery_timeout,
                    expected_serial_sha256=args.expect_recovery_serial_sha256,
                )
            else:
                serial, state = wait_for_adb_state(
                    args.adb,
                    args.serial,
                    {"recovery"},
                    args.recovery_timeout,
                    require_unique=args.require_empty_adb_baseline,
                    strict_inventory=args.require_empty_adb_baseline,
                )
        if state != "recovery":
            raise RuntimeError(f"expected recovery state, got {state}")

        if args.owner_expect_adb_inventory_sha256 is not None:
            # Native-to-recovery legitimately changes the raw USB bytes.  The
            # post-transition producer is therefore a fresh exact-role gate;
            # only an already-present Recovery branch must retain its
            # same-epoch USB digest before effect.
            post_usb_inventory_sha256 = _owner_usb_inventory_sha256(
                OWNER_ADB_ROLE_RECOVERY,
            )
            if bound_recovery is not None and (
                post_usb_inventory_sha256
                != args.owner_expect_usb_inventory_sha256
            ):
                raise RuntimeError("owner USB inventory changed before flash")
            if bound_recovery is None:
                log(
                    "owner post-transition USB inventory receipt="
                    f"{post_usb_inventory_sha256}"
                )
            post_role_digest = _owner_adb_inventory_sha256(
                args.expect_recovery_serial_sha256,
                OWNER_ADB_ROLE_RECOVERY,
            )
            if bound_recovery is not None and (
                post_role_digest != args.owner_expect_adb_inventory_sha256
            ):
                raise RuntimeError("owner ADB inventory changed before flash")

        with sealed_local_image_copy(image_path, local_hash, image_size) as sealed_image_path:
            with phase_timer("flash_boot_image"):
                flash_boot_image(args, serial, sealed_image_path, local_hash, image_size)
        with phase_timer("reboot_twrp_to_system"):
            reboot_twrp_to_system(args, serial, adb_baseline=adb_baseline)
        with phase_timer(f"verify_{args.post_flash_target.replace('-', '_')}"):
            verify_post_flash_target(args)
        if OWNER_EFFECT_STATE is not None:
            _emit_owner_receipt(OWNER_EFFECT_STATE)
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("interrupted")
        if OWNER_EFFECT_STATE is not None:
            _emit_owner_receipt(OWNER_EFFECT_STATE)
        raise SystemExit(130)
    except Exception as exc:
        log(f"error: {exc}")
        if OWNER_EFFECT_STATE is not None:
            _emit_owner_receipt(OWNER_EFFECT_STATE)
        raise SystemExit(1)
