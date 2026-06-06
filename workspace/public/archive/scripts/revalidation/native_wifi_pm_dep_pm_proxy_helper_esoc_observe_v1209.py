#!/usr/bin/env python3
"""V1209: pm_proxy_helper multi-sample esoc0 observer (300ms/1s/3s/5s).

V1208 LIVE PASS (pm_proxy_helper fd probe at 300ms):
  pph_alive=1, pph_esoc0_count=0, pph_subsys_esoc0_count=0,
  pph_subsys_modem_count=1, pph_wchan=SyS_nanosleep

  V853 Android fd-holders: vendor_per_mgr (pm-service) holds subsys_esoc0 + subsys_modem.
  pm_proxy_helper NOT shown as esoc0 holder in Android snapshot.
  pm_proxy_helper opens subsys_modem as fd=3 (first file opened after exec).
  pm_proxy_helper does NOT mmap vendor_peripheral_prop (no vendor property decision).

V1209 hypothesis: pm_proxy_helper opens subsys_modem unconditionally, then tries
subsys_esoc0 in a separate thread (blocks in mdm_subsys_powerup per V849 pattern).
Multi-sample probe (300ms, 1s, 3s, 5s) will show:
  - Does esoc0 ever appear in pph fds? (→ pph tries esoc0 in background thread)
  - Does pph wchan change to mdm_subsys_powerup? (→ confirms esoc0 attempt)
  - Does pph exit before 5s? (→ oneshot vs long-lived decision)
  - pph state: S=sleeping, D=blocked (mdm_subsys_powerup)

Decisions:
  v1209-pph-esoc0-appears-at-Ns: esoc0_count>0 at sample N
  v1209-pph-wchan-mdm-subsys-powerup: pph wchan = mdm_subsys_powerup at any sample
  v1209-pph-exits-before-5s: pph exits before 5s (no esoc0 attempt or quick fail)
  v1209-pph-alive-no-esoc0-at-5s: alive at 5s, still no esoc0 fd
  v1209-pcie-link-training-failed: fallback
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import native_wifi_pm_dep_pm_proxy_helper_esoc_probe_v1208 as v1208

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1209-pph-multi-sample-esoc-observe")
LATEST_POINTER = Path("tmp/wifi/latest-v1209-pph-multi-sample-esoc-observe.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "3c46f8cf3394762485b328215000da14599f16a9a7a63e5d69312f84d6b1d435"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v246"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1209"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1209/pm-dep-pph-esoc-observe-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1209/pm-dep-pph-esoc-observe-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1209/pm-dep-pph-esoc-observe-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1209-"

_ORIG_V1209_PATCH_DEFAULTS = v1208.patch_defaults


def _pph_samples(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Parse pm_service_trigger_observer.pph_sample.* fields."""
    steps = manifest.get("steps", [])
    samples: dict[str, dict[str, str]] = {}
    run_dir = manifest.get("_run_dir", "")
    labels = ("300ms", "1s", "3s", "5s")
    _fields = ("alive", "elapsed_ms", "state", "wchan",
               "esoc0_count", "subsys_esoc0_count", "subsys_modem_count")
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
        for line in text.splitlines():
            line = line.strip()
            for lbl in labels:
                for fld in _fields:
                    prefix = f"pm_service_trigger_observer.pph_sample.{lbl}.{fld}="
                    if line.startswith(prefix):
                        if lbl not in samples:
                            samples[lbl] = {}
                        samples[lbl][fld] = line.split("=", 1)[1].strip()
    return [dict(samples.get(lbl, {}), label=lbl) for lbl in labels]


def _int_field(d: dict[str, str], key: str, default: int = -1) -> int:
    try:
        return int(d.get(key, ""))
    except (ValueError, TypeError):
        return default


def decide_v1209(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1209-pph-multi-sample-esoc-observe-plan-ready",
            True,
            "plan-only; no device mutation",
            "deploy v246, run V1209 live gate (pph multi-sample 300ms/1s/3s/5s)",
        )

    base_decision, base_pass, base_reason, base_next = v1208.decide_v1208(args, manifest)
    if base_decision in ("v1208-policy-load-failed",
                         "v1208-pph-probe-not-captured",
                         "v1205-policy-load-failed",
                         "v1205-no-status-entries"):
        return (
            base_decision.replace("v1208", "v1209").replace("v1205", "v1209"),
            False, base_reason, base_next,
        )

    samples = _pph_samples(manifest)
    if not samples or all(not s.get("alive") for s in samples):
        return (
            "v1209-pph-samples-not-captured",
            False,
            "pph_sample fields missing from output; helper v246 version check needed",
            "check helper v246 marker and child output",
        )

    # Check if esoc0 ever appears
    esoc0_appeared_at = None
    subsys_esoc0_appeared_at = None
    mdm_subsys_powerup_at = None
    last_alive_label = None
    last_dead_label = None

    for s in samples:
        lbl = s.get("label", "?")
        alive = _int_field(s, "alive", 0)
        esoc0 = _int_field(s, "esoc0_count", -1)
        subsys_esoc0 = _int_field(s, "subsys_esoc0_count", -1)
        wchan = s.get("wchan", "")
        if alive:
            last_alive_label = lbl
            if esoc0 > 0 and esoc0_appeared_at is None:
                esoc0_appeared_at = lbl
            if subsys_esoc0 > 0 and subsys_esoc0_appeared_at is None:
                subsys_esoc0_appeared_at = lbl
            if "mdm_subsys_powerup" in wchan and mdm_subsys_powerup_at is None:
                mdm_subsys_powerup_at = lbl
        else:
            if last_dead_label is None:
                last_dead_label = lbl

    sample_summary = "; ".join(
        f"{s.get('label', '?')}(alive={s.get('alive', '?')} "
        f"modem={s.get('subsys_modem_count', '?')} "
        f"esoc0={s.get('subsys_esoc0_count', '?')} "
        f"wchan={s.get('wchan', '?')})"
        for s in samples
    )

    if subsys_esoc0_appeared_at:
        return (
            f"v1209-pph-subsys-esoc0-appears-at-{subsys_esoc0_appeared_at}",
            True,
            f"pph opened /dev/subsys_esoc0 at {subsys_esoc0_appeared_at}! "
            f"samples: {sample_summary}",
            "pph tries esoc0 — but blocks in mdm_subsys_powerup until MDM hardware responds. "
            "Next: per_mgr dep mechanism classification (how does per_mgr see pph esoc0 state).",
        )

    if esoc0_appeared_at:
        return (
            f"v1209-pph-esoc0-appears-at-{esoc0_appeared_at}",
            True,
            f"pph opened /dev/esoc-0 at {esoc0_appeared_at}! "
            f"samples: {sample_summary}",
            "pph accesses raw esoc-0 — trace what it does with it.",
        )

    if mdm_subsys_powerup_at:
        return (
            f"v1209-pph-wchan-mdm-subsys-powerup-at-{mdm_subsys_powerup_at}",
            True,
            f"pph wchan=mdm_subsys_powerup at {mdm_subsys_powerup_at} — "
            f"pph DOES try subsys_esoc0 (blocks in powerup). "
            f"samples: {sample_summary}",
            "pph tries esoc0 via subsys_device_open → mdm_subsys_powerup → waits for MDM. "
            "MDM never responds (GPIO142=0). "
            "Next: advance MDM power-on sequence (esoc0 powerup → GPIO135/142 handshake).",
        )

    if last_alive_label == "5s":
        return (
            "v1209-pph-alive-no-esoc0-at-5s",
            True,
            f"pph alive at 5s, no esoc0 ever; samples: {sample_summary}",
            "pph does NOT try esoc0 within 5s. "
            "Check pph binary strings for decision logic (ro.* property or sysfs read).",
        )

    if last_dead_label:
        return (
            f"v1209-pph-exits-before-{last_dead_label}-no-esoc0",
            True,
            f"pph exited by {last_dead_label}, no esoc0 fd observed; "
            f"samples: {sample_summary}",
            "pph is short-lived and never opened esoc0 — check binary strings.",
        )

    return (
        "v1209-pcie-link-training-failed",
        base_pass,
        f"pph_probe_no_esoc0; {base_reason[:200]}",
        base_next,
    )


def patch_defaults() -> None:
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
    import native_wifi_pm_mdm_pcie_observe_v1203 as v1203

    v1203.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1203.LATEST_POINTER = LATEST_POINTER
    v1203.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1203.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1193.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1193.LATEST_POINTER = LATEST_POINTER
    v1193.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1193.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1193.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1193.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1193.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1193.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1193.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1209_PATCH_DEFAULTS()

    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    patch_defaults()

    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
    import native_wifi_pm_mdm_pcie_observe_v1203 as v1203
    import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
    import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
    import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204
    import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1209"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1209(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    samples = _pph_samples(manifest)
    pph_probe = v1208._pph_probe(manifest)  # v245 compat alias (300ms)

    power_on = v1205._mdm_power_on_v1205(manifest)
    status_entries = power_on.get("_status_entries", [])
    pci_dev_counts = [
        int(e.get("pci_dev_count", "0"))
        for e in status_entries if e.get("pci_dev_count", "0").isdigit()
    ]
    pcie_link_states = list(dict.fromkeys(
        e.get("pcie_link_state", "") for e in status_entries if e.get("pcie_link_state")
    ))
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["status_entry_count"] = len(status_entries)
    manifest["pci_dev_count_max"] = max(pci_dev_counts, default=0)
    manifest["pcie_link_states"] = pcie_link_states
    manifest["per_mgr_esoc0_any"] = any(
        e.get("per_mgr_has_esoc0", "0") == "1" for e in status_entries
    )
    manifest["pph_samples"] = samples
    manifest["after_pm_proxy_helper_spawn"] = {
        "alive": v1208._int_field(pph_probe, "alive", -1),
        "esoc0_count": v1208._int_field(pph_probe, "esoc0_count", -1),
        "subsys_esoc0_count": v1208._int_field(pph_probe, "subsys_esoc0_count", -1),
        "subsys_modem_count": v1208._int_field(pph_probe, "subsys_modem_count", -1),
        "wchan": pph_probe.get("wchan", ""),
    }
    manifest["wifi_bringup_executed"] = False

    sample_table = "\n".join(
        f"| {s.get('label','?')} | {s.get('alive','?')} | {s.get('state','?')} | "
        f"{s.get('wchan','?')} | {s.get('esoc0_count','?')} | "
        f"{s.get('subsys_esoc0_count','?')} | {s.get('subsys_modem_count','?')} |"
        for s in samples
    )
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", f"""# V1209 PM pm_proxy_helper Multi-Sample Esoc0 Observer

**Decision**: `{manifest['decision']}`
**Pass**: `{manifest['pass']}`
**Reason**: {manifest['reason'][:500]}
**Next**: {manifest['next_step']}

| label | alive | state | wchan | esoc0 | subsys_esoc0 | subsys_modem |
|---|---|---|---|---|---|---|
{sample_table}

| key | value |
|---|---|
| per_mgr_esoc0_any | {manifest['per_mgr_esoc0_any']} |
| pci_dev_count_max | {manifest['pci_dev_count_max']} |
| pcie_link_states | {manifest['pcie_link_states']} |
| status_entry_count | {manifest['status_entry_count']} |
""")
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision              : {manifest['decision']}")
    print(f"pass                  : {manifest['pass']}")
    print(f"reason                : {manifest['reason'][:200]}")
    for s in samples:
        lbl = s.get("label", "?")
        print(f"pph[{lbl:5s}] alive={s.get('alive','?')} state={s.get('state','?')} "
              f"wchan={s.get('wchan','?'):30s} "
              f"modem={s.get('subsys_modem_count','?')} "
              f"esoc0={s.get('subsys_esoc0_count','?')}")
    print(f"per_mgr_esoc0_any     : {manifest['per_mgr_esoc0_any']}")
    print(f"pci_dev_count_max     : {manifest['pci_dev_count_max']}")
    print(f"status_entry_count    : {manifest['status_entry_count']}")
    print(f"manifest              : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
