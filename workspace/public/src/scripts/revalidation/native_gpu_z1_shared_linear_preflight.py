#!/usr/bin/env python3
"""Run V3323 GPU Z1 DRM msm shared-linear allocation preflight.

This is a no-flash, no-present probe. It builds a temporary static AArch64
helper, installs it under /cache/bin, and checks whether /dev/dri/card0 can
allocate a scanout-capable msm GEM buffer, mmap it, PRIME export/import it, and
accept it as an XBGR8888 KMS framebuffer without modesetting or presenting.
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
HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_drm_msm_shared_linear_probe_z1.c"
GPU_SOURCE = REPO_ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
KMS_SOURCE = REPO_ROOT / "workspace/public/src/native-init/a90_kms.c"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/gpu"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V3323_GPU_Z1_SHARED_LINEAR_PREFLIGHT_2026-06-27.md"
REMOTE_HELPER = "/cache/bin/a90_drm_msm_shared_linear_probe_z1"
DEFAULT_TOYBOX = "/bin/busybox"
RUN_ID = "V3323"
DECISION_DRY_RUN = "v3323-gpu-z1-shared-linear-preflight-dry-run"
DECISION_PASS_IOVA = "v3323-z1-drm-msm-shared-linear-preflight-pass-with-iova"
DECISION_PASS_NO_IOVA = "v3323-z1-drm-msm-shared-linear-preflight-pass-no-iova"
DECISION_PARTIAL = "v3323-z1-drm-msm-shared-linear-preflight-partial"
DECISION_FAILED = "v3323-z1-drm-msm-shared-linear-preflight-failed"

KEY_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.]+)=(?P<value>.*)$", re.MULTILINE)


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


def parse_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return int(stripped, 0)
    except ValueError:
        return default


def clean_resident_version(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("version: ") or line.startswith("A90 Linux init "):
            return line.strip()
    return text.strip().splitlines()[0] if text.strip() else ""


def parse_probe_stdout(text: str) -> dict[str, Any]:
    values = {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(text)}
    fields: dict[str, str] = {}

    for line in text.splitlines():
        if not line.startswith("probe."):
            continue
        if line.startswith("probe.mmap.sample "):
            values["probe.mmap.sample"] = line[len("probe.mmap.sample "):]
            fields.update({
                f"probe.mmap.sample.{key}": value
                for key, value in parse_tokens(line[len("probe.mmap.sample "):]).items()
            })
            continue
        first, *rest = line.split()
        if "=" not in first:
            continue
        first_key, first_value = first.split("=", 1)
        values[first_key] = first_value
        if first_key.startswith("probe.cleanup."):
            prefix = "probe.cleanup"
        else:
            prefix = first_key.rsplit(".", 1)[0]
        for key, value in parse_tokens(" ".join(rest)).items():
            fields[f"{prefix}.{key}"] = value

    result = values.get("probe.result", "")
    rc_iova = parse_int(values.get("probe.msm_gem_info.iova.rc"), -9999)
    if result == "z1-drm-msm-shared-linear-preflight-pass":
        decision = DECISION_PASS_IOVA if rc_iova == 0 else DECISION_PASS_NO_IOVA
    elif result:
        decision = DECISION_PARTIAL
    else:
        decision = DECISION_FAILED

    return {
        "stdout": text,
        "values": values,
        "fields": fields,
        "result": result,
        "decision": decision,
        "gem_new_ok": parse_int(values.get("probe.msm_gem_new.rc"), -1) == 0,
        "offset_ok": parse_int(values.get("probe.msm_gem_info.offset.rc"), -1) == 0,
        "iova_ok": rc_iova == 0,
        "mmap_ok": parse_int(values.get("probe.mmap.rc"), -1) == 0,
        "prime_export_ok": parse_int(values.get("probe.prime.export.rc"), -1) == 0,
        "prime_import_ok": parse_int(values.get("probe.prime.import.rc"), -1) == 0,
        "addfb2_ok": parse_int(values.get("probe.addfb2.rc"), -1) == 0,
        "rmfb_ok": parse_int(values.get("probe.cleanup.rmfb.rc"), -1) == 0,
        "close_handle_ok": parse_int(fields.get("probe.cleanup.close_handle.rc"), -1) == 0,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def serial_base64_install_helper(args: argparse.Namespace,
                                 out_dir: Path,
                                 steps: list[live_base.StepResult],
                                 local_binary: Path,
                                 summary: dict[str, Any]) -> None:
    target_dir = str(Path(REMOTE_HELPER).parent).replace("\\", "/")
    target_name = Path(REMOTE_HELPER).name
    tmp_target = f"{target_dir}/.{target_name}.serial-tmp.{os.getpid()}.{int(time.time())}"
    tmp_archive = f"{tmp_target}.xz"
    compressed = lzma.compress(local_binary.read_bytes(), preset=9 | lzma.PRESET_EXTREME)
    encoded = base64.b64encode(compressed).decode("ascii")
    local_hash = live_base.sha256_file(local_binary)
    chunk_size = args.serial_base64_chunk_chars
    if chunk_size <= 0 or chunk_size % 4 != 0:
        raise RuntimeError("--serial-base64-chunk-chars must be a positive multiple of 4")

    live_base.a90ctl(args, out_dir, steps, "install-z1-shared-linear-serial-mkdir", ["mkdir", target_dir], timeout=30, allow_error=True)
    live_base.a90ctl(args, out_dir, steps, "install-z1-shared-linear-serial-cleanup", ["run", args.toybox, "rm", "-f", tmp_target, tmp_archive], timeout=30, allow_error=True)
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
            f"install-z1-shared-linear-serial-chunk-{index:04d}",
            ["run", args.toybox, "sh", "-c", script],
            timeout=args.serial_chunk_timeout,
        )
    live_base.a90ctl(
        args,
        out_dir,
        steps,
        "install-z1-shared-linear-serial-xzcat",
        ["run", args.toybox, "sh", "-c", f"{shlex.quote(args.toybox)} xzcat {shlex.quote(tmp_archive)} > {shlex.quote(tmp_target)}"],
        timeout=60,
    )
    live_base.a90ctl(args, out_dir, steps, "install-z1-shared-linear-serial-chmod", ["run", args.toybox, "chmod", "755", tmp_target], timeout=30)
    sha_output = live_base.a90ctl(args, out_dir, steps, "install-z1-shared-linear-serial-sha", ["run", args.toybox, "sha256sum", tmp_target], timeout=60)
    if local_hash not in sha_output:
        raise RuntimeError(f"serial upload sha mismatch local={local_hash}\n{sha_output}")
    live_base.a90ctl(args, out_dir, steps, "install-z1-shared-linear-serial-mv", ["run", args.toybox, "mv", "-f", tmp_target, REMOTE_HELPER], timeout=30)
    live_base.a90ctl(args, out_dir, steps, "install-z1-shared-linear-serial-clean-archive", ["run", args.toybox, "rm", "-f", tmp_archive], timeout=30, allow_error=True)
    summary["install_path"] = "serial-base64"
    summary["serial_base64_chunks"] = (len(encoded) + chunk_size - 1) // chunk_size
    summary["serial_compressed_bytes"] = len(compressed)


def install_helper(args: argparse.Namespace,
                   out_dir: Path,
                   steps: list[live_base.StepResult],
                   local_binary: Path,
                   summary: dict[str, Any]) -> None:
    if args.device_ip:
        try:
            live_base.install_helper(args, out_dir, steps, "gpu-z1-shared-linear-probe", local_binary, REMOTE_HELPER)
            summary["install_path"] = "bridge-nc"
            return
        except Exception as exc:  # noqa: BLE001 - serial fallback keeps the no-flash run usable
            summary["bridge_nc_install_error"] = str(exc)
    else:
        summary["bridge_nc_install_error"] = "skipped: --device-ip not set"
    serial_base64_install_helper(args, out_dir, steps, local_binary, summary)


def render_report(summary: dict[str, Any]) -> str:
    probe = summary.get("probe") or {}
    values = probe.get("values") or {}
    fields = probe.get("fields") or {}
    build = summary.get("build") or {}
    decision = summary.get("decision", probe.get("decision", DECISION_DRY_RUN))

    lines = [
        "# Native Init V3323 GPU Z1 Shared Linear Preflight",
        "",
        "- Date: 2026-06-27",
        f"- Cycle: `{RUN_ID}`",
        "- Track: GPU rung ④ zero-copy KMS/dmabuf scanout.",
        f"- Decision: `{decision}`",
        "",
        "## Scope",
        "",
        "This was a no-flash Z1 allocator-bridge preflight. It built a temporary",
        "static AArch64 helper, installed it under `/cache/bin`, then checked whether",
        "`/dev/dri/card0` can allocate one msm DRM GEM buffer with",
        "`MSM_BO_SCANOUT | MSM_BO_WC`, mmap it, PRIME export/import it, and create",
        "an `XBGR8888` KMS framebuffer object from it. The helper creates no CRTC",
        "state, performs no pageflip, and does not present the framebuffer.",
        "",
        "## Safety",
        "",
        "- Flash/reboot: `0`",
        "- Partition/firmware writes: `0`",
        "- Display mutation: `0` (FB object creation/removal only; no present/modeset/pageflip)",
        "- PMIC/GDSC/regulator/GPIO/backlight writes: `0`",
        "- Probe scope: DRM allocation/import/export metadata only.",
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
        f"- Resident version: `{clean_resident_version(summary.get('resident_version', ''))}`",
        f"- Pre selftest fail=0: `{summary.get('pre_selftest_fail0', False)}`",
        f"- Post selftest fail=0: `{summary.get('post_selftest_fail0', False)}`",
        f"- DRM node: `{values.get('probe.node', '/dev/dri/card0')}`",
        f"- Target: `{values.get('probe.target.width', '')}`x`{fields.get('probe.target.height', '')}` "
        f"stride=`{fields.get('probe.target.stride', '')}` bytes=`{fields.get('probe.target.bytes', '')}` "
        f"format=`{fields.get('probe.target.format', '')}` flags=`{fields.get('probe.target.flags', '')}`",
        f"- Dumb-buffer cap: `{values.get('probe.cap.dumb_buffer', '')}`",
        f"- ADD_FB2 modifiers cap: `{values.get('probe.cap.addfb2_modifiers', '')}`",
        f"- PRIME cap: `{values.get('probe.cap.prime', '')}` "
        f"import=`{fields.get('probe.cap.import', '')}` export=`{fields.get('probe.cap.export', '')}`",
        f"- MSM GEM new: rc=`{values.get('probe.msm_gem_new.rc', '')}` handle=`{fields.get('probe.msm_gem_new.handle', '')}` "
        f"flags=`{fields.get('probe.msm_gem_new.flags', '')}`",
        f"- GEM offset: rc=`{values.get('probe.msm_gem_info.offset.rc', '')}` value=`{fields.get('probe.msm_gem_info.offset.value', '')}`",
        f"- GEM IOVA: rc=`{values.get('probe.msm_gem_info.iova.rc', '')}` value=`{fields.get('probe.msm_gem_info.iova.value', '')}`",
        f"- GEM flags: rc=`{values.get('probe.msm_gem_info.flags.rc', '')}` value=`{fields.get('probe.msm_gem_info.flags.value', '')}`",
        f"- mmap: rc=`{values.get('probe.mmap.rc', '')}` sample=`{values.get('probe.mmap.sample', '')}`",
        f"- PRIME export: rc=`{values.get('probe.prime.export.rc', '')}` fd_valid=`{fields.get('probe.prime.export.fd_valid', '')}`",
        f"- PRIME import: rc=`{values.get('probe.prime.import.rc', '')}` handle=`{fields.get('probe.prime.import.handle', '')}` "
        f"same_handle=`{fields.get('probe.prime.import.same_handle', '')}`",
        f"- ADDFB2: rc=`{values.get('probe.addfb2.rc', '')}` fb_id=`{fields.get('probe.addfb2.fb_id', '')}`",
        f"- Cleanup: rmfb=`{values.get('probe.cleanup.rmfb.rc', '')}` "
        f"close_import=`{fields.get('probe.cleanup.close_import.rc', '')}` "
        f"close_handle=`{fields.get('probe.cleanup.close_handle.rc', '')}`",
        f"- Helper result: `{probe.get('result', '')}`",
        "",
        "## Interpretation",
        "",
    ]
    if decision == DECISION_PASS_IOVA:
        lines.extend([
            "The display-side shared-linear allocation path is proven, and the msm GEM",
            "also returned an IOVA. Z2 can attempt a real zero-copy source build by",
            "making the GPU path render into this shared scanout-linear memory, while",
            "keeping the current KGSL-linear to KMS CPU-copy path as fallback.",
        ])
    elif decision == DECISION_PASS_NO_IOVA:
        lines.extend([
            "The display-side shared-linear allocation path is proven: msm GEM allocation,",
            "mmap, PRIME export/import, and KMS FB creation all passed. The helper did",
            "not get an IOVA, so this does not yet prove that the current KGSL command",
            "submit path can directly target the same memory. The next step should first",
            "find a KGSL import/target route for this dma-buf/GEM, or pivot the rendering",
            "submit path to DRM msm for this rung.",
        ])
    elif decision == DECISION_PARTIAL:
        lines.extend([
            "The preflight was only partial. Do not remove the CPU-copy KMS present path.",
            "Use the failed rc above to choose the next bounded source unit. If GEM_NEW",
            "or ADDFB2 failed, the DRM-msm shared-linear scanout path is not viable on",
            "the current resident without a different allocator.",
        ])
    else:
        lines.extend([
            "The live helper did not produce a usable preflight result. Keep the existing",
            "CPU-copy KMS path and inspect the private run logs before spending a source",
            "iteration on zero-copy.",
        ])
    lines.extend([
        "",
        "## Current Source Grounding",
        "",
        f"- Z1 helper: `{rel(HELPER_SOURCE)}`",
        f"- Existing KMS path: `{rel(KMS_SOURCE)}` already proves implicit linear scanout through",
        "  KMS framebuffer objects.",
        f"- Existing GPU present path: `{rel(GPU_SOURCE)}` renders into a KGSL linear BO, syncs it,",
        "  then line-copies into the KMS framebuffer. Z2 must replace only that final copy after",
        "  a shared-buffer path is proven.",
        "",
        "## Validation",
        "",
        f"- Runner: `{rel(REPO_ROOT / 'workspace/public/src/scripts/revalidation/native_gpu_z1_shared_linear_preflight.py')}`",
        f"- Private summary: `{summary.get('out_dir', '')}/summary.json`",
        f"- Pass: `{summary.get('pass', False)}`",
        "",
    ])
    return "\n".join(lines)


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = PRIVATE_RUNS / f"v3323-gpu-z1-shared-linear-preflight-{now_label()}"
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
            "power_write": False,
            "no_present_or_modeset": True,
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
        live_base.a90ctl(args, out_dir, steps, "resident-status", ["status"], timeout=90, allow_error=True)
        pre_selftest = live_base.a90ctl(args, out_dir, steps, "resident-selftest", ["selftest"], timeout=90, allow_error=True)
        summary["resident_version"] = version.strip()
        summary["version_ok"] = "A90 Linux init" in version
        summary["pre_selftest_fail0"] = "fail=0" in pre_selftest

        build_dir = out_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        helper_bin = live_base.build_helper(
            build_dir,
            steps,
            source=HELPER_SOURCE,
            output_name="a90_drm_msm_shared_linear_probe_z1",
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
            "gpu-z1-shared-linear-preflight",
            [REMOTE_HELPER],
            timeout=60,
            allow_error=True,
        )
        probe = parse_probe_stdout(probe_stdout)
        summary["probe"] = probe
        post_selftest = live_base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        summary["post_selftest_fail0"] = "fail=0" in post_selftest
        summary["decision"] = probe["decision"]
        summary["pass"] = bool(
            summary["post_selftest_fail0"] and
            probe.get("result") == "z1-drm-msm-shared-linear-preflight-pass"
        )
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
    parser.add_argument("--transfer-port", type=int, default=18192)
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
            "decision": DECISION_DRY_RUN,
            "helper_source": rel(HELPER_SOURCE),
            "remote_helper": REMOTE_HELPER,
            "probe": {},
            "build": {},
            "pass": False,
        }

    if args.write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("pass") or not args.run_live else 1


if __name__ == "__main__":
    raise SystemExit(main())
