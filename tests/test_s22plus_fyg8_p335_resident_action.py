from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import threading
import unittest
from unittest import mock
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p335_resident_action.py"
)
ACTIVATION = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p335_resident_action_v1.json"
)
SCRIPTS = SOURCE.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from tests import test_s22plus_fyg8_p335_retained_listener_acm_observer as fixture  # noqa: E402


def load_module():
    spec = importlib.util.spec_from_file_location("p335_action_test", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P335 action runner import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeLease:
    def __init__(self, events: list[str]):
        self.events = events
        self.actions = []

    def snapshot(self):
        return {
            "state": "ACTIVE",
            "rollback_required": False,
            "actions_started": 0,
            "actions_completed": 0,
            "actions_remaining": 16,
        }

    def begin_action(self, action, _binding):
        self.events.append("intent")
        return {"action": action, "ordinal": 1}

    def record_action_result(self, _intent, result, _binding):
        self.events.append("result:" + result["status"])


class P335ResidentActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_activation_is_canonical_and_audit_is_host_only(self):
        value = json.loads(ACTIVATION.read_text())
        self.assertEqual(ACTIVATION.read_bytes(), self.module.canonical(value))
        checked = self.module.validate_activation(require_pass=False)
        self.assertEqual(checked["value"], value)
        self.assertEqual(
            value["independent_review"],
            {
                "status": "pass-go",
                "verdict": "PASS_GO_P335_RESIDENT_ACTION_RUNNER_H0_V1",
            },
        )
        self.assertEqual(
            value["inputs"]["runner"]["sha256"],
            hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        )
        result = self.module.audit()
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["live_authorized"])

    def test_activation_rejects_boolean_integer_substitution(self):
        self.assertFalse(
            self.module._typed_equal(
                {"session": {"commands_per_session": 3}},
                {"session": {"commands_per_session": True}},
            )
        )

    def test_session_evidence_marks_one_primary_and_all_supporting_results(self):
        commands = []
        for index, command in enumerate(self.module.runtime.DEFAULT_COMMANDS):
            commands.append(
                SimpleNamespace(
                    command=command,
                    output=f"output-{index}\n".encode(),
                    exit_code=0,
                    signal_number=0,
                    duration_ms=index + 1,
                    ok=True,
                )
            )
        record = SimpleNamespace(
            boot_id=b"B" * 32,
            nonce=b"N" * 32,
            authenticated=True,
            clean_close=True,
            result=SimpleNamespace(commands=commands),
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            action_dir = base / "action-01"
            action_dir.mkdir()
            with mock.patch.object(self.module, "ROOT", base):
                value, payload = self.module._session_evidence(
                    "kernel", 1, record, b"tx", b"rx", action_dir
                )
        self.assertEqual(sum(item["primary"] for item in value["commands"]), 1)
        self.assertTrue(value["commands"][1]["primary"])
        self.assertEqual(value["fixed_command_count"], 3)
        self.assertTrue(value["full_protocol_tuple"])
        self.assertEqual(json.loads(payload), value)

    def test_action_orders_intent_before_one_full_session(self):
        events: list[str] = []
        lease = FakeLease(events)
        endpoint = SimpleNamespace(identity_sha256="e" * 64, tty_class=Path("/unused"))
        binding = {"per_boot_id": hashlib.sha256(b"B" * 32).hexdigest()}
        value = {
            "commands": [
                {"name": name, "primary": name == "identity"}
                for name in self.module.resident.ACTION_NAMES
            ]
        }
        record = SimpleNamespace(boot_id=b"B" * 32)
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary) / "evidence"

            def exchange(*_args):
                events.append("exchange")
                return record, b"tx", b"rx"

            with (
                mock.patch.object(self.module, "EVIDENCE_DIR", evidence_dir),
                mock.patch.object(
                    self.module,
                    "validate_activation",
                    return_value={"receipt": {"size": 1, "sha256": "a" * 64}},
                ),
                mock.patch.object(
                    self.module,
                    "_current_context",
                    return_value=(
                        SimpleNamespace(), lease, binding, b"K" * 32, set()
                    ),
                ),
                mock.patch.object(
                    self.module,
                    "_select_endpoint",
                    return_value=(endpoint, {}),
                ),
                mock.patch.object(
                    self.module.cdc,
                    "_udev_properties",
                    return_value={
                        "ID_MM_DEVICE_IGNORE": "1",
                        "ID_MM_PORT_IGNORE": "1",
                        "ID_USB_INTERFACE_NUM": "00",
                    },
                ),
                mock.patch.object(
                    self.module, "_exchange_full_tuple", side_effect=exchange
                ) as exchanged,
                mock.patch.object(
                    self.module,
                    "_session_evidence",
                    return_value=(value, b"{}\n"),
                ),
                mock.patch.object(
                    self.module,
                    "_write_once",
                    return_value={"path": "result", "size": 3, "sha256": "b" * 64},
                ),
                mock.patch.object(
                    self.module.resident.ResidentLease,
                    "open",
                    return_value=lease,
                ),
            ):
                result = self.module.run_action("identity")
        self.assertEqual(events, ["intent", "exchange", "result:ok"])
        exchanged.assert_called_once()
        self.assertEqual(result["ordinal"], 1)
        self.assertEqual(result["action"], "identity")

    def test_post_intent_failure_is_uncertain_and_not_replayed(self):
        events: list[str] = []
        lease = FakeLease(events)
        endpoint = SimpleNamespace(identity_sha256="e" * 64, tty_class=Path("/unused"))
        binding = {"per_boot_id": "b" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary) / "evidence"
            with (
                mock.patch.object(self.module, "EVIDENCE_DIR", evidence_dir),
                mock.patch.object(
                    self.module,
                    "validate_activation",
                    return_value={"receipt": {}},
                ),
                mock.patch.object(
                    self.module,
                    "_current_context",
                    return_value=(
                        SimpleNamespace(), lease, binding, b"K" * 32, set()
                    ),
                ),
                mock.patch.object(
                    self.module,
                    "_select_endpoint",
                    return_value=(endpoint, {}),
                ),
                mock.patch.object(
                    self.module.cdc,
                    "_udev_properties",
                    return_value={
                        "ID_MM_DEVICE_IGNORE": "1",
                        "ID_MM_PORT_IGNORE": "1",
                        "ID_USB_INTERFACE_NUM": "00",
                    },
                ),
                mock.patch.object(
                    self.module,
                    "_exchange_full_tuple",
                    side_effect=OSError("fixture cut"),
                ),
                mock.patch.object(
                    self.module,
                    "_write_once",
                    return_value={"size": 10, "sha256": "c" * 64},
                ),
            ):
                with self.assertRaisesRegex(
                    self.module.ActionError, "rollback is required"
                ):
                    self.module.run_action("kernel")
        self.assertEqual(events, ["intent", "result:uncertain"])

    def test_boot_digest_mismatch_stops_before_first_exec(self):
        sent: list[int] = []
        diagnostics = [
            SimpleNamespace(stage=0, code=0),
            SimpleNamespace(stage=1, code=0),
            SimpleNamespace(stage=2, code=0),
        ]

        def send(_fd, frame_type, *_args):
            sent.append(frame_type)

        with (
            mock.patch.object(
                self.module.observer._CODEC, "_validate_key", return_value=b"K" * 32
            ),
            mock.patch.object(
                self.module.observer._CODEC,
                "_read_exact",
                return_value=self.module.runtime.DEVICE_BANNER,
            ),
            mock.patch.object(
                self.module.observer._CODEC,
                "_read_frame",
                side_effect=[object(), object(), object(), object(), object(), object()],
            ),
            mock.patch.object(
                self.module.observer._P333,
                "parse_diagnostic_frame",
                side_effect=diagnostics,
            ),
            mock.patch.object(
                self.module.observer._CODEC,
                "_expect",
                side_effect=[b"N" * 32, b"R" * 32],
            ),
            mock.patch.object(self.module.observer._CODEC, "_validate_nonce"),
            mock.patch.object(
                self.module.observer._CODEC,
                "constant_time_equal",
                return_value=True,
            ),
            mock.patch.object(self.module.observer._CODEC, "_send", side_effect=send),
            mock.patch.object(
                self.module.observer,
                "decode_boot_id_frame",
                return_value=b"B" * 32,
            ),
            mock.patch.object(
                self.module.observer,
                "_raise_partial",
                side_effect=self.module.observer.AuthObserverError("fixture stop"),
            ),
        ):
            with self.assertRaises(self.module.observer.AuthObserverError):
                self.module._exchange_before_exec_bound(
                    9,
                    b"K" * 32,
                    self.module.observer._RawWriter(None),
                    hashlib.sha256(b"C" * 32).hexdigest(),
                    set(),
                )
        self.assertEqual(
            sent,
            [self.module.runtime.FRAME_OPEN, self.module.runtime.FRAME_AUTH],
        )

    def test_real_codec_full_tuple_checks_boot_before_commands(self):
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        helper = fixture.P335RetainedListenerObserverTests(
            "test_two_same_fd_sessions_then_one_physical_reopen"
        )
        thread = threading.Thread(
            target=helper._serve_sessions,
            args=(peer, (fixture.NONCES[0],), errors),
        )
        thread.start()
        try:
            result = self.module._exchange_before_exec_bound(
                host.fileno(),
                fixture.TEST_KEY,
                self.module.observer._RawWriter(None),
                hashlib.sha256(fixture.BOOT_ID).hexdigest(),
                set(),
            )
        finally:
            host.close()
            thread.join(timeout=5)
            peer.close()
        self.assertFalse(errors)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(result.commands), 3)
        self.assertTrue(all(command.ok for command in result.commands))
        self.assertEqual(
            hashlib.sha256(result.audit.boot_id).hexdigest(),
            hashlib.sha256(fixture.BOOT_ID).hexdigest(),
        )

    def test_replayed_challenge_stops_before_auth_and_exec(self):
        sent: list[int] = []
        diagnostics = [
            SimpleNamespace(stage=0, code=0),
            SimpleNamespace(stage=1, code=0),
            SimpleNamespace(stage=2, code=0),
        ]
        nonce = b"N" * 32
        with (
            mock.patch.object(
                self.module.observer._CODEC, "_validate_key", return_value=b"K" * 32
            ),
            mock.patch.object(
                self.module.observer._CODEC,
                "_read_exact",
                return_value=self.module.runtime.DEVICE_BANNER,
            ),
            mock.patch.object(
                self.module.observer._CODEC,
                "_read_frame",
                side_effect=[object(), object(), object(), object()],
            ),
            mock.patch.object(
                self.module.observer._P333,
                "parse_diagnostic_frame",
                side_effect=diagnostics,
            ),
            mock.patch.object(
                self.module.observer._CODEC, "_expect", return_value=nonce
            ),
            mock.patch.object(self.module.observer._CODEC, "_validate_nonce"),
            mock.patch.object(
                self.module.observer._CODEC,
                "_send",
                side_effect=lambda _fd, kind, *_args: sent.append(kind),
            ),
            mock.patch.object(
                self.module.observer,
                "_raise_partial",
                side_effect=self.module.observer.AuthObserverError("fixture replay"),
            ),
        ):
            with self.assertRaises(self.module.observer.AuthObserverError):
                self.module._exchange_before_exec_bound(
                    9,
                    b"K" * 32,
                    self.module.observer._RawWriter(None),
                    hashlib.sha256(fixture.BOOT_ID).hexdigest(),
                    {hashlib.sha256(nonce).hexdigest()},
                )
        self.assertEqual(sent, [self.module.runtime.FRAME_OPEN])


if __name__ == "__main__":
    unittest.main()
