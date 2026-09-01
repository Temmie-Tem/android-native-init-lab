#!/usr/bin/env python3
"""Hostile H0 tests for the inactive exact S20+ restricted ADB proxy model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import ast
import importlib.util
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
    "s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0.py"
)


def load_module():
    name = "s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0_tested"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load restricted proxy model")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RestrictedAdbProxyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.source = SOURCE.read_bytes()

    def setUp(self):
        self.serial = "RFCM0000000"
        self.child = self.m.ChildIdentity(pid=4101, uid=1000, gid=1000, start_ticks=811)
        self.peer = self.m.PeerCredentials(
            source=self.m.SO_PEERCRED_SOURCE,
            pid=self.child.pid,
            uid=self.child.uid,
            gid=self.child.gid,
            process_start_ticks=self.child.start_ticks,
            direct_child_pidfd_bound=True,
        )
        self.server = self.m.BoundServerIdentity(
            pid=2101,
            uid=1000,
            start_ticks=411,
            pidfd_bound=True,
            listener_fd=17,
            listener_inode=7001,
            executable_device=33,
            executable_inode=8001,
            executable_size=self.m.ADB_IDENTITY["size"],
            executable_sha256=self.m.ADB_IDENTITY["sha256"],
        )
        self.held_adb = self.m.HeldAdbFileIdentity(
            device=33,
            inode=8001,
            size=self.m.ADB_IDENTITY["size"],
            sha256=self.m.ADB_IDENTITY["sha256"],
        )
        self.upstream = self.m.EstablishedPeerProof(
            family="AF_INET",
            state="ESTABLISHED",
            local_address="127.0.0.1",
            local_port=42111,
            peer_address="127.0.0.1",
            peer_port=5037,
            proxy_socket_fd=23,
            proxy_socket_inode=9001,
            held_proxy_fd_inode=9001,
            server_peer_inode=7002,
            server_peer_fd=19,
            server_local_address="127.0.0.1",
            server_local_port=5037,
            server_observed_peer_address="127.0.0.1",
            server_observed_peer_port=42111,
            server_pid=self.server.pid,
            server_uid=self.server.uid,
            server_start_ticks=self.server.start_ticks,
            server_listener_inode=self.server.listener_inode,
            observed_owner_fd_inodes=((17, self.server.listener_inode), (19, 7002), (21, 7010)),
        )

    def connection(self, index, expectation):
        requests = tuple(self.m.encode_request(service) for service in expectation.services)
        event = self.m.WireEvent
        if not expectation.upstream:
            events = (
                event("downstream-request", requests[0]),
                event("proxy-to-downstream-local-version", self.m.LOCAL_VERSION_RESPONSE),
                event("downstream-eof", b""),
            )
        elif expectation.requires_transport_id:
            transport_id = (42).to_bytes(8, "little")
            output = b"model=SM-G986N\n"
            events = (
                event("downstream-request", requests[0]),
                event("proxy-to-upstream-request", requests[0]),
                event("upstream-to-proxy-status", b"OKAY"),
                event("proxy-to-downstream-status", b"OKAY"),
                event("upstream-to-proxy-transport-id", transport_id),
                event("proxy-to-downstream-transport-id", transport_id),
                event("downstream-request", requests[1]),
                event("proxy-to-upstream-request", requests[1]),
                event("upstream-to-proxy-status", b"OKAY"),
                event("proxy-to-downstream-status", b"OKAY"),
                event("upstream-to-proxy-output", output),
                event("proxy-to-downstream-output", output),
                event("upstream-eof", b""),
                event("downstream-eof", b""),
            )
        else:
            response = b"0004test"
            events = (
                event("downstream-request", requests[0]),
                event("proxy-to-upstream-request", requests[0]),
                event("upstream-to-proxy-status", b"OKAY"),
                event("proxy-to-downstream-status", b"OKAY"),
                event("upstream-to-proxy-protocol-string", response),
                event("proxy-to-downstream-protocol-string", response),
                event("upstream-eof", b""),
                event("downstream-eof", b""),
            )
        return self.m.ConnectionTrace(
            index=index,
            peer=self.peer,
            events=events,
            upstream=self.upstream if expectation.upstream else None,
            reconnect_count=0,
        )

    def trace(self, ordinal):
        expectations = self.m.expected_connections(ordinal, self.serial)
        connections = tuple(
            self.connection(index, expectation)
            for index, expectation in enumerate(expectations, 1)
        )
        return self.m.ProxyTrace(
            ordinal=ordinal,
            child=self.child,
            held_adb=self.held_adb,
            connections=connections,
            command_attempt_count=1,
            accepted_connection_count=len(expectations),
            upstream_connection_count=sum(item.upstream for item in expectations),
        )

    def assert_rejected(self, trace, pattern=None, server=None):
        with self.assertRaisesRegex(
            self.m.AdbProxyV1Error, pattern or ".*"
        ):
            self.m.validate_proxy_trace(trace, self.serial, server or self.server)

    def mutate_connection(self, trace, position, **changes):
        values = list(trace.connections)
        values[position] = replace(values[position], **changes)
        return replace(trace, connections=tuple(values))

    def mutate_event(self, trace, connection_position, event_position, **changes):
        connection = trace.connections[connection_position]
        events = list(connection.events)
        events[event_position] = replace(events[event_position], **changes)
        return self.mutate_connection(
            trace, connection_position, events=tuple(events)
        )

    def test_render_plan_is_exact_inactive_h0(self):
        plan = self.m.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_MODEL_PASS_GO_NOT_ACTIVE",
        )
        self.assertEqual(plan["target"], {
            "model": "SM-G986N",
            "device": "y2q",
            "product": "y2qksx",
            "build": "G986NKSS8IYC2",
        })
        self.assertTrue(plan["gates"])
        self.assertFalse(any(plan["gates"].values()))
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["connected_backends"], [])
        self.assertFalse(plan["authority"]["device_contact"])
        self.assertFalse(plan["authority"]["adb_executed"])
        self.assertFalse(plan["authority"]["real_socket_or_network_used"])
        self.assertFalse(plan["authority"]["live_authority"])

    def test_self_normalized_anchor_is_exact(self):
        self.assertEqual(
            self.m.normalized_source_sha256(self.source),
            self.m.EXPECTED_SELF_NORMALIZED_SHA256,
        )
        self.assertEqual(
            self.m.render_plan()["self"]["sha256"],
            self.m.sha256_bytes(self.source),
        )
        transitioned, status_count = re.subn(
            rb'^STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_MODEL_PASS_GO_NOT_ACTIVE"$',
            b'STATUS = "REVIEWED_NOT_ACTIVE"',
            self.source,
            count=1,
            flags=re.MULTILINE,
        )
        self.assertEqual(status_count, 1)
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

    def test_exact_phase_runtime_and_adb_identities_are_pinned(self):
        for identity in (self.m.PHASE_A_IDENTITY, self.m.RUNTIME_IDENTITY):
            payload = Path(identity["path"]).read_bytes()
            self.assertEqual(len(payload), identity["size"])
            self.assertEqual(self.m.sha256_bytes(payload), identity["sha256"])
        adb = Path(self.m.ADB_IDENTITY["path"])
        self.assertEqual(adb.resolve(), Path(self.m.ADB_IDENTITY["canonical_realpath"]))
        payload = adb.read_bytes()
        self.assertEqual(len(payload), self.m.ADB_IDENTITY["size"])
        self.assertEqual(self.m.sha256_bytes(payload), self.m.ADB_IDENTITY["sha256"])
        self.assertEqual(self.m.ADB_IDENTITY["server_version_hex"], "0029")

    def test_cli_is_render_only(self):
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

    def test_all_true_gates_still_reach_unimplemented_stub(self):
        patches = [
            mock.patch.object(self.m, name, True)
            for name in self.m.NORMALIZED_GATE_NAMES
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        with self.assertRaisesRegex(
            self.m.AdbProxyV1Error, "executor is not implemented"
        ):
            self.m.attended_open_and_read()

    def test_false_gate_stops_before_any_model_operation(self):
        with mock.patch.object(
            self.m, "expected_connections", side_effect=AssertionError("protocol touched")
        ):
            with self.assertRaisesRegex(self.m.AdbProxyV1Error, "inactive"):
                self.m.attended_open_and_read()

    def test_protocol_sequences_are_closed_per_ordinal(self):
        self.assertEqual(self.m.expected_connections(1, self.serial), ())
        for ordinal in (2, 3, 4, 5, 6):
            sequence = self.m.expected_connections(ordinal, self.serial)
            self.assertEqual(len(sequence), 2)
            self.assertEqual(sequence[0].services, ("host:version",))
            self.assertFalse(sequence[0].upstream)
            self.assertTrue(sequence[1].upstream)
        self.assertEqual(
            self.m.upstream_allowlist(2, self.serial), ("host:devices-l",)
        )
        self.assertEqual(
            self.m.upstream_allowlist(3, self.serial),
            (f"host-serial:{self.serial}:get-devpath",),
        )
        self.assertEqual(
            self.m.upstream_allowlist(4, self.serial),
            (f"host:tport:serial:{self.serial}", self.m.EXEC_SERVICE),
        )
        self.assertEqual(
            self.m.upstream_allowlist(5, self.serial),
            self.m.upstream_allowlist(4, self.serial),
        )
        self.assertEqual(
            self.m.upstream_allowlist(6, self.serial), ("host:devices-l",)
        )

    def test_host_version_response_is_exact_0029_and_never_forwarded(self):
        self.assertEqual(self.m.LOCAL_VERSION_RESPONSE, b"OKAY00040029")
        for ordinal in range(1, 7):
            result = self.m.validate_proxy_trace(
                self.trace(ordinal), self.serial, self.server
            )
            self.assertFalse(result["host_version_forwarded"])
            self.assertFalse(result["upstream_version_frame_forwarded"])
            self.assertNotIn("host:version", result["forwarded_services"])

    def test_every_exact_ordinal_trace_accepts_once(self):
        for ordinal in range(1, 7):
            result = self.m.validate_proxy_trace(
                self.trace(ordinal), self.serial, self.server
            )
            self.assertTrue(result["accepted"])
            self.assertEqual(result["command_attempt_count"], 1)
            self.assertEqual(result["reconnects"], 0)
            self.assertFalse(result["host_kill_forwarded"])
            self.assertFalse(result["host_start_server_forwarded"])

    def test_fragmented_frames_are_reassembled_by_audit_decoder_only(self):
        wire = self.m.encode_request("host:devices-l")
        self.assertEqual(
            self.m.decode_request_stream((wire[:1], wire[1:4], wire[4:8], wire[8:])),
            ("host:devices-l",),
        )
        plan = self.m.render_plan()
        self.assertFalse(plan["wire_event_model"]["incremental_socket_parser_implemented"])
        self.assertTrue(plan["wire_event_model"]["post_run_audit_only"])

    def test_partial_length_and_payload_at_eof_are_rejected(self):
        for chunks in ((b"00",), (b"000fhost:dev",)):
            with self.subTest(chunks=chunks):
                with self.assertRaisesRegex(self.m.AdbProxyV1Error, "partial"):
                    self.m.decode_request_stream(chunks)

    def test_oversize_malformed_and_empty_frames_are_rejected(self):
        samples = (
            (b"1001",),
            (b"0000",),
            (b"000Gxxxx",),
            (b"0004a\x00bc",),
            (b"0001\xff",),
            (b"",),
        )
        for chunks in samples:
            with self.subTest(chunks=chunks):
                with self.assertRaises(self.m.AdbProxyV1Error):
                    self.m.decode_request_stream(chunks)

    def test_serial_grammar_and_ordinal_type_are_exact(self):
        for serial in ("", "../device", " serial", "x" * 129, None):
            with self.subTest(serial=serial):
                with self.assertRaises(self.m.AdbProxyV1Error):
                    self.m.expected_connections(2, serial)
        for ordinal in (0, 7, True, "2"):
            with self.subTest(ordinal=ordinal):
                with self.assertRaises(self.m.AdbProxyV1Error):
                    self.m.expected_connections(ordinal, self.serial)

    def test_wrong_so_peercred_source_pid_uid_or_gid_is_rejected(self):
        trace = self.trace(2)
        variants = (
            replace(self.peer, source="CALLER"),
            replace(self.peer, pid=self.peer.pid + 1),
            replace(self.peer, uid=self.peer.uid + 1),
            replace(self.peer, gid=self.peer.gid + 1),
            replace(self.peer, process_start_ticks=self.peer.process_start_ticks + 1),
            replace(self.peer, direct_child_pidfd_bound=False),
        )
        for peer in variants:
            with self.subTest(peer=peer):
                changed = tuple(replace(item, peer=peer) for item in trace.connections)
                self.assert_rejected(replace(trace, connections=changed), "peer")

    def test_host_kill_and_start_server_attempts_are_rejected_before_forward(self):
        for forbidden in ("host:kill", "host:start-server"):
            with self.subTest(forbidden=forbidden):
                trace = self.trace(2)
                wire = self.m.encode_request(forbidden)
                trace = self.mutate_event(trace, 1, 0, payload=wire)
                self.assert_rejected(trace, "forbidden ADB service")

    def test_unexpected_and_repeated_service_frames_are_rejected(self):
        trace = self.trace(2)
        unexpected = self.m.encode_request("host:devices")
        unexpected_trace = self.mutate_event(trace, 1, 0, payload=unexpected)
        unexpected_trace = self.mutate_event(
            unexpected_trace, 1, 1, payload=unexpected
        )
        self.assert_rejected(
            unexpected_trace,
            "frame sequence",
        )
        repeated = self.m.encode_request("host:devices-l") * 2
        repeated_trace = self.mutate_event(trace, 1, 0, payload=repeated)
        repeated_trace = self.mutate_event(repeated_trace, 1, 1, payload=repeated)
        self.assert_rejected(
            repeated_trace,
            "repeated",
        )

    def test_third_frame_is_rejected_as_excess(self):
        wire = self.m.encode_request("host:devices-l") * 3
        with self.assertRaisesRegex(self.m.AdbProxyV1Error, "excess"):
            self.m.decode_request_stream((wire,))

    def test_partial_and_oversize_trace_frames_are_rejected(self):
        trace = self.trace(2)
        for wire in (b"000fhost:dev", b"1001"):
            with self.subTest(wire=wire):
                self.assert_rejected(
                    self.mutate_event(trace, 1, 0, payload=wire)
                )

    def test_extra_event_nonempty_eof_and_wrong_local_version_are_rejected(self):
        trace = self.trace(2)
        connection = trace.connections[1]
        self.assert_rejected(
            self.mutate_connection(
                trace,
                1,
                events=connection.events + (self.m.WireEvent("downstream-eof", b""),),
            ),
            "event order",
        )
        self.assert_rejected(
            self.mutate_event(trace, 1, 7, payload=b"x"),
            "EOF",
        )
        self.assert_rejected(
            self.mutate_event(trace, 0, 1, payload=b"OKAY00040028"),
            "host:version isolation",
        )

    def test_version_connection_can_never_have_an_upstream(self):
        trace = self.trace(2)
        self.assert_rejected(
            self.mutate_connection(trace, 0, upstream=self.upstream),
            "host:version isolation",
        )

    def test_upstream_forwarding_and_statuses_are_byte_exact(self):
        trace = self.trace(4)
        self.assert_rejected(
            self.mutate_event(trace, 1, 7, payload=b"0004nope"),
            "second upstream request relay bytes",
        )
        self.assert_rejected(
            self.mutate_event(trace, 1, 8, payload=b"FAIL"),
            "second upstream status relay",
        )
        self.assert_rejected(
            self.mutate_event(trace, 1, 11, payload=b"changed"),
            "output relay bytes",
        )

    def test_tport_reply_requires_exact_nonzero_uint64le_before_exec(self):
        trace = self.trace(4)
        for raw in (b"", b"\x01" * 7, b"\x01" * 9, b"\x00" * 8):
            with self.subTest(raw=raw):
                self.assert_rejected(
                    self.mutate_event(trace, 1, 4, payload=raw),
                    "transport-id",
                )
        self.assert_rejected(
            self.mutate_event(
                trace, 1, 4, kind="downstream-request"
            ),
            "event order",
        )

    def test_non_tport_services_reject_transport_id_bytes(self):
        trace = self.trace(2)
        connection = trace.connections[1]
        events = list(connection.events)
        events.insert(
            4,
            self.m.WireEvent(
                "upstream-to-proxy-transport-id", (1).to_bytes(8, "little")
            ),
        )
        self.assert_rejected(
            self.mutate_connection(trace, 1, events=tuple(events)),
            "event order",
        )

    def test_partial_status_protocol_string_and_wrong_response_relay_reject(self):
        query = self.trace(2)
        self.assert_rejected(
            self.mutate_event(query, 1, 2, payload=b"OK"), "status relay"
        )
        self.assert_rejected(
            self.mutate_event(query, 1, 4, payload=b"0005test"),
            "partial",
        )
        self.assert_rejected(
            self.mutate_event(query, 1, 5, payload=b"0004nope"),
            "protocol-string relay",
        )

    def test_oversize_output_wrong_output_relay_and_nonempty_eof_reject(self):
        execution = self.trace(4)
        oversized = b"x" * (self.m.MAX_RELAY_OUTPUT_BYTES + 1)
        self.assert_rejected(
            self.mutate_event(execution, 1, 10, payload=oversized),
            "output exceeds",
        )
        self.assert_rejected(
            self.mutate_event(execution, 1, 11, payload=b"different"),
            "output relay",
        )
        self.assert_rejected(
            self.mutate_event(execution, 1, 12, payload=b"x"),
            "EOF choreography",
        )

    def test_missing_upstream_proof_is_rejected(self):
        trace = self.trace(2)
        self.assert_rejected(
            self.mutate_connection(trace, 1, upstream=None),
            "proof is absent",
        )

    def test_upstream_owner_proof_precedes_first_wire_event_validation(self):
        trace = self.mutate_connection(self.trace(2), 1, upstream=None)
        with mock.patch.object(
            self.m,
            "_validate_ordered_events",
            wraps=self.m._validate_ordered_events,
        ) as validator:
            self.assert_rejected(trace, "proof is absent")
            self.assertEqual(validator.call_count, 1)  # local version only

    def test_upstream_peer_pid_uid_start_listener_and_peer_inode_drift_reject(self):
        variants = (
            replace(self.upstream, server_pid=self.server.pid + 1),
            replace(self.upstream, server_uid=self.server.uid + 1),
            replace(self.upstream, server_start_ticks=self.server.start_ticks + 1),
            replace(self.upstream, server_listener_inode=self.server.listener_inode + 1),
            replace(self.upstream, server_peer_inode=7999),
        )
        for upstream in variants:
            with self.subTest(upstream=upstream):
                trace = self.mutate_connection(self.trace(2), 1, upstream=upstream)
                self.assert_rejected(trace, "owner|owned")

    def test_upstream_connection_tuple_and_inode_role_drift_reject(self):
        variants = (
            replace(self.upstream, family="AF_UNIX"),
            replace(self.upstream, state="LISTEN"),
            replace(self.upstream, peer_address="127.0.0.2"),
            replace(self.upstream, peer_port=5038),
            replace(self.upstream, server_observed_peer_port=42112),
            replace(self.upstream, server_observed_peer_address="127.0.0.2"),
            replace(self.upstream, server_local_port=5038),
            replace(self.upstream, held_proxy_fd_inode=9002),
            replace(self.upstream, proxy_socket_inode=self.server.listener_inode),
            replace(self.upstream, proxy_socket_inode=self.upstream.server_peer_inode),
            replace(self.upstream, server_peer_inode=self.server.listener_inode),
        )
        for upstream in variants:
            with self.subTest(upstream=upstream):
                trace = self.mutate_connection(self.trace(2), 1, upstream=upstream)
                self.assert_rejected(trace)

    def test_bound_server_exact_adb_identity_is_required(self):
        for server in (
            replace(self.server, executable_sha256="0" * 64),
            replace(self.server, executable_size=self.server.executable_size + 1),
            replace(self.server, listener_inode=0),
            replace(self.server, pid=True),
            replace(self.server, pidfd_bound=False),
        ):
            with self.subTest(server=server):
                self.assert_rejected(self.trace(2), server=server)

    def test_server_and_direct_child_owner_roles_compose_exactly(self):
        self.assert_rejected(
            self.trace(2),
            "effective uid differ",
            server=replace(self.server, uid=0),
        )
        self.assert_rejected(
            self.trace(2),
            "pid roles overlap",
            server=replace(self.server, pid=self.child.pid),
        )

    def test_server_executable_must_equal_separate_held_adb_owner(self):
        trace = self.trace(2)
        self.assert_rejected(
            replace(trace, held_adb=replace(self.held_adb, inode=8002)),
            "server executable",
        )
        proof = replace(
            self.upstream,
            observed_owner_fd_inodes=((18, self.server.listener_inode), (19, 7002)),
        )
        self.assert_rejected(
            self.mutate_connection(trace, 1, upstream=proof),
            "owned by bound server",
        )
        reused_fd = replace(
            self.upstream,
            server_peer_fd=self.server.listener_fd,
            observed_owner_fd_inodes=(
                (self.server.listener_fd, self.server.listener_inode),
                (self.server.listener_fd, self.upstream.server_peer_inode),
            ),
        )
        self.assert_rejected(
            self.mutate_connection(trace, 1, upstream=reused_fd),
            "overlap|owned by bound server",
        )

    def test_reconnect_or_repeated_connection_is_rejected(self):
        trace = self.trace(2)
        self.assert_rejected(
            self.mutate_connection(trace, 1, reconnect_count=1), "reconnect"
        )
        self.assert_rejected(
            replace(
                trace,
                connections=trace.connections + (trace.connections[1],),
                accepted_connection_count=3,
            ),
            "connection count|sequence",
        )

    def test_one_command_attempt_and_exact_connection_counters_are_required(self):
        trace = self.trace(2)
        variants = (
            replace(trace, command_attempt_count=2),
            replace(trace, accepted_connection_count=1),
            replace(trace, upstream_connection_count=2),
        )
        for value in variants:
            with self.subTest(value=value):
                self.assert_rejected(value)

    def test_connection_order_and_indices_are_exact(self):
        trace = self.trace(2)
        self.assert_rejected(
            replace(trace, connections=tuple(reversed(trace.connections))), "index"
        )
        self.assert_rejected(
            self.mutate_connection(trace, 0, index=2), "index"
        )

    def test_exec_service_is_fixed_snapshot_and_bounded(self):
        self.assertTrue(self.m.EXEC_SERVICE.startswith("exec:sh '-c' "))
        self.assertEqual(self.m._adb_escape_arg("-c"), "'-c'")
        self.assertEqual(self.m._adb_escape_arg("a'b"), "'a'\\''b'")
        self.assertEqual(
            self.m.EXEC_SERVICE,
            "exec:sh '-c' " + self.m._adb_escape_arg(self.m.REMOTE_SNAPSHOT),
        )
        self.assertEqual(len(self.m.REMOTE_SNAPSHOT.encode()), 1_472)
        self.assertEqual(
            self.m.sha256_bytes(self.m.REMOTE_SNAPSHOT.encode()),
            self.m.REMOTE_SNAPSHOT_SHA256,
        )
        self.assertEqual(len(self.m.EXEC_SERVICE.encode()), 1_523)
        self.assertEqual(
            self.m.sha256_bytes(self.m.EXEC_SERVICE.encode()),
            self.m.EXEC_SERVICE_SHA256,
        )
        self.assertIn("ro.product.model", self.m.EXEC_SERVICE)
        self.assertIn("/proc/sys/kernel/random/boot_id", self.m.EXEC_SERVICE)
        self.assertLessEqual(
            len(self.m.EXEC_SERVICE.encode("utf-8")), self.m.MAX_SERVICE_BYTES
        )
        self.assertEqual(
            self.m.expected_connections(4, self.serial)[1].services[1],
            self.m.expected_connections(5, self.serial)[1].services[1],
        )

    def test_fixed_snapshot_equals_exact_pinned_phase_a_literal(self):
        tree = ast.parse(Path(self.m.PHASE_A_IDENTITY["path"]).read_text())
        values = []
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(
                isinstance(target, ast.Name) and target.id == "REMOTE_SNAPSHOT"
                for target in node.targets
            ):
                values.append(ast.literal_eval(node.value))
        self.assertEqual(values, [self.m.REMOTE_SNAPSHOT])

    def test_seccomp_policy_is_structural_and_unimplemented(self):
        policy = self.m.render_plan()["seccomp_policy_model"]
        self.assertFalse(policy["implemented"])
        self.assertFalse(policy["installed"])
        self.assertEqual(policy["initial_transition"]["syscall"], "execveat")
        self.assertEqual(policy["initial_transition"]["path"], "empty")
        self.assertEqual(policy["initial_transition"]["flags"], "AT_EMPTY_PATH")
        self.assertEqual(policy["initial_transition"]["maximum_successes"], 1)
        self.assertTrue(policy["filter_installed_before_child_exec"])
        self.assertFalse(policy["classic_filter_is_stateful"])
        self.assertTrue(policy["held_adb_fd_cloexec_close_required"])
        self.assertEqual(
            policy["followup_execveat_success_impossible"],
            "UNPROVED_REQUIRED_INVARIANT",
        )
        self.assertFalse(policy["fd_number_reuse_bypass_closed"])
        self.assertEqual(
            set(policy["unconditionally_denied"]),
            {"clone", "clone3", "fork", "vfork", "execve", "bind", "listen"},
        )
        self.assertFalse(policy["classic_filter_is_stateful"])
        self.assertFalse(policy["filter_bytes_pinned"])

    def test_private_proxy_shape_has_no_caller_path_or_reconnect(self):
        proxy = self.m.render_plan()["private_proxy"]
        self.assertEqual(proxy["family"], "AF_UNIX")
        self.assertEqual(proxy["parent_mode"], "0700")
        self.assertFalse(proxy["caller_supplied_path"])
        self.assertEqual(proxy["reconnects"], 0)
        self.assertFalse(proxy["implemented"])
        version = self.m.render_plan()["version_isolation"]
        self.assertTrue(
            version["unavailable_proxy_can_trigger_local_server_launch_attempt"]
        )
        self.assertEqual(
            version["launch_attempt_blocked_only_by_preinstalled_seccomp"],
            "DESIGNED_NOT_IMPLEMENTED_OR_PROVED",
        )
        self.assertFalse(version["upstream_version_frame_forwarded"])
        self.assertFalse(version["separate_upstream_version_connection"])
        self.assertIn("exact-held-ADB-executable", version["server_version_basis"])

    def test_source_has_no_socket_subprocess_or_connected_entrypoint(self):
        text = self.source.decode("utf-8")
        self.assertNotIn("import socket", text)
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("--connected", text)
        self.assertNotIn("os.system", text)
        self.assertNotIn("Popen(", text)
        self.assertNotIn("create_connection(", text)
        self.assertNotIn("socket.socket(", text)


if __name__ == "__main__":
    unittest.main()
