#!/usr/bin/env python3
"""V497 execns helper v50 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V497 deploy approval phrase. It does not load SELinux policy, start
service-manager, start Wi-Fi HAL/CNSS, connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v49_deploy_preflight as v49


deploy = v49.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v497-execns-helper-v50-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v497-a90_android_execns_probe-v50/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "265ce1d7ebdc2fae4be071e903134feaed8929eb65bb65f5de7198c690c6a48f"
deploy.HELPER_MARKER = "a90_android_execns_probe v50"
deploy.SERVICE_MODE_TOKEN = "wifi-active-session-scan-only"
deploy.DEPLOY_LABEL = "v50"
deploy.DEPLOY_NAME = "execns-helper-v50"
deploy.DEPLOY_PLAN_VERSION = "V497"
deploy.DEPLOY_LOG_PREFIX = "v497"
deploy.SUMMARY_TITLE = "v497 Execns Helper v50 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v497 deploy execns helper v50 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_scan_only_surface_v497.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v50",
    "wifi-active-session-scan-only",
    "--allow-scan-only",
    "wifi_scan_only.begin",
    "wifi_scan_only.raw_results_redacted=1",
)


def run_v497_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v497-scan-only-preflight")
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
    store.write_text("host/v497-scan-only-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v497-scan-only-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "reason": manifest.get("reason", ""),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v497_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v50 deploy still requires exact approval", "deploy helper v50, then rerun V497 preflight after V496 contract-ready"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v50 already current", "run V497 after V496 contract-ready"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V497 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v497_result and v497_result.get("decision") not in {
        "v497-native-scan-only-preflight-ready",
        "v497-native-scan-only-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V497 preflight decision={v497_result.get('decision')}", "inspect V497 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v50 deployed or already current; V497 helper preflight was rerun", "run V490-V496 chain, then approved V497 scan-only proof"


deploy.run_v373_preflight = run_v497_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
