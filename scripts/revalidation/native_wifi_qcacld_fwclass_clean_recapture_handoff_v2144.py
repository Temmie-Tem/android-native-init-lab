#!/usr/bin/env python3
"""V2144 clean recapture for the V2168 QCACLD firmware_class fasttransport route."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Any, Callable

import a90_ncm_transport as ncm_transport
from a90harness.evidence import EvidenceStore


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V2144"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2144-qcacld-fwclass-clean-recapture-handoff"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2144_QCACLD_FWCLASS_CLEAN_RECAPTURE_2026-06-05.md"
)
TEST_IMAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v2168-qcacld-fwclass-fasttransport-test-boot"
    / "boot_linux_v2168_qcacld_fwclass_fasttransport.img"
)
ROLLBACK_IMAGE = REPO_ROOT / "stage3" / "boot_linux_v725_fasttransport.img"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.245 (v2168-qcacld-fwclass-fasttransport)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2168.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2168.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2168-helper.result"
TEST_EVIDENCE_LABEL = os.environ.get("A90_WIFI_TEST_EVIDENCE_LABEL", "v2168")
SIBLING_FLAG_PATH = "/cache/native-init-sibling-fwssctl-v641"
DEFAULT_HELPER_WAIT_SEC = 260.0
POLL_INTERVAL_SEC = 5.0
FAST_EVIDENCE_DIR = "a90-v2144-evidence"
FAST_EVIDENCE_STEPS = {
    f"test-{TEST_EVIDENCE_LABEL}-log",
    f"test-{TEST_EVIDENCE_LABEL}-summary",
    f"test-{TEST_EVIDENCE_LABEL}-helper-result",
    "test-dmesg-full",
    "test-dmesg-wifi-filter",
    "test-icnss-stats",
    "test-icnss-debugfs-ls",
    "test-wlan0-state",
    "test-wlan0-ifconfig",
    "test-sys-wifi-mac-node",
    "test-supplicant-strace",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[object], *, timeout: float) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": [str(item) for item in command],
            "started": started.isoformat(),
            "ended": now_iso(),
            "timeout": False,
            "rc": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": [str(item) for item in command],
            "started": started.isoformat(),
            "ended": now_iso(),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def write_step(store: EvidenceStore,
               steps: list[dict[str, Any]],
               name: str,
               result: dict[str, Any]) -> None:
    stdout_file = f"{name}.stdout.txt"
    stderr_file = f"{name}.stderr.txt"
    stdout_path = store.write_log("host", stdout_file, str(result.get("stdout") or ""))
    stderr_path = store.write_log("host", stderr_file, str(result.get("stderr") or ""))
    stdout_file = str(stdout_path.relative_to(store.run_dir))
    stderr_file = str(stderr_path.relative_to(store.run_dir))
    steps.append({
        "name": name,
        "command": result["command"],
        "started": result["started"],
        "ended": result["ended"],
        "timeout": result["timeout"],
        "rc": result["rc"],
        "ok": result["ok"],
        "stdout_file": stdout_file,
        "stderr_file": stderr_file,
    })


def a90ctl_command(command: list[str], *, timeout: float | None = None) -> list[object]:
    base: list[object] = ["python3", "scripts/revalidation/a90ctl.py"]
    if timeout is not None:
        base.extend(["--timeout", str(timeout)])
    base.extend(command)
    return base


def a90ctl_step(store: EvidenceStore,
                steps: list[dict[str, Any]],
                name: str,
                command: list[str],
                *,
                timeout: float = 60.0,
                bridge_timeout: float | None = None) -> dict[str, Any]:
    result = run_command(a90ctl_command(command, timeout=bridge_timeout), timeout=timeout)
    if "[busy]" in str(result.get("stdout") or ""):
        hide = run_command(a90ctl_command(["hide"], timeout=20), timeout=30.0)
        write_step(store, steps, f"{name}-hide-on-busy", hide)
        result = run_command(a90ctl_command(command, timeout=bridge_timeout), timeout=timeout)
    write_step(store, steps, name, result)
    return result


def flash_command(image: Path, expect_version: str, *, from_native: bool) -> list[object]:
    command: list[object] = [
        "python3",
        "scripts/revalidation/native_init_flash.py",
        image,
        "--expect-version",
        expect_version,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "240",
        "--recovery-timeout",
        "240",
    ]
    if from_native:
        command.append("--from-native")
    return command


def read_evidence_text(store: EvidenceStore, name: str) -> str:
    path = store.run_dir / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("["):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def intish(value: object) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def set_sibling_precondition(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    script = (
        "set -e; "
        "if [ -e /cache/native-init-qrtr-servloc-boot-v724 ]; then "
        "echo qrtr_servloc_flag_present=1; exit 42; fi; "
        "umask 077; "
        f"printf run > {SIBLING_FLAG_PATH}; "
        "/cache/bin/busybox sync; "
        f"echo sibling_flag_path={SIBLING_FLAG_PATH}; "
        f"printf 'sibling_flag_value='; /cache/bin/busybox cat {SIBLING_FLAG_PATH}; echo"
    )
    return a90ctl_step(
        store,
        steps,
        "set-sibling-fwssctl-flag",
        ["run", "/cache/bin/busybox", "sh", "-c", script],
        timeout=60,
        bridge_timeout=45,
    )


def wait_for_helper_completion(store: EvidenceStore,
                               steps: list[dict[str, Any]],
                               *,
                               max_wait_sec: float) -> dict[str, Any]:
    deadline = time.monotonic() + max_wait_sec
    polls: list[str] = []
    result_exists = False
    summary_armed = True
    wlan0_present = False
    helper_exited = False
    helper_timed_out = False
    last_stdout = ""

    while time.monotonic() <= deadline:
        command = (
            "result_exists=0; summary_armed=0; wlan0_present=0; helper_exited=0; helper_timed_out=0; "
            f"test -s {TEST_HELPER_RESULT_PATH} && result_exists=1; "
            f"if /cache/bin/busybox grep -q '^state=armed' {TEST_SUMMARY_PATH} 2>/dev/null; "
            "then summary_armed=1; fi; "
            f"if /cache/bin/busybox grep -q '^helper_exited=1' {TEST_SUMMARY_PATH} 2>/dev/null; "
            "then helper_exited=1; fi; "
            f"if /cache/bin/busybox grep -q '^helper_timed_out=1' {TEST_SUMMARY_PATH} 2>/dev/null; "
            "then helper_timed_out=1; fi; "
            "test -e /sys/class/net/wlan0 && wlan0_present=1; "
            f"result_size=$(/cache/bin/busybox wc -c < {TEST_HELPER_RESULT_PATH} 2>/dev/null || echo 0); "
            f"summary_head=$(/cache/bin/busybox head -n 1 {TEST_SUMMARY_PATH} 2>/dev/null || true); "
            "echo result_exists=$result_exists summary_armed=$summary_armed "
            "wlan0_present=$wlan0_present helper_exited=$helper_exited "
            "helper_timed_out=$helper_timed_out result_size=$result_size summary_head=$summary_head"
        )
        result = run_command(
            a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", command], timeout=30),
            timeout=45,
        )
        if "[busy]" in str(result.get("stdout") or ""):
            run_command(a90ctl_command(["hide"], timeout=20), timeout=30)
            result = run_command(
                a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", command], timeout=30),
                timeout=45,
            )
        last_stdout = str(result.get("stdout") or "")
        polls.append(f"[{now_iso()}] rc={result.get('rc')} timeout={result.get('timeout')} {last_stdout.strip()}")
        result_exists = "result_exists=1" in last_stdout
        summary_armed = "summary_armed=1" in last_stdout
        wlan0_present = "wlan0_present=1" in last_stdout
        helper_exited = "helper_exited=1" in last_stdout
        helper_timed_out = "helper_timed_out=1" in last_stdout
        if (result_exists and not summary_armed) or (not summary_armed and (helper_exited or helper_timed_out)):
            break
        time.sleep(POLL_INTERVAL_SEC)

    helper_done_without_result = (not summary_armed) and (helper_exited or helper_timed_out)
    completed = (result_exists and not summary_armed) or helper_done_without_result
    stdout_path = store.write_log("host", "test-helper-wait-polls.txt", "\n".join(polls) + "\n")
    stdout_file = str(stdout_path.relative_to(store.run_dir))
    steps.append({
        "name": "test-helper-wait-polls",
        "command": ["poll", TEST_HELPER_RESULT_PATH, TEST_SUMMARY_PATH],
        "started": polls[0].split("]")[0].lstrip("[") if polls else now_iso(),
        "ended": now_iso(),
        "timeout": not completed,
        "rc": 0 if completed else 1,
        "ok": completed,
        "stdout_file": stdout_file,
        "stderr_file": "",
    })
    return {
        "result_exists": result_exists,
        "summary_armed": summary_armed,
        "wlan0_present": wlan0_present,
        "helper_exited": helper_exited,
        "helper_timed_out": helper_timed_out,
        "helper_done_without_result": helper_done_without_result,
        "last_stdout": last_stdout,
        "poll_count": len(polls),
        "completed": completed,
    }


def collect_test_evidence(store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    collect_test_evidence_fast(store, steps)
    commands: dict[str, list[str]] = {
        "test-version": ["version"],
        "test-status": ["status"],
        "test-selftest": ["selftest"],
        "test-bootstatus": ["bootstatus"],
        f"test-{TEST_EVIDENCE_LABEL}-log": ["run", "/cache/bin/busybox", "cat", TEST_LOG_PATH],
        f"test-{TEST_EVIDENCE_LABEL}-summary": ["run", "/cache/bin/busybox", "cat", TEST_SUMMARY_PATH],
        f"test-{TEST_EVIDENCE_LABEL}-helper-result": ["run", "/cache/bin/busybox", "cat", TEST_HELPER_RESULT_PATH],
        "test-dmesg-full": ["run", "/cache/bin/busybox", "dmesg"],
        "test-dmesg-wifi-filter": [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                "dmesg | grep -Ei "
                "'A90v2168|A90v2137|wlan0|swlan0|set_features|Assigning MAC|icnss|FW ready|FW_READY|"
                "wlfw|WLFW|BDF|bdwlan|regdb|firmware_class|request_firmware|qca|HDD|wlanmdsp' "
                "| tail -800"
            ),
        ],
        "test-icnss-stats": ["run", "/cache/bin/busybox", "cat", "/sys/kernel/debug/icnss/stats"],
        "test-icnss-debugfs-ls": ["run", "/cache/bin/busybox", "ls", "-la", "/sys/kernel/debug/icnss"],
        "test-wlan0-state": [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                "if [ -e /sys/class/net/wlan0 ]; then echo wlan0=present; "
                "for f in address operstate carrier flags mtu type uevent; do "
                "printf '%s=' \"$f\"; /cache/bin/busybox cat /sys/class/net/wlan0/$f 2>/dev/null || echo unreadable; "
                "done; "
                "else echo wlan0=absent; fi"
            ),
        ],
        "test-wlan0-ifconfig": [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            "(/cache/bin/toybox ip addr show wlan0 2>/dev/null || /cache/bin/busybox ifconfig wlan0 2>/dev/null || true)",
        ],
        "test-sys-wifi-mac-node": [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            "ls -la /sys/wifi /sys/wifi/mac_addr 2>/dev/null; /cache/bin/busybox stat /sys/wifi/mac_addr 2>/dev/null || true",
        ],
    }
    for name, command in commands.items():
        if (store.run_dir / f"{name}.stdout.txt").exists():
            continue
        a90ctl_step(store, steps, name, command, timeout=120, bridge_timeout=90)


def extract_fast_evidence_archive(store: EvidenceStore,
                                  steps: list[dict[str, Any]],
                                  archive_path: Path) -> dict[str, Any]:
    extracted: list[str] = []
    rejected: list[str] = []
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = Path(member.name).name
                if not name.endswith(".stdout.txt"):
                    rejected.append(member.name)
                    continue
                step_name = name.removesuffix(".stdout.txt")
                if step_name not in FAST_EVIDENCE_STEPS:
                    rejected.append(member.name)
                    continue
                file_obj = tar.extractfile(member)
                if file_obj is None:
                    rejected.append(member.name)
                    continue
                text = file_obj.read().decode("utf-8", errors="replace")
                write_step(
                    store,
                    steps,
                    step_name,
                    {
                        "command": ["fast-upload", "extract", step_name],
                        "started": now_iso(),
                        "ended": now_iso(),
                        "timeout": False,
                        "rc": 0,
                        "ok": True,
                        "stdout": text,
                        "stderr": "",
                    },
                )
                extracted.append(step_name)
    except tarfile.TarError as exc:
        return {"ok": False, "reason": f"tar-extract-failed:{exc}", "extracted": extracted, "rejected": rejected}
    return {
        "ok": bool(extracted),
        "reason": "ok" if extracted else "no-fast-evidence-extracted",
        "extracted": sorted(extracted),
        "rejected": sorted(rejected),
    }


def collect_test_evidence_fast(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    transfer = ncm_transport.FastTransferSession(store, steps, run_step=a90ctl_step)
    started = time.monotonic()
    if not transfer.ensure_device_reachable():
        result = {
            "ok": False,
            "reason": transfer.reason,
            "method": "ncm-targzip-nc",
            "elapsed_sec": 0.0,
            "extracted": [],
        }
        ncm_transport.write_compact_step(
            store,
            steps,
            "test-fast-evidence-upload-skipped",
            command=["fast-upload", "v2144-evidence"],
            ok=False,
            rc=1,
            stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        )
        return result

    collector_path = store.path("test-fast-evidence-collector.sh")
    collector_script = "\n".join([
        "#!/cache/bin/busybox sh",
        "set -u",
        "remote_host=\"$1\"",
        "remote_port=\"$2\"",
        "bb=/cache/bin/busybox",
        "toy=/cache/bin/toybox",
        "tmp=/cache/a90-fastupload-v2144-$$",
        f"payload=$tmp/{FAST_EVIDENCE_DIR}",
        "if [ ! -x \"$bb\" ]; then echo fast_evidence.reason=busybox-missing; exit 42; fi",
        "$bb rm -rf \"$tmp\"",
        "$bb mkdir -p \"$payload\"",
        "copy_if() { src=\"$1\"; dst=\"$2\"; [ -f \"$src\" ] && $bb cp \"$src\" \"$payload/$dst\" || true; }",
        f"copy_if {shlex.quote(TEST_LOG_PATH)} test-{TEST_EVIDENCE_LABEL}-log.stdout.txt",
        f"copy_if {shlex.quote(TEST_SUMMARY_PATH)} test-{TEST_EVIDENCE_LABEL}-summary.stdout.txt",
        f"copy_if {shlex.quote(TEST_HELPER_RESULT_PATH)} test-{TEST_EVIDENCE_LABEL}-helper-result.stdout.txt",
        "$bb dmesg > \"$payload/test-dmesg-full.stdout.txt\" 2>&1 || true",
        (
            "$bb dmesg | $bb grep -Ei "
            "'A90v2168|A90v2137|wlan0|swlan0|set_features|Assigning MAC|icnss|FW ready|FW_READY|"
            "wlfw|WLFW|BDF|bdwlan|regdb|firmware_class|request_firmware|qca|HDD|wlanmdsp' "
            "> \"$payload/test-dmesg-wifi-filter.stdout.txt\" 2>&1 || true"
        ),
        "$bb cat /sys/kernel/debug/icnss/stats > \"$payload/test-icnss-stats.stdout.txt\" 2>&1 || true",
        "$bb ls -la /sys/kernel/debug/icnss > \"$payload/test-icnss-debugfs-ls.stdout.txt\" 2>&1 || true",
        (
            "if [ -e /sys/class/net/wlan0 ]; then echo wlan0=present; "
            "for f in address operstate carrier flags mtu type uevent; do "
            "printf '%s=' \"$f\"; $bb cat /sys/class/net/wlan0/$f 2>/dev/null || echo unreadable; "
            "done; else echo wlan0=absent; fi"
        ) + " > \"$payload/test-wlan0-state.stdout.txt\" 2>&1 || true",
        (
            "if [ -x \"$toy\" ]; then $toy ip addr show wlan0; "
            "else $bb ifconfig wlan0; fi"
        ) + " > \"$payload/test-wlan0-ifconfig.stdout.txt\" 2>&1 || true",
        "$bb ls -la /sys/wifi /sys/wifi/mac_addr > \"$payload/test-sys-wifi-mac-node.stdout.txt\" 2>&1 || true",
        "$bb stat /sys/wifi/mac_addr >> \"$payload/test-sys-wifi-mac-node.stdout.txt\" 2>&1 || true",
        (
            "{ i=0; for src in /cache/a90-wifi/a90_supplicant_strace*; do "
            "[ -f \"$src\" ] || continue; "
            "echo \"===== $src =====\"; $bb cat \"$src\"; i=$((i+1)); "
            "done; echo test_supplicant_strace_file_count=$i; } "
            "> \"$payload/test-supplicant-strace.stdout.txt\" 2>&1 || true"
        ),
        f"(cd \"$tmp\" && $bb tar -cf - {FAST_EVIDENCE_DIR}) | $bb gzip -c | $bb timeout 5 $bb nc -w 1 \"$remote_host\" \"$remote_port\"",
        "rc=$?",
        "$bb rm -rf \"$tmp\"",
        "echo fast_evidence.nc_rc=$rc",
        "exit \"$rc\"",
    ]) + "\n"
    collector_path.write_text(collector_script, encoding="utf-8")
    collector_sha = sha256(collector_path)
    collector_transfer = transfer.transfer_file(
        label="test-fast-evidence-collector",
        local_path=collector_path,
        remote_path="/cache/a90-fastupload-v2144.sh",
        expected_sha256=collector_sha,
        mode="700",
    )
    if not collector_transfer.get("ok"):
        result = {
            "ok": False,
            "reason": "collector-script-transfer-failed",
            "method": "ncm-targzip-nc",
            "elapsed_sec": round(time.monotonic() - started, 3),
            "collector_transfer": collector_transfer,
            "extracted": [],
        }
        ncm_transport.write_compact_step(
            store,
            steps,
            "test-fast-evidence-upload-result",
            command=["fast-upload-result", "v2144-evidence"],
            ok=False,
            rc=1,
            stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        )
        return result

    archive_path = store.path("test-fast-evidence.tgz")
    with ncm_transport.TcpArchiveReceiver(archive_path, timeout=90.0) as receiver:
        remote_host = transfer.host_link_local + "%" + transfer.device_ifname
        step = a90ctl_step(
            store,
            steps,
            "test-fast-evidence-device-stream",
            ["run", "/cache/bin/busybox", "sh", "/cache/a90-fastupload-v2144.sh", remote_host, str(receiver.port)],
            timeout=120,
            bridge_timeout=100,
        )

    output = "\n".join([str(step.get("stdout") or ""), str(step.get("stderr") or "")])
    fields = parse_key_values(output)
    validation = ncm_transport.validate_uploaded_archive(archive_path)
    extraction = extract_fast_evidence_archive(store, steps, archive_path) if validation.get("ok") else {
        "ok": False,
        "reason": str(validation.get("reason") or "validation-failed"),
        "extracted": [],
        "rejected": [],
    }
    device_nc_rc = fields.get("fast_evidence.nc_rc", "")
    device_stream_ok = bool(step.get("ok")) and device_nc_rc in {"", "0"}
    ok = (
        device_stream_ok
        and bool(receiver.result.get("ok"))
        and bool(validation.get("ok"))
        and bool(extraction.get("ok"))
    )
    result = {
        "ok": ok,
        "reason": "ok" if ok else "upload-validation-or-extract-failed",
        "method": "ncm-targzip-nc",
        "elapsed_sec": round(time.monotonic() - started, 3),
        "device_nc_rc": device_nc_rc,
        "archive_path": rel(archive_path) if archive_path.exists() else "",
        "receiver": receiver.result,
        "validation": {key: value for key, value in validation.items() if key != "connect_result_text"},
        "extraction": extraction,
        "host_ifname": transfer.ifname,
        "host_link_local": transfer.host_link_local,
    }
    ncm_transport.write_compact_step(
        store,
        steps,
        "test-fast-evidence-upload-result",
        command=["fast-upload-result", "v2144-evidence"],
        ok=ok,
        rc=0 if ok else 1,
        stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
    )
    return result


def rollback(store: EvidenceStore,
             steps: list[dict[str, Any]],
             *,
             rollback_image: Path = ROLLBACK_IMAGE,
             rollback_expect_version: str = ROLLBACK_EXPECT_VERSION) -> dict[str, Any]:
    first = run_command(flash_command(rollback_image, rollback_expect_version, from_native=True), timeout=720)
    write_step(store, steps, "rollback-from-native", first)
    if first["ok"]:
        ok = True
        attempt = "from-native"
    else:
        second = run_command(flash_command(rollback_image, rollback_expect_version, from_native=False), timeout=720)
        write_step(store, steps, "rollback-from-recovery", second)
        ok = bool(second["ok"])
        attempt = "from-recovery"
    a90ctl_step(store, steps, "rollback-status", ["status"], timeout=90, bridge_timeout=60)
    a90ctl_step(store, steps, "rollback-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    return {"ok": ok, "attempt": attempt}


def extract_state_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("State:"):
            return line
    match = re.search(r"State: [^\n]+", text)
    return match.group(0) if match else ""


def extract_wlan0_address(text: str) -> str:
    for raw_line in text.splitlines():
        if raw_line.startswith("address="):
            return raw_line.split("=", 1)[1].strip()
    return ""


def classify(store: EvidenceStore,
             test_flash: dict[str, Any],
             helper_wait: dict[str, Any],
             rollback_result: dict[str, Any]) -> dict[str, Any]:
    dmesg = read_evidence_text(store, "test-dmesg-full.stdout.txt")
    dmesg_filter = read_evidence_text(store, "test-dmesg-wifi-filter.stdout.txt")
    helper = read_evidence_text(store, "test-v2168-helper-result.stdout.txt")
    summary = read_evidence_text(store, "test-v2168-summary.stdout.txt")
    icnss_stats = read_evidence_text(store, "test-icnss-stats.stdout.txt")
    wlan0_state = read_evidence_text(store, "test-wlan0-state.stdout.txt")
    helper_fields = parse_key_values(helper)
    summary_fields = parse_key_values(summary)

    helper_has_result = "A90_EXECNS_RESULT_FILE_BEGIN" in helper
    helper_missing = (
        not bool(helper.strip())
        or not helper_has_result
        or ((("No such file or directory" in helper) or ("can't open" in helper)) and not helper_has_result)
    )
    summary_armed = "state=armed" in summary or bool(helper_wait.get("summary_armed"))
    wlan0_present = "wlan0=present" in wlan0_state or bool(helper_wait.get("wlan0_present"))
    fw_ready_dmesg = bool(re.search(r"FW[ _-]?READY|FW ready", dmesg_filter, re.IGNORECASE))
    assigning_mac = "Assigning MAC from Macloader" in dmesg
    set_features_fail = "set_features() failed" in dmesg
    swlan0_fail = "failed to generating swlan0 mac addr" in dmesg
    state_line = (
        extract_state_line(icnss_stats)
        or helper_fields.get("wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.state.line", "")
        or helper_fields.get("wlan_pd_icnss_ipc_snapshot.after_boot_wlan_trigger.icnss_stats.state.line", "")
    )
    icnss_fw_ready_processed = max(
        intish(helper_fields.get("wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.fw_ready.processed")),
        intish(helper_fields.get("wlan_pd_icnss_ipc_snapshot.after_boot_wlan_trigger.icnss_stats.event.fw_ready.processed")),
    )
    icnss_register_driver_processed = max(
        intish(helper_fields.get("wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.register_driver.processed")),
        intish(helper_fields.get("wlan_pd_icnss_ipc_snapshot.after_boot_wlan_trigger.icnss_stats.event.register_driver.processed")),
    )
    helper_fw_ready = icnss_fw_ready_processed > 0 or "FW READY" in state_line
    helper_intact = not helper_missing and not summary_armed

    if not test_flash.get("ok"):
        label = "clean-fwclass-test-flash-failed"
        passed = False
        reason = "test boot flash/verify did not complete"
    elif not rollback_result.get("ok"):
        label = "clean-fwclass-rollback-failed"
        passed = False
        reason = "test evidence was collected but rollback did not verify"
    elif wlan0_present and helper_intact and helper_fw_ready:
        label = "clean-fwclass-wlan0-helper-intact-fwready-consistent"
        passed = True
        reason = "late recapture preserved wlan0 and helper/ICNSS state shows FW READY"
    elif wlan0_present and helper_intact:
        label = "clean-fwclass-wlan0-helper-intact-fwready-dmesg-only"
        passed = True
        reason = "late recapture preserved wlan0 with intact helper, but FW_READY is only visible outside parsed helper counters"
    elif wlan0_present:
        label = "clean-fwclass-wlan0-helper-missing"
        passed = False
        reason = "wlan0 persisted, but helper result or summary was still incomplete"
    else:
        label = "clean-fwclass-no-wlan0"
        passed = False
        reason = "late recapture did not preserve wlan0"

    return {
        "label": label,
        "decision": f"v2144-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "helper_intact": helper_intact,
        "helper_missing": helper_missing,
        "summary_armed": summary_armed,
        "summary_state": summary_fields.get("state", ""),
        "helper_wait": helper_wait,
        "wlan0_present": wlan0_present,
        "wlan0_address": extract_wlan0_address(wlan0_state),
        "fw_ready_dmesg": fw_ready_dmesg,
        "assigning_mac": assigning_mac,
        "set_features_fail": set_features_fail,
        "swlan0_fail": swlan0_fail,
        "icnss_state_line": state_line,
        "icnss_fw_ready_processed": icnss_fw_ready_processed,
        "icnss_register_driver_processed": icnss_register_driver_processed,
        "helper_fw_ready": helper_fw_ready,
        "requested_wlanmdsp": "wlanmdsp.mbn" in dmesg,
    }


def render_report(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
    ]
    return "\n".join([
        "# Native Init V2144 QCACLD Firmware Class Clean Recapture",
        "",
        "## Summary",
        "",
        "- Cycle: `V2144`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Gate Results",
        "",
        f"- `wlan0_present`: `{c['wlan0_present']}` address `{c['wlan0_address']}`",
        f"- `helper_intact`: `{c['helper_intact']}` missing `{c['helper_missing']}` summary_armed `{c['summary_armed']}`",
        f"- `icnss_state_line`: `{c['icnss_state_line']}`",
        f"- `icnss_fw_ready_processed`: `{c['icnss_fw_ready_processed']}`",
        f"- `icnss_register_driver_processed`: `{c['icnss_register_driver_processed']}`",
        f"- `fw_ready_dmesg`: `{c['fw_ready_dmesg']}`",
        f"- `assigning_mac`: `{c['assigning_mac']}`",
        f"- `set_features_fail`: `{c['set_features_fail']}`",
        f"- `swlan0_fail`: `{c['swlan0_fail']}`",
        f"- `requested_wlanmdsp`: `{c['requested_wlanmdsp']}`",
        "",
        "## Reframe",
        "",
        "- This recaptures the V2168 fasttransport route with a late collection window so `helper.result` and helper-embedded `/sys/kernel/debug/icnss/stats` counters are available.",
        "- If `wlan0` and FW_READY persist while `requested_wlanmdsp` remains false, this firmware_class path is independent of the modem tftp `wlanmdsp.mbn` branch for native bring-up.",
        "- Connectivity, scans, credentials, DHCP/routes, and external ping remain blocked until MAC assignment and degraded-interface errors are resolved.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2168 rollbackable test boot, bounded firmware_class fallback sysfs writes from the V2137/V2168 contract, and rollback to `stage3/boot_linux_v725_fasttransport.img` with selftest verification.",
        "",
    ])


def run_handoff(*,
                cycle: str = CYCLE,
                out_dir: Path = OUT_DIR,
                report_path: Path = REPORT_PATH,
                test_image: Path = TEST_IMAGE,
                test_expect_version: str = TEST_EXPECT_VERSION,
                rollback_image: Path = ROLLBACK_IMAGE,
                rollback_expect_version: str = ROLLBACK_EXPECT_VERSION,
                helper_wait_sec: float = DEFAULT_HELPER_WAIT_SEC,
                post_flash_hook: Callable[[EvidenceStore, list[dict[str, Any]]], dict[str, Any]] | None = None) -> dict[str, Any]:
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    preflight = {
        "cycle": cycle,
        "test_image": rel(test_image),
        "test_image_exists": test_image.exists(),
        "test_image_sha256": sha256(test_image) if test_image.exists() else "",
        "rollback_image": rel(rollback_image),
        "rollback_image_exists": rollback_image.exists(),
        "rollback_image_sha256": sha256(rollback_image) if rollback_image.exists() else "",
    }
    store.write_json("preflight.json", preflight)
    if not preflight["test_image_exists"] or not preflight["rollback_image_exists"]:
        classification = {
            "label": "clean-fwclass-preflight-blocked",
            "decision": f"{cycle.lower()}-clean-fwclass-preflight-blocked",
            "pass": False,
            "reason": "test or rollback image missing",
        }
        manifest = {
            **classification,
            "cycle": cycle,
            "classification": classification,
            "preflight": preflight,
            "steps": steps,
            "out_dir": rel(out_dir),
        }
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_report(manifest))
        report_path.write_text(render_report(manifest), encoding="utf-8")
        return manifest

    a90ctl_step(store, steps, "pre-status", ["status"], timeout=90, bridge_timeout=60)
    a90ctl_step(store, steps, "pre-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    set_sibling_precondition(store, steps)
    test_flash = run_command(flash_command(test_image, test_expect_version, from_native=True), timeout=720)
    write_step(store, steps, "test-flash-from-native", test_flash)

    helper_wait: dict[str, Any] = {
        "result_exists": False,
        "summary_armed": True,
        "wlan0_present": False,
        "completed": False,
        "poll_count": 0,
    }
    hook_result: dict[str, Any] | None = None
    if test_flash["ok"]:
        if post_flash_hook is not None:
            hook_result = post_flash_hook(store, steps)
            store.write_json("post-flash-hook.json", hook_result)
        helper_wait = wait_for_helper_completion(store, steps, max_wait_sec=helper_wait_sec)
        collect_test_evidence(store, steps)

    rollback_result = rollback(
        store,
        steps,
        rollback_image=rollback_image,
        rollback_expect_version=rollback_expect_version,
    )
    classification = classify(store, test_flash, helper_wait, rollback_result)
    manifest = {
        "cycle": cycle,
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "preflight": preflight,
        "test_flash_ok": bool(test_flash["ok"]),
        "rollback": rollback_result,
        "post_flash_hook": hook_result,
        "classification": classification,
        "steps": steps,
        "out_dir": rel(out_dir),
    }
    store.write_json("manifest.json", manifest)
    summary = render_report(manifest)
    store.write_text("summary.md", summary)
    report_path.write_text(summary, encoding="utf-8")
    return manifest


def main() -> int:
    manifest = run_handoff()
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": manifest["out_dir"],
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
