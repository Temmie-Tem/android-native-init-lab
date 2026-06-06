#!/usr/bin/env python3
"""V499 execns helper v51 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V499 deploy approval phrase. It does not start daemons, connect, request
DHCP, route traffic, ping externally, or bring up Wi-Fi.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v50_deploy_preflight as v50


deploy = v50.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v499-execns-helper-v51-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v499-a90_android_execns_probe-v51/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "830662d66c3030641a9d73c482ab0b67f42b45cf064668ae293966c76e0b825d"
deploy.HELPER_MARKER = "a90_android_execns_probe v51"
deploy.SERVICE_MODE_TOKEN = "wifi-connect-tool-surface"
deploy.DEPLOY_LABEL = "v51"
deploy.DEPLOY_NAME = "execns-helper-v51"
deploy.DEPLOY_PLAN_VERSION = "V499"
deploy.DEPLOY_LOG_PREFIX = "v499"
deploy.SUMMARY_TITLE = "v499 Execns Helper v51 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v499 deploy execns helper v51 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_connect_ping_v499.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v51",
    "wifi-connect-tool-surface",
    "wifi_connect_tool_surface.begin",
    "wifi_connect_tool_surface.strategy=wpa-supplicant-plus-dhcp-plus-ping",
)


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
        args.remote_helper,
        "--helper-sha256",
        args.helper_sha256,
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
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v51 deploy still requires exact approval", "deploy helper v51, then rerun V499 readiness"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v51 already current", "run V499 readiness"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V499 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v499_result and v499_result.get("decision") not in {
        "v499-native-connect-ping-readiness-ready",
        "v499-native-connect-ping-readiness-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V499 preflight decision={v499_result.get('decision')}", "inspect V499 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v51 deployed or already current; V499 readiness was rerun", "complete V497/V498 and then implement approved V500 live connect/DHCP/ping"


deploy.run_v373_preflight = run_v499_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
