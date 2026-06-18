#!/usr/bin/env python3
"""V2750 host-side entrypoint for the proven native speaker feature.

This is the first clean API/CLI facade over the V2748-proven audio path.  It is
host-only by default: `--plan` emits a staged contract and the exact legacy V2639
runner command to execute later.  No device action, no flash, no mixer write, no
ACDB SET, and no PCM playback happen unless a future unit explicitly wires a live
mode.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import native_audio_acdb_setcal_replay_live_handoff_v2639 as v2639
import native_audio_speaker_profiles_v2749 as profiles

Mode = Literal["probe", "listen"]

RUN_ID = "V2750"
BUILD_TAG = "v2750-audio-speaker-feature-entrypoint"
DEFAULT_DEPLOY_MANIFEST = Path(
    "workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json"
)
STAGED_CONTRACT = (
    "preflight-v2321-health",
    "flash-v2334-audio-candidate",
    "adsp-boot-once",
    "snd-materialize-once",
    "install-profile-artifacts",
    "write-global-app-type-config",
    "write-stream-app-type-config",
    "apply-speaker-route",
    "replay-acdb-setcal-sequence",
    "bounded-pcm-playback",
    "capture-dmesg-and-focused-state",
    "reverse-deallocate",
    "reverse-route-reset",
    "rollback-v2321",
    "post-rollback-selftest",
)


@dataclass(frozen=True)
class PlaybackRequest:
    profile_id: str
    mode: Mode
    amplitude: float
    duration_ms: int
    countdown_sec: int

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "PlaybackRequest":
        profile = profiles.get_profile(args.profile)
        mode: Mode = "listen" if args.mode == "listen" else "probe"
        limits = profile.limits_for_mode(mode)
        amplitude = limits.default_amplitude if args.amplitude is None else float(args.amplitude)
        duration_ms = limits.default_duration_ms if args.duration_ms is None else int(args.duration_ms)
        profile.validate_playback(mode=mode, amplitude=amplitude, duration_ms=duration_ms)
        return cls(
            profile_id=profile.profile_id,
            mode=mode,
            amplitude=amplitude,
            duration_ms=duration_ms,
            countdown_sec=int(args.listen_countdown_sec),
        )


def rel(path: Path | str) -> str:
    return str(path)


def legacy_v2639_command(request: PlaybackRequest, deploy_manifest: Path, manifest_path: Path, report_path: Path) -> list[str]:
    command = [
        "python3",
        "workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py",
        "--run-live",
        "--audio-profile",
        request.profile_id,
        "--amplitude",
        str(request.amplitude),
        "--duration-ms",
        str(request.duration_ms),
        "--v2636-manifest",
        rel(deploy_manifest),
        "--manifest-path",
        rel(manifest_path),
        "--report",
        rel(report_path),
        "--write-report",
    ]
    if request.mode == "listen":
        command.extend(["--listen-test", "--listen-countdown-sec", str(request.countdown_sec)])
    return command


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    request = PlaybackRequest.from_args(args)
    profile = profiles.get_profile(request.profile_id)
    manifest_path = Path(args.manifest_path)
    report_path = Path(args.report)
    deploy_manifest = Path(args.v2636_manifest)
    live_command = legacy_v2639_command(request, deploy_manifest, manifest_path, report_path)
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2750-audio-speaker-feature-entrypoint-plan",
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "profile": profile.manifest(),
        "request": asdict(request),
        "staged_contract": list(STAGED_CONTRACT),
        "entrypoint_status": {
            "clean_profile_api": True,
            "single_host_entrypoint": True,
            "native_init_command_surface": False,
            "live_execution_delegates_to_v2639": True,
            "legacy_runner_run_id": v2639.RUN_ID,
        },
        "legacy_v2639_live_command": live_command,
        "safety": {
            "amplitude_cap": profile.limits_for_mode(request.mode).max_amplitude,
            "duration_cap_ms": profile.limits_for_mode(request.mode).max_duration_ms,
            "no_smart_amp_gain_boost_changes": True,
            "rollback_target": "v2321",
            "forbidden_stale_cal_types": list(profile.forbidden_stale_cal_types),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="emit the host-only feature plan")
    parser.add_argument("--profile", choices=profiles.list_profiles(), default=profiles.INTERNAL_SPEAKER_SAFE.profile_id)
    parser.add_argument("--mode", choices=("probe", "listen"), default="listen")
    parser.add_argument("--amplitude", type=float, default=None)
    parser.add_argument("--duration-ms", type=int, default=None)
    parser.add_argument("--listen-countdown-sec", type=int, default=5)
    parser.add_argument("--v2636-manifest", type=Path, default=DEFAULT_DEPLOY_MANIFEST)
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=Path("workspace/private/builds/audio/v2750-speaker-feature-entrypoint/manifest.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/reports/NATIVE_INIT_V2750_AUDIO_SPEAKER_FEATURE_ENTRYPOINT_HOST_ONLY_2026-06-19.md"),
    )
    args = parser.parse_args(argv)
    if not args.plan:
        parser.error("V2750 supports host-only --plan only; live command execution remains delegated to V2639")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(json.dumps(build_plan(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
