#!/usr/bin/env python3
"""V1796 one-run WLAN-PD PM-service count/sample observer handoff."""

from __future__ import annotations

import hashlib
import io
import os
import re
import tarfile
import time
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_output_visibility_handoff_v1688 as runner


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1796"
V1795_OUT = REPO_ROOT / "tmp" / "wifi" / "v1795-pm-service-count-sample-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1795/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1796-pm-service-count-sample-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1796_PM_SERVICE_COUNT_SAMPLE_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.148 (v1795-pm-service-count-sample-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1795.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1795.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1795-helper.result"
DMESG_PATTERN = (
    "A90v1795|wlan_pd_service_object_visible_trigger|wlan_pd_service_object_visible|"
    "wlan_pd_cnss_nonlog_control_flow|pm_server_uprobe|pm_server_register|"
    "pm-service-init|pm_service_init|pm_service_add_peripheral|"
    "first_count=|second_count=|record=|devnode=|pm-server-register|pm-service|"
    "PeripheralManager|peripheral|vndservicemanager|vndbinder|service-manager|"
    "servicemanager|hwservicemanager|pm_proxy_helper|wlan_pd|wlanmdsp|tftp|"
    "rmt_storage|pd-mapper|qrtr|service 69|wlfw|wlfw_start|"
    "wlfw_service_request|icnss|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|Brought out of reset|modem: loading"
)

NAME_RE = re.compile(r'\bname="?([^"\s]+)"?')
DEVNODE_RE = re.compile(r'\bdevnode="?([^"\s]+)"?')
FIELD_RE_TEMPLATE = r'\b{key}="?([^"\s]+)"?'
SENSITIVE_VERSION_CREATOR_RE = re.compile(r"(made by )[^\s\r\n]+")


def configure_runner() -> None:
    runner.CYCLE = CYCLE
    runner.V1687_OUT = V1795_OUT
    runner.DEFAULT_SOURCE_MANIFEST = V1795_OUT / "manifest.json"
    runner.DEFAULT_TEST_IMAGE = (
        V1795_OUT / "boot_linux_v1795_pm_service_count_sample_observer.img"
    )
    runner.LOCAL_PROPERTY_ROOT = (
        V1795_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    )
    runner.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    runner.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    runner.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    runner.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    runner.TEST_LOG_PATH = TEST_LOG_PATH
    runner.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    runner.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    runner.DMESG_PATTERN = DMESG_PATTERN


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def field_bool(fields: dict[str, str], key: str) -> bool:
    return fields.get(key) == "1"


def parse_token(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text or "")
    return reliable_observed_string(match.group(1)) if match else ""


def parse_field(key: str, text: str) -> str:
    pattern = re.compile(FIELD_RE_TEMPLATE.format(key=re.escape(key)))
    return parse_token(pattern, text)


def reliable_observed_string(value: str) -> str:
    if not value or value == "none" or "\ufffd" in value:
        return ""
    if "`" in value:
        return ""
    if any(ord(ch) < 32 for ch in value):
        return ""
    return value


def report_value(value: object) -> str:
    text = str(value or "")
    if reliable_observed_string(text):
        return text
    return "unreliable-entry-fetcharg"


def uu_char(value: int) -> str:
    value &= 0x3f
    return chr(value + 0x20) if value else "`"


def uuencode_bytes(data: bytes, *, name: str, mode: int = 0o644) -> str:
    lines = [f"begin {mode:o} {name}\n"]
    for offset in range(0, len(data), 45):
        chunk = data[offset:offset + 45]
        padded = chunk + b"\0" * ((3 - len(chunk) % 3) % 3)
        encoded: list[str] = []
        for index in range(0, len(padded), 3):
            first, second, third = padded[index], padded[index + 1], padded[index + 2]
            encoded.extend(
                uu_char(value)
                for value in (
                    first >> 2,
                    ((first << 4) & 0x30) | (second >> 4),
                    ((second << 2) & 0x3c) | (third >> 6),
                    third & 0x3f,
                )
            )
        lines.append(uu_char(len(chunk)) + "".join(encoded) + "\n")
    lines.append("`\nend\n")
    return "".join(lines)


def build_property_tar_gz() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in runner.local_property_files():
            info = tar.gettarinfo(path, arcname=path.name)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            with path.open("rb") as handle:
                tar.addfile(info, handle)
    return buffer.getvalue()


def run_serial_step(store: Any,
                    steps: list[dict[str, Any]],
                    name: str,
                    argv: list[str],
                    *,
                    timeout: float = 45.0,
                    allow_error: bool = False) -> dict[str, Any]:
    input_mode = os.environ.get("A90CTL_INPUT_MODE", "normal")
    char_delay = float(os.environ.get("A90CTL_INPUT_CHAR_DELAY_SEC", "0.02"))
    host_timeout = timeout
    if input_mode == "slow":
        wire_chars = 20 + sum((len(arg.encode("utf-8")) * 2) + 8 for arg in argv)
        host_timeout += wire_chars * char_delay + 15.0
    result = runner.fwbase.base.run_a90ctl_step(
        store,
        steps,
        name,
        runner.fwbase.base.a90ctl_command_timed(
            argv,
            timeout=timeout,
            retry_unsafe=input_mode in {"double", "slow"},
        ),
        host_timeout,
    )
    if not result["ok"] and not allow_error:
        raise RuntimeError(
            f"serial property deploy step failed: {name} rc={result['rc']} "
            f"timeout={result['timeout']}"
        )
    return result


def deploy_property_root_serial(args: Any,
                                store: Any,
                                steps: list[dict[str, Any]]) -> dict[str, Any]:
    stamp = str(int(time.time()))
    tar_name = f"v1796-props-{stamp}.tgz"
    staging_dir = str(Path(REMOTE_PROPERTY_ROOT).parent)
    staging = f"{staging_dir}/.{tar_name}.uu"
    tmp_tgz = f"{staging_dir}/.{tar_name}"
    tar_bytes = build_property_tar_gz()
    tar_sha = hashlib.sha256(tar_bytes).hexdigest()
    encoded = uuencode_bytes(tar_bytes, name=tar_name)
    chunk_size = 500 if os.environ.get("A90CTL_INPUT_MODE") in {"double", "slow"} else 1000
    remote_files = [REMOTE_PROPERTY_ROOT + "/" + path.name for path in runner.local_property_files()]
    toolbox = getattr(args, "toybox", "") or "/cache/bin/busybox"
    if toolbox == "/cache/bin/toybox":
        toolbox = "/cache/bin/busybox"

    run_serial_step(store, steps, "property-serial-hide", ["hide"], timeout=8.0, allow_error=True)
    run_serial_step(store, steps, "property-serial-rm-root", ["run", toolbox, "rm", "-rf", REMOTE_PROPERTY_ROOT])
    run_serial_step(store, steps, "property-serial-mkdir-root", ["run", toolbox, "mkdir", "-p", REMOTE_PROPERTY_ROOT])
    run_serial_step(
        store,
        steps,
        "property-serial-chmod-parent",
        [
            "run",
            toolbox,
            "chmod",
            "755",
            str(Path(REMOTE_PROPERTY_ROOT).parent.parent),
            str(Path(REMOTE_PROPERTY_ROOT).parent),
            REMOTE_PROPERTY_ROOT,
        ],
    )
    run_serial_step(store, steps, "property-serial-rm-staging", ["run", toolbox, "rm", "-f", staging, tmp_tgz], allow_error=True)
    for offset in range(0, len(encoded), chunk_size):
        chunk_index = offset // chunk_size
        chunk = encoded[offset:offset + chunk_size]
        run_serial_step(
            store,
            steps,
            f"property-serial-append-{chunk_index:03d}",
            ["appendfile", staging, chunk],
            timeout=45.0,
        )
    run_serial_step(store, steps, "property-serial-uudecode", ["run", toolbox, "uudecode", "-o", tmp_tgz, staging], timeout=60.0)
    sha_result = run_serial_step(store, steps, "property-serial-tar-sha256", ["run", toolbox, "sha256sum", tmp_tgz])
    if tar_sha not in str(sha_result.get("stdout") or ""):
        raise RuntimeError("serial property tar sha256 mismatch")
    run_serial_step(
        store,
        steps,
        "property-serial-extract",
        ["run", "/cache/bin/busybox", "tar", "-xzf", tmp_tgz, "-C", REMOTE_PROPERTY_ROOT],
        timeout=90.0,
    )
    run_serial_step(store, steps, "property-serial-chmod-files", ["run", toolbox, "chmod", "444", *remote_files], timeout=45.0)
    property_info_sha = runner.sha256_file(runner.LOCAL_PROPERTY_ROOT / "property_info")
    vendor_default_sha = runner.sha256_file(
        runner.LOCAL_PROPERTY_ROOT / "u:object_r:vendor_default_prop:s0"
    )
    property_info = run_serial_step(
        store,
        steps,
        "property-serial-property-info-sha256",
        ["run", toolbox, "sha256sum", REMOTE_PROPERTY_ROOT + "/property_info"],
    )
    vendor_default = run_serial_step(
        store,
        steps,
        "property-serial-vendor-default-sha256",
        ["run", toolbox, "sha256sum", REMOTE_PROPERTY_ROOT + "/u:object_r:vendor_default_prop:s0"],
    )
    run_serial_step(store, steps, "property-serial-cleanup", ["run", toolbox, "rm", "-f", staging, tmp_tgz], allow_error=True)
    return {
        "remote_property_root": REMOTE_PROPERTY_ROOT,
        "file_count": len(remote_files),
        "bytes": sum(path.stat().st_size for path in runner.local_property_files()),
        "uploaded": [
            {
                "local": runner.display_path(path),
                "remote": REMOTE_PROPERTY_ROOT + "/" + path.name,
                "sha256": runner.sha256_file(path),
                "bytes": path.stat().st_size,
                "mode": "0444",
            }
            for path in runner.local_property_files()
        ],
        "transport": "serial-uudecode-tar-gz",
        "tar_gz_bytes": len(tar_bytes),
        "tar_gz_sha256": tar_sha,
        "encoded_bytes": len(encoded.encode("utf-8")),
        "property_info_sha_ok": property_info_sha in str(property_info.get("stdout") or ""),
        "vendor_default_sha_ok": vendor_default_sha in str(vendor_default.get("stdout") or ""),
    }


def prepare_tcpctl_args(args: Any) -> Any:
    targs = runner.tcp_args(args)
    targs.device_binary = runner.tcpctl_host.DEFAULT_DEVICE_BINARY
    targs.idle_timeout = max(300, int(args.tcp_ready_timeout) + 120)
    targs.max_clients = 16
    targs.token_path = runner.tcpctl_host.DEFAULT_TCPCTL_TOKEN_PATH
    targs.device_helper = "/cache/bin/a90_usbnet"
    targs._v1796_ncm_started = False
    return targs


def bridge_step(targs: Any,
                store: Any,
                steps: list[dict[str, Any]],
                name: str,
                command: str,
                *,
                timeout: float,
                allow_error: bool = False,
                use_cmdv1: bool = True) -> str:
    try:
        output = runner.tcpctl_host.device_command(
            targs,
            command,
            timeout=timeout,
            allow_error=allow_error,
            use_cmdv1=use_cmdv1,
        )
    except Exception as exc:
        runner.write_transfer_step(
            store,
            steps,
            name,
            ["bridge", command],
            "",
            str(exc),
            False,
            rc=1,
        )
        raise
    runner.write_transfer_step(
        store,
        steps,
        name,
        ["bridge", command],
        output,
        "",
        True,
    )
    return output


def ensure_ncm_device_ip(targs: Any,
                         store: Any,
                         steps: list[dict[str, Any]]) -> None:
    bridge_step(
        targs,
        store,
        steps,
        "ncm-enable",
        f"run {targs.device_helper} ncm",
        timeout=45.0,
        allow_error=True,
    )
    bridge_step(
        targs,
        store,
        steps,
        "ncm-ifconfig",
        f"run {targs.toybox} ifconfig ncm0 {targs.device_ip} netmask 255.255.255.0 up",
        timeout=45.0,
    )
    ping_output = runner.tcpctl_host.host_ping(targs, 2)
    runner.write_transfer_step(
        store,
        steps,
        "ncm-host-ping",
        ["ping", targs.device_ip],
        ping_output,
        "",
        True,
    )
    targs._v1796_ncm_started = True


def ensure_tcpctl_ready(args: Any,
                        store: Any,
                        steps: list[dict[str, Any]]) -> tuple[Any, Any | None]:
    targs = prepare_tcpctl_args(args)
    try:
        output = runner.tcpctl_host.wait_for_tcpctl(targs, 2.0)
        runner.write_transfer_step(
            store,
            steps,
            "tcpctl-ready-existing",
            ["tcpctl", "ping"],
            output,
            "",
            True,
        )
        return targs, None
    except RuntimeError:
        pass

    ensure_ncm_device_ip(targs, store, steps)
    runner.tcpctl_host.best_effort_hide_menu(targs)
    if not targs.no_auth:
        runner.tcpctl_host.get_tcpctl_token(targs)
    command = runner.tcpctl_host.tcpctl_listen_command(targs)
    tcp_thread = runner.tcpctl_host.BridgeRunThread(targs, command, echo=False)
    tcp_thread.start()
    if not tcp_thread.ready.wait(args.tcp_ready_timeout):
        text = tcp_thread.text()
        runner.write_transfer_step(
            store,
            steps,
            "tcpctl-auto-start",
            ["tcpctl", "start"],
            text,
            "tcpctl did not become ready",
            False,
            rc=1,
        )
        raise RuntimeError(f"tcpctl did not become ready after start: {text[-400:]}")
    try:
        ready_output = runner.tcpctl_host.wait_for_tcpctl(targs, args.tcp_ready_timeout)
    except RuntimeError as exc:
        runner.write_transfer_step(
            store,
            steps,
            "tcpctl-ready-after-start",
            ["tcpctl", "ping"],
            "",
            str(exc),
            False,
            rc=1,
        )
        raise
    runner.write_transfer_step(
        store,
        steps,
        "tcpctl-ready-after-start",
        ["tcpctl", "ping"],
        ready_output,
        "",
        True,
    )
    runner.write_transfer_step(
        store,
        steps,
        "tcpctl-auto-start",
        ["tcpctl", "start"],
        tcp_thread.text(),
        "",
        True,
    )
    return targs, tcp_thread


def stop_tcpctl(targs: Any,
                tcp_thread: Any | None,
                store: Any,
                steps: list[dict[str, Any]]) -> None:
    if tcp_thread is None:
        return
    try:
        output = runner.tcpctl_host.tcpctl_request(targs, "shutdown", timeout=5.0)
        ok = "OK" in output
    except Exception as exc:  # noqa: BLE001 - cleanup evidence only
        output = ""
        ok = False
        runner.write_transfer_step(
            store,
            steps,
            "tcpctl-auto-stop",
            ["tcpctl", "shutdown"],
            output,
            str(exc),
            False,
            rc=1,
        )
    else:
        runner.write_transfer_step(
            store,
            steps,
            "tcpctl-auto-stop",
            ["tcpctl", "shutdown"],
            output,
            "",
            ok,
            rc=0 if ok else 1,
        )
    tcp_thread.join(10.0)


def restore_ncm_off(targs: Any,
                    store: Any,
                    steps: list[dict[str, Any]]) -> None:
    if not getattr(targs, "_v1796_ncm_started", False):
        return
    try:
        output = runner.tcpctl_host.device_command(
            targs,
            f"run {targs.device_helper} off",
            timeout=20.0,
            allow_error=True,
            use_cmdv1=False,
        )
    except Exception as exc:  # noqa: BLE001 - USB re-enumeration can cut output
        runner.write_transfer_step(
            store,
            steps,
            "ncm-off",
            ["bridge", f"run {targs.device_helper} off"],
            "",
            str(exc),
            False,
            rc=1,
        )
    else:
        runner.write_transfer_step(
            store,
            steps,
            "ncm-off",
            ["bridge", f"run {targs.device_helper} off"],
            output,
            "",
            True,
        )
    time.sleep(3.0)
    bridge_step(
        targs,
        store,
        steps,
        "ncm-off-selftest",
        "selftest",
        timeout=45.0,
    )


def deploy_property_root(args: Any,
                         store: Any,
                         steps: list[dict[str, Any]]) -> dict[str, Any]:
    targs, tcp_thread = ensure_tcpctl_ready(args, store, steps)
    try:
        files = runner.local_property_files()
        remote_dev = str(Path(REMOTE_PROPERTY_ROOT).parent)
        remote_cycle = str(Path(remote_dev).parent)
        runner.tcp_run(targs, [targs.toybox, "rm", "-rf", REMOTE_PROPERTY_ROOT], timeout=30.0)
        runner.tcp_run(targs, [targs.toybox, "mkdir", "-p", REMOTE_PROPERTY_ROOT], timeout=30.0)
        for path in (remote_cycle, remote_dev, REMOTE_PROPERTY_ROOT):
            runner.tcp_run(targs, [targs.toybox, "chmod", "755", path], timeout=30.0)

        uploaded: list[dict[str, Any]] = []
        for index, local_path in enumerate(files, start=1):
            remote_path = REMOTE_PROPERTY_ROOT + "/" + local_path.name
            uploaded.append(
                runner.transfer_file(
                    targs,
                    store,
                    steps,
                    local_path,
                    remote_path,
                    index,
                    args.transfer_port + index,
                )
            )
        sha_text = runner.tcp_run(
            targs,
            [targs.toybox, "sha256sum", REMOTE_PROPERTY_ROOT + "/property_info"],
            timeout=30.0,
        )
        vendor_text = runner.tcp_run(
            targs,
            [targs.toybox, "sha256sum", REMOTE_PROPERTY_ROOT + "/u:object_r:vendor_default_prop:s0"],
            timeout=30.0,
        )
        property_info_sha = runner.sha256_file(runner.LOCAL_PROPERTY_ROOT / "property_info")
        vendor_default_sha = runner.sha256_file(
            runner.LOCAL_PROPERTY_ROOT / "u:object_r:vendor_default_prop:s0"
        )
        return {
            "remote_property_root": REMOTE_PROPERTY_ROOT,
            "file_count": len(uploaded),
            "bytes": sum(item["bytes"] for item in uploaded),
            "uploaded": uploaded,
            "property_info_sha_ok": property_info_sha in sha_text,
            "vendor_default_sha_ok": vendor_default_sha in vendor_text,
        }
    finally:
        stop_tcpctl(targs, tcp_thread, store, steps)
        restore_ncm_off(targs, store, steps)


def collect_event_fields(fields: dict[str, str], event: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe.{event}."
    result = {
        f"{event}_hits": fields.get(prefix + "hit_count", ""),
        f"{event}_first_hit_line": fields.get(prefix + "first_hit_line", ""),
        f"{event}_fetch_args": fields.get(prefix + "fetch_args", ""),
        f"{event}_sample_count": fields.get(prefix + "sample_count", ""),
    }
    for index in range(4):
        result[f"{event}_sample_line_{index}"] = fields.get(
            prefix + f"sample_line_{index}",
            "",
        )
    return result


def sample_lines(details: dict[str, Any], event: str) -> list[str]:
    lines: list[str] = []
    for key in [f"{event}_first_hit_line", *(f"{event}_sample_line_{i}" for i in range(4))]:
        line = str(details.get(key) or "")
        if reliable_observed_string(line) and line not in lines:
            lines.append(line)
    return lines


def parse_count_from_lines(key: str, lines: list[str]) -> int | None:
    pattern = re.compile(rf"\b{re.escape(key)}=(0x[0-9a-fA-F]+|\d+)\b")
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        try:
            return int(match.group(1), 0)
        except ValueError:
            continue
    return None


def collect_names_and_devnodes(lines: list[str]) -> tuple[list[str], list[str]]:
    names: list[str] = []
    devnodes: list[str] = []
    for line in lines:
        name = parse_token(NAME_RE, line)
        devnode = parse_token(DEVNODE_RE, line)
        if name and name not in names:
            names.append(name)
        if devnode and devnode not in devnodes:
            devnodes.append(devnode)
    return names, devnodes


def collect_pm_fields(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe."
    result: dict[str, Any] = {
        "helper_label": fields.get("wlan_pd_service_object_visible_trigger.label", ""),
        "provider_seen": fields.get("wlan_pd_service_object_visible_trigger.provider_seen", ""),
        "as_interface_hits": fields.get(
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_as_interface_call.hit_count",
            "",
        ),
        "register_tx_hits": fields.get(
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_call.hit_count",
            "",
        ),
        "requested_wlanmdsp": fields.get("wlan_pd_service_object_visible_trigger.requested_wlanmdsp", ""),
        "wlfw_service69_seen": fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen", ""),
        "wlan0_present": fields.get("wlan_pd_service_object_visible_trigger.wlan0_present", ""),
        "policy_load_result": fields.get("pm_service_trigger_observer.policy_load.result", ""),
        "pm_proxy_helper_ready": fields.get("wlan_pd_service_object_visible_trigger.pm_proxy_helper_ready", ""),
        "per_mgr_ready": fields.get("wlan_pd_service_object_visible_trigger.per_mgr_ready", ""),
        "per_mgr_state": fields.get("wlan_pd_service_object_visible.per_mgr.state", ""),
        "per_mgr_zombie": fields.get("wlan_pd_service_object_visible.per_mgr.zombie", ""),
        "tftp_running": fields.get("wlan_pd_service_object_visible_trigger.tftp_running", ""),
        "cnss_daemon_running": fields.get("wlan_pd_service_object_visible_trigger.cnss_daemon_running", ""),
        "pm_server_label": fields.get(prefix + "label", ""),
        "pm_server_register_entry_hits": fields.get(prefix + "pm_server_register_entry.hit_count", ""),
        "pm_server_loop_node_hits": fields.get(prefix + "pm_server_register_loop_node.hit_count", ""),
        "pm_server_match_hits": fields.get(prefix + "pm_server_register_match.hit_count", ""),
        "pm_server_success_return_hits": fields.get(prefix + "pm_server_register_success_return.hit_count", ""),
        "pm_server_no_peripheral_hits": fields.get(prefix + "pm_server_register_no_peripheral.hit_count", ""),
    }
    for key in (
        "pm_server_register_entry",
        "pm_server_register_strcmp_call",
        "pm_server_register_no_peripheral",
        "pm_service_main_supported_list_init",
        "pm_service_init_helper_entry",
        "pm_service_init_get_system_info_call",
        "pm_service_init_get_system_info_fail",
        "pm_service_init_first_count_load",
        "pm_service_init_first_add_peripheral_call",
        "pm_service_init_first_add_peripheral_fail_log",
        "pm_service_init_second_count_load",
        "pm_service_init_second_add_peripheral_call",
        "pm_service_init_second_add_peripheral_fail_log",
        "pm_service_add_peripheral_entry",
        "pm_service_add_peripheral_known_name",
        "pm_service_add_peripheral_init_fail",
        "pm_service_add_peripheral_list_commit",
        "pm_service_pre_binder_init_done",
    ):
        result.update(collect_event_fields(fields, key))

    first_count_lines = sample_lines(result, "pm_service_init_first_count_load")
    second_count_lines = sample_lines(result, "pm_service_init_second_count_load")
    first_count = parse_count_from_lines("first_count", first_count_lines)
    second_count = parse_count_from_lines("second_count", second_count_lines)
    first_add_lines = sample_lines(result, "pm_service_init_first_add_peripheral_call")
    second_add_lines = sample_lines(result, "pm_service_init_second_add_peripheral_call")
    entry_lines = sample_lines(result, "pm_service_add_peripheral_entry")
    known_lines = sample_lines(result, "pm_service_add_peripheral_known_name")
    init_fail_lines = sample_lines(result, "pm_service_add_peripheral_init_fail")
    first_names, first_devnodes = collect_names_and_devnodes(first_add_lines)
    second_names, second_devnodes = collect_names_and_devnodes(second_add_lines)
    entry_names, entry_devnodes = collect_names_and_devnodes(entry_lines)
    known_names, known_devnodes = collect_names_and_devnodes(known_lines)
    init_fail_names, init_fail_devnodes = collect_names_and_devnodes(init_fail_lines)

    result.update(
        {
            "pm_service_first_count": "" if first_count is None else str(first_count),
            "pm_service_second_count": "" if second_count is None else str(second_count),
            "pm_service_first_add_names": ",".join(first_names),
            "pm_service_first_add_devnodes": ",".join(first_devnodes),
            "pm_service_second_add_names": ",".join(second_names),
            "pm_service_second_add_devnodes": ",".join(second_devnodes),
            "pm_service_entry_names": ",".join(entry_names),
            "pm_service_entry_devnodes": ",".join(entry_devnodes),
            "pm_service_known_names": ",".join(known_names),
            "pm_service_known_devnodes": ",".join(known_devnodes),
            "pm_service_init_fail_names": ",".join(init_fail_names),
            "pm_service_init_fail_devnodes": ",".join(init_fail_devnodes),
            "pm_server_register_entry_peripheral": parse_field(
                "peripheral",
                str(result.get("pm_server_register_entry_first_hit_line") or ""),
            ),
            "pm_server_register_entry_client": parse_field(
                "client",
                str(result.get("pm_server_register_entry_first_hit_line") or ""),
            ),
            "pm_server_register_strcmp_candidate": parse_field(
                "candidate",
                str(result.get("pm_server_register_strcmp_call_first_hit_line") or ""),
            ),
            "pm_server_register_strcmp_requested": parse_field(
                "requested",
                str(result.get("pm_server_register_strcmp_call_first_hit_line") or ""),
            ),
            "pm_server_register_no_peripheral_name": parse_field(
                "peripheral",
                str(result.get("pm_server_register_no_peripheral_first_hit_line") or ""),
            ),
        }
    )
    return result


def safety_ok(fields: dict[str, str]) -> bool:
    return all(
        field_bool(fields, key)
        for key in (
            "wlan_pd_service_object_visible_trigger.no_esoc0",
            "wlan_pd_service_object_visible_trigger.no_forced_rc1",
            "wlan_pd_service_object_visible_trigger.no_fake_online",
            "wlan_pd_service_object_visible_trigger.no_per_proxy",
            "wlan_pd_service_object_visible_trigger.no_wifi_hal",
            "wlan_pd_service_object_visible_trigger.no_scan_connect",
            "wlan_pd_service_object_visible_trigger.no_credentials",
            "wlan_pd_service_object_visible_trigger.no_dhcp_routes",
            "wlan_pd_service_object_visible_trigger.no_external_ping",
        )
    )


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_pm_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = field_bool(helper_fields, "wlan_pd_service_object_visible_trigger.begin")
    nonlog_contract_seen = field_bool(helper_fields, "wlan_pd_cnss_nonlog_control_flow.begin")
    late_listener_contract_seen = field_bool(helper_fields, "wifi_companion_service_notifier_late_listener.begin")
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "nonlog_contract_seen": nonlog_contract_seen,
            "late_listener_contract_seen": late_listener_contract_seen,
            "safety_ok": safety_ok(helper_fields),
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1795 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen or not nonlog_contract_seen or not late_listener_contract_seen:
        return f"{args.cycle.lower()}-service-object-contract-missing", False, "helper result missed service-object, nonlog, or late listener fields", details
    if not details["safety_ok"]:
        return f"{args.cycle.lower()}-safety-contract-regression", False, "one or more hard-stop safety fields regressed", details

    label = "count-fetcharg-unavailable"
    first_count = intish(details.get("pm_service_first_count"))
    second_count_text = str(details.get("pm_service_second_count") or "")
    first_count_text = str(details.get("pm_service_first_count") or "")
    first_add_hits = intish(details.get("pm_service_init_first_add_peripheral_call_hits"))
    init_fail_hits = intish(details.get("pm_service_add_peripheral_init_fail_hits"))
    list_commit_hits = intish(details.get("pm_service_add_peripheral_list_commit_hits"))
    observed_names = ",".join(
        value
        for value in (
            str(details.get("pm_service_first_add_names") or ""),
            str(details.get("pm_service_entry_names") or ""),
            str(details.get("pm_service_known_names") or ""),
            str(details.get("pm_service_init_fail_names") or ""),
        )
        if value
    )
    observed_devnodes = ",".join(
        value
        for value in (
            str(details.get("pm_service_first_add_devnodes") or ""),
            str(details.get("pm_service_entry_devnodes") or ""),
            str(details.get("pm_service_known_devnodes") or ""),
            str(details.get("pm_service_init_fail_devnodes") or ""),
        )
        if value
    )
    details["pm_service_observed_names"] = observed_names
    details["pm_service_observed_devnodes"] = observed_devnodes

    if list_commit_hits > 0:
        label = "list-commit-progress"
        reason = "PM-service committed a supported-list node; stop before any PM repair, restart-PD request, or WLAN-PD cascade"
    elif not first_count_text or not second_count_text:
        reason = "PM-service count load uprobes fired without reliable first_count/second_count fetchargs; stop for observer repair"
    elif first_count >= 2 and (
        "modem" in observed_names.split(",") or "/dev/subsys_modem" in observed_devnodes.split(",")
    ) and init_fail_hits > 0:
        label = "modem-devnode-access-fail"
        reason = "Primary PM-service discovery included modem and add-peripheral still failed before list commit; stop before any devnode repair"
    elif first_count >= 1 and first_add_hits > 0 and "SDX50M" in observed_names.split(",") and "modem" not in observed_names.split(","):
        label = "sdx50m-only-first-loop"
        reason = "Primary PM-service discovery samples exposed SDX50M but not modem; stop before any devnode or sysfs repair"
    else:
        reason = "PM-service count/sample observer produced rollback-verified evidence but not one of the fixed list-population labels"

    details["pm_service_count_sample_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_sample_lines(gate: dict[str, Any], event: str) -> list[str]:
    return [
        f"- {event} sample {index}: `{report_value(gate.get(f'{event}_sample_line_{index}'))}`"
        for index in range(4)
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} PM-service Count Sample Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD PM-service count/sample discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- helper label: `{gate.get('helper_label')}`",
        f"- PM server label: `{gate.get('pm_server_label')}`",
        f"- PM-service count/sample label: `{gate.get('pm_service_count_sample_label')}`",
        f"- first/second count: `{gate.get('pm_service_first_count')}` / `{gate.get('pm_service_second_count')}`",
        f"- first add names/devnodes: `{gate.get('pm_service_first_add_names')}` / `{gate.get('pm_service_first_add_devnodes')}`",
        f"- second add names/devnodes: `{gate.get('pm_service_second_add_names')}` / `{gate.get('pm_service_second_add_devnodes')}`",
        f"- add-peripheral observed names: `{gate.get('pm_service_observed_names')}`",
        f"- add-peripheral observed devnodes: `{gate.get('pm_service_observed_devnodes')}`",
        f"- provider seen: `{gate.get('provider_seen')}`",
        f"- asInterface hits: `{gate.get('as_interface_hits')}`",
        f"- register/vote TX hits: `{gate.get('register_tx_hits')}`",
        f"- requested `wlanmdsp`: `{gate.get('requested_wlanmdsp')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- wlan0 present: `{gate.get('wlan0_present')}`",
        "",
        "## PM-service Count Uprobes",
        "",
        f"- first count hits/fetchargs: `{gate.get('pm_service_init_first_count_load_hits')}` / `{gate.get('pm_service_init_first_count_load_fetch_args')}`",
        f"- first count first hit: `{report_value(gate.get('pm_service_init_first_count_load_first_hit_line'))}`",
        f"- second count hits/fetchargs: `{gate.get('pm_service_init_second_count_load_hits')}` / `{gate.get('pm_service_init_second_count_load_fetch_args')}`",
        f"- second count first hit: `{report_value(gate.get('pm_service_init_second_count_load_first_hit_line'))}`",
        "",
        "## PM-service First-loop Samples",
        "",
        f"- first add call hits/fail hits: `{gate.get('pm_service_init_first_add_peripheral_call_hits')}` / `{gate.get('pm_service_init_first_add_peripheral_fail_log_hits')}`",
        f"- first add fetchargs: `{gate.get('pm_service_init_first_add_peripheral_call_fetch_args')}`",
        *render_sample_lines(gate, "pm_service_init_first_add_peripheral_call"),
        "",
        "## PM-service Add-peripheral Samples",
        "",
        f"- entry/init-fail/list-commit hits: `{gate.get('pm_service_add_peripheral_entry_hits')}` / `{gate.get('pm_service_add_peripheral_init_fail_hits')}` / `{gate.get('pm_service_add_peripheral_list_commit_hits')}`",
        f"- entry names/devnodes: `{gate.get('pm_service_entry_names')}` / `{gate.get('pm_service_entry_devnodes')}`",
        f"- known names/devnodes: `{gate.get('pm_service_known_names')}` / `{gate.get('pm_service_known_devnodes')}`",
        f"- init-fail names/devnodes: `{gate.get('pm_service_init_fail_names')}` / `{gate.get('pm_service_init_fail_devnodes')}`",
        *render_sample_lines(gate, "pm_service_add_peripheral_entry"),
        *render_sample_lines(gate, "pm_service_add_peripheral_init_fail"),
        "",
        "## PM Register Request Uprobes",
        "",
        f"- register entry hits: `{gate.get('pm_server_register_entry_hits')}`",
        f"- register entry peripheral/client: `{report_value(gate.get('pm_server_register_entry_peripheral'))}` / `{report_value(gate.get('pm_server_register_entry_client'))}`",
        f"- register strcmp candidate/requested: `{gate.get('pm_server_register_strcmp_candidate')}` / `{gate.get('pm_server_register_strcmp_requested')}`",
        f"- no-peripheral requested: `{gate.get('pm_server_register_no_peripheral_name')}`",
        f"- loop/match/success/no-peripheral hits: `{gate.get('pm_server_loop_node_hits')}` / `{gate.get('pm_server_match_hits')}` / `{gate.get('pm_server_success_return_hits')}` / `{gate.get('pm_server_no_peripheral_hits')}`",
        "",
        "## Route Health",
        "",
        f"- policy-load result: `{gate.get('policy_load_result')}`",
        f"- `pm_proxy_helper` ready: `{gate.get('pm_proxy_helper_ready')}`",
        f"- `pm-service` ready: `{gate.get('per_mgr_ready')}`",
        f"- `pm-service` state/zombie: `{gate.get('per_mgr_state')}` / `{gate.get('per_mgr_zombie')}`",
        f"- `tftp_server` running: `{gate.get('tftp_running')}`",
        f"- `cnss-daemon` running: `{gate.get('cnss_daemon_running')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- tar.gz bytes/SHA256: `{property_deploy.get('tar_gz_bytes')}` / `{property_deploy.get('tar_gz_sha256')}`",
        f"- Uploaded files: `{property_deploy.get('file_count')}`",
        f"- Uploaded bytes: `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label; do not repair PM-service devnodes, chase WLAN-PD cascade, start Wi-Fi HAL, scan/connect, DHCP/routes, or external ping in this run.",
        "",
    ]
    return "\n".join(lines)


def sanitize_evidence_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sanitized = SENSITIVE_VERSION_CREATOR_RE.sub(r"\1[redacted]", text)
        if sanitized != text:
            item.write_text(sanitized, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    runner.deploy_property_root = deploy_property_root_serial
    runner.classify_gate = classify_gate
    runner.render_report = render_report
    rc = runner.main(argv)
    sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
