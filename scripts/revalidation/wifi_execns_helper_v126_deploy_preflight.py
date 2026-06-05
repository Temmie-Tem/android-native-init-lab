#!/usr/bin/env python3
"""V829 execns helper v126 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v829-execns-helper-v126-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v829-execns-helper-v126-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "106d408acf6d48c6a38350756cd921e8ffb8fcc518708855036fd858e79236e2"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v126"
deploy.SERVICE_MODE_TOKEN = "--allow-servloc-domain-list-probe"
deploy.DEPLOY_LABEL = "v126"
deploy.DEPLOY_NAME = "execns-helper-v126"
deploy.DEPLOY_PLAN_VERSION = "V829"
deploy.DEPLOY_LOG_PREFIX = "v829"
deploy.SUMMARY_TITLE = "v829 Execns Helper v126 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v829 deploy execns helper v126 only; "
    "no daemon start and no Wi-Fi bring-up"
)

V829_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py")


def run_v829_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v829-servloc-domain-list-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(V829_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.remote_helper,
        "--helper-sha256",
        args.helper_sha256,
        "--helper-marker",
        deploy.HELPER_MARKER,
        "--local-helper",
        str(args.local_helper),
        "plan",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v829-servloc-domain-list-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v829-servloc-domain-list-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v829_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V829 helper deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V829 helper v126 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V829 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v829_result and v829_result.get("decision") != "v829-servloc-domain-list-probe-plan-ready":
        return (
            f"{deploy.DEPLOY_NAME}-deploy-postflight-review",
            False,
            f"V829 plan decision={v829_result.get('decision')}",
            "inspect helper v126 post-deploy V829 plan output",
        )
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v126 deployed or already current; V829 plan was rerun", "run V829 bounded service-locator probe"


deploy.run_v373_preflight = run_v829_plan
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
