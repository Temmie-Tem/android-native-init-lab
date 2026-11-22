#!/usr/bin/env python3
"""Run the retained S20+ TWRP observer in its own reviewed source view."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


SCRIPT = Path(__file__).resolve()
SCRIPTS = SCRIPT.parent
ROOT = SCRIPT.parents[5]
PRIVATE = ROOT / "workspace/private"
REVIEW_ROOT = PRIVATE / "outputs/s20plus_g986n/twrp_observe_source_view_v1"
QUALIFICATION = REVIEW_ROOT / "qualification.json"
TEST_LOG = REVIEW_ROOT / "tests.log"
TEST_SOURCE = ROOT / "tests/test_s20plus_g986n_twrp_observe_source_view_v1.py"
HISTORICAL_REVIEW = PRIVATE / "outputs/s20plus_g986n/twrp_binding_refresh_rev29"
RUN_ROOT = PRIVATE / "runs/s20plus-g986n-routine-actions"
CAMPAIGN_GUARD = PRIVATE / "runs/s20plus-g986n-autonomous-research/active-campaign.json"
BASELINE = SCRIPTS / "s20plus_g986n_twrp_baseline_v1.py"
BWRAP = Path("/usr/bin/bwrap")
PYTHON = Path("/usr/bin/python3.14")
PINS = {
    BWRAP: (80_424, "523da3e7399044be5163aee6f57a77a6bef7454376e28f0a0627920bae1b76b6"),
    REVIEW_ROOT / "device_action_raw_capture_v1.py":
        (25_006, "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4"),
    SCRIPTS / "s20plus_g986n_boot_only_f1_transport_v1.py":
        (10_937, "f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea"),
}
SOURCE_BINDS = (
    (REVIEW_ROOT / "device_action_raw_capture_v1.py", SCRIPTS / "device_action_raw_capture_v1.py"),
    (SCRIPTS / "s20plus_g986n_boot_only_f1_transport_v1.py",
     SCRIPTS / "s22plus_boot_only_f1_transport.py"),
)
BASELINE_TEST_LOG = HISTORICAL_REVIEW / "baseline-tests.log"
QUALIFICATION_BINDS = (
    (QUALIFICATION, HISTORICAL_REVIEW / "baseline-qualification.json"),
    (TEST_LOG, BASELINE_TEST_LOG),
)
REVIEW_SCHEMA = "s20plus_g986n_twrp_baseline_v1-qualification"
REVIEW_PASS = {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0}
FINGERPRINT_SCRIPT = (
    "import json; import s20plus_g986n_twrp_baseline_v1 as baseline; "
    "capture = baseline.routine.bounded_command(['/usr/bin/printf', '%s', 'source-view-read'], 4, 32); "
    "assert capture == (0, b'source-view-read', b''), 'bounded capture failed'; "
    "baseline.identity.validate_host_closure(enforce_self=True); "
    "print(json.dumps(baseline.fingerprint(), sort_keys=True))"
)


def read_file(path, *, mode=None, maximum=16 * 1024 * 1024):
    if path.resolve(strict=True) != path:
        raise ValueError(f"indirect input: {path.name}")

    def identity(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size < 1 or before.st_size > maximum
                or mode is not None and stat.S_IMODE(before.st_mode) != mode):
            raise ValueError(f"unexpected input metadata: {path.name}")
        data = stream.read(maximum + 1)
        if (len(data) != before.st_size or identity(os.fstat(stream.fileno())) != identity(before)
                or identity(path.lstat()) != identity(before)):
            raise ValueError(f"input changed while reading: {path.name}")
    return data


def file_receipt(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def view_receipt():
    files = {}
    for path in (SCRIPT, TEST_SOURCE, PYTHON, *PINS):
        pin = file_receipt(read_file(path))
        if path in PINS and (pin["size"], pin["sha256"]) != PINS[path]:
            raise ValueError(f"unexpected source view input: {path.name}")
        files[str(path)] = pin
    return {"mode": "observe-only", "files": files,
            "source_binds": [[str(src), str(dst)] for src, dst in SOURCE_BINDS]}


def command(*, observe):
    args = [str(BWRAP), "--unshare-user", "--uid", str(os.getuid()), "--gid", str(os.getgid()),
            "--cap-drop", "ALL", "--ro-bind", "/", "/", "--tmpfs", "/tmp", "--dev", "/dev"]
    for source, destination in SOURCE_BINDS:
        args += ["--ro-bind", str(source), str(destination)]
    if observe:
        if RUN_ROOT.resolve(strict=True) != RUN_ROOT or not RUN_ROOT.is_dir():
            raise ValueError("indirect S20+ run directory")
        args += ["--bind", str(RUN_ROOT), str(RUN_ROOT)]
        for source, destination in QUALIFICATION_BINDS:
            args += ["--ro-bind", str(source), str(destination)]
    args += ["--chdir", str(SCRIPTS), "--", str(PYTHON), "-E", "-s", "-B",
             "-X", "pycache_prefix=/dev/null"]
    return args + ([str(BASELINE), "--observe"] if observe else ["-c", FINGERPRINT_SCRIPT])


def clean_environment():
    return {"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
            "TMPDIR": "/tmp"}


def require_review(expected_view):
    data = read_file(QUALIFICATION, mode=0o400, maximum=64 * 1024)
    review = json.loads(data)
    canonical = (json.dumps(review, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    tests = read_file(TEST_LOG, mode=0o400, maximum=64 * 1024)
    if (data != canonical or review.get("schema") != REVIEW_SCHEMA
            or review.get("review") != REVIEW_PASS or review.get("observation_view") != expected_view
            or review.get("tests") != {"path": str(BASELINE_TEST_LOG), **file_receipt(tests)}
            or not tests.rstrip().endswith(b"OK")):
        raise ValueError("independent S20+ observe-only review differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review-input", action="store_true")
    mode.add_argument("--observe", action="store_true")
    options = parser.parse_args()
    actual_view = view_receipt()
    if options.review_input:
        checked = subprocess.check_output(command(observe=False), env=clean_environment(), timeout=30)
        print(json.dumps({"fingerprint": json.loads(checked), "observation_view": actual_view,
                          "device_commands": 0}, sort_keys=True))
        return 0
    require_review(actual_view)
    if os.path.lexists(CAMPAIGN_GUARD) or os.path.lexists(RUN_ROOT / "active-action.json"):
        raise ValueError("an S20+ owner already holds a guard")
    return subprocess.run(command(observe=True), env=clean_environment(), check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"verdict": "STOP_S20PLUS_TWRP_SOURCE_VIEW", "reason": str(exc)}))
        raise SystemExit(2)
