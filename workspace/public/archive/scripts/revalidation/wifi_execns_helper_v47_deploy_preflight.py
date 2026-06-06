#!/usr/bin/env python3
"""V489 execns helper v47 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V489 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v46_deploy_preflight as v46


deploy = v46.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v489-execns-helper-v47-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v489-a90_android_execns_probe-v47/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "ee49f2b762081c3d617cf84f957080846c8c003ef1ea08836772ae21d7149efb"
deploy.HELPER_MARKER = "a90_android_execns_probe v47"
deploy.SERVICE_MODE_TOKEN = "sepolicy-compile-proof"
deploy.DEPLOY_LABEL = "v47"
deploy.DEPLOY_NAME = "execns-helper-v47"
deploy.DEPLOY_PLAN_VERSION = "V489"
deploy.DEPLOY_LOG_PREFIX = "v489"
deploy.SUMMARY_TITLE = "v489 Execns Helper v47 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v489 deploy execns helper v47 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_selinux_compile_proof_v489.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v47",
    "sepolicy-compile-proof",
    "sepolicy_compile.begin",
    "sepolicy_compile.policy_load_executed=0",
    "sepolicy_compile.result",
)


def run_v489_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v489-selinux-compile-proof-preflight")
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
    store.write_text("host/v489-selinux-compile-proof-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v489-selinux-compile-proof-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v489_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v47 deploy still requires exact approval", "deploy helper v47, then run V489 compile proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v47 already current", "run V489 compile proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V489 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v489_result and not v489_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V489 preflight decision={v489_result.get('decision')}", "inspect V489 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v47 deployed or already current; V489 preflight is ready", "run approved V489 SELinux compile proof"


deploy.run_v373_preflight = run_v489_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
