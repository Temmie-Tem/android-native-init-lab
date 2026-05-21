#!/usr/bin/env python3
"""V501 execns helper v52 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V501 deploy approval phrase. It does not run the connect executor, start
daemons, connect, request DHCP, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v51_deploy_preflight as v51


deploy = v51.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v501-execns-helper-v52-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v501-a90_android_execns_probe-v52/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "2a3b83f852e17f93cf82a9617f396457718024f28ac510fb915848e3e3547a7d"
deploy.HELPER_MARKER = "a90_android_execns_probe v52"
deploy.SERVICE_MODE_TOKEN = "wifi-active-session-connect-ping"
deploy.DEPLOY_LABEL = "v52"
deploy.DEPLOY_NAME = "execns-helper-v52"
deploy.DEPLOY_PLAN_VERSION = "V501"
deploy.DEPLOY_LOG_PREFIX = "v501"
deploy.SUMMARY_TITLE = "v501 Execns Helper v52 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v501 deploy execns helper v52 only; "
    "no live connect and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_connect_ping_v500.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v52",
    "wifi-active-session-connect-ping",
    "--allow-connect-dhcp-ping",
    "--connect-config",
    "wifi_connect_ping.executor_implemented=0",
)


def run_v500_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v500-connect-ping-preflight")
    command = [
        deploy.sys.executable,
        str(deploy.repo_path(deploy.V373_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--helper",
        args.remote_helper,
        "--helper-sha256",
        args.helper_sha256,
        "preflight",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v500-connect-ping-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v500-connect-ping-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "reason": manifest.get("reason", ""),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v500_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v52 deploy still requires exact approval", "deploy helper v52, then rerun V500/V499 readiness"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v52 already current", "run V500 readiness"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V501 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v500_result and v500_result.get("decision") not in {
        "v500-native-connect-ping-blocked",
        "v500-native-connect-ping-ready",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V500 preflight decision={v500_result.get('decision')}", "inspect V500 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v52 deployed or already current; V500 preflight was rerun", "implement v53 live connect executor body, then run V500 with exact approval"


deploy.run_v373_preflight = run_v500_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
