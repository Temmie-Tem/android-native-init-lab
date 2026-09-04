"""Resume only P339 post-transfer health against its original document input.

The old bundle includes a Tier-3 Process-v2 document digest. Read those exact
historical bytes from Git for bundle reconstruction; the current policy and
every executable/artifact check remain in place. Never rewrite preparation,
approval, prior journal records, or the working-tree policy. This fixed run
already transferred candidate and rollback once. No transfer is reachable.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import subprocess

import device_action_f1_live_v2 as live
import s22plus_fyg8_p300_identity_tiers as tiers


ROOT = Path(__file__).resolve().parents[5]
RUN = ROOT / "workspace/private/runs/device-action-f1-live-v2/p339-ready2-prepared-20260905-2"
MANIFEST = ROOT / "workspace/public/src/device-action/manifests/s22plus_fyg8_p339_process_v2_ready_2.json"
PREPARED_SHA256 = "d621bcfc8492bf9f47cc6659fb05cb39e208025193259bbbe82f8c3558881ac6"
DOCUMENT = "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
REVISION = "965c5d5d75"
DOCUMENT_IDENTITY = {
    "size": 36833,
    "sha256": "9be05e23b203b2c8f8ff831da25c20daee328b26100e4b1ca694ff7cd9ddbde9",
}
LIVE_SHA256 = "5b7f782919035e444686c347d8a04ed2a1764281d5bf08dac63e4545d58e340c"
FINAL_ROOT = RUN / "health-resume-1"


def identity(payload):
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


@contextmanager
def original_document_input():
    """Restore one historical input in memory, not a policy or authorization."""
    result = subprocess.run(
        ["git", "show", "--no-ext-diff", "--no-textconv", f"{REVISION}:{DOCUMENT}"],
        cwd=ROOT, capture_output=True, check=True, timeout=10,
    )
    if result.stderr or identity(result.stdout) != DOCUMENT_IDENTITY:
        raise live.F1LiveError("P339 original document bytes differ")
    if tiers.TIER3_DIRECT_PATHS.get("process_v2_contract") != Path(DOCUMENT):
        raise live.F1LiveError("P339 document input path differs")
    original = tiers.tier3_materials

    def historical(root):
        if root.resolve() != ROOT:
            raise live.F1LiveError("P339 historical input root differs")
        values = original(root)
        if "direct:process_v2_contract" not in values:
            raise live.F1LiveError("P339 document input is missing")
        return values | {"direct:process_v2_contract": result.stdout}

    tiers.tier3_materials = historical
    try:
        yield
    finally:
        tiers.tier3_materials = original


class HealthOnlyBackend(live.SamsungOdinBackend):
    def transfer(self, *args, **kwargs):
        raise live.F1LiveError("P339 health resumption cannot transfer")

    def request_download(self, *args, **kwargs):
        raise live.F1LiveError("P339 health resumption cannot request Download")

    def verify_final(self, prepared, run_dir, lease, destination):
        if prepared.run_dir != RUN or destination != RUN:
            raise live.F1LiveError("P339 health destination differs")
        # Earlier health polls and complete retained-log reads remain intact.
        # One new fixed child gives the existing reader an unused namespace.
        FINAL_ROOT.mkdir(mode=0o700)
        live.core._fsync_dir(RUN)
        return super().verify_final(prepared, run_dir, lease, FINAL_ROOT)


class RetainedClient(live.d0.AdbReadOnlyClient):
    """Run the original parsers over the completed, fixed health capture only."""

    def __init__(self):
        super().__init__(Path("/usr/bin/adb"), expected_model="SM-S906N", expected_device="g0q")
        self._inputs = iter((
            (0, "adb devices"), (1, "adb get-devpath"),
            (2, "adb read-only shell"), (3, "adb read-only shell"),
            (6, "adb devices"), (7, "adb get-devpath"),
        ))

    def _run(self, arguments, label, timeout=20):
        index, expected = next(self._inputs)
        if label != expected:
            raise live.F1LiveError("P339 retained health read order differs")
        path = FINAL_ROOT / "raw-adb" / f"{index:04d}-{label.replace(' ', '-')}.capture.json"
        handle = live.raw_capture.load_handle(path)
        return live.raw_capture.decode_success_stdout(handle, maximum=live.d0.MAX_TEXT_OUTPUT)


def retained_final(prepared):
    """Rederive health already collected before the final projection exception."""
    if prepared.run_dir != RUN:
        raise live.F1LiveError("P339 retained health owner differs")
    snapshots = live.odin_core.list_snapshot_receipts(RUN / "odin-endpoints")
    if not snapshots or snapshots[-1]["sequence"] != 35:
        raise live.F1LiveError("P339 retained endpoint sequence differs")
    absence = snapshots[-1]
    if (
        absence["live_devices"] or absence["live_device_identities"]
        or absence["endpoint_transition_evidence"] is None
        or absence["raw_capture_receipt"]["sha256"]
        != "330965a3e11ce9c38e56427b5a7bf14967642d09bb6305199a8440c71dc4e8e0"
    ):
        raise live.F1LiveError("P339 retained Download absence differs")
    client = RetainedClient()
    serial = client.one_serial()
    topology = client.topology(serial)
    if serial != prepared.private_target["serial"] or topology != prepared.private_target["topology"]:
        raise live.F1LiveError("P339 retained target continuity differs")
    health = live.d0.validate_health(
        prepared.bundle, client.properties(serial), client.root_health(serial), True, "final_health"
    )
    payloads, receipts = [], []
    for index in (1, 2):
        path = FINAL_ROOT / f"rollback-observer-{index}.bin"
        capture_path = FINAL_ROOT / f"{index + 3:04d}-observer-eof.capture.json"
        handle = live.raw_capture.require_success(live.raw_capture.load_handle(capture_path))
        if handle.stdout_path != path:
            raise live.F1LiveError("P339 retained log location differs")
        payload = live.raw_capture.read_stdout(handle, maximum=live.MAX_OBSERVER_BYTES)
        raw, _ = live.core._stable_read(capture_path, "P339 retained log receipt", 64 * 1024)
        payloads.append(payload)
        receipts.append({
            "path": str(path), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "raw_capture": {"path": str(capture_path), **identity(raw)},
            "read_to_eof": True, "stderr_bytes": 0,
            # The former in-memory wall time was lost; retain the producer's
            # durable measured duration, not a fabricated new collection time.
            "elapsed_sec": json.loads(raw)["elapsed_msec"] / 1000,
        })
    if not payloads[0] or payloads[0] != payloads[1]:
        raise live.F1LiveError("P339 retained logs are not stable and identical")
    final_serial = client.one_serial()
    if final_serial != serial or client.topology(final_serial) != topology:
        raise live.F1LiveError("P339 retained final target differs")
    acceptance = prepared.bundle.manifest["observation"]["acceptance"]
    error = None
    try:
        marker = live.classify_acceptance(payloads[0], acceptance)
    except live.F1LiveError as exc:
        error = live._p339_stock_error(payloads[0], exc)
        marker = live._p339_parser_failure_classification(payloads[0], exc)
    observer = {
        "reads": receipts, "byte_identical": True,
        "bytes": len(payloads[0]), "sha256": hashlib.sha256(payloads[0]).hexdigest(),
        "exact_marker_count": marker["exact_count"], "marker_family_count": marker["family_count"],
        "classification": marker, "accepted": marker["accepted"] is True,
    }
    if error is None:
        observer["p339_stock"] = live._p320_terminal_projection(marker)
    else:
        observer["p339_stock_error"] = error
    result = {
        "health": health, "observer": observer, "rollback_verified": True,
        "target_evidence_sha256": live.core.json_sha256({
            "serial": hashlib.sha256(serial.encode()).hexdigest(),
            "topology": hashlib.sha256(topology.encode()).hexdigest(),
        }),
    }
    live._validate_final_observer(prepared, {
        "final_evidence": result, "marker_accepted": observer["accepted"],
    })
    return result


class RetainedBackend(HealthOnlyBackend):
    """Reporting-cut finalizer: no device or endpoint operation is available."""

    def __init__(self):
        pass

    def endpoint_session(self, run_dir):
        if run_dir != RUN / "odin-endpoints":
            raise live.F1LiveError("P339 retained endpoint owner differs")
        return nullcontext(None)

    def wait_download(self, *args, **kwargs):
        raise live.F1LiveError("P339 retained finalization cannot wait for Download")

    def verify_final(self, prepared, run_dir, lease, destination):
        if destination != RUN:
            raise live.F1LiveError("P339 retained destination differs")
        return retained_final(prepared)


@contextmanager
def p339_final_projection():
    """Exclude P339 from the P328-only fallback; all original checks remain."""
    original = live._finish_rollback
    source = inspect.getsource(original)
    anchor = '            and not _p338_bundle(prepared.bundle)\n        ):\n            error = final["observer"].get("p328_stock_error")'
    if source.count(anchor) != 1:
        raise live.F1LiveError("P339 final projection repair anchor differs")
    repaired = source.replace(anchor, anchor.replace(
        '\n        ):', '\n            and not _p339_bundle(prepared.bundle)\n        ):'
    ), 1)
    namespace = dict(vars(live))
    exec(compile(repaired, "<P339 retained final projection>", "exec", dont_inherit=True), namespace)
    live._finish_rollback = namespace["_finish_rollback"]
    try:
        yield
    finally:
        live._finish_rollback = original


@contextmanager
def final_capture_location():
    original = live._validate_final_observer

    def validate(prepared, state):
        if prepared.run_dir != RUN or prepared.prepared["manifest_id"] != "s22plus-fyg8-p339-process-v2-ready-2":
            raise live.F1LiveError("P339 final capture owner differs")
        # Change only the expected location of final read evidence. The
        # original health, target, raw-handle and decoder checks all run.
        return original(replace(prepared, run_dir=FINAL_ROOT), state)

    live._validate_final_observer = validate
    try:
        yield
    finally:
        live._validate_final_observer = original


def run(*, recover=False):
    if identity(Path(live.__file__).read_bytes())["sha256"] != LIVE_SHA256:
        raise live.F1LiveError("P339 original live source differs")
    if identity((RUN / "prepared.json").read_bytes())["sha256"] != PREPARED_SHA256:
        raise live.F1LiveError("P339 prepared bytes differ")
    with original_document_input(), final_capture_location():
        prepared = live.load_prepared(ROOT, MANIFEST, RUN)
        journal = live.core.Journal(RUN / "transaction", prepared.binding_sha256)
        state = journal.state()
        if state not in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED", "CLOSED"}:
            raise live.F1LiveError("P339 is not in post-transfer health/closure")
        current = live._state(prepared)
        for kind in ("candidate", "rollback"):
            receipt = live._validate_transfer_result(prepared, kind, 1)
            if (
                receipt["classification"] != "odin_transfer_completed"
                or current.get(f"{kind}_completed") is not True
                or current.get(f"{kind}_classification") != "odin_transfer_completed"
                or list(RUN.glob(f"{kind}-attempt-0[2-9]*"))
            ):
                raise live.F1LiveError("P339 exact 1/1 completed transfers differ")
        if not recover:
            final = retained_final(prepared)
            return {
                "verdict": "PASS_P339_HISTORICAL_DOCUMENT_HEALTH_RESUME_H0",
                "state": state, "bundle_sha256": prepared.bundle.sha256,
                "original_document": DOCUMENT_IDENTITY,
                "device_contact": False, "transfer_allowed": False,
                "current_policy_replaced": False,
                "retained_final_sha256": live.core.json_sha256(final),
                "final_health_verified_from_retained_raw": True,
            }
        with p339_final_projection():
            return live.recover_prepared(
                prepared, RetainedBackend()
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--recover", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(recover=args.recover), sort_keys=True, indent=2))
