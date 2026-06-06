#!/usr/bin/env python3
"""V487 execns helper v45 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V487 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v44_deploy_preflight as v44


deploy = v44.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v487-execns-helper-v45-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v487-a90_android_execns_probe-v45/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "387b4f10a3f6e11805b1680cdf18f25f3be8b939826739e06edc7ea6b3c07770"
deploy.HELPER_MARKER = "a90_android_execns_probe v45"
deploy.SERVICE_MODE_TOKEN = "selinux-domain-proof"
deploy.DEPLOY_LABEL = "v45"
deploy.DEPLOY_NAME = "execns-helper-v45"
deploy.DEPLOY_PLAN_VERSION = "V487"
deploy.DEPLOY_LOG_PREFIX = "v487"
deploy.SUMMARY_TITLE = "v487 Execns Helper v45 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v487 deploy execns helper v45 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_selinux_init_handoff_v487.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v45",
    "selinux-domain-proof",
    "--selinux-print-current",
    "selinux_postexec_static.current",
    "postexec.match",
)


def run_v487_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v487-selinux-init-handoff-preflight")
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
    store.write_text("host/v487-selinux-init-handoff-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v487-selinux-init-handoff-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v487_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(
            check.severity == "deploy" and check.status != "pass"
            for check in checks
        )
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v45 deploy still requires exact approval", "deploy helper v45, then run V487 proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v45 already current", "run V487 proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V487 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v487_result and not v487_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V487 preflight decision={v487_result.get('decision')}", "inspect V487 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v45 deployed or already current; V487 preflight is ready", "run approved V487 static SELinux postexec proof"


deploy.run_v373_preflight = run_v487_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
