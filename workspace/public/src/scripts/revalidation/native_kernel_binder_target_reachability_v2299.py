#!/usr/bin/env python3
"""Build and optionally run the Binder BB-T target reachability helper.

Default behavior is build-only. The live BB-T path is gated by an exact
confirmation phrase and performs only a two-process, one-way, zero-object
Binder transaction to prove target reachability. It does not send malformed
objects, does not use BC_FREE_BUFFER, does not send replies, and does not
attempt a UAF trigger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

import a90_ncm_transport as ncm
import a90ctl


REPO_ROOT = Path(__file__).resolve().parents[5]
HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_binder_target_bbt.c"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/security"
REMOTE_HELPER = "/cache/bin/a90_binder_target_bbt"
REMOTE_OUTPUT = "/cache/a90-binder-bbt.out"
REMOTE_DEVNODE = "/dev/binder"
BBT_CONFIRMATION = (
    "Stage B-Binder BB-T go: one-shot well-formed Binder target reachability "
    "on v2237, no malformed objects, no UAF trigger, no retry"
)

FORBIDDEN_HELPER_TOKENS = [
    "BINDER_SET_CONTEXT_MGR_EXT",
    "BC_TRANSACTION_SG",
    "BC_REPLY",
    "BC_REPLY_SG",
    "BC_FREE_BUFFER",
    "BC_ACQUIRE",
    "BC_RELEASE",
    "BC_INCREFS",
    "BC_DECREFS",
    "BC_REQUEST_DEATH_NOTIFICATION",
    "BC_CLEAR_DEATH_NOTIFICATION",
    "BINDER_TYPE_",
    "flat_binder_object",
]


class EvidenceStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        (run_dir / "logs/host").mkdir(parents=True, exist_ok=True)
        (run_dir / "logs/device").mkdir(parents=True, exist_ok=True)

    def write_text(self, relative_path: str, text: str) -> Path:
        path = self.run_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", errors="replace")
        return path

    def write_log(self, namespace: str, name: str, text: str) -> Path:
        return self.write_text(f"logs/{namespace}/{name}", text)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def label_now() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def record_step(store: EvidenceStore,
                steps: list[dict[str, Any]],
                *,
                name: str,
                command: list[object],
                rc: int | None,
                ok: bool,
                stdout: str = "",
                stderr: str = "",
                timeout: bool = False,
                namespace: str = "host") -> dict[str, Any]:
    stdout_path = store.write_log(namespace, f"{name}.stdout.txt", stdout)
    stderr_path = store.write_log(namespace, f"{name}.stderr.txt", stderr)
    step = {
        "name": name,
        "command": [str(item) for item in command],
        "started": utc_now(),
        "ended": utc_now(),
        "timeout": timeout,
        "rc": rc,
        "ok": ok,
        "stdout_file": str(stdout_path.relative_to(store.run_dir)),
        "stderr_file": str(stderr_path.relative_to(store.run_dir)),
    }
    steps.append(step)
    return step


def run_host(store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[object],
             *,
             timeout: float = 120.0,
             allow_error: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        record_step(
            store,
            steps,
            name=name,
            command=command,
            rc=completed.returncode,
            ok=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        record_step(
            store,
            steps,
            name=name,
            command=command,
            rc=None,
            ok=False,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timeout=True,
        )
        raise
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(f"{name} failed rc={completed.returncode}")
    return completed


def run_a90(args: argparse.Namespace,
            store: EvidenceStore,
            steps: list[dict[str, Any]],
            name: str,
            command: list[str],
            *,
            timeout: float = 12.0,
            allow_error: bool = False) -> dict[str, Any]:
    try:
        result = a90ctl.run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            timeout,
            command,
            retry_unsafe=False,
        )
        ok = result.rc == 0
        step = record_step(
            store,
            steps,
            name=name,
            command=["a90ctl", *command],
            rc=result.rc,
            ok=ok,
            stdout=result.text,
            namespace="device",
        )
        step["protocol"] = {"begin": result.begin, "end": result.end, "status": result.status}
        if result.rc != 0 and not allow_error:
            raise RuntimeError(f"{name} failed rc={result.rc}")
        return {**step, "stdout": result.text, "stderr": "", "fields": parse_key_values(result.text)}
    except Exception as exc:
        step = record_step(
            store,
            steps,
            name=name,
            command=["a90ctl", *command],
            rc=None,
            ok=False,
            stderr=str(exc),
            namespace="device",
        )
        if not allow_error:
            raise
        return {**step, "stdout": "", "stderr": str(exc), "fields": {}}


def ncm_run_step(args: argparse.Namespace):
    def _run_step(store: EvidenceStore,
                  steps: list[dict[str, Any]],
                  name: str,
                  command: list[str],
                  *,
                  timeout: float = 12.0,
                  bridge_timeout: float = 10.0) -> dict[str, Any]:
        return run_a90(
            args,
            store,
            steps,
            name,
            command,
            timeout=max(timeout, bridge_timeout),
            allow_error=True,
        )

    return _run_step


def scan_helper_source(store: EvidenceStore,
                       steps: list[dict[str, Any]]) -> dict[str, Any]:
    source = HELPER_SOURCE.read_text(encoding="utf-8", errors="replace")
    matches = [token for token in FORBIDDEN_HELPER_TOKENS if token in source]
    result = {
        "forbidden_tokens": matches,
        "ok": not matches,
    }
    record_step(
        store,
        steps,
        name="scan-helper-source",
        command=["python", "scan-helper-source"],
        rc=0 if result["ok"] else 1,
        ok=bool(result["ok"]),
        stdout=json.dumps(result, indent=2, sort_keys=True) + "\n",
    )
    if matches:
        raise RuntimeError(f"helper contains forbidden Binder tokens: {matches}")
    return result


def build_helper(args: argparse.Namespace,
                 store: EvidenceStore,
                 steps: list[dict[str, Any]]) -> Path:
    output = store.run_dir / "a90_binder_target_bbt"
    run_host(
        store,
        steps,
        "build-helper",
        [
            args.cc,
            "-static",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            output,
            HELPER_SOURCE,
        ],
    )
    run_host(store, steps, "strip-helper", [args.strip, output])
    run_host(store, steps, "file-helper", ["file", output])
    return output


def require_confirmation(args: argparse.Namespace) -> None:
    if not args.run_live:
        return
    if args.confirm != BBT_CONFIRMATION:
        raise RuntimeError(
            "refusing live BB-T run: exact confirmation phrase required:\n"
            f"{BBT_CONFIRMATION}"
        )


def selftest_ok(text: str) -> bool:
    return "fail=0" in text or " selftest.fail=0" in text


def preflight(args: argparse.Namespace,
              store: EvidenceStore,
              steps: list[dict[str, Any]]) -> None:
    version = run_a90(args, store, steps, "preflight-version", ["version"], timeout=10)
    if "0.9.268" not in version["stdout"] or "v2237" not in version["stdout"]:
        raise RuntimeError("resident baseline is not v2237 / 0.9.268; refusing BB-T")
    run_a90(args, store, steps, "preflight-status", ["status"], timeout=10)
    selftest = run_a90(args, store, steps, "preflight-selftest", ["selftest", "verbose"], timeout=20)
    if not selftest_ok(selftest["stdout"]):
        raise RuntimeError("preflight selftest did not report fail=0")


def shell_quote_script(script: str) -> list[str]:
    return ["run", "/cache/bin/busybox", "sh", "-c", script]


def live_bbt(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             local_helper: Path,
             helper_sha256: str) -> dict[str, Any]:
    preflight(args, store, steps)
    run_a90(
        args,
        store,
        steps,
        "dmesg-before",
        shell_quote_script("/cache/bin/busybox dmesg | /cache/bin/busybox tail -n 180"),
        timeout=15,
        allow_error=True,
    )

    devnode_probe = run_a90(
        args,
        store,
        steps,
        "devnode-precheck",
        shell_quote_script(
            "if [ -e /dev/binder ]; then "
            "echo bbt.devnode_preexisting=1; /cache/bin/busybox ls -l /dev/binder; "
            "else echo bbt.devnode_preexisting=0; fi"
        ),
        timeout=10,
        allow_error=True,
    )
    if "bbt.devnode_preexisting=1" in devnode_probe["stdout"]:
        return {"decision": "bbt-aborted-devnode-preexisting", "ok": False}

    created_devnode = False
    try:
        make_node = run_a90(
            args,
            store,
            steps,
            "devnode-create",
            shell_quote_script(
                f"/cache/bin/busybox mknod {shlex.quote(REMOTE_DEVNODE)} c 10 81 && "
                f"/cache/bin/busybox chmod 600 {shlex.quote(REMOTE_DEVNODE)} && "
                f"/cache/bin/busybox ls -l {shlex.quote(REMOTE_DEVNODE)}"
            ),
            timeout=10,
            allow_error=True,
        )
        created_devnode = make_node.get("rc") == 0 or "crw" in make_node["stdout"]
        if not created_devnode:
            return {"decision": "bbt-devnode-create-failed", "ok": False}

        transfer = ncm.FastTransferSession(
            store,
            steps,
            run_step=ncm_run_step(args),
            enabled=not args.no_fast_transfer,
        )
        try:
            transfer_result = transfer.transfer_file(
                label="bbt-helper",
                local_path=local_helper,
                remote_path=REMOTE_HELPER,
                expected_sha256=helper_sha256,
                mode="700",
            )
        finally:
            transfer.close()
        if not transfer_result.get("ok"):
            return {"decision": "bbt-helper-transfer-failed", "ok": False, "transfer": transfer_result}

        remote_script = (
            f"OUT={shlex.quote(REMOTE_OUTPUT)}; "
            f"rm -f \"$OUT\"; "
            f"{shlex.quote(REMOTE_HELPER)} --path {shlex.quote(REMOTE_DEVNODE)} "
            "--length 1048576 >\"$OUT\" 2>&1 & "
            "pid=$!; i=0; timed_out=0; "
            "while /cache/bin/busybox kill -0 \"$pid\" 2>/dev/null; do "
            "if [ \"$i\" -ge 10 ]; then timed_out=1; echo bbt.runner_timeout=1; "
            "/cache/bin/busybox kill -9 \"$pid\" 2>/dev/null; break; fi; "
            "i=$((i+1)); /cache/bin/busybox sleep 1; "
            "done; "
            "wait \"$pid\" 2>/dev/null; rc=$?; "
            "cat \"$OUT\" 2>/dev/null; "
            "echo bbt.runner_elapsed_sec=$i; "
            "echo bbt.runner_timeout=$timed_out; "
            "echo bbt.runner_rc=$rc; "
            "exit \"$rc\""
        )
        helper_run = run_a90(
            args,
            store,
            steps,
            "bbt-helper-run",
            shell_quote_script(remote_script),
            timeout=30,
            allow_error=True,
        )
        fields = parse_key_values(helper_run["stdout"])
        return {
            "decision": fields.get("bbt.decision") or "bbt-helper-no-decision",
            "ok": fields.get("bbt.decision") == "bbt-target-ok",
            "fields": fields,
            "helper_rc": helper_run.get("rc"),
        }
    finally:
        cleanup_script = f"/cache/bin/busybox rm -f {shlex.quote(REMOTE_HELPER)} {shlex.quote(REMOTE_OUTPUT)}"
        if created_devnode:
            cleanup_script += f" {shlex.quote(REMOTE_DEVNODE)}"
        run_a90(args, store, steps, "cleanup", shell_quote_script(cleanup_script), timeout=10, allow_error=True)
        run_a90(
            args,
            store,
            steps,
            "dmesg-after",
            shell_quote_script("/cache/bin/busybox dmesg | /cache/bin/busybox tail -n 180"),
            timeout=15,
            allow_error=True,
        )
        post_selftest = run_a90(
            args,
            store,
            steps,
            "post-selftest",
            ["selftest", "verbose"],
            timeout=20,
            allow_error=True,
        )
        if not selftest_ok(post_selftest["stdout"]):
            store.write_text("post_selftest_failed.txt", post_selftest["stdout"])


def write_summary(store: EvidenceStore,
                  steps: list[dict[str, Any]],
                  *,
                  args: argparse.Namespace,
                  helper_path: Path,
                  helper_sha256: str,
                  scan_result: dict[str, Any],
                  live_result: dict[str, Any] | None) -> dict[str, Any]:
    summary = {
        "decision": "v2299-binder-bbt-helper-built-not-run",
        "run_live": args.run_live,
        "helper_source": str(HELPER_SOURCE.relative_to(REPO_ROOT)),
        "helper_binary_private": str(helper_path.relative_to(REPO_ROOT)),
        "helper_sha256": helper_sha256,
        "remote_helper": REMOTE_HELPER,
        "remote_devnode": REMOTE_DEVNODE,
        "bbt_confirmation_required": BBT_CONFIRMATION,
        "scan_result": scan_result,
        "hard_stops": [
            "no malformed objects",
            "no BC_TRANSACTION_SG",
            "no BC_REPLY",
            "no BC_FREE_BUFFER",
            "no BINDER_SET_CONTEXT_MGR_EXT",
            "no heap spray",
            "no UAF trigger",
            "no retry",
        ],
        "steps": steps,
    }
    if live_result is not None:
        summary["live_result"] = live_result
        summary["decision"] = str(live_result.get("decision") or "v2299-binder-bbt-live-unknown")
    store.write_text("summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true", help="run the live BB-T target gate")
    parser.add_argument("--confirm", default="", help="exact BB-T confirmation phrase for --run-live")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--no-fast-transfer", action="store_true", help="disable NCM helper transfer")
    args = parser.parse_args()

    require_confirmation(args)
    out_dir = args.out_dir or PRIVATE_RUNS / f"v2299-binder-bbt-target-{label_now()}"
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []

    scan_result = scan_helper_source(store, steps)
    helper = build_helper(args, store, steps)
    helper_sha = sha256_file(helper)
    live_result = live_bbt(args, store, steps, helper, helper_sha) if args.run_live else None
    summary = write_summary(
        store,
        steps,
        args=args,
        helper_path=helper,
        helper_sha256=helper_sha,
        scan_result=scan_result,
        live_result=live_result,
    )
    print(json.dumps({
        "decision": summary["decision"],
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "run_live": args.run_live,
        "helper_sha256": helper_sha,
    }, indent=2, sort_keys=True))
    return 0 if not args.run_live or bool((live_result or {}).get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
