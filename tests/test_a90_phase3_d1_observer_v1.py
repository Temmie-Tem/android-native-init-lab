"""Focused host-only tests for the Phase 3 D1 live observer."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for path in (SERVER_DIR, REVAL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import a90_phase3_d1_observer_v1 as observer  # noqa: E402


def ready_marker(*, pid: str = "321") -> str:
    return "\n".join(
        (
            "schema=a90-debian-network-ssh-v1-ready",
            "owner=debian-sysvinit",
            "pid1_exe=/usr/sbin/init",
            "ncm_ifname=ncm0",
            "ncm_address=192.168.7.2/24",
            "ncm_peer=192.168.7.1",
            f"dropbear_pid={pid}",
            "dropbear_listen=192.168.7.2:2222",
            "dropbear_auth=public-key-only",
            "dropbear_forwarding=disabled",
        )
    ) + "\n"


def proof_transcript(
    *,
    failure: str = "",
    failure_absent: str = "1",
    live_owner: str = "1",
) -> str:
    return (
        f"{observer.READY_BEGIN}\n"
        f"{ready_marker()}"
        f"{observer.READY_END}\n"
        f"{observer.FAILURE_BEGIN}\n"
        f"{failure}"
        f"{observer.FAILURE_END}\n"
        f"{observer.LIVE_BEGIN}\n"
        "pid1_exe=/usr/sbin/init\n"
        "dropbear_pid=321\n"
        "dropbear_exe=/usr/sbin/dropbear\n"
        "listener_count=1\n"
        "listener_endpoint=1\n"
        f"listener_owner={live_owner}\n"
        f"failure_absent={failure_absent}\n"
        f"{observer.LIVE_END}\n"
    )


class A90Phase3D1ObserverV1Tests(unittest.TestCase):
    def spec(self) -> SimpleNamespace:
        return SimpleNamespace(
            observer_key=Path("/private/observer-key"),
            observer_port=2222,
            observer_device="192.168.7.2",
            handoff_attempt_limit=1,
        )

    def args(self) -> SimpleNamespace:
        return SimpleNamespace(ssh_connect_timeout=8.0)

    def test_ready_marker_is_exact_and_adversarial_mutations_fail(self) -> None:
        self.assertEqual(
            observer.validate_ready_marker(ready_marker())["dropbear_pid"],
            "321",
        )
        mutations = (
            ready_marker(pid="0"),
            ready_marker(pid="+1"),
            ready_marker().replace("owner=debian-sysvinit", "owner=native-init"),
            ready_marker().replace(
                "dropbear_auth=public-key-only\n",
                "dropbear_auth=public-key-only\ndropbear_auth=public-key-only\n",
            ),
            ready_marker().replace("dropbear_forwarding=disabled\n", ""),
            ready_marker().replace("\n", "\r\n"),
            ready_marker().removesuffix("\n"),
        )
        for value in mutations:
            with self.subTest(value=value[:80]), self.assertRaises(
                observer.ContractError
            ):
                observer.validate_ready_marker(value)

    def test_live_probe_requires_current_pid_exe_endpoint_and_owner(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ssh"],
            returncode=0,
            stdout=proof_transcript(),
            stderr="",
        )
        with mock.patch.object(observer.subprocess, "run", return_value=completed):
            value = observer.observe_phase3_service(self.spec(), self.args())
        self.assertTrue(value["proof"])
        self.assertTrue(value["ssh_public_key_session"])
        self.assertTrue(value["listener_live_exact_owner"])

        wrong_owner = subprocess.CompletedProcess(
            args=["ssh"],
            returncode=0,
            stdout=proof_transcript(live_owner="0"),
            stderr="",
        )
        with mock.patch.object(observer.subprocess, "run", return_value=wrong_owner):
            value = observer.observe_phase3_service(self.spec(), self.args())
        self.assertFalse(value["proof"])

    def test_persisted_service_proof_is_reparsed_and_exact(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ssh"],
            returncode=0,
            stdout=proof_transcript(),
            stderr="",
        )
        with mock.patch.object(observer.subprocess, "run", return_value=completed):
            value = observer.observe_phase3_service(self.spec(), self.args())
        self.assertEqual(
            observer.validate_persisted_phase3_service(value),
            value,
        )
        mutations = (
            {**value, "returncode": True},
            {**value, "listener_live_exact_owner": "yes"},
            {**value, "ready_marker": {"proof": True}},
            {
                **value,
                "text": value["text"].replace(
                    "failure_absent=1\n",
                    "failure_absent=0\n",
                ),
            },
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(
                observer.ContractError
            ):
                observer.validate_persisted_phase3_service(mutation)

    def test_failure_marker_or_nonzero_ssh_never_proves(self) -> None:
        for returncode, failure, failure_absent in (
            (0, "schema=a90-debian-network-ssh-v1-failure\n", "0"),
            (0, "", "0"),
            (255, "", "1"),
        ):
            completed = subprocess.CompletedProcess(
                args=["ssh"],
                returncode=returncode,
                stdout=proof_transcript(
                    failure=failure,
                    failure_absent=failure_absent,
                ),
                stderr="",
            )
            with self.subTest(
                returncode=returncode,
                failure=failure,
                failure_absent=failure_absent,
            ), mock.patch.object(
                observer.subprocess,
                "run",
                return_value=completed,
            ):
                self.assertFalse(
                    observer.observe_phase3_service(self.spec(), self.args())["proof"]
                )

    def test_remote_command_is_key_only_and_rechecks_listener_owner(self) -> None:
        command = observer.phase3_ssh_command(self.spec(), self.args())
        self.assertIn("BatchMode=yes", command)
        self.assertIn("IdentitiesOnly=yes", command)
        self.assertIn("PreferredAuthentications=publickey", command)
        self.assertIn("PasswordAuthentication=no", command)
        self.assertIn("KbdInteractiveAuthentication=no", command)
        self.assertIn("StrictHostKeyChecking=no", command)
        remote = command[-1]
        for token in (
            observer.READY_PATH,
            observer.FAILURE_PATH,
            "/proc/$dropbear_pid/exe",
            "/usr/bin/ss -H -ltnp",
            "listener_count",
            "listener_owner_match",
            "failure_absent",
        ):
            self.assertIn(token, remote)
        for forbidden in ("reboot", "flash", "dd ", "rm -rf", "mkfs"):
            self.assertNotIn(forbidden, remote)

    def test_phase3_service_proof_replaces_legacy_dropbear_marker_fact(self) -> None:
        proven = SimpleNamespace(state=observer.base.display.FactState.PROVEN)
        facts = {
            "native_release": proven,
            "debian_pid1": proven,
            "dropbear": proven,
            "display_acquisition": proven,
        }
        captured: dict[str, object] = {}

        def classify(**kwargs):
            captured.update(kwargs)
            return facts

        with tempfile.TemporaryDirectory() as raw:
            transaction = Path(raw)
            pre_handoff = {"return_epoch_before_handoff": {"exact": True}}
            with mock.patch.object(
                observer.base,
                "run_handoff",
                return_value={"text": "handoff"},
            ), mock.patch.object(
                observer.base,
                "observe_ssh",
                return_value={
                    "native_release_marker_text": "release",
                    "pid1_comm_init": True,
                    "proc1_exe_init": True,
                    "dropbear_started": False,
                    "display_status": "ready",
                },
            ), mock.patch.object(
                observer,
                "observe_phase3_service",
                return_value={"proof": True},
            ), mock.patch.object(
                observer.base.display,
                "classify_phase2_display_facts",
                side_effect=classify,
            ), mock.patch.object(
                observer.base.display,
                "facts_to_dict",
                return_value={"exact": True},
            ), mock.patch.object(
                observer.base,
                "wait_for_candidate_return_attended_once",
                return_value={"proof": True},
            ), mock.patch.object(
                observer.base,
                "collect_and_clear_retained_pmsg",
                return_value={"proof": True},
            ):
                value = observer.observe_attended_after_handoff(
                    self.spec(),
                    self.args(),
                    transaction,
                    pre_handoff,
                )
        self.assertIs(captured["dropbear_started"], True)
        self.assertTrue(value["phase3_service_proven"])
        self.assertTrue(value["display_mechanical_proof"])


if __name__ == "__main__":
    unittest.main()
