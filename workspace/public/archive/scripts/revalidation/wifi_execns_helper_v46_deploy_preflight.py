#!/usr/bin/env python3
"""V488 execns helper v46 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V488 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v45_deploy_preflight as v45


deploy = v45.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v488-execns-helper-v46-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v488-a90_android_execns_probe-v46/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "81a205579fada4d286eb4cac751a378c09a46757eb39aed593176cbead12ef24"
deploy.HELPER_MARKER = "a90_android_execns_probe v46"
deploy.SERVICE_MODE_TOKEN = "sepolicy-inventory"
deploy.DEPLOY_LABEL = "v46"
deploy.DEPLOY_NAME = "execns-helper-v46"
deploy.DEPLOY_PLAN_VERSION = "V488"
deploy.DEPLOY_LOG_PREFIX = "v488"
deploy.SUMMARY_TITLE = "v488 Execns Helper v46 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v488 deploy execns helper v46 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_selinux_policy_inventory_v488.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v46",
    "sepolicy-inventory",
    "sepolicy_inventory.begin",
    "sepolicy.hash.%s.match",
    "sepolicy_inventory.compile_inputs_present",
)


def run_v488_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v488-selinux-policy-inventory-preflight")
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
    store.write_text("host/v488-selinux-policy-inventory-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v488-selinux-policy-inventory-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v488_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v46 deploy still requires exact approval", "deploy helper v46, then run V488 inventory"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v46 already current", "run V488 inventory"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V488 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v488_result and not v488_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V488 preflight decision={v488_result.get('decision')}", "inspect V488 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v46 deployed or already current; V488 preflight is ready", "run approved V488 SELinux policy inventory"


deploy.run_v373_preflight = run_v488_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
