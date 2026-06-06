#!/usr/bin/env python3
"""Acceptance validation for the v725-fasttransport baseline.

Transport-only validation. This script does not run Wi-Fi scan/connect,
credentials, DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

import a90_ncm_transport as ncm
import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as v2144
from a90harness.evidence import EvidenceStore, safe_artifact_label, wifi_artifact_dir


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
EXPECTED_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"


def run_command(command: list[object], *, timeout: float) -> dict[str, Any]:
    started = ncm.now_iso()
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
            "started": started,
            "ended": ncm.now_iso(),
            "timeout": False,
            "rc": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": [str(item) for item in command],
            "started": started,
            "ended": ncm.now_iso(),
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


def a90ctl(command: list[str], *, timeout: float = 20.0, bridge_timeout: float = 10.0) -> list[object]:
    return ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "--timeout", str(bridge_timeout), *command]


def a90ctl_step(store: EvidenceStore,
                steps: list[dict[str, Any]],
                name: str,
                command: list[str],
                *,
                timeout: float = 30.0,
                bridge_timeout: float = 15.0,
                allow_reboot_no_end: bool = False) -> dict[str, Any]:
    result = run_command(a90ctl(command, bridge_timeout=bridge_timeout), timeout=timeout)
    output = "\n".join([str(result.get("stdout") or ""), str(result.get("stderr") or "")])
    if "[busy]" in output:
        hide = run_command(a90ctl(["hide"], bridge_timeout=20), timeout=30)
        write_step(store, steps, f"{name}-hide-on-busy", hide)
        result = run_command(a90ctl(command, bridge_timeout=bridge_timeout), timeout=timeout)
    if allow_reboot_no_end and result.get("rc") != 0 and "reboot: syncing" in str(result.get("stderr") or result.get("stdout") or ""):
        result = {**result, "ok": True, "rc": 0}
    write_step(store, steps, name, result)
    return result


def status_summary(text: str) -> dict[str, Any]:
    return {
        "version_ok": EXPECTED_VERSION in text,
        "selftest_fail0": "fail=0" in text,
        "ncm_present": "ncm=present" in text,
        "tcpctl_stopped": "tcpctl=stopped" in text,
        "raw": "\n".join(
            line for line in text.splitlines()
            if any(token in line for token in ("init:", "selftest:", "exposure:", "netservice:", "ncm="))
        ),
    }


def a90_candidates() -> list[dict[str, Any]]:
    return ncm.host_ncm_candidates(ncm.host_netdev_snapshot(), require_link_local=False)


def candidate_brief(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "ifname": item.get("ifname"),
            "ifindex": item.get("ifindex"),
            "address": item.get("address"),
            "driver": item.get("driver"),
            "usb_vendor": item.get("usb_vendor"),
            "usb_product": item.get("usb_product"),
            "usb_serial": item.get("usb_serial"),
            "interface_number": item.get("interface_number"),
            "link_local": item.get("link_local"),
            "sysfs_path": item.get("sysfs_path"),
            "cdc_ncm": item.get("cdc_ncm"),
        }
        for item in items
    ]


def run_json_subprocess(store: EvidenceStore,
                        steps: list[dict[str, Any]],
                        name: str,
                        command: list[object],
                        *,
                        timeout: float) -> dict[str, Any]:
    result = run_command(command, timeout=timeout)
    write_step(store, steps, name, result)
    text = str(result.get("stdout") or "")
    try:
        parsed = json.loads(text[text.index("{"):])
    except (ValueError, json.JSONDecodeError):
        parsed = {"ok": False, "parse_error": True, "stdout": text[-2000:]}
    parsed["_step_ok"] = bool(result.get("ok"))
    return parsed


def run_transport_smoke(store: EvidenceStore,
                        steps: list[dict[str, Any]],
                        *,
                        label: str,
                        sizes_mib: str,
                        extra_args: list[str] | None = None,
                        timeout: float = 180.0) -> dict[str, Any]:
    command: list[object] = [
        "python3",
        "workspace/public/src/scripts/revalidation/a90_ncm_transport_smoke.py",
        "--label",
        label,
        "--sizes-mib",
        sizes_mib,
        "--upload",
    ]
    if extra_args:
        command.extend(extra_args)
    return run_json_subprocess(store, steps, f"transport-smoke-{label}", command, timeout=timeout)


def run_idempotent_netservice(store: EvidenceStore, steps: list[dict[str, Any]], *, count: int) -> dict[str, Any]:
    before = candidate_brief(a90_candidates())
    durations: list[int] = []
    ok = True
    for index in range(count):
        step = a90ctl_step(
            store,
            steps,
            f"netservice-start-idempotent-{index + 1}",
            ["netservice", "start"],
            timeout=30,
            bridge_timeout=20,
        )
        ok = ok and bool(step.get("ok"))
        match = re.search(r"duration_ms=(\d+)", str(step.get("stdout") or ""))
        if match:
            durations.append(int(match.group(1)))
    after = candidate_brief(a90_candidates())
    same_sysfs = bool(before and after and before[0].get("sysfs_path") == after[0].get("sysfs_path"))
    result = {
        "ok": ok and same_sysfs and all(duration <= 1000 for duration in durations),
        "same_sysfs_path": same_sysfs,
        "durations_ms": durations,
        "before": before,
        "after": after,
    }
    ncm.write_compact_step(
        store,
        steps,
        "netservice-idempotent-result",
        command=["netservice-idempotent-result"],
        ok=bool(result["ok"]),
        rc=0 if result["ok"] else 1,
        stdout=json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    return result


def run_nm_repair_probe(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = a90_candidates()
    if not candidates:
        result = {"ok": False, "reason": "no-a90-ncm-candidate-before-disconnect"}
        ncm.write_compact_step(
            store,
            steps,
            "nm-repair-probe-skipped",
            command=["nm-repair-probe"],
            ok=False,
            rc=1,
            stdout=json.dumps(result, indent=2, sort_keys=True) + "\n",
        )
        return result
    ifname = str(candidates[0].get("ifname") or "")
    disconnect = run_command(["nmcli", "device", "disconnect", ifname], timeout=20)
    write_step(store, steps, "nm-device-disconnect", disconnect)
    time.sleep(1.0)
    smoke = run_transport_smoke(store, steps, label="baseline-nm-repair", sizes_mib="1", timeout=90)
    return {
        "ok": bool(smoke.get("ok")),
        "ifname": ifname,
        "disconnect_ok": bool(disconnect.get("ok")),
        "smoke": smoke,
    }


def wait_for_status(store: EvidenceStore, steps: list[dict[str, Any]], *, timeout_sec: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_sec
    attempts = 0
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        attempts += 1
        result = run_command(a90ctl(["status"], bridge_timeout=5), timeout=8)
        last = result
        summary = status_summary(str(result.get("stdout") or ""))
        if (
            result.get("ok")
            and summary.get("version_ok")
            and summary.get("selftest_fail0")
            and summary.get("ncm_present")
            and summary.get("tcpctl_stopped")
        ):
            write_step(store, steps, "cold-reboot-status-ready", result)
            return {
                "ok": True,
                "attempts": attempts,
                "elapsed_sec": round(timeout_sec - (deadline - time.monotonic()), 3),
                "status": summary,
            }
        time.sleep(5)
    if last is not None:
        write_step(store, steps, "cold-reboot-status-timeout-last", last)
    return {"ok": False, "attempts": attempts, "elapsed_sec": timeout_sec}


def run_cold_reboot_probe(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    reboot = a90ctl_step(
        store,
        steps,
        "cold-reboot-command",
        ["reboot"],
        timeout=5,
        bridge_timeout=2,
        allow_reboot_no_end=True,
    )
    ready = wait_for_status(store, steps, timeout_sec=180)
    smoke: dict[str, Any] = {}
    if ready.get("ok"):
        smoke = run_transport_smoke(store, steps, label="baseline-cold-reboot", sizes_mib="1,32", timeout=120)
    return {
        "ok": bool(reboot.get("ok")) and bool(ready.get("ok")) and bool(smoke.get("ok")),
        "reboot_ok": bool(reboot.get("ok")),
        "ready": ready,
        "smoke": smoke,
    }


def run_v2144_collector_probe(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    out = store.run_dir / "v2144-collector"
    substore = EvidenceStore(out)
    substeps: list[dict[str, Any]] = []
    v2144.collect_test_evidence(substore, substeps)
    fast_result: dict[str, Any] = {}
    extracted: list[str] = []
    for step in substeps:
        if step.get("name") == "test-fast-evidence-upload-result":
            text = (out / step["stdout_file"]).read_text(encoding="utf-8", errors="replace")
            fast_result = json.loads(text)
            extracted = fast_result.get("extraction", {}).get("extracted", [])
            break
    substore.write_json("collector-probe.json", {
        "out_dir": str(out),
        "fast_result": fast_result,
        "extracted": extracted,
        "steps": substeps,
    })
    result = {
        "ok": bool(fast_result.get("ok")) and len(extracted) >= 8,
        "out_dir": str(out),
        "fast_ok": bool(fast_result.get("ok")),
        "elapsed_sec": fast_result.get("elapsed_sec"),
        "extracted_count": len(extracted),
        "extracted": extracted,
    }
    ncm.write_compact_step(
        store,
        steps,
        "v2144-collector-fastupload-result",
        command=["v2144-collector-fastupload-result"],
        ok=bool(result["ok"]),
        rc=0 if result["ok"] else 1,
        stdout=json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--skip-cold-reboot", action="store_true")
    args = parser.parse_args()

    safe_label = safe_artifact_label(args.label, default="baseline")
    out_dir = wifi_artifact_dir("runs", f"v725-fasttransport-baseline-validation-{safe_label}", timestamp=True)
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []

    initial_status = a90ctl_step(store, steps, "initial-status", ["status"], timeout=30, bridge_timeout=15)
    initial = status_summary(str(initial_status.get("stdout") or ""))
    idempotent = run_idempotent_netservice(store, steps, count=5)
    bigfile = run_transport_smoke(store, steps, label="baseline-bigfile", sizes_mib="1,32,128", timeout=240)
    nm_repair = run_nm_repair_probe(store, steps)
    cold_reboot = {"ok": True, "skipped": True} if args.skip_cold_reboot else run_cold_reboot_probe(store, steps)
    v2144_probe = run_v2144_collector_probe(store, steps)
    final_status = a90ctl_step(store, steps, "final-status", ["status"], timeout=30, bridge_timeout=15)
    final = status_summary(str(final_status.get("stdout") or ""))

    checks = {
        "initial_status": initial,
        "idempotent_netservice": idempotent,
        "bigfile_transport": bigfile,
        "nm_repair": nm_repair,
        "cold_reboot": cold_reboot,
        "v2144_collector": v2144_probe,
        "final_status": final,
    }
    pass_all = (
        bool(initial.get("version_ok"))
        and bool(initial.get("selftest_fail0"))
        and bool(idempotent.get("ok"))
        and bool(bigfile.get("ok"))
        and bool(nm_repair.get("ok"))
        and bool(cold_reboot.get("ok"))
        and bool(v2144_probe.get("ok"))
        and bool(final.get("version_ok"))
        and bool(final.get("selftest_fail0"))
        and bool(final.get("ncm_present"))
        and bool(final.get("tcpctl_stopped"))
    )
    manifest = {
        "label": safe_label,
        "decision": "v725-fasttransport-baseline-accepted" if pass_all else "v725-fasttransport-baseline-blocked",
        "pass": pass_all,
        "out_dir": str(out_dir),
        "checks": checks,
        "steps": steps,
    }
    store.write_json("manifest.json", manifest)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": manifest["out_dir"],
        "initial_status": initial,
        "final_status": final,
        "idempotent_ok": idempotent.get("ok"),
        "bigfile_ok": bigfile.get("ok"),
        "nm_repair_ok": nm_repair.get("ok"),
        "cold_reboot_ok": cold_reboot.get("ok"),
        "v2144_collector_ok": v2144_probe.get("ok"),
    }, indent=2, sort_keys=True))
    return 0 if pass_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
