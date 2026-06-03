#!/usr/bin/env python3
"""V1920 clean-DSP/service74 plus V1847 PM-open integration handoff.

The important sequencing detail is that this runner arms only the V641
clean-DSP one-shot flag, then lets the V1847 flash-handoff perform the reboot
into the PM-service open-context test image.  Running V787 first would consume
the flag on stock v724 and would not test the combined boot window.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import native_wifi_pm_service_open_context_handoff_v1847 as v1847
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir


CYCLE = "V1920"
OUT_DIR = repo_path("tmp/wifi/v1920-clean-dsp-pm-open-integration")
HANDOFF_DIR = OUT_DIR / "v1847-handoff"
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1920_CLEAN_DSP_PM_OPEN_INTEGRATION_2026-06-04.md")
V1847_INNER_REPORT = OUT_DIR / "v1847-handoff-report.md"
V641_FLAG = "/cache/native-init-sibling-fwssctl-v641"
V724_QRTR_FLAG = "/cache/native-init-qrtr-servloc-boot-v724"
V1846_INIT = repo_path("tmp/wifi/v1846-pm-service-open-context-test-boot/init_v1846_pm_service_open_context")
V1846_BOOT = repo_path("tmp/wifi/v1846-pm-service-open-context-test-boot/boot_linux_v1846_pm_service_open_context.img")

SECRET_RE = re.compile(r"t[e]mmie[0-9A-Za-z_@.-]*")
REDACT_PATTERNS = (
    (SECRET_RE, "[REDACTED]"),
    (re.compile(r"made by [^\r\n]+"), "made by [redacted]"),
    (re.compile(r"creator: made by [^\r\n]+"), "creator: made by [redacted]"),
)


def redact(text: str) -> str:
    result = text
    for pattern, replacement in REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float = 60.0) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        proc = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = redact(proc.stdout)
        rc = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        output = redact((exc.stdout or "") + (exc.stderr or "") + f"\n[timeout after {timeout}s]\n")
        rc = 124
        timed_out = True
    path = f"host/{name}.txt"
    store.write_text(path, "$ " + " ".join(command) + "\n" + output.rstrip() + "\n")
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "ok": rc == 0,
        "timed_out": timed_out,
        "started": started.isoformat(),
        "file": path,
        "output_tail": output.splitlines()[-20:],
    }


def a90ctl(command: list[str]) -> list[str]:
    return [sys.executable, "scripts/revalidation/a90ctl.py", "--timeout", "45", *command]


def shell_a90(script: str) -> list[str]:
    return a90ctl(["run", "/cache/bin/busybox", "sh", "-c", script])


def flag_probe_script() -> str:
    return (
        f"for f in {V641_FLAG} {V724_QRTR_FLAG} /cache/native-init-sibling-fwssctl-v641.log; do "
        'if [ -e "$f" ]; then echo "exists $f"; /cache/bin/busybox ls -l "$f"; '
        '/cache/bin/busybox tail -n 20 "$f" 2>/dev/null || true; '
        'else echo "missing $f"; fi; done'
    )


def arm_clean_dsp_flag_script() -> str:
    return (
        f"if [ -e {V724_QRTR_FLAG} ]; then echo v1920.blocked=qrtr_flag_present; exit 42; fi; "
        f"umask 077; printf run > {V641_FLAG}; sync; "
        f"echo v1920.clean_dsp_flag_armed=1; /cache/bin/busybox ls -l {V641_FLAG}; "
        f"/cache/bin/busybox cat {V641_FLAG}"
    )


def cleanup_flag_script() -> str:
    return (
        f"if [ -e {V641_FLAG} ]; then /cache/bin/busybox rm -f {V641_FLAG}; "
        "echo v1920.cleaned_leftover_clean_dsp_flag=1; "
        "else echo v1920.cleaned_leftover_clean_dsp_flag=0; fi"
    )


def has_clean_dsp_hook() -> dict[str, Any]:
    required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
    )
    results: dict[str, Any] = {}
    for path in (V1846_INIT, V1846_BOOT):
        if not path.exists():
            results[rel(path)] = {"exists": False, "ok": False, "missing": list(required)}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        results[rel(path)] = {"exists": True, "ok": not missing, "missing": missing}
    return results


def run_v1847_handoff() -> int:
    v1847.DEFAULT_OUT_DIR = HANDOFF_DIR
    v1847.DEFAULT_REPORT_PATH = V1847_INNER_REPORT
    v1847.DMESG_PATTERN = (
        "A90v641|sibling fwssctl|wifi-v641-fwssctl|adsp:|cdsp:|slpi:|"
        + v1847.DMESG_PATTERN
    )
    return v1847.main([])


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def positive_count_list(value: object) -> bool:
    return any(intish(part.strip()) > 0 for part in str(value or "").split(",") if part.strip())


def text_contains(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    regex = re.compile(pattern, re.IGNORECASE)
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if regex.search(text):
            return True
    return False


def classify(handoff: dict[str, Any], hook: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    gate = handoff.get("gate") if isinstance(handoff.get("gate"), dict) else {}
    hook_ok = all(item.get("ok") for item in hook.values())
    prearm_ok = any(step["name"] == "arm-clean-dsp-flag" and step["ok"] for step in steps)
    handoff_ok = bool(handoff.get("pass"))
    rollback = handoff.get("post_rollback_verification") or {}
    rollback_ok = bool(rollback.get("version_ok")) and bool(rollback.get("selftest_fail_zero"))
    clean_dsp_seen = text_contains(HANDOFF_DIR, r"A90v641|sibling fwssctl proof|wifi-v641-fwssctl")
    service74 = bool(gate.get("klog_service74_positive")) or bool(gate.get("raw_service74_text_positive")) or positive_count_list(gate.get("raw_service74_text_counts"))
    service180 = bool(gate.get("klog_service180_positive")) or bool(gate.get("raw_service180_text_positive")) or positive_count_list(gate.get("raw_service180_text_counts"))
    pm_open = gate.get("open_context_path") == "/dev/subsys_modem" and intish(gate.get("open_context_fd")) >= 0
    wlan_pd = bool(gate.get("raw_wlan_pd_text_positive")) or positive_count_list(gate.get("raw_wlan_pd_text_counts"))
    wlfw69 = bool(gate.get("lower_service69_progress")) or intish(gate.get("wlfw_service69_seen")) > 0
    wlan0 = bool(gate.get("lower_wlan0_present")) or str(gate.get("wlan0_present", "0")) not in {"", "0", "False", "false"}
    wlanmdsp = intish(gate.get("requested_wlanmdsp")) > 0

    if not hook_ok or not prearm_ok or not handoff_ok or not rollback_ok:
        label = "clean-dsp-pm-open-handoff-failed"
        reason = "clean-DSP hook, pre-arm, V1847 handoff, or rollback verification failed"
        passed = False
    elif service74 and pm_open and (wlan_pd or wlfw69 or wlan0 or wlanmdsp):
        label = "service74-pm-open-wlanpd-progress"
        reason = "clean-DSP/service74 and PM `/dev/subsys_modem` open coexisted and lower WLAN-PD/WLFW69/wlanmdsp/wlan0 markers advanced"
        passed = True
    elif service74 and pm_open:
        label = "service74-pm-open-post74-stall"
        reason = "service74 and PM `/dev/subsys_modem` open coexisted, but WLAN-PD/WLFW69/wlanmdsp/wlan0 stayed absent"
        passed = True
    elif pm_open and not service74:
        label = "pm-open-service74-absent"
        reason = "V1847 PM `/dev/subsys_modem` open survived, but clean-DSP/service74 did not appear in the same boot"
        passed = True
    elif service74 and not pm_open:
        label = "service74-present-pm-open-absent"
        reason = "clean-DSP/service74 appeared, but V1847 PM open-context did not reach `/dev/subsys_modem`"
        passed = True
    else:
        label = "service74-pm-open-both-absent"
        reason = "neither service74 nor V1847 PM open-context appeared in the combined boot"
        passed = True

    return {
        "label": label,
        "decision": f"v1920-{label}",
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "prearm_ok": prearm_ok,
        "handoff_ok": handoff_ok,
        "rollback_ok": rollback_ok,
        "clean_dsp_seen": clean_dsp_seen,
        "service180": service180,
        "service74": service74,
        "pm_open_subsys_modem": pm_open,
        "wlan_pd": wlan_pd,
        "wlfw69": wlfw69,
        "wlanmdsp": wlanmdsp,
        "wlan0": wlan0,
        "open_context_path": gate.get("open_context_path", ""),
        "open_context_fd": gate.get("open_context_fd", ""),
        "raw_service180_text_counts": gate.get("raw_service180_text_counts", ""),
        "raw_service74_text_counts": gate.get("raw_service74_text_counts", ""),
        "raw_wlan_pd_text_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "lower_service69_progress": gate.get("lower_service69_progress", ""),
        "lower_wlan0_present": gate.get("lower_wlan0_present", ""),
    }


def render_report(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["label", c["label"], c["reason"]],
        ["hook/prearm/handoff", f"{c['hook_ok']} / {c['prearm_ok']} / {c['handoff_ok']}", f"rollback={c['rollback_ok']}"],
        ["clean_dsp_seen", c["clean_dsp_seen"], "A90v641/sibling fwssctl text in handoff evidence"],
        ["service180/service74", f"{c['service180']} / {c['service74']}", f"{c['raw_service180_text_counts']} / {c['raw_service74_text_counts']}"],
        ["pm_open", c["pm_open_subsys_modem"], f"{c['open_context_path']} fd={c['open_context_fd']}"],
        ["wlanpd/wlfw69/wlanmdsp/wlan0", f"{c['wlan_pd']} / {c['wlfw69']} / {c['wlanmdsp']} / {c['wlan0']}", f"wlan_pd_counts={c['raw_wlan_pd_text_counts']}"],
    ]
    lines = [
        "# Native Init V1920 Clean-DSP PM-Open Integration\n\n",
        "## Summary\n\n",
        f"- Cycle: `{CYCLE}`\n",
        f"- Decision: `{c['decision']}`\n",
        f"- Label: `{c['label']}`\n",
        f"- Pass: `{manifest['pass']}`\n",
        f"- Reason: {c['reason']}\n",
        f"- Evidence: `{manifest['out_dir']}`\n",
        f"- Inner handoff: `{manifest['handoff_manifest']}`\n\n",
        "## Matrix\n\n",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "\n\n## Steps\n\n",
    ]
    for step in manifest["steps"]:
        lines.append(f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`\n")
    lines.extend([
        "\n## Safety\n\n",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.\n",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.\n",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1847 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.\n",
    ])
    return "".join(lines)


def main() -> int:
    ensure_private_dir(OUT_DIR)
    store = EvidenceStore(OUT_DIR)
    store.mkdir("host")
    steps: list[dict[str, Any]] = []
    steps.append(run_host(store, "pre-version", a90ctl(["version"])))
    steps.append(run_host(store, "pre-selftest", a90ctl(["selftest"])))
    steps.append(run_host(store, "pre-flags", shell_a90(flag_probe_script())))
    hook = has_clean_dsp_hook()
    store.write_json("host/v1846-clean-dsp-hook.json", hook)

    steps.append(run_host(store, "arm-clean-dsp-flag", shell_a90(arm_clean_dsp_flag_script())))
    handoff_rc = 1
    try:
        handoff_rc = run_v1847_handoff()
    finally:
        steps.append(run_host(store, "cleanup-leftover-clean-dsp-flag", shell_a90(cleanup_flag_script())))
        steps.append(run_host(store, "post-mounts", a90ctl(["cat", "/proc/mounts"])))
        steps.append(run_host(store, "post-selftest", a90ctl(["selftest"])))
        steps.append(run_host(store, "post-status", a90ctl(["status"])))

    handoff_manifest_path = HANDOFF_DIR / "manifest.json"
    handoff = load_json(handoff_manifest_path)
    classification = classify(handoff, hook, steps)
    if handoff_rc != 0:
        classification["handoff_rc"] = handoff_rc
        classification["handoff_ok"] = False
        if classification["pass"]:
            classification["pass"] = False
            classification["label"] = "clean-dsp-pm-open-handoff-failed"
            classification["decision"] = "v1920-clean-dsp-pm-open-handoff-failed"
            classification["reason"] = f"inner V1847 handoff returned rc={handoff_rc}"

    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "handoff_manifest": rel(handoff_manifest_path),
        "pass": bool(classification["pass"]),
        "decision": classification["decision"],
        "label": classification["label"],
        "reason": classification["reason"],
        "classification": classification,
        "hook": hook,
        "steps": steps,
        "host_metadata": host_metadata,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_report(manifest))
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"label={manifest['label']} "
        f"service74={classification['service74']} "
        f"pm_open={classification['pm_open_subsys_modem']} "
        f"wlanpd={classification['wlan_pd']} "
        f"wlan0={classification['wlan0']} "
        f"out_dir={manifest['out_dir']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
