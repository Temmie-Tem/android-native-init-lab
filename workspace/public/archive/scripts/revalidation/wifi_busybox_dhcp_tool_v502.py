#!/usr/bin/env python3
"""V502 BusyBox DHCP-tool deploy/preflight wrapper.

This deploys only `/cache/bin/busybox` from the already-built static ARM64
BusyBox artifact.  The purpose is to satisfy the native Wi-Fi connect/DHCP
tool-surface gate without starting Android daemons, connecting Wi-Fi, changing
routes, or sending external packets.
"""

from __future__ import annotations

from a90harness.evidence import workspace_private_input_path

import wifi_execns_helper_v12_deploy_preflight as deploy


BUSYBOX_SHA256 = "95fcbded9318a643e51e15bc5b0f2f5281996e0b82d303ce0af8f9acc9685e7c"
EXECNS_HELPER = "/cache/bin/a90_android_execns_probe"
EXECNS_HELPER_SHA256 = "2a3b83f852e17f93cf82a9617f396457718024f28ac510fb915848e3e3547a7d"

deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v502-busybox-dhcp-tool-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = workspace_private_input_path(
    "external_tools", "userland", "bin", "busybox-aarch64-static"
)
deploy.DEFAULT_REMOTE_HELPER = "/cache/bin/busybox"
deploy.DEFAULT_HELPER_SHA256 = BUSYBOX_SHA256
deploy.HELPER_MARKER = "Usage: busybox"
deploy.SERVICE_MODE_TOKEN = "udhcpc"
deploy.DEPLOY_LABEL = "busybox-dhcp"
deploy.DEPLOY_NAME = "busybox-dhcp-tool"
deploy.DEPLOY_PLAN_VERSION = "V502"
deploy.DEPLOY_LOG_PREFIX = "v502"
deploy.SUMMARY_TITLE = "v502 BusyBox DHCP Tool Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v502 deploy busybox DHCP tool only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_connect_ping_v499.py")
deploy.READ_ONLY_COMMANDS = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("netservice-status", ["netservice", "status"], 10.0),
    ("stat-helper", ["stat", deploy.DEFAULT_REMOTE_HELPER], 10.0),
    ("sha-helper", ["run", deploy.DEFAULT_TOYBOX, "sha256sum", deploy.DEFAULT_REMOTE_HELPER], 10.0),
    ("helper-usage", ["run", deploy.DEFAULT_REMOTE_HELPER], 20.0),
    ("ps", ["run", deploy.DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
)


def local_helper_info(args: deploy.argparse.Namespace) -> dict[str, object]:
    path = deploy.repo_path(args.local_helper)
    info: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "file_output": "",
        "strings_busybox_usage": False,
        "strings_udhcpc": False,
        "static_aarch64": False,
    }
    if not path.exists():
        return info
    info["sha256"] = deploy.sha256_file(path)
    rc, file_output = deploy.run_host(["file", "-L", str(path)], timeout=10)
    info["file_output"] = file_output.strip()
    info["static_aarch64"] = rc == 0 and "ARM aarch64" in file_output and "statically linked" in file_output
    rc, strings_output = deploy.run_host(["strings", str(path)], timeout=15)
    if rc == 0:
        info["strings_busybox_usage"] = "Usage: busybox" in strings_output
        info["strings_udhcpc"] = "udhcpc" in strings_output
    return info


def build_checks(args: deploy.argparse.Namespace,
                 store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult],
                 local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks: list[deploy.Check] = []
    version = deploy.capture_text(store, steps, "version")
    status = deploy.capture_text(store, steps, "status")
    selftest = deploy.capture_text(store, steps, "selftest")
    busybox_usage = deploy.capture_text(store, steps, "helper-usage")
    busybox_sha = deploy.capture_text(store, steps, "sha-helper")
    ps = deploy.capture_text(store, steps, "ps")
    netdev = deploy.capture_text(store, steps, "proc-net-dev")
    managers = [line.strip() for line in ps.splitlines() if deploy.MANAGER_RE.search(line)]
    wifi_links = [line.strip() for line in netdev.splitlines() if deploy.WIFI_RE.search(line)]
    remote_sha_match = args.helper_sha256 in busybox_sha
    remote_has_dhcp = "Usage: busybox" in busybox_usage and "udhcpc" in busybox_usage

    deploy.add_check(
        checks,
        "local-busybox-dhcp-tool",
        "pass" if (
            local["exists"]
            and local["sha256"] == args.helper_sha256
            and local["static_aarch64"]
            and local["strings_busybox_usage"]
            and local["strings_udhcpc"]
        ) else "blocked",
        "blocker",
        (
            f"exists={local['exists']} sha={local['sha256'] or 'missing'} "
            f"static_aarch64={local['static_aarch64']} "
            f"usage={local['strings_busybox_usage']} udhcpc={local['strings_udhcpc']}"
        ),
        [str(local["path"]), str(local["file_output"])],
        "rebuild or restore the static BusyBox artifact before DHCP-tool deploy",
    )
    if args.command == "plan":
        deploy.add_check(checks, "plan-only", "pass", "info", "no bridge or host network command executed", [], "run preflight next")
        return checks

    deploy.add_check(
        checks,
        "native-version",
        "pass" if args.expect_version in version else "warn",
        "warning",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:3],
        "refresh baseline if native version intentionally changed",
    )
    deploy.add_check(
        checks,
        "native-clean",
        "pass" if deploy.step_ok(steps, "status") and deploy.step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked",
        "blocker",
        "status/selftest rc=0 fail=0 expected",
        [line.strip() for line in (status + "\n" + selftest).splitlines() if line.strip().startswith("selftest:")][:4],
        "fix native health before BusyBox deploy",
    )
    deploy.add_check(
        checks,
        "ncm-host-reachable",
        "pass" if ping and ping["ok"] else ("blocked" if deploy.ncm_required(args) else "warn"),
        "blocker" if deploy.ncm_required(args) else "warning",
        f"ping_rc={ping['rc'] if ping else 'skipped'} device_ip={args.device_ip} transfer_method={args.transfer_method}",
        [ping["file"]] if ping else [],
        "run ncm_host_setup.py setup before NCM deploy; auto/serial can use serial fallback",
    )
    deploy.add_check(
        checks,
        "service-manager-processes-clean",
        "pass" if not managers else "blocked",
        "blocker",
        f"process_count={len(managers)}",
        managers[:8],
        "do not deploy while a service-manager experiment is active",
    )
    deploy.add_check(
        checks,
        "wifi-link-surface-clean",
        "pass" if not wifi_links else "blocked",
        "blocker",
        f"wifi_link_count={len(wifi_links)}",
        wifi_links[:8],
        "do not deploy while Wi-Fi bring-up is active",
    )
    deploy.add_check(
        checks,
        "remote-busybox-dhcp-tool",
        "pass" if remote_sha_match and remote_has_dhcp else "needs-deploy",
        "deploy",
        f"sha_match={remote_sha_match} usage_udhcpc={remote_has_dhcp}",
        [line for line in busybox_sha.splitlines() if args.remote_helper in line][:2]
        + [line for line in busybox_usage.splitlines() if "BusyBox" in line or "udhcpc" in line][:6],
        "approved V502 run installs static BusyBox as /cache/bin/busybox",
    )
    deploy.add_check(
        checks,
        "approval-gate",
        "pass" if deploy.approved(args) else "needs-operator",
        "approval",
        f"phrase_match={args.approval_phrase == deploy.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
        [deploy.APPROVAL_PHRASE],
        "exact phrase and flags required before /cache/bin/busybox write",
    )
    return checks


def run_v499_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v499-connect-ping-readiness-preflight")
    command = [
        deploy.sys.executable,
        str(deploy.repo_path(deploy.V373_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        EXECNS_HELPER,
        "--helper-sha256",
        EXECNS_HELPER_SHA256,
        "preflight",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v499-connect-ping-readiness-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v499-connect-ping-readiness-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "reason": manifest.get("reason", ""),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v499_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; BusyBox DHCP-tool deploy still requires exact approval", "deploy BusyBox, then rerun V499/V500 readiness"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; BusyBox DHCP tool already current", "run V499/V500 readiness"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V502 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v499_result and v499_result.get("decision") not in {
        "v499-native-connect-ping-readiness-ready",
        "v499-native-connect-ping-readiness-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V499 preflight decision={v499_result.get('decision')}", "inspect V499 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "BusyBox DHCP tool deployed or already current; V499 readiness was rerun", "complete scan-only proof and implement V500 live connect executor"


deploy.local_helper_info = local_helper_info
deploy.build_checks = build_checks
deploy.run_v373_preflight = run_v499_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
