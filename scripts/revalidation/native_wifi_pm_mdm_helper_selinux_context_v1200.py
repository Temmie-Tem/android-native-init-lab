#!/usr/bin/env python3
"""V1200 Option A: mdm_helper SELinux context repair via --pm-observer-set-mdm-helper-selinux-context.

V1199 Option B proved IMG_XFER_DONE alone does not trigger MHI device creation:
SDX50M requires actual firmware bytes via ks/MHI pipe.

V1200 adds --pm-observer-set-mdm-helper-selinux-context (helper v239) to the
V1198 PM observer sequence. This calls write_selinux_attr("current",
"u:r:vendor_mdm_helper:s0") in the child process before execv of
/vendor/bin/mdm_helper, using the same current-attr mechanism that achieves
the kernel→vendor_per_mgr domain transition in V1191.

Gate: does mdm_helper run as vendor_mdm_helper:s0, open /dev/esoc-0, and
spawn /vendor/bin/ks which opens /dev/mhi_0305_01.01.00_pipe_10?
GPIO 142 IRQ count change = MDM fully powered on.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

_ORIG_V1193_PATCH_DEFAULTS = v1193.patch_defaults

DEFAULT_OUT_DIR = Path("tmp/wifi/v1200-pm-mdm-helper-selinux-context")
LATEST_POINTER = Path(
    "tmp/wifi/latest-v1200-pm-mdm-helper-selinux-context.txt"
)
DEFAULT_EXECNS_HELPER_SHA256 = (
    "824ddb597cae36ec9e1163e1bcbf426934a37b9887eab98607f030c8d7766afa"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v241"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1200"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1200/pm-mdm-helper-selinux-context-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1200/pm-mdm-helper-selinux-context-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1200/pm-mdm-helper-selinux-context-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1200-"

SUBSYS_ESOC0_FLAG = "--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc"
RESTART_LEVEL_FLAG = "--pm-observer-set-mdm3-restart-level-related"
MDM_HELPER_SELINUX_FLAG = "--pm-observer-set-mdm-helper-selinux-context"
PRIVATE_FIRMWARE_MOUNTS_FLAG = "--pm-observer-private-firmware-mounts"


def pm_mdm_helper_selinux_context_v1200_child_command(args: Any) -> list[str]:
    result = v1193.v1191._ORIG_VNDSERVICE_GATE_CMD(args)
    if v1191.POLICY_LOAD_FLAG not in result:
        result.append(v1191.POLICY_LOAD_FLAG)
    if v1193.MDM_BEFORE_CNSS_FLAG not in result:
        result.append(v1193.MDM_BEFORE_CNSS_FLAG)
    if SUBSYS_ESOC0_FLAG not in result:
        result.append(SUBSYS_ESOC0_FLAG)
    if RESTART_LEVEL_FLAG not in result:
        result.append(RESTART_LEVEL_FLAG)
    if MDM_HELPER_SELINUX_FLAG not in result:
        result.append(MDM_HELPER_SELINUX_FLAG)
    if PRIVATE_FIRMWARE_MOUNTS_FLAG not in result:
        result.append(PRIVATE_FIRMWARE_MOUNTS_FLAG)
    return result


def _mdm_power_on(manifest: dict[str, Any]) -> dict[str, Any]:
    """Parse pm_observer_mdm_power_on.status.* entries from step payloads."""
    steps = manifest.get("steps", [])
    result: dict[str, Any] = {
        "begin": "",
        "restart_level_set": "",
        "restart_level_write_ok": "",
        "gpio142_before": "",
        "gpio142_after": "",
        "gpio142_fired": "",
        "gpio142_elapsed_ms": "",
        "child_status": "",
        "reboot_required": "",
        "end": "",
    }
    status_entries: list[dict[str, str]] = []
    run_dir = manifest.get("_run_dir", "")
    for step in steps:
        text = ""
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            fpath = Path(run_dir) / step_file
            try:
                text = fpath.read_text(errors="replace")
            except OSError:
                pass
        if not text:
            text = step.get("payload", "") or ""
        current_status: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            for key in result:
                prefix = f"pm_observer_mdm_power_on.{key}="
                if line.startswith(prefix):
                    result[key] = line.split("=", 1)[1].strip()
            for skey in (
                "elapsed_ms",
                "gpio142_count",
                "mdm3_state",
                "mdm3_crash_count",
                "child_wchan",
                "mhi_dev_count",
                "mdm_helper_wchans",
                "mdm_helper_fds",
                "ks_count",
                "ks_wchans",
            ):
                prefix = f"pm_observer_mdm_power_on.status.{skey}="
                if line.startswith(prefix):
                    current_status[skey] = line.split("=", 1)[1].strip()
                    if len(current_status) == 10:
                        status_entries.append(dict(current_status))
                        current_status = {}
    result["_status_entries"] = status_entries  # type: ignore[assignment]
    return result


def _mdm_helper_domain(manifest: dict[str, Any]) -> dict[str, Any]:
    """Check mdm_helper SELinux domain transition result."""
    steps = manifest.get("steps", [])
    run_dir = manifest.get("_run_dir", "")
    result: dict[str, Any] = {
        "selinux_current_ok": "",
        "selinux_current_before": "",
        "selinux_current_after": "",
    }
    for step in steps:
        text = ""
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            try:
                text = (Path(run_dir) / step_file).read_text(errors="replace")
            except OSError:
                pass
        if not text:
            text = step.get("payload", "") or ""
        for line in text.splitlines():
            line = line.strip()
            # Look for mdm_helper selinux_current markers
            for key, prefix in (
                ("selinux_current_ok",
                 "wifi_hal_composite_child.mdm_helper.selinux_current.ok="),
                ("selinux_current_before",
                 "wifi_hal_composite_child.mdm_helper.selinux_current.before="),
                ("selinux_current_after",
                 "wifi_hal_composite_child.mdm_helper.selinux_current.after="),
            ):
                if line.startswith(prefix):
                    result[key] = line.split("=", 1)[1].strip()
    return result


def decide_v1200(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1200-pm-mdm-helper-selinux-context-plan-ready",
            True,
            "plan-only; no device mutation",
            "deploy helper v239 (if needed), then run V1200 live gate",
        )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on(manifest)
    mdm_domain = _mdm_helper_domain(manifest)

    if gate.get("begin") != "1":
        return (
            "v1200-vndservice-gate-not-activated",
            False,
            "vndservice gate not activated; verify helper v239 and flags",
            "check helper version and command flags",
        )

    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1200-policy-load-failed",
            False,
            f"precompiled policy load failed: {policy_result!r}",
            "verify selinuxfs is mounted and vendor precompiled_sepolicy exists",
        )

    esoc0_found = mdm_early.get("esoc0_found", "") == "1"
    if not esoc0_found:
        return (
            "v1200-mdm-helper-esoc0-not-found",
            False,
            "mdm_helper did not open esoc-0; subsys_esoc0 trigger not reached",
            "check mdm_helper SELinux domain and esoc-0 node",
        )

    power_begin = power_on.get("begin", "") == "1"
    if not power_begin:
        return (
            "v1200-mdm-power-on-not-triggered",
            False,
            "pm_observer_mdm_power_on block not reached",
            f"verify {SUBSYS_ESOC0_FLAG} is in command",
        )

    status_entries = power_on.get("_status_entries", [])
    gpio_fired = power_on.get("gpio142_fired", "") == "1"
    elapsed_ms = power_on.get("gpio142_elapsed_ms", "?")

    mdm3_states = list(dict.fromkeys(
        e.get("mdm3_state", "") for e in status_entries if e.get("mdm3_state")
    ))
    crash_counts = [e.get("mdm3_crash_count", "") for e in status_entries]
    max_crash = max((int(c) for c in crash_counts if c.isdigit()), default=0)

    # Check for esoc-0 fd in mdm_helper_fds
    esoc0_fds_seen: list[str] = []
    mhi_fds_seen: list[str] = []
    for e in status_entries:
        fds = e.get("mdm_helper_fds", "none")
        if fds and fds != "none":
            for fd in fds.split(","):
                fd = fd.strip()
                if "/dev/esoc" in fd and fd not in esoc0_fds_seen:
                    esoc0_fds_seen.append(fd)
                if "/dev/mhi" in fd and fd not in mhi_fds_seen:
                    mhi_fds_seen.append(fd)

    mhi_dev_max = max(
        (int(e.get("mhi_dev_count", "0"))
         for e in status_entries if e.get("mhi_dev_count", "0").isdigit()),
        default=0,
    )
    ks_seen = any(
        e.get("ks_count", "0") not in ("0", "")
        for e in status_entries
    )

    # Check mdm_helper domain transition
    context_ok = mdm_domain.get("selinux_current_ok") == "1"
    context_after = mdm_domain.get("selinux_current_after", "?")

    if not status_entries and not power_on.get("end", ""):
        return (
            "v1200-device-rebooted-before-polling",
            False,
            "no status entries and no end marker; device likely rebooted",
            "check mss restart_level; RELATED restart may cascade",
        )

    if gpio_fired:
        return (
            "v1200-gpio142-fired",
            True,
            (
                f"GPIO 142 fired at elapsed={elapsed_ms}ms; MDM powered on; "
                f"mdm_helper_domain={context_after}; "
                f"esoc0_fds={esoc0_fds_seen}; mhi_fds={mhi_fds_seen}"
            ),
            "GPIO 142 confirmed — check MHI device, ks, WLFW, wlan0",
        )

    if mhi_fds_seen or mhi_dev_max > 0:
        return (
            "v1200-mhi-active-gpio142-pending",
            True,
            (
                f"MHI path active: mhi_fds={mhi_fds_seen} mhi_dev_max={mhi_dev_max}; "
                f"GPIO 142 not yet fired; "
                f"mdm_helper_domain={context_after}; esoc0_fds={esoc0_fds_seen}"
            ),
            "MHI active; MDM firmware transfer in progress; observe GPIO 142",
        )

    if esoc0_fds_seen:
        return (
            "v1200-mdm-helper-has-esoc0-fd-no-mhi",
            True,
            (
                f"mdm_helper opened esoc-0: {esoc0_fds_seen}; "
                f"context_ok={context_ok} context_after={context_after!r}; "
                f"no MHI fd yet; mdm3_states={mdm3_states}; "
                f"status_count={len(status_entries)}"
            ),
            (
                "SELinux context fix works — esoc-0 opened; "
                "ks spawn or MHI pipe not yet observed; extend hold or add ks observation"
            ),
        )

    if not context_ok:
        return (
            "v1200-mdm-helper-context-transition-failed",
            False,
            (
                f"selinux_current write failed for mdm_helper; "
                f"context_after={context_after!r}; "
                f"policy may lack vendor_mdm_helper dyntransition allow rule; "
                f"mdm3_states={mdm3_states}"
            ),
            (
                "vendor_mdm_helper domain transition denied; "
                "may need explicit allow in private policy patch"
            ),
        )

    if max_crash > 0:
        return (
            "v1200-mdm3-crash-nonzero",
            False,
            (
                f"mdm3 crash_count={max_crash}; MDM SSR; "
                f"context_after={context_after!r}; states={mdm3_states}"
            ),
            "MDM SSR with RELATED restart; check esoc/MHI/firmware path",
        )

    wchans_sample = [e.get("mdm_helper_wchans", "") for e in status_entries[:3]]
    return (
        "v1200-context-applied-but-esoc0-not-opened",
        False,
        (
            f"context_ok={context_ok} context_after={context_after!r}; "
            f"esoc0_fds=[] mhi_fds=[]; "
            f"mdm3_states={mdm3_states}; crash=0; "
            f"wchans_sample={wchans_sample}"
        ),
        (
            "Domain transition may still be denied; check dmesg AVC denials; "
            "may need explicit allow vendor_mdm_helper esoc_device in private policy"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on(manifest)
    mdm_domain = _mdm_helper_domain(manifest)
    status_entries = power_on.get("_status_entries", [])

    rows = [
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["policy_load_result", policy.get("result", "")],
        ["gate_result", gate.get("result", "")],
        ["per_mgr_domain", domain.get("domain_value", "")],
        ["mdm_helper_esoc0_found", mdm_early.get("esoc0_found", "")],
        ["mdm_helper_context_ok", mdm_domain.get("selinux_current_ok", "")],
        ["mdm_helper_context_before", mdm_domain.get("selinux_current_before", "")],
        ["mdm_helper_context_after", mdm_domain.get("selinux_current_after", "")],
        ["restart_level_set", power_on.get("restart_level_set", "")],
        ["restart_level_write_ok", power_on.get("restart_level_write_ok", "")],
        ["gpio142_before", power_on.get("gpio142_before", "")],
        ["gpio142_fired", power_on.get("gpio142_fired", "")],
        ["gpio142_elapsed_ms", power_on.get("gpio142_elapsed_ms", "")],
        ["status_entry_count", str(len(status_entries))],
    ]
    for i, e in enumerate(status_entries[:10]):
        rows.append([
            f"status[{i}]",
            f"t={e.get('elapsed_ms','')}ms gpio={e.get('gpio142_count','')} "
            f"mdm3={e.get('mdm3_state','')} crash={e.get('mdm3_crash_count','')} "
            f"mhi_dev={e.get('mhi_dev_count','')} "
            f"wchans={e.get('mdm_helper_wchans','')[:60]} "
            f"fds={e.get('mdm_helper_fds','')[:60]}",
        ])
    lines = [
        "# V1200 PM Observer: mdm_helper SELinux context repair",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## MDM Helper Context + Power-On Gate",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


def patch_defaults() -> None:
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180

    v1193.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1193.LATEST_POINTER = LATEST_POINTER
    v1193.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1193.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1193.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1193.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1193.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1193.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1193.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1193_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1183.pm_per_proxy_vndservice_gate_child_command = (
        pm_mdm_helper_selinux_context_v1200_child_command
    )
    v1106.pm_cnss_child_command = pm_mdm_helper_selinux_context_v1200_child_command


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    patch_defaults()
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1200"
    manifest["generated_at"] = _now_iso()
    manifest["subsys_esoc0_flag"] = SUBSYS_ESOC0_FLAG
    manifest["restart_level_flag"] = RESTART_LEVEL_FLAG
    manifest["mdm_helper_selinux_flag"] = MDM_HELPER_SELINUX_FLAG
    manifest["mdm_before_cnss_flag"] = v1193.MDM_BEFORE_CNSS_FLAG
    manifest["policy_load_flag"] = v1191.POLICY_LOAD_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1200(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on(manifest)
    mdm_domain = _mdm_helper_domain(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)
    status_entries = power_on.get("_status_entries", [])

    esoc0_fds_all: list[str] = []
    mhi_fds_all: list[str] = []
    for e in status_entries:
        fds = e.get("mdm_helper_fds", "none")
        if fds and fds != "none":
            for fd in fds.split(","):
                fd = fd.strip()
                if fd:
                    if "/dev/esoc" in fd and fd not in esoc0_fds_all:
                        esoc0_fds_all.append(fd)
                    if "/dev/mhi" in fd and fd not in mhi_fds_all:
                        mhi_fds_all.append(fd)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["gate_open"] = gate.get("gate_open") == "1"
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["mdm_helper_esoc0_found"] = mdm_early.get("esoc0_found", "") == "1"
    manifest["mdm_helper_context_ok"] = mdm_domain.get("selinux_current_ok") == "1"
    manifest["mdm_helper_context_after"] = mdm_domain.get("selinux_current_after", "")
    manifest["restart_level_write_ok"] = power_on.get("restart_level_write_ok", "") == "1"
    manifest["power_on_begin"] = power_on.get("begin", "") == "1"
    manifest["gpio142_fired"] = power_on.get("gpio142_fired", "") == "1"
    manifest["gpio142_elapsed_ms"] = power_on.get("gpio142_elapsed_ms", "")
    manifest["status_entry_count"] = len(status_entries)
    manifest["esoc0_fds_seen"] = esoc0_fds_all
    manifest["mhi_fds_seen"] = mhi_fds_all
    manifest["mhi_dev_count_max"] = max(
        (int(e.get("mhi_dev_count", "0"))
         for e in status_entries if e.get("mhi_dev_count", "0").isdigit()),
        default=0,
    )
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision                         : {manifest['decision']}")
    print(f"pass                             : {manifest['pass']}")
    print(f"reason                           : {manifest['reason'][:200]}")
    print(f"next                             : {manifest['next_step']}")
    print(f"policy_load_result               : {manifest['policy_load_result']}")
    print(f"per_mgr_domain                   : {manifest['per_mgr_domain']!r}")
    print(f"mdm_helper_esoc0_found           : {manifest['mdm_helper_esoc0_found']}")
    print(f"mdm_helper_context_ok            : {manifest['mdm_helper_context_ok']}")
    print(f"mdm_helper_context_after         : {manifest['mdm_helper_context_after']!r}")
    print(f"restart_level_write_ok           : {manifest['restart_level_write_ok']}")
    print(f"power_on_begin                   : {manifest['power_on_begin']}")
    print(f"gpio142_fired                    : {manifest['gpio142_fired']}")
    print(f"status_entry_count               : {manifest['status_entry_count']}")
    print(f"esoc0_fds_seen                   : {manifest['esoc0_fds_seen']}")
    print(f"mhi_fds_seen                     : {manifest['mhi_fds_seen']}")
    print(f"mhi_dev_count_max                : {manifest['mhi_dev_count_max']}")
    print(f"wifi_bringup_executed            : {manifest['wifi_bringup_executed']}")
    print(f"manifest                         : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
