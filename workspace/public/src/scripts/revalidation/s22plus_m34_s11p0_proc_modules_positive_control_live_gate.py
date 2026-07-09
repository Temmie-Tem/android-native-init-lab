#!/usr/bin/env python3
"""Guarded S22+ M34 S11P0 proc-modules positive-control live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

S11P0 keeps the S10C0/S9 module recipe, keeps the direct cmd-db.ko
finit_module acceptance gate, and adds a /proc/modules positive-control
predicate over watchdog modules:

    (cmd-db.ko rc == 0 || rc == -EEXIST) &&
    (/proc/modules has qcom_wdt_core || /proc/modules has gh_virt_wdt)

Predicate true means HIT and should re-enter Download mode. Predicate false
parks, requiring manual Download rollback.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_m34_runtime_gadget_split import (
    M34_S10C0_PROBE_MODULE,
    M34_S10C0_PROBE_PROC_NAME,
    M34_S11P0_MODULE_LOAD_PROBE,
    M34_S11P0_POSITIVE_CONTROL_MODULES,
    M34_S11P0_POSITIVE_CONTROL_PROC_NAMES,
)
from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    EXPECTED_MAGISK_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    append_log,
    flash_ap,
    host_snapshot,
    odin_devices,
    poll_android,
    repo_root,
    require_current_android,
    resolve,
    run,
    utc_now,
    verify_ap,
    wait_for_odin,
)
from s22plus_m25_hs_only_usb2_acm_live_gate import (
    EXPECTED_BASE_BOOT_SHA256,
    record_timeline_event,
    verify_partition_hash,
)
from s22plus_m34_s10c0_direct_finit_loader_audit_live_gate import (
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    EXPECTED_STOCK_BOOT_RAW_SHA256,
    rollback_boot_only_from_download,
    wait_for_odin_absent,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability


LIVE_ACK_TOKEN = "S22PLUS-M34-S11P0-PROC-MODULES-POSITIVE-CONTROL-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M34-S11P0-PROC-MODULES-POSITIVE-CONTROL-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_STAGE = "S11P0"
EXPECTED_STAGE_NUMBER = 21
DISPLAY_SERIAL_REDACTED = "<S22_SERIAL_REDACTED>"
EXPECTED_M34_MARKER = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S11P0"
EXPECTED_M34_AP_SHA256 = "dacb20dc0466487e6ad30f7ad5ebcb053a9593966922464eba4b3ed60e5f3b45"
EXPECTED_M34_BOOT_SHA256 = "3ac8b8a5dde2ef6c3f7170c258a4dc6f3a3f9a4bb4575b5af5cf3380952d7881"
EXPECTED_M34_INIT_SHA256 = "efd8141e8c552b4e30f0052186b801d36420476d155e7c489c0a8644718dd5f6"
EXPECTED_M34_MODULE_LIST_SHA256 = "c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26"
EXPECTED_M34_TEMPLATE_SOURCE_SHA256 = "70f4326294da2f27c7736f5119c7c9ad32f10e02e066fd2f2530ca91a8e4078b"
EXPECTED_M34_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M34_BASE_BOOT_SHA256 = EXPECTED_BASE_BOOT_SHA256
EXPECTED_MODULE_COUNT = 89
EXPECTED_MEMBER = "boot.img.lz4"
EXPECTED_MODULE_ENTRY = "s22plus_m34_s11p0_runtime_gadget_split.modules"
EXPECTED_SCHEMA = "s22plus_m34_s11p0_result_v1"

DEFAULT_M34_AP = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_14/S11P0/odin4/AP.tar.md5")
DEFAULT_M34_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_14/manifest.json")
ACTIVE_EXCEPTION_INSERT_ANCHOR = "   **Consumed exception (2026-07-10, S22+ Magisk boot-baseline restore boot-only gate):**"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m34_s11p0_proc_modules_positive_control_live_gate_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def policy_required_markers() -> list[str]:
    return [
        "S22+ M34 S11P0 proc-modules positive-control native-init boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_STAGE,
        EXPECTED_M34_MARKER,
        EXPECTED_M34_AP_SHA256,
        EXPECTED_M34_BOOT_SHA256,
        EXPECTED_M34_INIT_SHA256,
        EXPECTED_M34_MODULE_LIST_SHA256,
        EXPECTED_M34_TEMPLATE_SOURCE_SHA256,
        EXPECTED_M34_KERNEL_SHA256,
        EXPECTED_M34_BASE_BOOT_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        EXPECTED_STOCK_BOOT_RAW_SHA256,
        "S11P0 keeps the S10C0/S9 module recipe",
        "S11P0 positive-controls native-init /proc/modules with watchdog modules",
        f"module_load_probe={M34_S11P0_MODULE_LOAD_PROBE}",
        "predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
        "phase=s11_proc_modules_positive_control_probe",
        "s11_proc_modules_positive_control=1",
        "proc_modules=1",
        "direct_finit_rc=1",
        f"probe_module={M34_S10C0_PROBE_MODULE}",
        f"probe_proc_name={M34_S10C0_PROBE_PROC_NAME}",
        "positive_control=watchdog_proc_visible",
        "positive_control_proc_names=" + ",".join(M34_S11P0_POSITIVE_CONTROL_PROC_NAMES),
        "positive_control_modules=" + ",".join(M34_S11P0_POSITIVE_CONTROL_MODULES),
        "cmd_db_proc_seen=",
        "qcom_wdt_core_proc_seen=",
        "gh_virt_wdt_proc_seen=",
        "watchdog_proc_seen=",
        "cmd_db_seen=",
        "cmd_db_rc=",
        "modules_open_rc=",
        "modules_read_rc=",
        "attempted=",
        "ok=",
        "eexist=",
        "fail=",
        "first_fail_index=",
        "first_fail_rc=",
        "first_fail_name=",
        "both_graphs_closure=1",
        "devlink_supplier_closure=1",
        "substrate_load_set=waipio_devlink",
        "driver_load_only=1",
        "manual_power_write=0",
        f"module_count={EXPECTED_MODULE_COUNT}",
        "configfs_gadget=0",
        "udc_bind=0",
        "role_write_discriminator=0",
        "typec_readback=0",
        "reboot_request=download",
        "download_beacon=1",
        "true_action=reboot_download",
        "false_action=park",
        "download-beacon-hit",
        "download-beacon-miss-parked-manual-download-required",
        "HIT means native-init /proc/modules can see a watchdog positive control",
        "MISS means watchdog positive-control visibility failed or the loader did not reach the expected state",
        "no configfs gadget setup",
        "no UDC bind",
        "no TypeC role write",
        "no ssusb role write",
        "no Android/Magisk handoff",
        "no persistent partition mount",
        "no block write",
        "manual Download rollback is recovery-only",
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [marker for marker in policy_required_markers() if marker not in normalized]


def agents_exception_active_template() -> str:
    marker_lines = "\n".join(f"   `{marker}`" for marker in policy_required_markers())
    return f"""   **Narrow operator-authorized exception (2026-07-10, S22+ M34 S11P0 proc-modules positive-control boot-only live gate):**
   After the Magisk boot baseline was restored and the M34 S11P0 host-build
   report pinned the exact artifact hashes, Codex may run one bounded attended
   boot-partition-only M34 S11P0 live gate on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py`.
   Live ack token: `{LIVE_ACK_TOKEN}`. Rollback ack token:
   `{ROLLBACK_ACK_TOKEN}`.

   The exact candidate AP.tar.md5 SHA256 must be
   `{EXPECTED_M34_AP_SHA256}`; contained padded `boot.img` SHA256 must be
   `{EXPECTED_M34_BOOT_SHA256}`; direct `/init` SHA256 must be
   `{EXPECTED_M34_INIT_SHA256}`; template source SHA256 must be
   `{EXPECTED_M34_TEMPLATE_SOURCE_SHA256}`; module-list SHA256 must be
   `{EXPECTED_M34_MODULE_LIST_SHA256}`; preserved kernel SHA256 must be
   `{EXPECTED_M34_KERNEL_SHA256}`; and known-booting base Magisk boot SHA256
   must be `{EXPECTED_M34_BASE_BOOT_SHA256}`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.
   Before live flash, the helper must verify the pinned Magisk boot-only
   rollback AP SHA256 `{EXPECTED_MAGISK_AP_SHA256}` and the S10C0-specific
   FYG8 stock boot-only fallback AP SHA256 `{EXPECTED_STOCK_BOOT_AP_SHA256}`
   generated from stock raw boot SHA256 `{EXPECTED_STOCK_BOOT_RAW_SHA256}`.

   The candidate is limited to freestanding direct PID1 M34 S11P0 behavior:
   `S22+ M34 S11P0 proc-modules positive-control native-init boot-only`,
   `{EXPECTED_M34_MARKER}`, `S11P0 keeps the S10C0/S9 module recipe`, and
   `S11P0 positive-controls native-init /proc/modules with watchdog modules`.
   It remains driver-load-only: `both_graphs_closure=1`,
   `devlink_supplier_closure=1`, `substrate_load_set=waipio_devlink`,
   `driver_load_only=1`, `manual_power_write=0`, `module_count=89`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`.

   S11P0 intentionally performs no downstream USB gadget work: no configfs
   gadget setup, no UDC bind, no TypeC role write, no ssusb role write, no
   FunctionFS, and no stock composite. Its observation is
   `s11_proc_modules_positive_control=1`,
   `module_load_probe={M34_S11P0_MODULE_LOAD_PROBE}`,
   `predicate=cmd_db_finit_accepted_and_watchdog_proc_visible`,
   `phase=s11_proc_modules_positive_control_probe`, `proc_modules=1`,
   `direct_finit_rc=1`, `probe_module={M34_S10C0_PROBE_MODULE}`,
   `probe_proc_name={M34_S10C0_PROBE_PROC_NAME}`,
   `positive_control=watchdog_proc_visible`,
   `positive_control_proc_names={','.join(M34_S11P0_POSITIVE_CONTROL_PROC_NAMES)}`,
   `positive_control_modules={','.join(M34_S11P0_POSITIVE_CONTROL_MODULES)}`,
   `cmd_db_proc_seen=`, `qcom_wdt_core_proc_seen=`,
   `gh_virt_wdt_proc_seen=`, `watchdog_proc_seen=`, `cmd_db_seen=`,
   `cmd_db_rc=`, `modules_open_rc=`, `modules_read_rc=`, `attempted=`,
   `ok=`, `eexist=`, `fail=`, `first_fail_index=`, `first_fail_rc=`, and
   `first_fail_name=`. Predicate true requests `reboot_request=download` with
   `download_beacon=1` and records `true_action=reboot_download`; predicate
   false records `false_action=park` and parks. The host-visible HIT is
   `download-beacon-hit`, where a new Odin Download endpoint appears after the
   original Download endpoint disconnects. MISS is
   `download-beacon-miss-parked-manual-download-required`; manual Download
   rollback is required and is recovery-only. HIT means native-init
   /proc/modules can see a watchdog positive control. MISS means watchdog
   positive-control visibility failed or the loader did not reach the expected
   state.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S11P1, S10C0 repeat, S10B repeat,
   B2/B3/B4, descriptor/composition pivots, FunctionFS/conn_gadget parity,
   display/distro candidates, kernel rebuilds, RDX PC dump retrieval, or any
   non-boot partition action.

   Required policy marker coverage:
{marker_lines}
"""


def has_exact_active_exception_template(text: str) -> bool:
    return " ".join(agents_exception_active_template().split()) in " ".join(text.split())


def verify_agents_text(agents: str, log_path: Path, *, source_label: str) -> None:
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_source={source_label}")
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"{source_label} missing M34 S11P0 authorization markers: {missing}")
    active_template_present = has_exact_active_exception_template(agents)
    append_log(log_path, f"agents_exception_exact_active_template_present={int(active_template_present)}")
    if not active_template_present:
        raise SystemExit(f"{source_label} marker coverage is present but exact M34 S11P0 active template is absent")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    verify_agents_text((root / "AGENTS.md").read_text(encoding="utf-8"), log_path, source_label="AGENTS.md")


def agents_candidate_text(current_agents: str) -> str:
    template = agents_exception_active_template()
    if missing_policy_markers(template):
        raise SystemExit("internal S11P0 active template is missing policy markers")
    if has_exact_active_exception_template(current_agents):
        return current_agents
    if ACTIVE_EXCEPTION_INSERT_ANCHOR not in current_agents:
        raise SystemExit("source AGENTS missing S11P0 insertion anchor")
    return current_agents.replace(ACTIVE_EXCEPTION_INSERT_ANCHOR, template + "\n\n" + ACTIVE_EXCEPTION_INSERT_ANCHOR, 1)


def find_stage(data: dict[str, Any], label: str) -> dict[str, Any]:
    for stage in data.get("stages", []):
        if stage.get("label") == label:
            return stage
    raise SystemExit(f"M34 manifest does not contain {label} stage")


def verify_m34_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M34 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    stage = find_stage(data, EXPECTED_STAGE)
    hashes = stage.get("hashes", {})
    safety = data.get("safety", {})
    matrix = data.get("matrix", {})
    runtime_steps = stage.get("runtime_steps", {})
    init_info = stage.get("init", {})
    closure = stage.get("closure", {})
    ramdisk = stage.get("ramdisk", {})

    append_log(log_path, f"m34_manifest_path={path}")
    append_log(log_path, f"m34_s11p0_manifest_hashes={json.dumps(hashes, sort_keys=True)}")

    if data.get("target") != EXPECTED_TARGET:
        raise SystemExit(f"M34 target mismatch: {data.get('target')!r}")
    if data.get("hashes", {}).get("template_source") != EXPECTED_M34_TEMPLATE_SOURCE_SHA256:
        raise SystemExit("M34 template source hash mismatch")
    if data.get("hashes", {}).get("nochange_repack_boot") != EXPECTED_M34_BASE_BOOT_SHA256:
        raise SystemExit("M34 no-change MagiskBoot repack is not pinned to the known booting base")
    if data.get("magiskboot", {}).get("nochange_repack_byte_identical") is not True:
        raise SystemExit("M34 no-change MagiskBoot repack is not byte-identical")
    if matrix.get("next_host_only_candidate") != EXPECTED_STAGE:
        raise SystemExit(f"M34 next host-only candidate mismatch: {matrix.get('next_host_only_candidate')!r}")

    required_matrix = {
        "s11p0_module_load_probe": M34_S11P0_MODULE_LOAD_PROBE,
        "s11p0_probe_module": M34_S10C0_PROBE_MODULE,
        "s11p0_probe_proc_name": M34_S10C0_PROBE_PROC_NAME,
        "s11p0_positive_control_proc_names": M34_S11P0_POSITIVE_CONTROL_PROC_NAMES,
        "s11p0_positive_control_modules": M34_S11P0_POSITIVE_CONTROL_MODULES,
        "s11p0_true_action": "reboot(download)",
        "s11p0_false_action": "park",
        "s11p0_starts_from_s10c0_module_recipe": True,
        "s11p0_uses_direct_finit_module_rc": True,
        "s11p0_beacon_hit_means_proc_modules_can_see_watchdog": True,
        "s11p0_skips_downstream_configfs_and_udc_to_isolate_module_load": True,
    }
    for key, expected in required_matrix.items():
        if matrix.get(key) != expected:
            raise SystemExit(f"M34 S11P0 matrix {key} mismatch: {matrix.get(key)!r} != {expected!r}")

    if stage.get("stage_number") != EXPECTED_STAGE_NUMBER:
        raise SystemExit(f"M34 S11P0 stage number mismatch: {stage.get('stage_number')!r}")
    if runtime_steps.get("module_load_probe") != M34_S11P0_MODULE_LOAD_PROBE:
        raise SystemExit(f"M34 S11P0 runtime module_load_probe mismatch: {runtime_steps!r}")

    required_hashes = {
        "ap_tar_md5": EXPECTED_M34_AP_SHA256,
        "boot_img": EXPECTED_M34_BOOT_SHA256,
        "base_boot": EXPECTED_M34_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M34_KERNEL_SHA256,
        "m34_init": EXPECTED_M34_INIT_SHA256,
        "m34_modules": EXPECTED_M34_MODULE_LIST_SHA256,
    }
    for key, expected in required_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M34 S11P0 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if stage.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit(f"M34 S11P0 tar members mismatch: {stage.get('tar_members')!r}")
    if closure.get("module_count") != EXPECTED_MODULE_COUNT:
        raise SystemExit(f"M34 S11P0 module count mismatch: {closure.get('module_count')!r}")
    for module in [M34_S10C0_PROBE_MODULE, *M34_S11P0_POSITIVE_CONTROL_MODULES]:
        if module not in closure.get("modules", []):
            raise SystemExit(f"M34 S11P0 closure missing module: {module}")
    if ramdisk.get("added_subset_entry") != EXPECTED_MODULE_ENTRY:
        raise SystemExit(f"M34 S11P0 module-list ramdisk entry mismatch: {ramdisk.get('added_subset_entry')!r}")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M34 S11P0 must not inject module binaries into boot ramdisk")

    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": "download-if-probe-true",
        "intended_reboot_syscall": True,
        "reboot_request": "download-if-probe-true",
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_binary_injection": False,
        "stage_s11p0_starts_from_s10c0_module_recipe": True,
        "stage_s11p0_module_load_probe": M34_S11P0_MODULE_LOAD_PROBE,
        "stage_s11p0_positive_control_proc_names": M34_S11P0_POSITIVE_CONTROL_PROC_NAMES,
        "stage_s11p0_true_reboot_download_false_park": True,
        "stage_s11p0_no_configfs_udc_or_role_write": True,
        "stage_s11p0_driver_load_only_no_manual_power_write": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M34 S11P0 safety {key} mismatch: {safety.get(key)!r} != {expected!r}")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M34_MARKER,
        "version=0.12",
        "stage=S11P0",
        "runtime_step=S11P0",
        "module_count=89",
        "reboot_request=download",
        "download_beacon=1",
        "configfs_gadget=0",
        "udc_bind=0",
        "role_write_discriminator=0",
        "typec_readback=0",
        "devlink_supplier_closure=1",
        "both_graphs_closure=1",
        f"module_load_probe={M34_S11P0_MODULE_LOAD_PROBE}",
        "s11_proc_modules_positive_control=1",
        "proc_modules=1",
        "direct_finit_rc=1",
        f"probe_module={M34_S10C0_PROBE_MODULE}",
        f"probe_proc_name={M34_S10C0_PROBE_PROC_NAME}",
        "positive_control=watchdog_proc_visible",
        "positive_control_proc_names=qcom_wdt_core,gh_virt_wdt",
        "positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko",
        "phase=s11_proc_modules_positive_control_probe",
        "predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
        "cmd_db_proc_seen=",
        "qcom_wdt_core_proc_seen=",
        "gh_virt_wdt_proc_seen=",
        "watchdog_proc_seen=",
        "true_action=reboot_download",
        "false_action=park",
        "phase=s11_proc_modules_positive_control_reboot_returned",
        "/proc/modules",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M34 S11P0 required string missing from manifest: {required}")


def verify_m34_artifacts(
    *,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> None:
    verify_ap(m34_ap, EXPECTED_M34_AP_SHA256, "m34_s11p0_candidate", log_path)
    verify_m34_manifest(m34_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)


def observe_download_beacon(
    *,
    run_dir: Path,
    log_path: Path,
    odin: Path,
    observe_sec: int,
    snapshot_interval_sec: float,
) -> tuple[str, str | None]:
    deadline = time.monotonic() + observe_sec
    next_snapshot = 0.0
    while time.monotonic() < deadline:
        devices = odin_devices(odin, log_path, "candidate-beacon-observe")
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during S11P0 observation: {devices}")
        if len(devices) == 1:
            host_snapshot(run_dir, log_path, "candidate_beacon_hit", odin)
            append_log(log_path, f"s11p0_result=download-beacon-hit odin_device={devices[0]}")
            return "download-beacon-hit", devices[0]
        now = time.monotonic()
        if now >= next_snapshot:
            host_snapshot(run_dir, log_path, "candidate_observe", odin)
            next_snapshot = now + snapshot_interval_sec
        time.sleep(1.0)
    append_log(log_path, "s11p0_result=download-beacon-miss-parked-manual-download-required")
    return "download-beacon-miss-parked-manual-download-required", None


def write_result_summary(
    run_dir: Path,
    log_path: Path,
    *,
    result: str,
    rc: int,
    rollback_target: str,
    rollback_device: str | None = None,
    android_serial: str | None = None,
    note: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema": EXPECTED_SCHEMA,
        "timestamp_utc": utc_now(),
        "target": EXPECTED_TARGET,
        "stage": EXPECTED_STAGE,
        "result": result,
        "rc": rc,
        "rollback_target": rollback_target,
        "candidate_ap_sha256": EXPECTED_M34_AP_SHA256,
        "candidate_boot_sha256": EXPECTED_M34_BOOT_SHA256,
        "candidate_init_sha256": EXPECTED_M34_INIT_SHA256,
        "base_boot_sha256": EXPECTED_M34_BASE_BOOT_SHA256,
        "module_load_probe": M34_S11P0_MODULE_LOAD_PROBE,
        "probe_module": M34_S10C0_PROBE_MODULE,
        "probe_proc_name": M34_S10C0_PROBE_PROC_NAME,
        "positive_control_proc_names": list(M34_S11P0_POSITIVE_CONTROL_PROC_NAMES),
    }
    if rollback_device is not None:
        payload["rollback_device"] = rollback_device
    if android_serial is not None:
        payload["android_serial"] = DISPLAY_SERIAL_REDACTED
    if note is not None:
        payload["note"] = note
    path = run_dir / "result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"result_json={path}")
    append_log(log_path, f"result_summary={json.dumps(payload, sort_keys=True)}")


def print_only_mode(args: argparse.Namespace) -> bool:
    return (
        args.print_agents_exception_active_template
        or args.write_agents_candidate is not None
        or args.verify_agents_candidate is not None
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m34-ap", type=Path, default=DEFAULT_M34_AP)
    parser.add_argument("--m34-manifest", type=Path, default=DEFAULT_M34_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--observe-sec", type=int, default=90)
    parser.add_argument("--snapshot-interval-sec", type=float, default=5.0)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--manual-download-wait-sec", type=int, default=300)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=240)
    parser.add_argument("--android-stability-samples", type=int, default=2)
    parser.add_argument("--android-stability-interval-sec", type=float, default=2.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--print-agents-exception-active-template", action="store_true")
    parser.add_argument("--write-agents-candidate", type=Path)
    parser.add_argument("--verify-agents-candidate", type=Path)
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.print_agents_exception_active_template,
            args.write_agents_candidate is not None,
            args.verify_agents_candidate is not None,
            args.rollback_from_download,
            args.live,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --print-agents-exception-active-template, "
            "--write-agents-candidate, --verify-agents-candidate, "
            "--rollback-from-download, and --live are mutually exclusive"
        )
    if args.observe_sec < 30:
        raise SystemExit("--observe-sec must be at least 30 for the M34 S11P0 download-beacon probe")
    if args.snapshot_interval_sec < 1.0:
        raise SystemExit("--snapshot-interval-sec must be at least 1.0")

    root = repo_root()
    m34_ap = resolve(root, args.m34_ap)
    m34_manifest = resolve(root, args.m34_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)

    if print_only_mode(args):
        with tempfile.TemporaryDirectory(prefix="s22plus_m34_s11p0_print_") as tmp:
            log_path = Path(tmp) / "s22plus_m34_s11p0_proc_modules_positive_control_live_gate.txt"
            append_log(log_path, f"=== {utc_now()} s22plus M34 S11P0 proc-modules positive-control live gate ===")
            verify_m34_artifacts(
                m34_ap=m34_ap,
                m34_manifest=m34_manifest,
                magisk_rollback_ap=magisk_rollback_ap,
                stock_rollback_ap=stock_rollback_ap,
                log_path=log_path,
            )
            if args.print_agents_exception_active_template:
                print(agents_exception_active_template(), end="")
                return 0
            if args.write_agents_candidate is not None:
                candidate_path = resolve(root, args.write_agents_candidate)
                agents_path = (root / "AGENTS.md").resolve()
                if candidate_path == agents_path:
                    raise SystemExit("--write-agents-candidate refuses to write AGENTS.md directly")
                if candidate_path.exists():
                    raise SystemExit(f"AGENTS candidate already exists; refuse to overwrite: {candidate_path}")
                candidate = agents_candidate_text((root / "AGENTS.md").read_text(encoding="utf-8"))
                verify_agents_text(candidate, log_path, source_label=str(candidate_path))
                candidate_path.parent.mkdir(parents=True, exist_ok=True)
                candidate_path.write_text(candidate, encoding="utf-8")
                print(
                    "write-agents-candidate ok: exact M34 S11P0 active exception inserted into candidate; "
                    f"no AGENTS.md write, no device action; candidate={candidate_path}"
                )
                return 0
            if args.verify_agents_candidate is not None:
                candidate_path = resolve(root, args.verify_agents_candidate)
                verify_agents_text(candidate_path.read_text(encoding="utf-8"), log_path, source_label=str(candidate_path))
                print(
                    "verify-agents-candidate ok: exact M34 S11P0 active exception is present; "
                    f"no AGENTS.md write, no device action; candidate={candidate_path}"
                )
                return 0

    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m34_s11p0_proc_modules_positive_control_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M34 S11P0 proc-modules positive-control live gate ===")

    verify_m34_artifacts(
        m34_ap=m34_ap,
        m34_manifest=m34_manifest,
        magisk_rollback_ap=magisk_rollback_ap,
        stock_rollback_ap=stock_rollback_ap,
        log_path=log_path,
    )
    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M34 S11P0 artifacts verified; no AGENTS/device action; log={log_path}")
        return 0

    odin = resolve(root, args.odin)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")
    verify_agents_exception(root, log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        devices = odin_devices(odin, log_path, "rollback-only")
        if len(devices) != 1:
            raise SystemExit(f"S11P0 rollback requires exactly one Odin device, got {devices}")
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=devices[0],
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="rollback_only",
        )
        write_result_summary(
            run_dir,
            log_path,
            result="rollback-only-no-s11p0-proof",
            rc=rollback.rc,
            rollback_target=rollback.rollback_target,
            rollback_device=rollback.rollback_device,
            android_serial=rollback.android_serial,
        )
        print(f"M34 S11P0 rollback-from-download completed rc={rollback.rc}; log={log_path}")
        return rollback.rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(log_path, selected_serial, args.android_stability_samples, args.android_stability_interval_sec)
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_M34_BASE_BOOT_SHA256, "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M34 S11P0 candidate, rollback APs, AGENTS exception, Android, and boot hash verified; log={log_path}")
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    print("M34 S11P0 live gate starting. HIT should self-enter Download mode if watchdog /proc/modules positive-control is visible.", flush=True)
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result="candidate-download-mode-missing", rc=2, rollback_target=args.rollback_target)
        print("download mode did not appear for M34 S11P0 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m34_ap, odin_device, log_path, "candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result="candidate-flash-failed", rc=candidate_rc or 3, rollback_target=args.rollback_target, rollback_device=odin_device)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            write_result_summary(run_dir, log_path, result="no-proof-original-download-never-disconnected", rc=4, rollback_target=args.rollback_target)
            return 4
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="no_disconnect",
        )
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result="no-proof-original-download-never-disconnected", rc=rollback.rc or 7, rollback_target=rollback.rollback_target, rollback_device=rollback.rollback_device, android_serial=rollback.android_serial)
        return rollback.rc or 7

    record_timeline_event(run_dir, "candidate_boot_ready")
    print(f"M34 S11P0 candidate flashed. Observing download beacon for {args.observe_sec}s.", flush=True)
    result, rollback_device = observe_download_beacon(
        run_dir=run_dir,
        log_path=log_path,
        odin=odin,
        observe_sec=args.observe_sec,
        snapshot_interval_sec=args.snapshot_interval_sec,
    )

    if result == "download-beacon-hit":
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            write_result_summary(run_dir, log_path, result=result, rc=4, rollback_target=args.rollback_target)
            return 4
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="beacon_hit",
        )
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result=result, rc=rollback.rc, rollback_target=rollback.rollback_target, rollback_device=rollback.rollback_device, android_serial=rollback.android_serial)
        print(f"M34 S11P0 live gate completed rc={rollback.rc}; result={result}; log={log_path}")
        return rollback.rc

    print(f"M34 S11P0 result={result}. Enter Download mode manually for rollback now; waiting up to {args.manual_download_wait_sec}s.", flush=True)
    rollback_device = wait_for_odin(odin, log_path, "manual-rollback-wait", args.manual_download_wait_sec)
    if rollback_device is None:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result=result, rc=4, rollback_target=args.rollback_target, note="manual Download rollback did not appear within bounded wait")
        print(f"M34 S11P0 MISS observed, but manual Download mode did not appear. Run --rollback-from-download after entering Download mode. log={log_path}", file=sys.stderr)
        return 4
    rollback = rollback_boot_only_from_download(
        odin=odin,
        rollback_ap=magisk_rollback_ap,
        stock_boot_fallback_ap=stock_rollback_ap,
        odin_device=rollback_device,
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=args.rollback_target,
        android_wait_sec=args.android_wait_sec,
        label="manual_after_miss",
    )
    record_timeline_event(run_dir, "live_session_end")
    write_result_summary(run_dir, log_path, result=result, rc=rollback.rc, rollback_target=rollback.rollback_target, rollback_device=rollback.rollback_device, android_serial=rollback.android_serial)
    print(f"M34 S11P0 live gate completed rc={rollback.rc}; result={result}; log={log_path}")
    return rollback.rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
