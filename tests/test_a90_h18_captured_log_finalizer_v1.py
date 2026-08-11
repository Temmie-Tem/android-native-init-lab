from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/server-distro/"
    / "a90_h18_captured_log_finalizer_v1.py"
)


class H18CapturedLogFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("h18_capture_finalizer_test", SCRIPT)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def _frame(
        self,
        sequence: int,
        command: list[str],
        body: list[str],
        *,
        duration_ms: int = 0,
    ) -> bytes:
        flags = "0x2" if command[0] == "run" else "0x0"
        lines = [
            f"A90P1 BEGIN seq={sequence} cmd={command[0]} argc={len(command)} flags={flags}",
            *body,
            f"[done] {command[0]} ({duration_ms}ms)",
            f"A90P1 END seq={sequence} cmd={command[0]} rc=0 errno=0 "
            f"duration_ms={duration_ms} flags={flags} status=ok",
        ]
        return ("\r\n".join(lines) + "\r\n").encode("utf-8")

    def _receipt(
        self,
        sequence: int,
        command: list[str],
        body: list[str],
    ) -> dict:
        raw = self._frame(sequence, command, body)
        transcript = self.module.observation.parse_a90p1_transcript(raw)
        return self.module._receipt_from_frame(raw, transcript.frames[0], command)

    def _payloads(self) -> tuple[list[str], list[str]]:
        opening = ["[1ms] prior exact native line", ""]
        final = [
            "[1ms] prior exact native line",
            "[11726ms] server-distro: D4 handoff stop stage=firstboot-overlay "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=4 evidence_bound=0 "
            "wifi_handoff_bound=0",
            "[11727ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 userdata_write=0",
            "",
        ]
        return opening, final

    def _opening_log(self) -> dict:
        opening, _ = self._payloads()
        return self._receipt(10, ["logcat"], opening)

    def _synthetic_streams(self) -> tuple[bytes, bytes]:
        commands = self.module._expected_commands()
        intent = self.module.INTENT_SHA256
        same_intent = {
            "enable": hashlib.sha256(
                self.module.d1._expected_h18_state(
                    intent, "armed-after-native-health"
                )
            ).hexdigest(),
            "latch": hashlib.sha256(
                self.module.d1._expected_h18_state(
                    intent, "automatic-handoff-dispatched-no-replay"
                )
            ).hexdigest(),
            "evidence": hashlib.sha256((intent + "\n").encode("ascii")).hexdigest(),
        }
        _, final_log = self._payloads()
        bodies = (
            [
                "A90AUTO_STATUS binding=1 enable=1 latch=1 "
                f"build={self.module.f1.CANDIDATE_BUILD}"
            ],
            [
                f"A90H18_INTENT_BINDING intent={intent} "
                f"enable_sha256={same_intent['enable']} "
                f"latch_sha256={same_intent['latch']} "
                f"evidence_sha256={same_intent['evidence']}"
            ],
            [
                f"version: {self.module.f1.CANDIDATE_VERSION} "
                f"build={self.module.f1.CANDIDATE_BUILD}"
            ],
            ["selftest: pass=11 warn=1 fail=0"],
            [
                "A90H18_POST_PHYSICAL_RETURN devt=259:36 "
                "ufs_mount_count=0 userdata_write=0"
            ],
            final_log,
        )
        encoded = [self.module.base.a90ctl.encode_cmdv1_line(command) for command in commands]
        tcp = ("\n".join(encoded) + "\n").encode("utf-8")
        serial_parts: list[bytes] = []
        for index, (command, echo, body) in enumerate(zip(commands, encoded, bodies), 1):
            prefix = echo if index == 1 else f"a90:/# {echo}"
            serial_parts.append((prefix + "\r\n").encode("utf-8"))
            serial_parts.append(self._frame(index, command, list(body)))
        serial_parts.append(b"a90:/# ")
        return tcp, b"".join(serial_parts)

    def _synthetic_capture(self) -> tuple[bytes, bytes, bytes]:
        tcp, serial = self._synthetic_streams()
        raw = (
            b"\n--- tcp->serial ---\n"
            + tcp
            + b"\n--- serial->tcp ---\n"
            + serial
        )
        return raw, tcp, serial

    def _receipts(self, raw: bytes | None = None) -> tuple[dict, ...]:
        if raw is None:
            raw, tcp, serial = self._synthetic_capture()
        else:
            marker = self.module.CAPTURE_MARKER_RE
            matches = list(marker.finditer(raw))
            streams = {b"tcp->serial": [], b"serial->tcp": []}
            for index, item in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
                streams[item.group(1)].append(raw[item.end() : end])
            tcp = b"".join(streams[b"tcp->serial"])
            serial = b"".join(streams[b"serial->tcp"])
        with mock.patch.multiple(
            self.module,
            TCP_STREAM_SIZE=len(tcp),
            TCP_STREAM_SHA256=hashlib.sha256(tcp).hexdigest(),
            SERIAL_STREAM_SIZE=len(serial),
            SERIAL_STREAM_SHA256=hashlib.sha256(serial).hexdigest(),
        ):
            return self.module._capture_receipts(raw)

    def _synthetic_stderr(self) -> bytes:
        lines = [
            "[bridge] tcp listener ready on 127.0.0.1:54321",
            "[bridge] press Ctrl-C to stop",
            f"[bridge] serial connected: {self.module.f1.EXACT_BRIDGE_DEVICE}",
        ]
        for port in range(32001, 32009):
            lines.append(f"[bridge] client connected: 127.0.0.1:{port}")
            lines.append(f"[bridge] client disconnected: 127.0.0.1:{port}")
        return ("\n".join(lines) + "\n").encode("utf-8")

    def _evidence(self) -> dict:
        receipts = self._receipts()
        return {
            "final_log_record": receipts[5],
            "auto_handoff_status": self.module.d1.parse_status(receipts[0]),
            "auto_handoff_status_record": receipts[0],
            "same_intent_binding": self.module._same_intent(receipts[1]),
            "native_health": {
                "exact_bridge": True,
                "selected_realpath": "/dev/ttyACM0",
                "version": receipts[2],
                "selftest": receipts[3],
            },
            "native_fallback_userdata": self.module._unmounted(receipts[4]),
            "bridge": {"localhost_session_count": 8},
        }

    def test_capture_has_exact_commands_frames_and_payload_prefix(self) -> None:
        receipts = self._receipts()
        self.assertEqual(len(receipts), 6)
        attribution = self.module._attribution(self._opening_log(), receipts[5])
        self.assertTrue(attribution["proof"])
        self.assertEqual(attribution["stage"], "firstboot-overlay")
        self.assertEqual(attribution["rc"], -1)
        self.assertEqual(attribution["errno"], 1)
        self.assertFalse(attribution["payload_prefix"]["command_envelope_compared"])

    def test_complete_receipts_are_not_a_prefix_but_payloads_are(self) -> None:
        final = self._receipts()[5]
        opening = self._opening_log()
        self.assertFalse(final["text"].startswith(opening["text"]))
        before = self.module._log_payload(opening, "opening")
        after = self.module._log_payload(final, "final")
        self.assertTrue(after.startswith(before))

    def test_capture_rejects_one_changed_outbound_byte(self) -> None:
        raw, _, _ = self._synthetic_capture()
        changed = bytearray(raw)
        index = changed.index(b"auto-handoff-status")
        changed[index] = ord("z")
        with self.assertRaises(self.module.ContractError):
            self._receipts(bytes(changed))

    def test_capture_rejects_missing_or_extra_response_frame(self) -> None:
        raw, _, _ = self._synthetic_capture()
        changed = raw.replace(b"A90P1 BEGIN seq=6", b"A90XX BEGIN seq=6", 1)
        with self.assertRaises(self.module.ContractError):
            self._receipts(changed)

    def test_payload_rejects_nonprefix_replacement(self) -> None:
        final = self._receipts()[5]
        changed = dict(final)
        changed["text"] = changed["text"].replace("[1ms] prior", "[2ms] prior", 1)
        with self.assertRaises(self.module.ContractError):
            self.module._attribution(self._opening_log(), changed)

    def test_payload_rejects_terminal_line_extension_without_separator(self) -> None:
        opening = self._receipt(10, ["logcat"], ["X"])
        _, final_lines = self._payloads()
        final = self._receipt(
            6,
            ["logcat"],
            ["X WAS_REPLACED", final_lines[1], final_lines[2], ""],
        )
        with self.assertRaises(self.module.ContractError):
            self.module._attribution(opening, final)

    def test_payload_rejects_duplicate_diagnostic_or_cleanup(self) -> None:
        final = self._receipts()[5]
        text = final["text"]
        _, final_lines = self._payloads()
        for line in (final_lines[1], final_lines[2]):
            changed = dict(final)
            changed["text"] = text.replace("[done] logcat", line + "\r\n[done] logcat", 1)
            with self.assertRaises(self.module.ContractError):
                self.module._attribution(self._opening_log(), changed)

    def test_payload_rejects_malformed_contradictory_marker_duplicates(self) -> None:
        final = self._receipts()[5]
        text = final["text"]
        malformed_diagnostic = (
            "[11725ms] server-distro: D4 handoff stop stage=firstboot-overlay "
            "rc=0 errno=0 root_mounted=1 writable_mounted=4 evidence_bound=0 "
            "wifi_handoff_bound=0"
        )
        malformed_cleanup = (
            "[11728ms] server-distro: D4 handoff failure cleanup_clean=0 "
            "root_mounted=1 recovery_required=1 userdata_unchanged=1 "
            "userdata_write=0"
        )
        for line in (malformed_diagnostic, malformed_cleanup):
            changed = dict(final)
            changed["text"] = text.replace(
                "[done] logcat", line + "\r\n[done] logcat", 1
            )
            with self.assertRaises(self.module.ContractError):
                self.module._attribution(self._opening_log(), changed)

    def test_payload_rejects_reordered_or_contradictory_cleanup(self) -> None:
        final = self._receipts()[5]
        text = final["text"]
        _, final_lines = self._payloads()
        diagnostic = final_lines[1]
        cleanup = final_lines[2]
        reordered = (
            text.replace(diagnostic, "X", 1)
            .replace(cleanup, diagnostic, 1)
            .replace("X", cleanup, 1)
        )
        contradictory = text.replace("cleanup_clean=1", "cleanup_clean=0", 1)
        for candidate in (reordered, contradictory):
            changed = dict(final)
            changed["text"] = candidate
            with self.assertRaises(self.module.ContractError):
                self.module._attribution(self._opening_log(), changed)

    def test_payload_rejects_stage_or_errno_drift(self) -> None:
        final = self._receipts()[5]
        for old, new in (
            ("stage=firstboot-overlay", "stage=evidence-bind"),
            ("errno=1", "errno=2"),
        ):
            changed = dict(final)
            changed["text"] = final["text"].replace(old, new, 1)
            with self.assertRaises(self.module.ContractError):
                self.module._attribution(self._opening_log(), changed)

    def test_bridge_stderr_is_exact_localhost_and_bound_serial(self) -> None:
        raw = self._synthetic_stderr()
        proof = self.module._validate_bridge_stderr(raw)
        self.assertEqual(proof["localhost_session_count"], 8)
        self.assertEqual(proof["external_network_contact_count"], 0)
        for changed in (
            raw.replace(b"127.0.0.1", b"127.0.0.2", 1),
            raw.replace(b"A90_Linux", b"OTHER_Linux", 1),
        ):
            with self.assertRaises(self.module.ContractError):
                self.module._validate_bridge_stderr(changed)

    def test_qualification_absence_fails_closed(self) -> None:
        closure = {"sha256": "a" * 64, "files": {}}
        with mock.patch.object(self.module, "REPO_ROOT", Path("/definitely/absent")):
            with self.assertRaises((OSError, self.module.ContractError)):
                self.module._load_qualification(closure)

    def test_review_report_requires_exact_internal_fields(self) -> None:
        closure = {"sha256": "a" * 64, "files": {"one": {}}}
        value = {
            "schema": self.module.REVIEW_SCHEMA,
            "capability": self.module.CAPABILITY,
            "verdict": "PASS_GO",
            "review_date": "2026-08-12",
            "reviewer": self.module.REVIEWER,
            "execution_closure_sha256": closure["sha256"],
            "execution_file_count": 1,
            "review_scope": self.module.REVIEW_SCOPE,
            "incident": self.module.INCIDENT,
            "new_hazard_or_incident": True,
            "findings": {"high": [], "medium": [], "low": []},
            "validated_invariants": list(self.module.REVIEW_REQUIRED_INVARIANTS),
            "review_contacts": {
                "device": 0,
                "dev": 0,
                "usb": 0,
                "network": 0,
                "workspace_private": 0,
                "s22plus_paths": 0,
                "file_modifications": 0,
            },
            "live_authority": False,
        }
        self.assertEqual(self.module._validate_review_report(value, closure), value)
        for key, changed in (
            ("verdict", "NO_GO"),
            ("incident", "old"),
            ("reviewer", "/root/other"),
            ("live_authority", True),
        ):
            bad = dict(value)
            bad[key] = changed
            with self.assertRaises(self.module.ContractError):
                self.module._validate_review_report(bad, closure)

    def test_execution_closure_binds_adapter_incident_and_predecessor(self) -> None:
        closure = self.module.execution_closure()
        self.assertIn(self.module.ADAPTER_REL, closure["files"])
        self.assertIn(self.module.INCIDENT_REPORT_REL, closure["files"])
        self.assertIn(
            "workspace/public/src/scripts/server-distro/a90_h18_ufs_d1_runner_v1.py",
            closure["files"],
        )
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

    def test_private_binding_rejects_mode_link_size_and_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture"
            path.write_bytes(b"exact")
            path.chmod(0o600)
            digest = self.module._sha256_bytes(b"exact")
            self.assertEqual(
                self.module._require_private_regular(path, path, 5, digest, "test"),
                b"exact",
            )
            path.chmod(0o644)
            with self.assertRaises(self.module.ContractError):
                self.module._require_private_regular(path, path, 5, digest, "test")

    def test_close_five_record_path_has_no_device_network_or_replay_call(self) -> None:
        records = [{"result_sha256": "x", "observation": {}} for _ in range(5)]
        records[0]["opening_log"] = self._opening_log()
        records[3]["observation"] = {"proof": False}
        records[4]["result_sha256"] = "b" * 64
        manifest = {"target": {"bridge_realpath": "/dev/ttyACM0"}}
        closure = {"sha256": "c" * 64, "files": {}}
        evidence = self._evidence()
        result = self.module._build_result(manifest, records, closure, evidence)
        with mock.patch.object(
            self.module,
            "_load_static_inputs",
            side_effect=[
                (manifest, records, closure, evidence),
                (manifest, records, closure, evidence),
                (
                    manifest,
                    records
                    + [
                        {
                            "result": result,
                            "result_sha256": self.module.f1.json_sha256(result),
                        }
                    ],
                    closure,
                    evidence,
                ),
                (
                    manifest,
                    records
                    + [
                        {
                            "result": result,
                            "result_sha256": self.module.f1.json_sha256(result),
                        },
                        {
                            "result": result,
                            "result_sha256": self.module.f1.json_sha256(result),
                        },
                    ],
                    closure,
                    evidence,
                ),
            ],
        ), mock.patch.object(
            self.module, "_validate_result", return_value=result
        ), mock.patch.object(
            self.module, "_write_record"
        ) as writer, mock.patch.object(
            self.module.base, "run_f1_cmd"
        ) as device_command, mock.patch.object(
            self.module.base.a90ctl, "bridge_exchange"
        ) as network_command:
            self.assertEqual(self.module.close(object()), result)
        self.assertEqual([call.args[0] for call in writer.call_args_list], [5, 6])
        device_command.assert_not_called()
        network_command.assert_not_called()

    def test_six_record_resume_appends_only_closed_without_device_contact(self) -> None:
        manifest = {}
        result = {"status": "terminal"}
        records = [{} for _ in range(5)] + [
            {"result": result, "result_sha256": "d" * 64}
        ]
        closure = {}
        evidence = {}
        with mock.patch.object(
            self.module,
            "_load_static_inputs",
            side_effect=[
                (manifest, records, closure, evidence),
                (
                    manifest,
                    records + [{"result": result, "result_sha256": "d" * 64}],
                    closure,
                    evidence,
                ),
            ],
        ), mock.patch.object(
            self.module, "_validate_result", return_value=result
        ), mock.patch.object(
            self.module, "_write_record"
        ) as writer, mock.patch.object(
            self.module.base, "run_f1_cmd"
        ) as device_command:
            self.assertEqual(self.module.close(object()), result)
        writer.assert_called_once_with(
            6, "closed", {"result_sha256": "d" * 64, "result": result}
        )
        device_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
