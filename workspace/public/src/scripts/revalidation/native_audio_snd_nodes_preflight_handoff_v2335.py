#!/usr/bin/env python3
"""V2335 gated live runner for AUD-3 /dev/snd materialization preflight.

This script is intentionally not the playback test.  The only live mutation it
can perform after the exact operator approval phrase is flashing the V2334 boot
artifact, issuing the existing AUD-2 ADSP liveness command if the card is not
already up, and running the V2334 token-gated /dev/snd materializer once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import a90_transport as transport

APPROVAL_PHRASE = (
    "AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, "
    "no open/ioctl/mixer/playback, rollback to V2321"
)

CANDIDATE_VERSION = "0.9.292"
CANDIDATE_TAG = "v2334-audio-snd-nodes-preflight"
CANDIDATE_SHA256 = "53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac"
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_TAG = "v2321-usb-clean-identity-rodata"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FALLBACK_V2237_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"

ADSP_TOKEN = "AUD2_ONE_SHOT_ADSP_BOOT"
SND_TOKEN = "AUD3_DEV_SND_MATERIALIZE_ONLY"

AUDIO_CARD_RE = re.compile(r"sm8150-tavil-snd-card|sm8150tavilsndc")
SND_CONTROL_OK_RE = re.compile(r"\bdevnode=/dev/snd/controlC\d+\b[^\r\n]*\bstate=ok\b")
SND_PCM_OK_RE = re.compile(r"\bdevnode=/dev/snd/pcmC\d+D\d+[pc]\b[^\r\n]*\bstate=ok\b")
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "GOAL.md").exists() and (parent / "workspace").exists():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
A90CTL = ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
FLASH = ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2334_audio_snd_nodes_preflight.img"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
FALLBACK_V2237_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V48_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def load_text(path: Path, limit: int = 1_000_000) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return ""
    return data[:limit].decode("utf-8", errors="replace")


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for raw_line in text.replace("\r", "").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not key or key.startswith("A90P1 "):
            continue
        value = value.strip()
        tokens = value.split()
        inline_attrs: list[tuple[str, str]] = []
        for token in tokens[1:]:
            if "=" not in token:
                continue
            attr_key, attr_value = token.split("=", 1)
            if attr_key and re.fullmatch(r"[A-Za-z0-9_]+", attr_key):
                inline_attrs.append((attr_key, attr_value))
        if tokens and inline_attrs and "." in key:
            prefix = key.rsplit(".", 1)[0]
            values.setdefault(key, []).append(tokens[0])
            for attr_key, attr_value in inline_attrs:
                values.setdefault(f"{prefix}.{attr_key}", []).append(attr_value.strip())
        else:
            values.setdefault(key, []).append(value)
    return values


def last_value(values: dict[str, list[str]], key: str, default: str | None = None) -> str | None:
    items = values.get(key)
    if not items:
        return default
    return items[-1]


def ensure_expected_file(path: Path, expected_sha: str, label: str) -> dict[str, Any]:
    exists = path.exists()
    actual_sha = sha256_file(path) if exists else ""
    return {
        "label": label,
        "path": rel(path),
        "exists": exists,
        "sha256": actual_sha,
        "expected_sha256": expected_sha,
        "sha256_ok": bool(exists and actual_sha == expected_sha),
    }


def preflight_state() -> dict[str, Any]:
    return {
        "candidate": ensure_expected_file(CANDIDATE_IMAGE, CANDIDATE_SHA256, CANDIDATE_TAG),
        "rollback": ensure_expected_file(ROLLBACK_IMAGE, ROLLBACK_SHA256, ROLLBACK_TAG),
        "fallback_v2237": ensure_expected_file(FALLBACK_V2237_IMAGE, FALLBACK_V2237_SHA256, "v2237-supplicant-terminate-poll"),
        "fallback_v48": {
            "label": "v48-final-fallback",
            "path": rel(FALLBACK_V48_IMAGE),
            "exists": FALLBACK_V48_IMAGE.exists(),
            "sha256": sha256_file(FALLBACK_V48_IMAGE) if FALLBACK_V48_IMAGE.exists() else "",
        },
        "flash_helper": rel(FLASH),
        "a90ctl": rel(A90CTL),
        "approval_phrase_required": APPROVAL_PHRASE,
        "candidate_expect_version_contains": CANDIDATE_VERSION,
        "rollback_expect_version_contains": ROLLBACK_VERSION,
        "hard_boundary": [
            "no ALSA open/ioctl",
            "no mixer/tinymix",
            "no tinyplay/PCM/playback",
            "no audio HAL",
            "no adsprpc invoke/ioctl",
            "no /dev/subsys_adsp open",
            "one snd-materialize-once command maximum",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and FLASH.exists()
        and A90CTL.exists()
    )


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    command = [
        "python3",
        rel(FLASH),
        rel(image),
        "--expect-version",
        expect_version,
        "--expect-sha256",
        expect_sha,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "260",
        "--recovery-timeout",
        "260",
    ]
    if from_native:
        command.append("--from-native")
    return command


def a90ctl_command(args: argparse.Namespace, native_command: list[str], *, hide_on_busy: bool = False,
                   allow_error: bool = False, timeout: float | None = None) -> list[str]:
    command = [
        "python3",
        rel(A90CTL),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(timeout if timeout is not None else args.command_timeout),
        "--input-mode",
        "slow",
    ]
    if hide_on_busy:
        command.append("--hide-on-busy")
    if allow_error:
        command.append("--allow-error")
    command.extend(native_command)
    return command


def dry_run_plan(state: dict[str, Any]) -> dict[str, Any]:
    placeholder = argparse.Namespace(bridge_host="127.0.0.1", bridge_port=54321, command_timeout=60.0)
    return {
        "decision": "v2335-audio-snd-preflight-runner-dry-run",
        "preflight_ok": preflight_ok(state),
        "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False)
        + ["--verify-only"],
        "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
        "candidate_health": [
            a90ctl_command(placeholder, ["version"], hide_on_busy=True),
            a90ctl_command(placeholder, ["status"], hide_on_busy=True),
            a90ctl_command(placeholder, ["selftest", "verbose"], hide_on_busy=True, timeout=120.0),
        ],
        "audio_window": [
            a90ctl_command(placeholder, ["audio", "adsp-status"], hide_on_busy=True, timeout=90.0),
            a90ctl_command(placeholder, ["audio", "adsp-boot-once", ADSP_TOKEN], hide_on_busy=True, timeout=90.0),
            "poll audio adsp-status / audio snd-status until ALSA card and sound sysfs device entries appear",
            a90ctl_command(placeholder, ["audio", "snd-status"], hide_on_busy=True, timeout=90.0),
            a90ctl_command(placeholder, ["audio", "snd-materialize-once", SND_TOKEN], timeout=90.0),
            a90ctl_command(placeholder, ["audio", "snd-status"], hide_on_busy=True, timeout=90.0),
        ],
        "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        "post_rollback_health": [
            a90ctl_command(placeholder, ["version"], hide_on_busy=True),
            a90ctl_command(placeholder, ["status"], hide_on_busy=True),
            a90ctl_command(placeholder, ["selftest", "verbose"], hide_on_busy=True, timeout=120.0),
        ],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_step(out_dir: Path, steps: list[dict[str, Any]], name: str, command: list[str], *,
             timeout: float, allow_error: bool = False) -> dict[str, Any]:
    started = time.time()
    text_path = out_dir / f"{len(steps):02d}_{name}.txt"
    json_path = out_dir / f"{len(steps):02d}_{name}.json"
    record: dict[str, Any] = {
        "name": name,
        "command": command,
        "timeout_sec": timeout,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout or ""
        record.update({
            "rc": completed.returncode,
            "ok": completed.returncode == 0 or allow_error,
            "elapsed_sec": round(time.time() - started, 3),
            "stdout_path": rel(text_path),
            "stdout_tail": output[-4000:],
        })
        text_path.write_text(output, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        record.update({
            "rc": None,
            "ok": False,
            "timeout": True,
            "elapsed_sec": round(time.time() - started, 3),
            "stdout_path": rel(text_path),
            "stdout_tail": output[-4000:],
        })
        text_path.write_text(output, encoding="utf-8", errors="replace")
    write_json(json_path, record)
    steps.append(record)
    if not record["ok"] and not allow_error:
        raise RuntimeError(f"step failed: {name}")
    return record


def run_serial_transport_step(out_dir: Path,
                              steps: list[dict[str, Any]],
                              name: str,
                              args: argparse.Namespace,
                              native_command: list[str],
                              *,
                              timeout: float,
                              retry_observation: bool = False,
                              allow_error: bool = False) -> dict[str, Any]:
    text_path = out_dir / f"{len(steps):02d}_{name}.txt"
    json_path = out_dir / f"{len(steps):02d}_{name}.json"
    result = transport.run_serial_command_recovered(
        native_command,
        host=args.bridge_host,
        port=args.bridge_port,
        timeout=timeout,
        retry_unsafe=retry_observation,
        recovery_step_prefix=name,
    )
    output = "".join([str(result.get("stdout") or ""), str(result.get("stderr") or "")])
    record: dict[str, Any] = {
        "name": name,
        "command": [str(part) for part in result.get("command", ["cmdv1", *native_command])],
        "timeout_sec": timeout,
        "started_at": result.get("started"),
        "rc": result.get("rc"),
        "ok": bool(result.get("ok")) or allow_error,
        "elapsed_sec": result.get("elapsed_sec"),
        "stdout_path": rel(text_path),
        "stdout_tail": output[-4000:],
        "transport": "a90_transport.serial",
    }
    if "protocol" in result:
        record["protocol"] = result.get("protocol")
    if "serial_recovery" in result:
        record["serial_recovery"] = result.get("serial_recovery")
        record["serial_recovery_contract"] = result.get("serial_recovery_contract")
    text_path.write_text(output, encoding="utf-8", errors="replace")
    write_json(json_path, record)
    steps.append(record)
    if not record["ok"] and not allow_error:
        raise RuntimeError(f"step failed: {name}")
    return record



def run_a90ctl_observation(args: argparse.Namespace,
                           out_dir: Path,
                           steps: list[dict[str, Any]],
                           name: str,
                           native_command: list[str],
                           *,
                           timeout: float = 120.0,
                           attempts: int = 3,
                           delay_sec: float = 2.0) -> dict[str, Any]:
    """Run a read-only native command with bounded serial-contention recovery.

    The audio command family is not in a90ctl.py's built-in SAFE_RETRY_COMMANDS,
    so protocol desynchronization during live handoffs must be handled by the
    runner for observation-only commands.  This helper is intentionally not used
    for token-gated mutation commands.
    """

    last_error: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return run_serial_transport_step(
                out_dir,
                steps,
                f"{name}-attempt-{attempt}",
                args,
                native_command,
                timeout=timeout,
                retry_observation=True,
            )
        except RuntimeError as exc:
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(delay_sec)
    raise RuntimeError(f"observation command failed after {attempts} attempts: {name}: {last_error}")

def stdout_of(step: dict[str, Any]) -> str:
    path_value = step.get("stdout_path")
    if not path_value:
        return ""
    return load_text(ROOT / str(path_value))


def classify_audio_status(text: str) -> dict[str, Any]:
    values = parse_key_values(text)
    dev_count = last_value(values, "audio.dev_snd.count")
    control_count = last_value(values, "audio.dev_snd.control_like")
    pcm_count = last_value(values, "audio.dev_snd.pcm_like")
    sound_count = last_value(values, "audio.sound_class.count")
    card_like = last_value(values, "audio.sound_class.card_like")
    control_like = last_value(values, "audio.sound_class.control_like")
    proc_cards = "\n".join(values.get("audio.proc_asound_cards", []))
    return {
        "has_audio_card": bool(AUDIO_CARD_RE.search(text) or AUDIO_CARD_RE.search(proc_cards)),
        "has_sound_class_control": control_like not in {None, "0"},
        "has_dev_snd_control": control_count not in {None, "0"} or bool(SND_CONTROL_OK_RE.search(text)),
        "has_dev_snd_pcm": pcm_count not in {None, "0"} or bool(SND_PCM_OK_RE.search(text)),
        "audio.sound_class.count": sound_count,
        "audio.sound_class.card_like": card_like,
        "audio.sound_class.control_like": control_like,
        "audio.dev_snd.count": dev_count,
        "audio.dev_snd.control_like": control_count,
        "audio.dev_snd.pcm_like": pcm_count,
    }


def selftest_ok(text: str) -> bool:
    return bool(SELFTEST_FAIL0_RE.search(text))


def wait_for_audio_card(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    deadline = time.monotonic() + args.card_timeout
    attempt = 0
    last: dict[str, Any] | None = None
    while time.monotonic() <= deadline:
        attempt += 1
        adsp = run_a90ctl_observation(
            args, out_dir, steps, f"poll-adsp-status-{attempt}", ["audio", "adsp-status"], timeout=90.0
        )
        snd = run_a90ctl_observation(
            args, out_dir, steps, f"poll-snd-status-{attempt}", ["audio", "snd-status"], timeout=90.0
        )
        combined = stdout_of(adsp) + "\n" + stdout_of(snd)
        classification = classify_audio_status(combined)
        last = {"attempt": attempt, **classification}
        if classification["has_audio_card"] and classification["has_sound_class_control"]:
            return last
        time.sleep(args.poll_interval)
    raise RuntimeError(f"ALSA card/control did not appear before timeout: {last}")


def verify_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise SystemExit(
            "refusing live run: exact --approval phrase required:\n"
            f"{APPROVAL_PHRASE}"
        )


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    verify_live_approval(args)
    if not preflight_ok(state):
        raise SystemExit("refusing live run: rollback/candidate/fallback preflight failed")

    out_dir = ROOT / f"workspace/private/runs/audio/v2335-snd-nodes-preflight-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": "v2335-audio-snd-nodes-preflight-live-started",
        "out_dir": rel(out_dir),
        "preflight": state,
        "steps": steps,
        "rolled_back": False,
    }
    write_json(out_dir / "preflight.json", state)

    candidate_flashed = False
    try:
        run_step(
            out_dir,
            steps,
            "preflight-current-v2321-verify",
            flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        current_selftest = run_a90ctl_observation(
            args, out_dir, steps, "preflight-current-selftest", ["selftest", "verbose"], timeout=120.0
        )
        if not selftest_ok(stdout_of(current_selftest)):
            raise RuntimeError("resident preflight selftest did not report fail=0")

        run_step(
            out_dir,
            steps,
            "flash-v2334-candidate",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flashed = True

        version = run_a90ctl_observation(args, out_dir, steps, "candidate-version", ["version"], timeout=90.0)
        if CANDIDATE_VERSION not in stdout_of(version):
            raise RuntimeError("candidate version output did not contain expected version")
        run_a90ctl_observation(args, out_dir, steps, "candidate-status", ["status"], timeout=90.0)
        candidate_selftest = run_a90ctl_observation(
            args, out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0
        )
        if not selftest_ok(stdout_of(candidate_selftest)):
            raise RuntimeError("candidate selftest did not report fail=0")

        pre_adsp = run_a90ctl_observation(
            args, out_dir, steps, "candidate-audio-adsp-status-before", ["audio", "adsp-status"], timeout=90.0
        )
        pre_snd = run_a90ctl_observation(
            args, out_dir, steps, "candidate-audio-snd-status-before", ["audio", "snd-status"], timeout=90.0
        )
        initial_audio = classify_audio_status(stdout_of(pre_adsp) + "\n" + stdout_of(pre_snd))
        result["initial_audio"] = initial_audio

        if not (initial_audio["has_audio_card"] and initial_audio["has_sound_class_control"]):
            run_serial_transport_step(
                out_dir,
                steps,
                "candidate-adsp-boot-once",
                args,
                ["audio", "adsp-boot-once", ADSP_TOKEN],
                timeout=90.0,
                retry_observation=False,
            )

        result["card_wait"] = wait_for_audio_card(args, out_dir, steps)

        before_materialize = run_a90ctl_observation(
            args, out_dir, steps, "snd-status-before-materialize", ["audio", "snd-status"], timeout=90.0
        )
        result["before_materialize"] = classify_audio_status(stdout_of(before_materialize))

        materialize = run_serial_transport_step(
            out_dir,
            steps,
            "snd-materialize-once",
            args,
            ["audio", "snd-materialize-once", SND_TOKEN],
            timeout=90.0,
            retry_observation=False,
        )
        result["materialize_tail"] = stdout_of(materialize)[-4000:]

        after_materialize = run_a90ctl_observation(
            args, out_dir, steps, "snd-status-after-materialize", ["audio", "snd-status"], timeout=90.0
        )
        after = classify_audio_status(stdout_of(after_materialize))
        result["after_materialize"] = after
        if not after["has_dev_snd_control"]:
            raise RuntimeError("materialization did not produce a /dev/snd control node")

        final_candidate_selftest = run_a90ctl_observation(
            args, out_dir, steps, "candidate-selftest-after-materialize", ["selftest", "verbose"], timeout=120.0
        )
        if not selftest_ok(stdout_of(final_candidate_selftest)):
            raise RuntimeError("candidate final selftest did not report fail=0")
        result["decision"] = "v2335-snd-materialize-live-pass-before-rollback"
    finally:
        if candidate_flashed:
            rollback_record = run_step(
                out_dir,
                steps,
                "rollback-v2321",
                flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
                timeout=args.flash_timeout,
                allow_error=True,
            )
            result["rolled_back"] = bool(rollback_record.get("ok"))
            try:
                rollback_version = run_a90ctl_observation(args, out_dir, steps, "rollback-version", ["version"], timeout=90.0)
                rollback_selftest = run_a90ctl_observation(
                    args, out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0
                )
                result["rollback_version_ok"] = ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = selftest_ok(stdout_of(rollback_selftest))
            except Exception as exc:  # noqa: BLE001 - record rollback diagnostics without masking original failure.
                result["rollback_health_error"] = str(exc)
        write_json(out_dir / "result.json", result)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="verify local artifacts and print the live plan; no bridge/flash")
    mode.add_argument("--run-live", action="store_true", help="perform the gated live materialization run")
    parser.add_argument("--approval", default="", help="exact operator phrase required with --run-live")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--command-timeout", type=float, default=60.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--card-timeout", type=float, default=70.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    args = parser.parse_args()

    state = preflight_state()
    if args.dry_run:
        payload = {
            "ok": preflight_ok(state),
            "preflight": state,
            "plan": dry_run_plan(state),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["ok"] else 1

    result = live_run(args, state)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("decision") != "v2335-snd-materialize-live-pass-before-rollback":
        return 1
    return 0 if result.get("rolled_back") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
