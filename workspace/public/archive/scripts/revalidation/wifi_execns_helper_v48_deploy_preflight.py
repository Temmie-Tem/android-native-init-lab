#!/usr/bin/env python3
"""V490 execns helper v48 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V490 deploy approval phrase. It does not load SELinux policy, reexec
init, start service-manager, start Wi-Fi HAL/CNSS, scan/connect, or Wi-Fi
bring-up.
"""

from __future__ import annotations

import wifi_execns_helper_v33_deploy_preflight as v33
import wifi_execns_helper_v47_deploy_preflight as v47


deploy = v47.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v490-execns-helper-v48-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v490-a90_android_execns_probe-v48/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "5bc491c7ed0c4da498c6ee16568004dd886df577edd5f8cbebd50fb0740db10c"
deploy.HELPER_MARKER = "a90_android_execns_probe v48"
deploy.SERVICE_MODE_TOKEN = "sepolicy-load-proof"
deploy.DEPLOY_LABEL = "v48"
deploy.DEPLOY_NAME = "execns-helper-v48"
deploy.DEPLOY_PLAN_VERSION = "V490"
deploy.DEPLOY_LOG_PREFIX = "v490"
deploy.SUMMARY_TITLE = "v490 Execns Helper v48 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v490 deploy execns helper v48 only; "
    "no policy load, no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_selinux_policy_load_proof_v490.py")

v33.V33_TOKENS = (
    "a90_android_execns_probe v48",
    "sepolicy-load-proof",
    "--allow-policy-load-proof",
    "sepolicy_load.begin",
    "sepolicy_load.policy_load_attempted=0",
)


def run_v490_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v490-selinux-policy-load-proof-preflight")
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
    store.write_text("host/v490-selinux-policy-load-proof-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v490-selinux-policy-load-proof-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v490_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"

    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v48 deploy still requires exact approval", "deploy helper v48, then run V490 policy-load proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v48 already current", "run V490 policy-load proof"

    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V490 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v490_result and not v490_result.get("pass"):
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V490 preflight decision={v490_result.get('decision')}", "inspect V490 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v48 deployed or already current; V490 preflight is ready", "run approved V490 SELinux policy-load proof"


deploy.run_v373_preflight = run_v490_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
