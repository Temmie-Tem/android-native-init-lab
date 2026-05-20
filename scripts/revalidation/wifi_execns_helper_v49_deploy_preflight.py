#!/usr/bin/env python3
"""V495 execns helper v49 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V495 deploy approval phrase. It does not load SELinux policy, reexec
init, start daemon/HAL/CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v48_deploy_preflight as v48


deploy = v48.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v495-execns-helper-v49-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v495-a90_android_execns_probe-v49/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "1faae7fd5e27e8aa302c62640588991177ec95d3c942e102fae845c9f89dfa89"
deploy.HELPER_MARKER = "a90_android_execns_probe v49"
deploy.SERVICE_MODE_TOKEN = "wifi-active-session-surface"
deploy.DEPLOY_LABEL = "v49"
deploy.DEPLOY_NAME = "execns-helper-v49"
deploy.DEPLOY_PLAN_VERSION = "V495"
deploy.DEPLOY_LOG_PREFIX = "v495"
deploy.SUMMARY_TITLE = "v495 Execns Helper v49 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v495 deploy execns helper v49 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_active_session_surface_v495.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v49",
    "wifi-active-session-surface",
    "--allow-iwifi-start-only",
    "wifi_active_session.begin",
    "wifi_active_session.cleanup_attempted=1",
)


def run_v495_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v495-active-session-preflight")
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
    store.write_text("host/v495-active-session-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v495-active-session-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "reason": manifest.get("reason", ""),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v495_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v49 deploy still requires exact approval", "deploy helper v49, then rerun V495 preflight after V494 contract-ready"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v49 already current", "run V495 after V494 contract-ready"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V495 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v495_result and v495_result.get("decision") not in {
        "v495-native-active-session-preflight-ready",
        "v495-native-active-session-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V495 preflight decision={v495_result.get('decision')}", "inspect V495 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v49 deployed or already current; V495 helper preflight was rerun", "run V490/V491/V492/V493/V494, then approved V495 active-session proof"


deploy.run_v373_preflight = run_v495_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
