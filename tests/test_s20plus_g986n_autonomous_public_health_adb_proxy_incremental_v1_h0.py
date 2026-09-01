#!/usr/bin/env python3
"""Hostile H0 tests for the pure incremental restricted-ADB model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import ast
import importlib.util
import inspect
import io
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_adb_proxy_incremental_v1_h0.py"
)
AUDIT_SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0.py"
)


def load_module():
    name = "s20plus_g986n_autonomous_public_health_adb_proxy_incremental_tested"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load incremental restricted-ADB model")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class IncrementalRestrictedAdbProxyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.source = SOURCE.read_bytes()

    def setUp(self):
        self.serial = "RFCM0000000"

    def event(self, kind, connection, payload=b""):
        return self.m.TranscriptFragment(kind, connection, payload)

    def fragments(self, kind, connection, payload, widths=(1, 2, 3, 5, 8)):
        result = []
        cursor = 0
        index = 0
        while cursor < len(payload):
            width = widths[index % len(widths)]
            result.append(self.event(kind, connection, payload[cursor : cursor + width]))
            cursor += width
            index += 1
        return result

    def local_events(self, widths=(1, 2, 3)):
        frame = self.m.encode_request(self.m.LOCAL_VERSION_SERVICE)
        return self.fragments("downstream", 1, frame, widths)

    def query_transcript(self, ordinal=2, payload=b"device-proof", widths=(1, 2, 3, 5)):
        service = self.m._services_for_ordinal(ordinal, self.serial)[1][0]
        request = self.m.encode_request(service)
        response = f"{len(payload):04x}".encode("ascii") + payload
        events = self.local_events(widths)
        events += self.fragments("downstream", 2, request, widths)
        events += self.fragments("upstream", 2, b"OKAY" + response, widths)
        events.append(self.event("upstream-eof", 2))
        return tuple(events), request, response

    def exec_transcript(self, ordinal=4, output=b"model=SM-G986N\n", widths=(1, 2, 3, 5, 8)):
        tport = self.m.encode_request(f"host:tport:serial:{self.serial}")
        exec_frame = self.m.encode_request(self.m.EXEC_SERVICE)
        transport_id = (42).to_bytes(8, "little")
        events = self.local_events(widths)
        events += self.fragments("downstream", 2, tport, widths)
        events += self.fragments("upstream", 2, b"OKAY" + transport_id, widths)
        events += self.fragments("downstream", 2, exec_frame, widths)
        events += self.fragments("upstream", 2, b"OKAY" + output, widths)
        events.append(self.event("upstream-eof", 2))
        return tuple(events), tport, transport_id, exec_frame

    def test_render_plan_is_review_pending_inactive_and_claim_bounded(self):
        plan = self.m.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_INCREMENTAL_V1_"
            "MODEL_PASS_GO_NOT_ACTIVE",
        )
        self.assertEqual(
            plan["target"],
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertFalse(any(plan["gates"].values()))
        self.assertFalse(any(plan["authority"].values()))
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["connected_backends"], [])
        model = plan["model"]
        self.assertTrue(model["caller_selects_transcript"])
        self.assertFalse(model["wire_observation_authenticated"])
        self.assertFalse(model["partial_results_exposed"])
        for key in (
            "caller_sink",
            "caller_callback",
            "caller_backend",
            "mutable_ledger",
            "import_visible_reducer",
            "reusable_session",
        ):
            self.assertIsNone(model[key])
        self.assertEqual(
            model["first_pass"],
            "full-validation-without-relay-emission-construction",
        )
        self.assertEqual(
            model["second_pass"],
            "success-only-frozen-relay-emission-derivation",
        )

    def test_committed_proxy_audit_is_exactly_pinned(self):
        identity = self.m.PROXY_AUDIT_IDENTITY
        payload = AUDIT_SOURCE.read_bytes()
        self.assertEqual(
            identity["commit"], "d561226f108869614128db9e46ea050c4a94b58c"
        )
        self.assertEqual(Path(identity["path"]), AUDIT_SOURCE)
        self.assertEqual(len(payload), identity["size"])
        self.assertEqual(self.m.sha256_bytes(payload), identity["sha256"])
        self.assertEqual(
            identity["sha256"],
            "18993008de3c236211c11de2756dc9b05424d9704cfdcb9c02f3cf70e9e29d92",
        )

    def test_self_normalized_anchor_is_exact_and_transition_stable(self):
        self.assertEqual(
            self.m.normalized_source_sha256(self.source),
            self.m.EXPECTED_SELF_NORMALIZED_SHA256,
        )
        transitioned, count = re.subn(
            rb'^STATUS = \(\n    "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_INCREMENTAL_V1_"\n    "MODEL_PASS_GO_NOT_ACTIVE"\n\)$',
            b'STATUS = (\n    "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_INCREMENTAL_V1_"\n    "MODEL_REVIEWED_NOT_ACTIVE"\n)',
            self.source,
            count=1,
            flags=re.MULTILINE,
        )
        self.assertEqual(count, 1)
        for name in self.m.NORMALIZED_GATE_NAMES:
            transitioned, count = re.subn(
                rf"^{name} = False$".encode("ascii"),
                f"{name} = True".encode("ascii"),
                transitioned,
                count=1,
                flags=re.MULTILINE,
            )
            self.assertEqual(count, 1)
        self.assertEqual(
            self.m.normalized_source_sha256(transitioned),
            self.m.EXPECTED_SELF_NORMALIZED_SHA256,
        )

    def test_fixed_exec_service_matches_committed_audit_constants(self):
        audit_text = AUDIT_SOURCE.read_text(encoding="utf-8")
        self.assertIn(self.m.REMOTE_SNAPSHOT_SHA256, audit_text)
        self.assertIn(self.m.EXEC_SERVICE_SHA256, audit_text)
        self.assertEqual(
            self.m.sha256_bytes(self.m.REMOTE_SNAPSHOT.encode()),
            self.m.REMOTE_SNAPSHOT_SHA256,
        )
        self.assertEqual(len(self.m.REMOTE_SNAPSHOT.encode()), 1_472)
        self.assertEqual(self.m.sha256_bytes(self.m.EXEC_SERVICE.encode()), self.m.EXEC_SERVICE_SHA256)
        self.assertEqual(len(self.m.EXEC_SERVICE.encode()), 1_523)

    def test_cli_is_render_only_and_gated_stub_is_unimplemented(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(self.m.run(["--render-plan"]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], self.m.STATUS)
        errors = io.StringIO()
        with redirect_stderr(errors):
            with self.assertRaises(SystemExit):
                self.m.run([])
            with self.assertRaises(SystemExit):
                self.m.run(["--connected"])
        with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "inactive"):
            self.m.attended_open_and_read()
        patches = [mock.patch.object(self.m, name, True) for name in self.m.NORMALIZED_GATE_NAMES]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "not implemented"):
            self.m.attended_open_and_read()

    def test_source_has_no_socket_process_device_or_callback_surface(self):
        tree = ast.parse(self.source.decode())
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            {
                "socket", "subprocess", "selectors", "select", "fcntl", "ctypes", "os"
            }.isdisjoint(imports)
        )
        forbidden_calls = {
            "system", "popen", "fork", "execve", "execveat", "connect", "bind",
            "listen", "accept", "send", "sendall", "recv",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else (
                    node.func.id if isinstance(node.func, ast.Name) else ""
                )
                self.assertNotIn(name, forbidden_calls)
        parameters = tuple(inspect.signature(self.m.validate_transcript).parameters)
        self.assertEqual(parameters, ("ordinal", "serial", "transcript"))

    def test_old_mutable_sink_ledger_and_session_surface_is_absent(self):
        self.assertFalse(hasattr(self.m, "InMemoryRelayOps"))
        self.assertFalse(hasattr(self.m, "IncrementalProxySession"))
        self.assertFalse(hasattr(self.m, "_PureConnectionReducer"))
        self.assertFalse(hasattr(self.m, "validate_connection"))
        self.assertFalse(hasattr(self.m, "derive_connection_emissions"))
        text = self.source.decode()
        for token in (
            "self._owner", "self._emissions", "self._archived_emissions",
            "self._owned_emissions", "ops._claim", "ops._emit",
        ):
            self.assertNotIn(token, text)
        self.assertNotIn("callback:", text)
        self.assertNotIn("sink:", text)

    def test_arbitrary_service_has_no_import_visible_reducer_or_emitter(self):
        forbidden = self.m.encode_request("host:kill")
        self.assertIs(type(forbidden), bytes)
        for name, value in vars(self.m).items():
            if name in {"encode_request", "_services_for_ordinal"}:
                continue
            if (
                inspect.isfunction(value)
                and getattr(value, "__module__", None) == self.m.__name__
            ):
                parameters = set(inspect.signature(value).parameters)
                self.assertFalse(
                    "services" in parameters and "events" in parameters,
                    f"import-visible arbitrary-service processor: {name}",
                )

    def test_rejection_traceback_exposes_no_emission_or_mutable_accumulator(self):
        request = self.m.encode_request(self.m.DEVICES_LONG_SERVICE)
        transcript = tuple(
            self.local_events((99,))
            + [self.event("downstream", 2, request)]
        )
        try:
            self.m.validate_transcript(2, self.serial, transcript)
        except self.m.IncrementalProxyV1Error as error:
            traceback = error.__traceback__
            observed_frames = 0
            while traceback is not None:
                if traceback.tb_frame.f_globals.get("__name__") == self.m.__name__:
                    observed_frames += 1
                    for name, value in tuple(traceback.tb_frame.f_locals.items()):
                        self.assertNotIsInstance(value, self.m.RelayEmission, name)
                        self.assertIsNot(type(value), list, name)
                        if type(value) is tuple:
                            self.assertFalse(
                                any(
                                    isinstance(item, self.m.RelayEmission)
                                    for item in value
                                ),
                                name,
                            )
                traceback = traceback.tb_next
            self.assertGreater(observed_frames, 0)
        else:
            self.fail("incomplete accepted request unexpectedly returned a result")

    def test_transcript_must_be_exact_tuple_and_exact_fragment_type(self):
        local = tuple(self.local_events())
        for wrong in (list(local), iter(local), bytearray()):
            with self.subTest(wrong=type(wrong).__name__):
                with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "immutable tuple"):
                    self.m.validate_transcript(2, self.serial, wrong)

        class Derived(self.m.TranscriptFragment):
            pass

        derived = Derived("downstream", 1, self.m.encode_request("host:version"))
        with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "type differs"):
            self.m.validate_transcript(2, self.serial, (derived,))

    def test_fragment_field_type_confusion_and_terminal_payload_reject(self):
        cases = (
            self.m.TranscriptFragment("downstream", True, b"x"),
            self.m.TranscriptFragment(7, 1, b"x"),
            self.m.TranscriptFragment("downstream", 1, bytearray(b"x")),
            self.m.TranscriptFragment("upstream-eof", 1, b"x"),
            self.m.TranscriptFragment("downstream", 1, b""),
            self.m.TranscriptFragment("unknown", 1, b""),
        )
        for item in cases:
            with self.subTest(item=item):
                with self.assertRaises(self.m.IncrementalProxyV1Error):
                    self.m.validate_transcript(2, self.serial, (item,))

    def test_result_is_fresh_frozen_and_contains_only_immutable_tuples(self):
        first = self.m.validate_transcript(1, self.serial, ())
        second = self.m.validate_transcript(1, self.serial, ())
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIs(type(first.results), tuple)
        self.assertIs(type(first.emissions), tuple)
        with self.assertRaises(FrozenInstanceError):
            first.accepted = False
        self.assertFalse(hasattr(first, "owner"))
        self.assertFalse(hasattr(first, "ledger"))

    def test_old_injection_reset_and_reuse_have_no_structural_target(self):
        result = self.m.validate_transcript(1, self.serial, ())
        for name in (
            "_owner", "_emissions", "_archived_emissions", "_owned_emissions", "ops"
        ):
            self.assertFalse(hasattr(result, name))
        # Repeated validation is a new functional derivation, not reuse of a sink/session.
        self.assertEqual(result, self.m.validate_transcript(1, self.serial, ()))

    def test_sequential_and_concurrent_calls_have_no_reusable_state(self):
        transcript, _, _ = self.query_transcript(2)
        first = self.m.validate_transcript(2, self.serial, transcript)
        second = self.m.validate_transcript(2, self.serial, transcript)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertFalse(hasattr(transcript, "clear"))
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(
                    lambda _: self.m.validate_transcript(2, self.serial, transcript),
                    range(32),
                )
            )
        self.assertTrue(all(item == first for item in results))
        self.assertEqual(len({id(item) for item in results}), len(results))

    def test_ordinal_service_closure_is_exact(self):
        self.assertEqual(self.m._services_for_ordinal(1, self.serial), ())
        for ordinal in (2, 6):
            self.assertEqual(
                self.m._services_for_ordinal(ordinal, self.serial),
                (("host:version",), ("host:devices-l",)),
            )
        self.assertEqual(
            self.m._services_for_ordinal(3, self.serial),
            (("host:version",), (f"host-serial:{self.serial}:get-devpath",)),
        )
        for ordinal in (4, 5):
            self.assertEqual(
                self.m._services_for_ordinal(ordinal, self.serial),
                (("host:version",), (f"host:tport:serial:{self.serial}", self.m.EXEC_SERVICE)),
            )

    def test_ordinal_one_is_zero_connection_and_rejects_any_event(self):
        result = self.m.validate_transcript(1, self.serial, ())
        self.assertTrue(result.accepted)
        self.assertEqual(result.connections, 0)
        self.assertEqual(result.emissions, ())
        with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "no connection"):
            self.m.validate_transcript(1, self.serial, (self.event("timeout", 1),))

    def test_every_query_ordinal_accepts_fragmented_exact_transcript(self):
        for ordinal in (2, 3, 6):
            with self.subTest(ordinal=ordinal):
                transcript, request, response = self.query_transcript(ordinal)
                result = self.m.validate_transcript(ordinal, self.serial, transcript)
                self.assertTrue(result.accepted)
                self.assertEqual(result.connections, 2)
                self.assertEqual(result.upstream_request_frames, 1)
                self.assertEqual(result.upstream_bytes, request)
                self.assertEqual(
                    result.downstream_bytes,
                    self.m.LOCAL_VERSION_RESPONSE + b"OKAY" + response,
                )

    def test_both_exec_ordinals_accept_fragmented_exact_transcript(self):
        for ordinal in (4, 5):
            with self.subTest(ordinal=ordinal):
                transcript, tport, transport_id, exec_frame = self.exec_transcript(
                    ordinal, b"fixed-output"
                )
                result = self.m.validate_transcript(ordinal, self.serial, transcript)
                self.assertEqual(result.upstream_bytes, tport + exec_frame)
                self.assertEqual(result.upstream_request_frames, 2)
                self.assertEqual(result.results[1].output_bytes, 12)
                self.assertIn(b"OKAY" + transport_id + b"OKAY", result.downstream_bytes)
                self.assertTrue(result.downstream_bytes.endswith(b"fixed-output"))

    def test_every_two_way_request_split_accepts_only_after_full_transcript(self):
        checked = 0
        for ordinal in (2, 3, 4, 5, 6):
            services = self.m._services_for_ordinal(ordinal, self.serial)[1]
            for service in services:
                frame = self.m.encode_request(service)
                for cut in range(1, len(frame)):
                    if service == services[0]:
                        prefix = self.local_events() + [self.event("downstream", 2, frame[:cut])]
                    else:
                        tport = self.m.encode_request(services[0])
                        prefix = self.local_events() + [
                            self.event("downstream", 2, tport),
                            self.event("upstream", 2, b"OKAY" + (1).to_bytes(8, "little")),
                            self.event("downstream", 2, frame[:cut]),
                        ]
                    with self.assertRaises(self.m.IncrementalProxyV1Error):
                        self.m.validate_transcript(ordinal, self.serial, tuple(prefix))
                    checked += 1
        self.assertEqual(checked, 3_188)

    def test_forbidden_unknown_wrong_serial_and_pipelined_frames_reject(self):
        attacks = (
            self.m.encode_request("host:kill"),
            self.m.encode_request("host:start-server"),
            self.m.encode_request("host:devices"),
            self.m.encode_request("host-serial:OTHER:get-devpath"),
            self.m.encode_request("host:devices-l") + self.m.encode_request("host:kill"),
        )
        for attack in attacks:
            transcript = tuple(self.local_events() + [self.event("downstream", 2, attack)])
            with self.subTest(attack=attack[:24]):
                with self.assertRaises(self.m.IncrementalProxyV1Error):
                    self.m.validate_transcript(3, self.serial, transcript)

    def test_partial_header_payload_eof_and_timeout_reject(self):
        frame = self.m.encode_request("host:devices-l")
        for partial in (frame[:1], frame[:3], frame[:4], frame[:-1]):
            for terminal in ("downstream-eof", "timeout"):
                transcript = tuple(self.local_events() + [
                    self.event("downstream", 2, partial), self.event(terminal, 2)
                ])
                with self.subTest(size=len(partial), terminal=terminal):
                    with self.assertRaises(self.m.IncrementalProxyV1Error):
                        self.m.validate_transcript(2, self.serial, transcript)

    def test_oversize_uppercase_nul_non_utf8_and_extra_frames_reject(self):
        attacks = (b"ffff", b"000Chost:devices-l", b"000dhost:devices\x00", b"0001\xff")
        for attack in attacks:
            transcript = tuple(self.local_events() + [self.event("downstream", 2, attack)])
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(2, self.serial, transcript)

    def test_exec_before_tport_reply_and_coalesced_tport_exec_reject(self):
        tport = self.m.encode_request(f"host:tport:serial:{self.serial}")
        exec_frame = self.m.encode_request(self.m.EXEC_SERVICE)
        cases = (
            self.local_events() + [self.event("downstream", 2, tport), self.event("downstream", 2, exec_frame)],
            self.local_events() + [self.event("downstream", 2, tport + exec_frame)],
        )
        for transcript in cases:
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(4, self.serial, tuple(transcript))

    def test_fail_bad_partial_status_and_partial_transport_id_reject(self):
        query = self.m.encode_request("host:devices-l")
        for response in (b"FAIL", b"OK", b"NOPE"):
            transcript = tuple(self.local_events() + [
                self.event("downstream", 2, query), self.event("upstream", 2, response)
            ])
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(2, self.serial, transcript)
        tport = self.m.encode_request(f"host:tport:serial:{self.serial}")
        for response in (b"OKAY" + bytes(8), b"OKAY" + b"\x01" * 7):
            transcript = tuple(self.local_events() + [
                self.event("downstream", 2, tport), self.event("upstream", 2, response),
                self.event("upstream-eof", 2),
            ])
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(4, self.serial, transcript)

    def test_partial_extra_bad_protocol_string_and_wrong_eof_reject(self):
        request = self.m.encode_request("host:devices-l")
        for response in (b"OKAY0004abc", b"OKAY0004abcde", b"OKAY000G"):
            transcript = tuple(self.local_events() + [
                self.event("downstream", 2, request), self.event("upstream", 2, response),
                self.event("upstream-eof", 2),
            ])
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(2, self.serial, transcript)

    def test_output_exact_bound_accepts_and_crossing_bound_rejects(self):
        transcript, _, _, _ = self.exec_transcript(
            output=b"x" * self.m.MAX_RELAY_OUTPUT_BYTES, widths=(100_000,)
        )
        result = self.m.validate_transcript(4, self.serial, transcript)
        self.assertEqual(result.results[1].output_bytes, self.m.MAX_RELAY_OUTPUT_BYTES)
        too_large, _, _, _ = self.exec_transcript(
            output=b"x" * (self.m.MAX_RELAY_OUTPUT_BYTES + 1), widths=(100_000,)
        )
        with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "relay bound"):
            self.m.validate_transcript(4, self.serial, too_large)

    def test_output_split_crossing_bound_rejects_whole_call(self):
        transcript, _, _, _ = self.exec_transcript(output=b"")
        prefix = list(transcript[:-1])
        # exec_transcript with empty output contributes the OKAY status fragment.
        prefix += [
            self.event("upstream", 2, b"x" * (self.m.MAX_RELAY_OUTPUT_BYTES - 1)),
            self.event("upstream", 2, b"yz"), self.event("upstream-eof", 2),
        ]
        with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "relay bound"):
            self.m.validate_transcript(4, self.serial, tuple(prefix))

    def test_duplicate_skipped_reconnected_and_extra_connections_reject(self):
        local = self.local_events()
        cases = (
            [self.event("downstream", 2, self.m.encode_request("host:devices-l"))],
            local + [self.event("downstream", 1, b"x")],
            local + [self.event("downstream", 3, b"x")],
        )
        for transcript in cases:
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(2, self.serial, tuple(transcript))

    def test_upstream_before_request_after_protocol_and_after_complete_reject(self):
        cases = (
            self.local_events() + [self.event("upstream", 2, b"OKAY")],
            list(self.query_transcript()[0]) + [self.event("upstream", 2, b"x")],
        )
        for transcript in cases:
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(2, self.serial, tuple(transcript))

    def test_fragment_count_bounds_reject(self):
        frame = self.m.encode_request("host:devices-l")
        with mock.patch.object(self.m, "MAX_DOWNSTREAM_FRAGMENTS_PER_CONNECTION", 2):
            transcript = tuple(self.local_events((99,)) + [
                self.event("downstream", 2, frame[:1]),
                self.event("downstream", 2, frame[1:2]),
                self.event("downstream", 2, frame[2:3]),
            ])
            with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "fragment count"):
                self.m.validate_transcript(2, self.serial, transcript)

    def test_upstream_fragment_count_bound_rejects(self):
        request = self.m.encode_request("host:devices-l")
        with mock.patch.object(self.m, "MAX_UPSTREAM_FRAGMENTS_PER_CONNECTION", 2):
            transcript = tuple(self.local_events((99,)) + [
                self.event("downstream", 2, request),
                self.event("upstream", 2, b"O"),
                self.event("upstream", 2, b"K"),
                self.event("upstream", 2, b"A"),
            ])
            with self.assertRaisesRegex(self.m.IncrementalProxyV1Error, "fragment count"):
                self.m.validate_transcript(2, self.serial, transcript)

    def test_invalid_ordinals_serials_and_selectors_reject(self):
        for ordinal in (True, 0, 7, "2"):
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(ordinal, self.serial, ())
        for serial in ("", "bad serial", "x" * 129, 7):
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(1, serial, ())
        result = self.m.validate_transcript(1, self.serial, ())
        for args in ((True, 1), (1, True), (0, 1), (1, 0)):
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                result.upstream_bytes_for_frame(*args)

    def test_incomplete_missing_and_abort_inputs_return_no_result(self):
        cases = (
            (),
            tuple(self.local_events()),
            tuple(self.local_events() + [self.event("downstream", 2, b"ffff")]),
        )
        for transcript in cases:
            with self.assertRaises(self.m.IncrementalProxyV1Error):
                self.m.validate_transcript(2, self.serial, transcript)


if __name__ == "__main__":
    unittest.main()
