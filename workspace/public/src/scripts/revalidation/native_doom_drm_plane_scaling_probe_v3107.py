#!/usr/bin/env python3
"""Build and run V3107 read-only DRM plane scaling probe.

This does not flash or reboot. It builds a static AArch64 helper, installs it
under /cache/bin, runs DRM GETPLANERESOURCES/GETPLANE/property ioctls, and writes
a public redacted report summarizing whether a hardware plane-scaling candidate
is exposed for the active CRTC.
"""

from __future__ import annotations

import argparse
import base64
import json
import lzma
import os
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Any

import native_kernel_timer_object_histogram_v2202 as live_base


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_drm_plane_probe_v3107.c"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/doom"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V3107_DOOM_DRM_PLANE_SCALING_PROBE_2026-06-23.md"
REMOTE_HELPER = "/cache/bin/a90_drm_plane_probe_v3107"
DEFAULT_TOYBOX = "/bin/busybox"
RUN_ID = "V3107"
DECISION_PASS = "v3107-drm-plane-scaling-candidate-live-pass"
DECISION_NO_CANDIDATE = "v3107-no-drm-plane-scaling-candidate"
DECISION_FAILED = "v3107-drm-plane-scaling-probe-failed"

KEY_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.]+)=(?P<value>.*)$", re.MULTILINE)
PLANE_RE = re.compile(r"^plane\.(?P<index>\d+)\.(?P<body>.+)$", re.MULTILINE)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def parse_tokens(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in body.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        result[key] = value
    return result


def parse_probe_stdout(text: str) -> dict[str, Any]:
    values = {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(text)}
    active_body = values.get("probe.active.connector_id")
    if active_body:
        for key, value in parse_tokens(f"connector_id={active_body}").items():
            values[f"probe.active.{key}"] = value
    planes: dict[str, dict[str, str]] = {}
    for match in PLANE_RE.finditer(text):
        index = match.group("index")
        body = match.group("body")
        current = planes.setdefault(index, {})
        if body.startswith("id="):
            current.update(parse_tokens(body))
        elif body.startswith("props."):
            current.update(parse_tokens(body.replace("props.", "props_", 1)))
        elif body.startswith("formats.sample="):
            current["formats_sample"] = body.split("=", 1)[1]

    candidate_count = int(values.get("probe.hw_scale_candidate_count", "0") or "0")
    exposed = values.get("probe.hw_scale.exposed", "0") == "1"
    return {
        "values": values,
        "planes": planes,
        "plane_count": int(values.get("probe.planes.count", "0") or "0"),
        "compatible_plane_count": int(values.get("probe.compatible_plane_count", "0") or "0"),
        "rect_props_plane_count": int(values.get("probe.rect_props_plane_count", "0") or "0"),
        "candidate_count": candidate_count,
        "hw_scale_exposed": exposed,
        "result": values.get("probe.result", ""),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def install_helper(args: argparse.Namespace,
                   out_dir: Path,
                   steps: list[live_base.StepResult],
                   local_binary: Path,
                   summary: dict[str, Any]) -> None:
    if args.device_ip:
        try:
            live_base.install_helper(args, out_dir, steps, "drm-plane-probe-v3107", local_binary, REMOTE_HELPER)
            summary["install_path"] = "bridge-nc"
            return
        except Exception as exc:  # noqa: BLE001 - fallback records the failed transfer mode
            summary["bridge_nc_install_error"] = str(exc)

        try:
            live_base.run_host(
                out_dir,
                steps,
                "install-drm-plane-probe-v3107-tcpctl",
                [
                    sys.executable,
                    str(SCRIPT_DIR / "tcpctl_host.py"),
                    "--bridge-host",
                    args.bridge_host,
                    "--bridge-port",
                    str(args.bridge_port),
                    "--device-ip",
                    args.device_ip,
                    "--device-binary",
                    REMOTE_HELPER,
                    "--toybox",
                    args.toybox,
                    "--connect-timeout",
                    str(args.connect_timeout),
                    "--tcp-timeout",
                    str(max(30.0, args.transfer_timeout)),
                    "--bridge-timeout",
                    str(max(60.0, args.transfer_timeout)),
                    "install",
                    "--local-binary",
                    str(local_binary),
                    "--transfer-port",
                    str(args.transfer_port + 1),
                    "--transfer-delay",
                    str(max(1.0, args.transfer_delay)),
                    "--transfer-timeout",
                    str(args.transfer_timeout),
                    "--install-control-channel",
                    "tcpctl",
                ],
                timeout=args.transfer_timeout + 45,
            )
            summary["install_path"] = "tcpctl"
            return
        except Exception as exc:  # noqa: BLE001 - serial fallback keeps the run moving without NCM
            summary["tcpctl_install_error"] = str(exc)
    else:
        summary["bridge_nc_install_error"] = "skipped: --device-ip not set"
        summary["tcpctl_install_error"] = "skipped: --device-ip not set"

    serial_base64_install_helper(args, out_dir, steps, local_binary, summary)


def serial_base64_install_helper(args: argparse.Namespace,
                                 out_dir: Path,
                                 steps: list[live_base.StepResult],
                                 local_binary: Path,
                                 summary: dict[str, Any]) -> None:
    target_dir = str(Path(REMOTE_HELPER).parent).replace("\\", "/")
    target_name = Path(REMOTE_HELPER).name
    tmp_target = f"{target_dir}/.{target_name}.serial-tmp.{os.getpid()}.{int(time.time())}"
    compressed = lzma.compress(local_binary.read_bytes(), preset=9 | lzma.PRESET_EXTREME)
    encoded = base64.b64encode(compressed).decode("ascii")
    local_hash = live_base.sha256_file(local_binary)
    chunk_size = args.serial_base64_chunk_chars
    if chunk_size <= 0 or chunk_size % 4 != 0:
        raise RuntimeError("--serial-base64-chunk-chars must be a positive multiple of 4")

    tmp_archive = f"{tmp_target}.xz"
    live_base.a90ctl(args, out_dir, steps, "install-drm-plane-probe-v3107-serial-mkdir", ["mkdir", target_dir], timeout=30, allow_error=True)
    live_base.a90ctl(args, out_dir, steps, "install-drm-plane-probe-v3107-serial-cleanup", ["run", args.toybox, "rm", "-f", tmp_target, tmp_archive], timeout=30, allow_error=True)
    for index, offset in enumerate(range(0, len(encoded), chunk_size)):
        chunk = encoded[offset:offset + chunk_size]
        script = (
            f"printf %s {shlex.quote(chunk)} | "
            f"{shlex.quote(args.toybox)} base64 -d >> {shlex.quote(tmp_archive)}"
        )
        live_base.a90ctl(
            args,
            out_dir,
            steps,
            f"install-drm-plane-probe-v3107-serial-chunk-{index:04d}",
            ["run", args.toybox, "sh", "-c", script],
            timeout=args.serial_chunk_timeout,
        )
    live_base.a90ctl(
        args,
        out_dir,
        steps,
        "install-drm-plane-probe-v3107-serial-xzcat",
        ["run", args.toybox, "sh", "-c", f"{shlex.quote(args.toybox)} xzcat {shlex.quote(tmp_archive)} > {shlex.quote(tmp_target)}"],
        timeout=60,
    )
    live_base.a90ctl(args, out_dir, steps, "install-drm-plane-probe-v3107-serial-chmod", ["run", args.toybox, "chmod", "755", tmp_target], timeout=30)
    sha_output = live_base.a90ctl(args, out_dir, steps, "install-drm-plane-probe-v3107-serial-sha", ["run", args.toybox, "sha256sum", tmp_target], timeout=60)
    if local_hash not in sha_output:
        raise RuntimeError(f"serial upload sha mismatch local={local_hash}\n{sha_output}")
    live_base.a90ctl(args, out_dir, steps, "install-drm-plane-probe-v3107-serial-mv", ["run", args.toybox, "mv", "-f", tmp_target, REMOTE_HELPER], timeout=30)
    live_base.a90ctl(args, out_dir, steps, "install-drm-plane-probe-v3107-serial-clean-archive", ["run", args.toybox, "rm", "-f", tmp_archive], timeout=30, allow_error=True)
    summary["install_path"] = "serial-base64"
    summary["serial_base64_chunks"] = (len(encoded) + chunk_size - 1) // chunk_size
    summary["serial_compressed_bytes"] = len(compressed)


def render_report(summary: dict[str, Any]) -> str:
    probe = summary.get("probe") or {}
    values = probe.get("values") or {}
    planes = probe.get("planes") or {}
    build = summary.get("build") or {}
    decision = summary.get("decision")
    exposed = bool(probe.get("hw_scale_exposed"))

    lines = [
        "# Native Init V3107 DOOM DRM Plane Scaling Probe",
        "",
        "- Date: 2026-06-23",
        f"- Cycle: `{RUN_ID}`",
        "- Track: DOOM large-frame scale-path optimization.",
        f"- Decision: `{decision}`",
        "",
        "## Scope",
        "",
        "This was a no-flash live probe on the installed V3104 resident. It",
        "built and installed a temporary read-only helper under `/cache/bin`, then",
        "queried DRM plane resources and plane properties through ioctls. No boot",
        "image was built, flashed, or rebooted.",
        "",
        "## Safety",
        "",
        "- Flash/reboot: `0`",
        "- Partition/firmware writes: `0`",
        "- Display mutation: `0`",
        "- Probe scope: DRM resource/property inventory only.",
        "",
        "## Build",
        "",
        f"- Helper source: `{rel(HELPER_SOURCE)}`",
        f"- Helper SHA-256: `{build.get('helper_sha256', '')}`",
        f"- Helper size: `{build.get('helper_size', 0)}` bytes",
        f"- Install path: `{summary.get('install_path', '')}`",
        "",
        "## Live Result",
        "",
        f"- Resident version check: `{summary.get('version_ok', False)}`",
        f"- Pre selftest fail=0: `{summary.get('pre_selftest_fail0', False)}`",
        f"- Post selftest fail=0: `{summary.get('post_selftest_fail0', False)}`",
        f"- DRM node: `{values.get('probe.node', '/dev/dri/card0')}`",
        f"- Universal planes cap rc: `{values.get('probe.client_cap.universal_planes.rc', '')}`",
        f"- Atomic client cap rc: `{values.get('probe.client_cap.atomic.rc', '')}`",
        f"- Resources: `crtcs={values.get('probe.resources.crtcs', '?')}`",
        f"- Active source: `{values.get('probe.active.source', '')}`",
        f"- Active connector scan rc: `{values.get('probe.active.connector_scan.rc', '')}`",
        f"- Active fallback current-plane rc: `{values.get('probe.active.fallback.current_plane.rc', '')}`",
        f"- Active path: connector=`{values.get('probe.active.connector_id', '')}` "
        f"encoder=`{values.get('probe.active.encoder_id', '')}` "
        f"crtc=`{values.get('probe.active.crtc_id', '')}` "
        f"crtc_index=`{values.get('probe.active.crtc_index', '')}` "
        f"current_plane=`{values.get('probe.active.current_plane_id', '')}`",
        f"- Plane count: `{probe.get('plane_count', 0)}`",
        f"- Compatible active-CRTC planes: `{probe.get('compatible_plane_count', 0)}`",
        f"- Planes with src/dst rectangle properties: `{probe.get('rect_props_plane_count', 0)}`",
        f"- Hardware scale candidate count: `{probe.get('candidate_count', 0)}`",
        f"- Hardware scale exposed: `{1 if exposed else 0}`",
        "",
        "## Plane Summary",
        "",
    ]
    for index in sorted(planes, key=lambda value: int(value)):
        plane = planes[index]
        lines.append(
            f"- plane {index}: id=`{plane.get('id', '')}` "
            f"compatible=`{plane.get('compatible_active_crtc', '')}` "
            f"rect_props=`{plane.get('rect_props', '')}` "
            f"XBGR=`{plane.get('has_xbgr8888', '')}` "
            f"XRGB=`{plane.get('has_xrgb8888', '')}` "
            f"candidate=`{plane.get('candidate', '')}` "
            f"formats=`{plane.get('formats_sample', '')}`"
        )
    if not planes:
        lines.append("- no plane detail was parsed")

    lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    if exposed:
        lines.extend([
            "The device exposes at least one active-CRTC-compatible plane with",
            "source/destination rectangle properties and an RGB8888 format compatible",
            "with the current DOOM frame path. This is enough to proceed to a bounded",
            "visual `drmModeSetPlane`/pageflip experiment for large DOOM scaling, still",
            "without GPU/GL, panel re-init, or power writes.",
        ])
    else:
        lines.extend([
            "The read-only probe did not find an active-CRTC-compatible plane with both",
            "rectangle properties and current RGB8888 formats. The next scale-path",
            "fallback should be a pre-scaled producer or cheaper CPU blit path rather",
            "than spending more time on display-plane scaling.",
        ])
    lines.extend([
        "",
        "## Next Step",
        "",
        "If `Hardware scale exposed` is `1`, implement a bounded V3108 plane-scaling",
        "visual candidate: allocate the DOOM-sized dumb buffer, attach it to the",
        "compatible plane with source 640x400 and destination demo rectangle, then",
        "restore the existing full-screen path on exit. If it is `0`, skip directly",
        "to the pre-scaled-producer fallback.",
        "",
    ])
    return "\n".join(lines)


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = PRIVATE_RUNS / f"v3107-drm-plane-scaling-probe-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[live_base.StepResult] = []
    summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "helper_source": rel(HELPER_SOURCE),
        "remote_helper": REMOTE_HELPER,
        "safety": {
            "flash_reboot": False,
            "partition_or_firmware_write": False,
            "display_mutation": False,
            "drm_read_only_inventory": True,
        },
    }

    try:
        os.environ.setdefault("A90CTL_INPUT_CHAR_DELAY_SEC", "0.25")
        live_base.run_host(out_dir, steps, "bridge-status", [
            sys.executable,
            str(SCRIPT_DIR / "a90_bridge.py"),
            "status",
            "--json",
        ], timeout=30, allow_error=True)
        version = live_base.a90ctl(args, out_dir, steps, "resident-version", ["version"], timeout=90, allow_error=True)
        status = live_base.a90ctl(args, out_dir, steps, "resident-status", ["status"], timeout=90, allow_error=True)
        pre_selftest = live_base.a90ctl(args, out_dir, steps, "resident-selftest", ["selftest"], timeout=90, allow_error=True)
        summary["version_ok"] = "v3104-doomgeneric-paced-tic" in version
        summary["status_ok"] = "fail=0" in status or "selftest: pass=" in status
        summary["pre_selftest_fail0"] = "fail=0" in pre_selftest

        build_dir = out_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        helper_bin = live_base.build_helper(
            build_dir,
            steps,
            source=HELPER_SOURCE,
            output_name="a90_drm_plane_probe_v3107",
            cc=args.cc,
            strip=args.strip,
        )
        summary["build"] = {
            "helper_local": str(helper_bin.relative_to(REPO_ROOT)),
            "helper_sha256": live_base.sha256_file(helper_bin),
            "helper_size": helper_bin.stat().st_size,
        }
        if not args.skip_install:
            install_helper(args, out_dir, steps, helper_bin, summary)

        probe_stdout = live_base.tcpctl_run(
            args,
            out_dir,
            steps,
            "drm-plane-probe-v3107",
            [REMOTE_HELPER],
            timeout=60,
        )
        probe = parse_probe_stdout(probe_stdout)
        summary["probe"] = probe
        post_selftest = live_base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        summary["post_selftest_fail0"] = "fail=0" in post_selftest
        summary["decision"] = DECISION_PASS if probe.get("hw_scale_exposed") else DECISION_NO_CANDIDATE
        summary["pass"] = bool(summary["post_selftest_fail0"] and probe.get("result"))
    except Exception as exc:
        summary["decision"] = DECISION_FAILED
        summary["pass"] = False
        summary["error"] = str(exc)
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [
            {
                "name": step.name,
                "returncode": step.returncode,
                "ok": step.ok,
                "elapsed_sec": step.elapsed_sec,
                "stdout_path": step.stdout_path,
                "stderr_path": step.stderr_path,
            }
            for step in steps
        ]
        write_json(out_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18177)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default=os.environ.get("A90_NCM_DEVICE_IP", ""))
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--serial-base64-chunk-chars", type=int, default=1024)
    parser.add_argument("--serial-chunk-timeout", type=float, default=45.0)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    if args.run_live:
        summary = run_live(args)
    else:
        summary = {
            "run_id": RUN_ID,
            "decision": "v3107-drm-plane-scaling-probe-dry-run",
            "helper_source": rel(HELPER_SOURCE),
            "remote_helper": REMOTE_HELPER,
            "probe": {},
            "build": {},
            "pass": False,
        }

    if args.write_report:
        REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("pass") or not args.run_live else 1


if __name__ == "__main__":
    raise SystemExit(main())
