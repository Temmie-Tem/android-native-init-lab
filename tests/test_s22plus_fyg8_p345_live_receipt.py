from __future__ import annotations

import copy
import hashlib
import hmac
from pathlib import Path
import stat
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402


KEY = b"k" * 32
KEY_SHA256 = hashlib.sha256(KEY).hexdigest()
BOOT_ID = b"b" * 32


class _ReceiptFixture:
    """Build one complete public-shape receipt from real P345 wire streams."""

    def __init__(self, run_dir: Path, *, variant="p345") -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True)
        self.variant = live.typed_evidence.SHELL_VARIANTS[variant]
        self.runtime = self.variant.runtime
        self.observer = self.variant.observer
        self.codec = live._open_header_initial_observer_module(  # noqa: SLF001
            self.runtime, self.observer, "p345-receipt-test"
        )
        self.spec = live.typed_evidence._shell_observer_spec(variant)
        self.prepared = self._prepared()
        self.audits = []
        self.rx_streams: list[bytes] = []
        self.tx_streams: list[bytes] = []
        self.proof = self._qualification_proof()
        self.payload = b"".join(self.rx_streams)
        self._write_supporting_receipts()
        self._write_raw_capture()
        self.value = self._receipt_value()
        self.publish(self.value)

    def _prepared(self) -> live.PreparedRun:
        acceptance = self.variant.adapter.acceptance_fixture()
        manifest = {
            "manifest_id": "p345-live-receipt-test",
            "candidate_ap": {"sha256": "a" * 64},
            "observation": {
                "acceptance": acceptance,
                "candidate_observer": self.spec,
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                    live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
                ),
            },
        }
        bundle = SimpleNamespace(
            manifest=manifest,
            sha256="b" * 64,
            profile={"target": {"download": {}}},
        )
        prepared = {
            "approval_binding_sha256": "c" * 64,
            "p328_auth_key_identity": {"size": 32, "sha256": KEY_SHA256},
            "approval_binding": {
                "p328_auth_key_identity": {"size": 32, "sha256": KEY_SHA256}
            },
        }
        return live.PreparedRun(
            ROOT,
            self.run_dir,
            bundle,
            prepared,
            {
                "schema": live.PRIVATE_TARGET_SCHEMA,
                "serial": "fixture",
                "topology": live.p324_typec_lane.SOURCE_TOPOLOGY,
            },
        )

    def _tag(
        self,
        domain: bytes,
        nonce: bytes,
        sequence: int | None = None,
        body: bytes = b"",
    ) -> bytes:
        message = bytearray(domain + self.runtime.P345_RUN_ID + nonce)
        if sequence is not None:
            message.extend(struct.pack("<I", sequence))
        message.extend(body)
        return hmac.new(KEY, bytes(message), hashlib.sha256).digest()

    def _frame(self, frame_type: int, sequence: int, payload: bytes) -> bytes:
        return self.codec.encode_frame(frame_type, sequence, payload)

    def _session(self, ordinal: int) -> tuple[bytes, bytes]:
        runtime = self.runtime
        observer = self.observer
        step = observer.QUALIFICATION_COMMANDS[ordinal - 1]
        nonce = bytes([ordinal]) * runtime.NONCE_SIZE
        rx = bytearray(runtime.DEVICE_BANNER)
        for stage in (
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            runtime.DIAGNOSTIC_STAGE_RNG,
        ):
            rx.extend(
                self._frame(
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    struct.pack("<Ii", stage, 0),
                )
            )
        rx.extend(self._frame(runtime.FRAME_CHALLENGE, 0, nonce))
        rx.extend(
            self._frame(
                runtime.FRAME_READY,
                1,
                self._tag(runtime.AUTH_DOMAIN_READY, nonce),
            )
        )
        rx.extend(
            self._frame(
                runtime.FRAME_BOOT_ID,
                runtime.P335_BOOT_ID_SEQUENCE,
                BOOT_ID
                + self.codec.compute_boot_id_tag(
                    KEY, runtime.P345_RUN_ID, nonce, BOOT_ID
                ),
            )
        )

        if ordinal == 1:
            middle = (
                b"P345-UID=65534\nP345-GID=65534\n"
                b"123.45 678.90\n"
                + observer.PROBE_DENIED_MARKER
                + observer.PROBE_ABSENT_MARKER
                + observer.CANARY_MARKER
            )
            flags, exit_code, term_signal = 0, 0, 0
        elif ordinal == 2:
            middle = b""
            flags, exit_code, term_signal = 0, 7, 0
        elif ordinal == 3:
            middle = b""
            flags, exit_code, term_signal = 1, -1, 9
        elif ordinal == 4:
            middle = observer.CANCEL_MARKER
            flags, exit_code, term_signal = runtime.P345_CANCELLED_FLAG, -1, 9
        else:
            middle = observer.PIPELINE_MARKER
            flags, exit_code, term_signal = 0, 0, 0

        outputs = (
            b"uid=0(root) gid=0(root) groups=0(root)\n",
            middle,
            b"P328-NONCE " + runtime.P345_RUN_ID_HEX.encode("ascii") + b"\n",
        )
        for sequence, output in zip((3, 4, 5), outputs):
            for offset in range(0, len(output), 1024):
                rx.extend(self._frame(runtime.FRAME_DATA, sequence, output[offset:offset+1024]))
            rx.extend(
                self._frame(
                    runtime.FRAME_EXIT,
                    sequence,
                    self.codec.EXIT.pack(
                        flags if sequence == 4 else 0,
                        exit_code if sequence == 4 else 0,
                        term_signal if sequence == 4 else 0,
                        len(output),
                        runtime.COMMAND_TIMEOUT_SEC * 1000 if ordinal == 3 and sequence == 4 else 1,
                    ),
                )
            )
            if ordinal == 4 and sequence == 4:
                rx.extend(
                    self._frame(
                        runtime.FRAME_CANCEL_ACK,
                        4,
                        struct.pack("<I", runtime.P345_CANCEL_STATUS_CONSUMED),
                    )
                )
        rx.extend(self._frame(runtime.FRAME_DONE, 6, struct.pack("<I", 3)))

        commands = (
            runtime.DEFAULT_COMMANDS[0],
            step.command,
            runtime.DEFAULT_COMMANDS[2],
        )
        tx = bytearray(self._frame(runtime.FRAME_OPEN, 0, runtime.P345_RUN_ID))
        tx.extend(
            self._frame(
                runtime.FRAME_AUTH,
                1,
                self._tag(runtime.AUTH_DOMAIN_OPEN, nonce),
            )
        )
        for sequence, command in zip((3, 4), commands[:2]):
            tx.extend(
                self._frame(
                    runtime.FRAME_EXEC,
                    sequence,
                    self._tag(runtime.AUTH_DOMAIN_EXEC, nonce, sequence, command)
                    + command,
                )
            )
        if ordinal == 4:
            tx.extend(
                self._frame(
                    runtime.FRAME_CANCEL,
                    runtime.P345_CANCEL_SEQUENCE,
                    runtime.cancel_tag(KEY, runtime.P345_RUN_ID, nonce),
                )
            )
        command = commands[2]
        tx.extend(
            self._frame(
                runtime.FRAME_EXEC,
                5,
                self._tag(runtime.AUTH_DOMAIN_EXEC, nonce, 5, command) + command,
            )
        )
        tx.extend(
            self._frame(
                runtime.FRAME_CLOSE,
                6,
                self._tag(runtime.AUTH_DOMAIN_CLOSE, nonce, 6),
            )
        )
        return bytes(rx), bytes(tx)

    def _qualification_proof(self) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        rx_offset = 0
        tx_offset = 0
        for ordinal, step in enumerate(self.observer.QUALIFICATION_COMMANDS, 1):
            rx, tx = self._session(ordinal)
            parsed = self.observer.parse_captured_session(self.codec, rx, tx, KEY)
            self.audits.append(parsed.session.audit)
            row = self.observer.validate_session_result(parsed, step)
            row["rx"]["offset"] = rx_offset
            row["tx"]["offset"] = tx_offset
            rows.append(row)
            self.rx_streams.append(rx)
            self.tx_streams.append(tx)
            rx_offset += len(rx)
            tx_offset += len(tx)
        proof = {
            "schema": self.observer.SCHEMA,
            "contract_id": self.observer.CONTRACT_ID,
            "target": self.observer.TARGET,
            "run_id_hex": self.observer.RUN_ID_HEX,
            "session_count": 5,
            "required_session_count": 5,
            "same_fd_session_count": 5,
            "reconnect_count": 0,
            "same_descriptor": True,
            "expected_boot_sha256": hashlib.sha256(BOOT_ID).hexdigest(),
            "sessions": rows,
            "proved": True,
            "authority_granted_by_observer": False,
        }
        self.observer.validate_qualification(proof)
        return proof

    def _write_supporting_receipts(self) -> None:
        live.cdc_acm_observer.persist_json(
            self.run_dir / "candidate-observer-baseline.json", {"baseline": True}
        )
        live.cdc_acm_observer.persist_json(
            self.run_dir / "candidate-observer-download-departure.json",
            {"download_endpoint_absent": True},
        )
        live.cdc_acm_observer.persist_json(
            self.run_dir / "candidate-observer-guard.json", {"guard": True}
        )

    def _write_raw_capture(self) -> None:
        writer = live.raw_capture.RawCaptureWriter(
            self.run_dir,
            "candidate-observer",
            stdout_maximum=live.P327_MAX_RAW_BYTES,
            stderr_maximum=1,
            argv0_name="tty-cdc-acm-p345",
            stdout_name="candidate-observer.raw",
            stderr_name="candidate-observer.raw.stderr",
        )
        writer.write_stdout(self.payload)
        handle = writer.finalize(returncode=0)
        self.capture_path = handle.receipt_path
        for path in (
            handle.stdout_path,
            handle.stderr_path,
            handle.receipt_path,
        ):
            if stat.S_IMODE(path.stat().st_mode) != 0o400:
                raise AssertionError(f"raw capture is not mode 0400: {path}")

    def _inventory(self) -> dict[str, object]:
        source = live.p324_typec_lane.SOURCE_TOPOLOGY
        candidate = live.p324_typec_lane.CANDIDATE_TOPOLOGY
        inventory = {
            "scan_complete": True,
            "all_endpoint_count": 1,
            "all_endpoint_identity_sha256": ["e" * 64],
            "foreign_candidate_like_count": 0,
            "foreign_candidate_like_identity_sha256": [],
            "rows": {
                source: {
                    "topology_sha256": hashlib.sha256(b"2-1.3").hexdigest(),
                    "endpoint_count": 0,
                    "exact_candidate_count": 0,
                    "candidate_like_count": 0,
                    "endpoint_identity_sha256": [],
                    "present": False,
                },
                candidate: {
                    "topology_sha256": hashlib.sha256(b"3-1.3").hexdigest(),
                    "endpoint_count": 1,
                    "exact_candidate_count": 1,
                    "candidate_like_count": 1,
                    "endpoint_identity_sha256": ["e" * 64],
                    "present": True,
                },
            },
        }
        live.p324_cdc_observer._validate_inventory(  # noqa: SLF001
            inventory, label="P345 synthetic receipt"
        )
        return inventory

    def _lane(self) -> dict[str, object]:
        source = live.p324_typec_lane.SOURCE_TOPOLOGY
        candidate = live.p324_typec_lane.CANDIDATE_TOPOLOGY
        inventory = self._inventory()
        return {
            "source_topology": source,
            "candidate_topology": candidate,
            "selector_topology_count": 1,
            "opens_only_candidate_topology": True,
            "device_commands": False,
            "end_inventory": inventory,
            "partner_before": {"fixture": 1},
            "partner_after": {"fixture": 1},
            "partner_continuous": True,
            "partner_poll_count": 1,
            "accepted_for_p324": True,
        }

    def _receipt_value(self) -> dict[str, object]:
        baseline = live._receipt(  # noqa: SLF001
            self.run_dir / "candidate-observer-baseline.json", "baseline"
        )
        departure = live._receipt(  # noqa: SLF001
            self.run_dir / "candidate-observer-download-departure.json", "departure"
        )
        guard = live._receipt(  # noqa: SLF001
            self.run_dir / "candidate-observer-guard.json", "guard"
        )
        spec_sha256 = live.cdc_acm_observer.digest(
            live._p327_inherited_spec(self.spec)  # noqa: SLF001
        )
        binding = live._candidate_observer_binding(self.prepared)  # noqa: SLF001
        lane = self._lane()
        raw = {
            "path": str(self.run_dir / "candidate-observer.raw"),
            **live._p327_identity(self.payload),  # noqa: SLF001
            "capture_receipt": live._receipt(  # noqa: SLF001
                self.capture_path, "capture"
            ),
        }
        candidate_row = lane["end_inventory"]["rows"][  # type: ignore[index]
            live.p324_typec_lane.CANDIDATE_TOPOLOGY
        ]
        return {
            "schema": f"s22plus_fyg8_{self.variant.prefix}_shell_qualification_acm_receipt_v1",  # noqa: SLF001
            "contract_id": self.observer.CONTRACT_ID,
            "target": self.runtime.TARGET,
            "binding": binding,
            "spec_sha256": spec_sha256,
            "baseline_sha256": baseline["sha256"],
            "download_departure_sha256": departure["sha256"],
            "guard_sha256": guard["sha256"],
            "accepted": True,
            "classification": "accepted",
            "bounded": True,
            "download_endpoint_absent": True,
            "raw": raw,
            "session_tx_hex": [payload.hex() for payload in self.tx_streams],
            "tx": live._p327_identity(b"".join(self.tx_streams)),  # noqa: SLF001
            "trailing_bytes_seen": 0,
            "trailing_rx": live._p327_identity(b""),  # noqa: SLF001
            "rx": live._p327_identity(self.payload),  # noqa: SLF001
            "auth_key_sha256": KEY_SHA256,
            "proof": self.proof,
            self.variant.prefix + "_readonly_research_shell_qualification": self.proof,
            "preauth_diagnostics": [[{"stage": d.stage, "code": d.code} for d in audit.diagnostics]
                                    for audit in self.audits],
            "rng_eagain_retries": [audit.rng_eagain_retries for audit in self.audits],
            "partial_sessions": [{"current_stage": audit.current_stage, "failure_stage": audit.failure_stage}
                                 for audit in self.audits],
            "qualification_complete": True,
            "pid1_framed_exec_proof": True,
            "busybox_ash_command_proof": True,
            "framed_session_closed": True,
            "same_tty_fd": True,
            "session_count": 5,
            "command_count": 15,
            "physical_reopen_count": 0,
            "later_action_lease_active": False,
            "caller_selected_command": False,
            "lane": lane,
            "topology_sha256": candidate_row["topology_sha256"],
            "endpoint_identity_sha256": "e" * 64,
        }

    def publish(self, value: dict[str, object]) -> None:
        path = self.run_dir / "candidate-observer.json"
        if path.exists():
            path.unlink()
        live.cdc_acm_observer.persist_json(path, value)


class P345LiveReceiptTests(unittest.TestCase):
    def _fixture(self, temporary: str) -> _ReceiptFixture:
        return _ReceiptFixture(Path(temporary) / "run")

    def _validate(self, fixture: _ReceiptFixture) -> dict[str, object]:
        with mock.patch.object(
            live, "_p328_read_auth_key", return_value=(KEY, KEY_SHA256)
        ):
            return live._p345_validate_receipt(  # noqa: SLF001
                fixture.prepared,
                fixture.run_dir / "candidate-observer.json",
                fixture.spec,
            )

    def test_real_framed_receipt_reopens_and_rederives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(temporary)
            result = self._validate(fixture)
            self.assertTrue(result["valid_receipt"])
            self.assertTrue(result["accepted"])
            self.assertTrue(result["accepted_for_p324"])
            self.assertEqual(result["source_topology_sha256"], hashlib.sha256(b"2-1.3").hexdigest())
            self.assertEqual(
                result["candidate_topology_sha256"],
                hashlib.sha256(b"3-1.3").hexdigest(),
            )

    def test_semantic_boot_raw_header_and_foreign_schema_mutations_reject(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(temporary)
            mutations = {
                "canary semantic": lambda value: value["proof"]["sessions"][0][
                    "semantic"
                ].__setitem__("marker_seen", False),
                "boot identity": lambda value: value["proof"]["sessions"][0].__setitem__(
                    "boot_id_sha256", "0" * 64
                ),
                "raw identity": lambda value: value["raw"].__setitem__(
                    "sha256", "0" * 64
                ),
                "header schema": lambda value: value.__setitem__(
                    "schema", "s22plus_fyg8_p344_shell_qualification_acm_receipt_v1"
                ),
                "foreign contract schema": lambda value: value.__setitem__(
                    "contract_id", "s22plus-fyg8-p344-open-read-observer-v1"
                ),
            }
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    candidate = copy.deepcopy(fixture.value)
                    mutate(candidate)
                    fixture.publish(candidate)
                    with self.assertRaises(live.F1LiveError):
                        self._validate(fixture)
                    fixture.publish(fixture.value)


if __name__ == "__main__":
    unittest.main()
