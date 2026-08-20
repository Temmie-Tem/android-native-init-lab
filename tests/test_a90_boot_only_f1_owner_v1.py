from __future__ import annotations

import copy
import datetime as dt
import hashlib
import inspect
import os
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "workspace/public/src/scripts/server-distro"
OWNER_PATH = SERVER / "a90_boot_only_f1_owner_v1.py"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import a90_boot_only_f1_contract_v1 as contract  # noqa: E402
import a90_boot_only_f1_observer_v1 as observer_v1  # noqa: E402
import a90_boot_only_f1_owner_v1 as owner  # noqa: E402
import a90_boot_only_f1_runtime_v1 as runtime_v1  # noqa: E402


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def runtime_member(path: Path, file_sha: str) -> dict[str, Any]:
    receipt = {"exact": str(path), "isolated": True}
    receipt_sha = sha(contract.canonical_json(receipt))
    roots = [
        {
            "path": "/fixed/runtime-root",
            "state": "PRESENT_DIRECTORY",
            "fileCount": 1,
            "totalBytes": 7,
            "treeSha256": "a" * 64,
        }
    ]
    libraries = [{"path": "/fixed/lib.so", "size": 7, "sha256": "b" * 64}]
    external_files = [
        {"path": "/fixed/sitecustomize.py", "size": 7, "sha256": "c" * 64}
    ]
    closure = {
        "versionReceiptSha256": receipt_sha,
        "runtimeRoots": roots,
        "externalFiles": external_files,
        "dynamicLibraries": libraries,
    }
    return {
        "path": str(path),
        "size": 1,
        "sha256": file_sha,
        "versionReceipt": receipt,
        "versionReceiptSha256": receipt_sha,
        "runtimeRoots": roots,
        "externalFiles": external_files,
        "dynamicLibraries": libraries,
        "runtimeClosureSha256": sha(contract.canonical_json(closure)),
    }


class ProtocolReceipt:
    def __init__(self, text: str, *, rc: int = 0, status: str = "ok") -> None:
        self.text = text
        self.rc = rc
        self.status = status


def observed_input() -> dict[str, Any]:
    bridge = {
        "selectedDevice": observer_v1.FIXED_BRIDGE_DEVICE,
        "selectedRealpath": "/dev/ttyACM0",
        "usbVendor": "04e8",
        "usbProduct": "6861",
        "bridgeProcessPid": 99,
        "bridgeProcessStartTicks": 100,
        "listenerSocketInode": 200,
        "otherTargetsPresent": 0,
    }
    bridge["receiptSha256"] = observer_v1._receipt_sha(bridge)
    return {
        "schema": observer_v1.OBSERVER_SCHEMA,
        "bridge": bridge,
        "version": observer_v1.command_receipt(
            ["version"], ProtocolReceipt("version: 0.11.192 build=phase3-minimal-h24\n")
        ),
        "selftest": observer_v1.command_receipt(
            ["selftest"],
            ProtocolReceipt("selftest: pass=41 warn=0 fail=0 duration=9ms entries=41\n"),
        ),
        "status": observer_v1.command_receipt(
            ["status"], ProtocolReceipt("pstore=mounted entries=0\n")
        ),
        "bootId": observer_v1.command_receipt(
            ["cat", "/proc/sys/kernel/random/boot_id"],
            ProtocolReceipt("12345678-1234-1234-1234-123456789abc\n"),
        ),
    }


def manifest() -> dict[str, Any]:
    return {
        "schema": contract.MANIFEST_SCHEMA,
        "capability": contract.CAPABILITY,
        "targetProfile": "A90_5G_OPERATOR_OWNED",
        "expectedStart": {
            "version": "0.11.192",
            "build": "phase3-minimal-h24",
            "residentQualificationPath": str(
                REPO / "workspace/public/a90/h24-resident-qualification.json"
            ),
            "residentQualificationSha256": "1" * 64,
        },
        "candidate": {
            "path": str(REPO / "workspace/private/candidate/boot.img"),
            "size": 58_368_000,
            "sha256": "2" * 64,
            "version": "0.11.194",
            "build": "phase3-minimal-h27",
        },
        "rollback": {
            "path": str(REPO / "workspace/private/rollback/boot.img"),
            "size": 60_882_944,
            "sha256": "3" * 64,
            "version": "V2321",
            "build": "native-init-v2321",
        },
        "flashHelper": {
            "path": str(owner.HELPER_PATH),
            "size": owner.SOURCE_PACKAGE_SPEC[0],
            "sha256": owner.SOURCE_PACKAGE_SPEC[1],
        },
        "timeouts": {"recoverySec": 180, "bridgeSec": 60, "healthSec": 240},
        "observation": {"acceptanceRuleSha256": "4" * 64},
        "recovery": {
            "plan": "V2321_BOOT_ONLY",
            "version": "V2321",
            "build": "native-init-v2321",
            "qualificationPath": str(
                REPO / "workspace/public/a90/v2321-recovery-qualification.json"
            ),
            "qualificationSha256": "e" * 64,
        },
        "hazards": [
            {
                "id": "RKP_CFP_DISABLED_RESIDENT",
                "qualificationPath": str(
                    REPO / "workspace/public/a90/h27-hazard-qualification.json"
                ),
                "qualificationSha256": "5" * 64,
            }
        ],
        "ownerClosureSha256": owner.owner_closure_sha256(),
    }


def snapshot(version: str, build: str, boot_identity: str) -> owner.LiveSnapshot:
    return owner.LiveSnapshot(
        target_evidence_sha256="6" * 64,
        boot_id="boot-20260817-a90",
        version=version,
        build=build,
        boot_identity_sha256=boot_identity,
        device_safety_state="RESIDENT_HEALTHY",
        recovery_available=True,
        other_targets_untouched=True,
        receipt_sha256="7" * 64,
    )


class FakeArtifact:
    def __init__(self, role: str) -> None:
        self.identity = {
            "role": role,
            "path": f"/fixed/{role}",
            "dev": 1,
            "ino": len(role) + 1,
            "mode": 0o100600,
            "uid": os.getuid(),
            "gid": os.getgid(),
            "nlink": 1,
            "size": 1,
            "sha256": sha(role.encode()),
        }
        if role in {"python-interpreter", "adb-transport"}:
            self.identity.update(
                versionReceiptSha256="8" * 64,
                runtimeClosureSha256="9" * 64,
            )

    def checkpoint(self) -> dict[str, Any]:
        return dict(self.identity)

    def close(self) -> None:
        return None


class FakeHeldSource:
    def __init__(self, path: Path, role: str) -> None:
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        raw = path.read_bytes()
        self.identity = {
            "role": role,
            "path": str(path),
            "size": len(raw),
            "sha256": sha(raw),
        }

    def checkpoint(self) -> dict[str, Any]:
        metadata = os.fstat(self.fd)
        if metadata.st_size != self.identity["size"]:
            raise contract.ContractError("fake held source size drift")
        if contract.BoundArtifact._hash_fd(self.fd, metadata.st_size) != self.identity["sha256"]:
            raise contract.ContractError("fake held source digest drift")
        return dict(self.identity)

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


class FakeFdExec:
    PROGRAM = "bound-fd-program"

    @classmethod
    def bootstrap_command(
        cls,
        python_executable: Path,
        source_fd: int,
        source_path: Path,
        source_size: int,
        source_sha256: str,
        arguments: tuple[str, ...],
    ) -> tuple[str, ...]:
        return (
            str(python_executable),
            "-I",
            "-c",
            cls.PROGRAM,
            str(source_fd),
            str(source_path),
            str(source_size),
            source_sha256,
            *arguments,
        )

    @staticmethod
    def bootstrap_pass_fds(source_fd: int) -> tuple[int]:
        return (source_fd,)


class FakeBridgeProcess:
    def __init__(
        self,
        pid: int = 4242,
        *,
        wait_timeout_once: bool = False,
        wait_timeout_always: bool = False,
    ) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.terminated = 0
        self.killed = 0
        self.wait_timeout_once = wait_timeout_once
        self.wait_timeout_always = wait_timeout_always

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated += 1

    def kill(self) -> None:
        self.killed += 1
        self.returncode = -9

    def wait(self, timeout: float) -> int:
        if self.wait_timeout_always or self.wait_timeout_once:
            self.wait_timeout_once = False
            raise subprocess.TimeoutExpired("bridge", timeout)
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


class FakeCommandProcess:
    def __init__(
        self,
        stdout_fd: int,
        payload: dict[str, Any],
        *,
        pid: int = 5252,
        returncode: int = 0,
        timeout: bool = False,
    ) -> None:
        self.pid = pid
        self.returncode = returncode
        self.timeout = timeout
        self.wait_calls = 0
        os.write(stdout_fd, contract.canonical_file_bytes(payload))

    def wait(self, timeout: float) -> int:
        self.wait_calls += 1
        if self.timeout and self.wait_calls == 1:
            raise subprocess.TimeoutExpired("observe", timeout)
        return self.returncode


def bridge_endpoint() -> dict[str, Any]:
    return {
        "selectedDevice": observer_v1.FIXED_BRIDGE_DEVICE,
        "selectedRealpath": "/dev/ttyACM0",
        "usbVendor": "04e8",
        "usbProduct": "6861",
        "otherTargetsPresent": 0,
    }


def bridge_receipt(pid: int = 4242) -> dict[str, Any]:
    value = {
        **bridge_endpoint(),
        "bridgeProcessPid": pid,
        "bridgeProcessStartTicks": 987654,
        "listenerSocketInode": 12345,
    }
    value["receiptSha256"] = observer_v1._receipt_sha(value)
    return value


def fake_bindings() -> owner.ExecutionBindings:
    return owner.ExecutionBindings(
        {
            role: FakeArtifact(role)  # type: ignore[arg-type]
            for role in ("candidate", "rollback", "python-interpreter", "adb-transport")
        }
    )


class FakeBackend:
    def __init__(
        self,
        source: owner.LiveSnapshot,
        final: owner.LiveSnapshot,
        *,
        candidate_rc: int = 0,
        candidate_released: bool = True,
        candidate_quiescent: bool = True,
        rollback_rc: int = 0,
    ) -> None:
        self.source = source
        self.final = final
        self.candidate_rc = candidate_rc
        self.candidate_released = candidate_released
        self.candidate_quiescent = candidate_quiescent
        self.rollback_rc = rollback_rc
        self.preflight_calls = 0
        self.candidate_calls = 0
        self.rollback_calls = 0

    def preflight(self, _manifest: dict[str, Any]) -> owner.LiveSnapshot:
        self.preflight_calls += 1
        return self.source

    @staticmethod
    def _effect(returncode: int, released: bool, quiescent: bool) -> owner.EffectResult:
        return owner.EffectResult(
            returncode=returncode,
            released=released,
            quiescent=quiescent,
            pid=1000,
            process_group=1000,
            stdout_sha256="a" * 64,
            stderr_sha256="b" * 64,
            duration_ms=1,
        )

    def run_candidate(
        self,
        _manifest: dict[str, Any],
        journal: contract.Journal,
        _bindings: owner.ExecutionBindings,
        approval_binding_sha256: str,
    ) -> owner.EffectResult:
        self.candidate_calls += 1
        journal.append(
            "CANDIDATE_LAUNCHED",
            {"approvalBindingSha256": approval_binding_sha256, "attempt": 1},
        )
        return self._effect(
            self.candidate_rc,
            self.candidate_released,
            self.candidate_quiescent,
        )

    def run_rollback(
        self,
        _manifest: dict[str, Any],
        journal: contract.Journal,
        _bindings: owner.ExecutionBindings,
        approval_binding_sha256: str,
    ) -> owner.EffectResult:
        self.rollback_calls += 1
        journal.append(
            "ROLLBACK_LAUNCHED",
            {"approvalBindingSha256": approval_binding_sha256, "attempt": 1},
        )
        return self._effect(self.rollback_rc, True, True)

    def observe(self, _expected: dict[str, Any]) -> owner.LiveSnapshot:
        return self.final


class ContractTests(unittest.TestCase):
    def test_canonical_json_rejects_duplicates_types_and_noncanonical_bytes(self) -> None:
        for raw in (
            b'{"a":1,"a":2}\n',
            b'{"a": 1}\n',
            b'{"a":1}\r\n',
            b'{"a":NaN}\n',
            b'{"a":1}',
        ):
            with self.subTest(raw=raw), self.assertRaises(contract.ContractError):
                contract.parse_canonical_bytes(raw, "hostile")
        self.assertEqual(contract.parse_canonical_bytes(b'{"a":1}\n', "ok"), {"a": 1})
        with self.assertRaises(contract.ContractError):
            contract.require_int(True, "not-int", minimum=0, maximum=1)

    def test_manifest_rejects_authority_fields_aliases_and_unknown_hazards(self) -> None:
        base = manifest()
        contract.validate_manifest(base)
        for mutation in (
            lambda value: value.update(command=["flash", "vendor_boot"]),
            lambda value: value.update(partition="boot"),
            lambda value: value.update(candidateAttempts=2),
            lambda value: value["candidate"].update(path=value["rollback"]["path"]),
            lambda value: value["hazards"][0].update(id="UNKNOWN"),
        ):
            hostile = copy.deepcopy(base)
            mutation(hostile)
            with self.assertRaises(contract.ContractError):
                contract.validate_manifest(hostile)
        for field in ("ownerClosureSha256",):
            hostile = copy.deepcopy(base)
            hostile[field] = "f" * 64
            with self.assertRaises(contract.ContractError):
                owner.validate_local_manifest_bindings(hostile)
        hostile = copy.deepcopy(base)
        hostile["flashHelper"]["sha256"] = "f" * 64
        with self.assertRaises(contract.ContractError):
            owner.validate_local_manifest_bindings(hostile)

    def test_runtime_qualification_and_review_are_external_exact_bindings(self) -> None:
        closure = owner.owner_closure_sha256()
        runtime = {
            "schema": contract.RUNTIME_QUALIFICATION_SCHEMA,
            "capability": contract.CAPABILITY,
            "ownerClosureSha256": closure,
            "python": runtime_member(owner.PYTHON_EXECUTABLE, "1" * 64),
            "adb": runtime_member(owner.ADB_EXECUTABLE, "4" * 64),
        }
        contract.validate_runtime_qualification(runtime, closure)
        for mutation in (
            lambda value: value["python"]["versionReceipt"].update(exact="/wrong"),
            lambda value: value["python"]["runtimeRoots"][0].update(fileCount=False),
            lambda value: value["python"]["dynamicLibraries"][0].update(sha256="f" * 64),
            lambda value: value["python"].update(runtimeClosureSha256="f" * 64),
        ):
            hostile = copy.deepcopy(runtime)
            mutation(hostile)
            with self.assertRaises(contract.ContractError):
                contract.validate_runtime_qualification(hostile, closure)
        runtime_sha = sha(contract.canonical_file_bytes(runtime))
        review = {
            "schema": contract.REVIEW_SCHEMA,
            "capability": contract.CAPABILITY,
            "ownerClosureSha256": closure,
            "runtimeQualificationSha256": runtime_sha,
            "verdict": "PASS_GO",
            "findings": {"high": 0, "medium": 0, "low": 0},
            "contacts": {
                "device": 0,
                "dev": 0,
                "usb": 0,
                "network": 0,
                "workspacePrivate": 0,
                "otherTarget": 0,
            },
        }
        contract.validate_review(review, closure, runtime_sha)
        for field in ("ownerClosureSha256", "runtimeQualificationSha256"):
            hostile = copy.deepcopy(review)
            hostile[field] = "f" * 64
            with self.assertRaises(contract.ContractError):
                contract.validate_review(hostile, closure, runtime_sha)

    def test_execution_closure_excludes_tests_reports_and_reviews(self) -> None:
        members = owner.owner_source_closure()
        self.assertNotIn("tests/test_a90_boot_only_f1_owner_v1.py", members)
        self.assertTrue(all(not path.startswith("docs/") for path in members))
        self.assertTrue(all("review" not in path for path in members))
        self.assertIn(
            "workspace/public/src/scripts/revalidation/"
            "a90_boot_only_f1_source_package_v1.py",
            members,
        )
        self.assertTrue(all("build_a90_boot_only" not in path for path in members))
        self.assertTrue(all("helper_bootstrap" not in path for path in members))
        self.assertTrue(all("command_bootstrap" not in path for path in members))

    def test_runtime_generator_reverifies_the_current_host_closure(self) -> None:
        closure = owner.owner_closure_sha256()
        generated = runtime_v1.build_runtime_qualification(closure)
        raw, stored = contract.load_canonical(
            owner.RUNTIME_QUALIFICATION_PATH, "runtime qualification"
        )
        self.assertGreater(len(raw), 1)
        self.assertEqual(stored, generated)
        self.assertEqual(
            runtime_v1.verify_runtime_qualification_current(generated, closure),
            generated,
        )
        self.assertEqual(generated["python"]["path"], str(owner.PYTHON_EXECUTABLE))
        self.assertEqual(generated["adb"]["path"], str(owner.ADB_EXECUTABLE))
        self.assertEqual(generated["python"]["versionReceipt"]["isolated"], 1)
        self.assertIs(generated["python"]["versionReceipt"]["safePath"], True)
        self.assertGreater(len(generated["python"]["dynamicLibraries"]), 0)
        self.assertGreater(len(generated["adb"]["dynamicLibraries"]), 0)

    def test_observer_separates_installed_resident_from_fresh_boot_health(self) -> None:
        expected = manifest()["expectedStart"]
        health = observer_v1.validate_observation_input(
            observed_input(), expected, recovery_available=True
        )
        self.assertEqual((health.version, health.build), ("0.11.192", "phase3-minimal-h24"))
        self.assertEqual(health.device_safety_state, "RESIDENT_HEALTHY")
        self.assertTrue(health.recovery_available)
        self.assertTrue(health.other_targets_untouched)
        self.assertRegex(health.boot_identity_sha256, r"^[0-9a-f]{64}$")
        candidate_health = observer_v1.validate_observation_input(
            observed_input(),
            {
                "version": "0.11.192",
                "build": "phase3-minimal-h24",
                "sha256": "a" * 64,
            },
            recovery_available=True,
        )
        self.assertRegex(candidate_health.receipt_sha256, r"^[0-9a-f]{64}$")

    def test_observer_rejects_attribution_health_and_framing_drift(self) -> None:
        expected = manifest()["expectedStart"]
        mutations = (
            lambda value: value["bridge"].update(otherTargetsPresent=1),
            lambda value: value["bridge"].update(selectedRealpath="/dev/ttyUSB0"),
            lambda value: value["version"].update(
                text="version: 0.11.194 build=phase3-minimal-h27\n"
            ),
            lambda value: value["selftest"].update(
                text="selftest: pass=40 warn=0 fail=1 duration=9ms entries=41\n"
            ),
            lambda value: value["status"].update(text="pstore=mounted entries=1\n"),
            lambda value: value["status"].update(
                text="pstore=mounted entries=0 entries=9\n"
            ),
            lambda value: value["bootId"].update(
                text=(
                    "12345678-1234-1234-1234-123456789abc\n"
                    "87654321-4321-4321-4321-cba987654321\n"
                )
            ),
            lambda value: value["bootId"].update(rc=False),
        )
        for mutation in mutations:
            hostile = copy.deepcopy(observed_input())
            mutation(hostile)
            hostile["bridge"]["receiptSha256"] = observer_v1._receipt_sha(
                hostile["bridge"]
            )
            for name in ("version", "selftest", "status", "bootId"):
                hostile[name]["receiptSha256"] = observer_v1._receipt_sha(
                    hostile[name]
                )
            with self.subTest(mutation=mutation), self.assertRaises(contract.ContractError):
                observer_v1.validate_observation_input(
                    hostile, expected, recovery_available=True
                )
        with self.assertRaisesRegex(contract.ContractError, "recovery"):
            observer_v1.validate_observation_input(
                observed_input(), expected, recovery_available=False
            )

    def test_bridge_probe_parsers_are_exact_and_fail_closed(self) -> None:
        self.assertNotIn(
            "adb_devices_output",
            inspect.signature(observer_v1.probe_endpoint_identity).parameters,
        )
        self.assertFalse(hasattr(observer_v1, "_adb_target_count"))
        with tempfile.TemporaryDirectory() as raw_root:
            tcp = Path(raw_root) / "tcp"
            tcp.write_text(
                "sl local_address rem_address st tx_queue rx_queue tr tm->when "
                "retrnsmt uid timeout inode\n"
                "0: 0100007F:D431 00000000:0000 0A 0:0 0:0 0 1000 0 12345\n",
                encoding="ascii",
            )
            self.assertEqual(observer_v1._listener_inode(tcp), 12345)
            tcp.write_text(
                "sl local_address rem_address st tx_queue rx_queue tr tm->when "
                "retrnsmt uid timeout inode\n"
                "0: 0100007F:D431 00000000:0000 0A 0:0 0:0 0 1000 0 12345\n"
                "1: 0100007F:D431 00000000:0000 0A 0:0 0:0 0 1000 0 12346\n",
                encoding="ascii",
            )
            with self.assertRaises(contract.ContractError):
                observer_v1._listener_inode(tcp)

        fields = ["S", *[str(index) for index in range(4, 23)]]
        fields[19] = "987654"
        self.assertEqual(
            observer_v1._process_start_ticks("123 (bridge worker) " + " ".join(fields)),
            987654,
        )
        with self.assertRaises(contract.ContractError):
            observer_v1._process_start_ticks("123 malformed")

    def test_owned_bridge_probe_binds_exact_pid_command_listener_and_tty(self) -> None:
        command = (str(observer_v1.PYTHON_EXECUTABLE), "-I", "-c", "bound")
        endpoint = bridge_endpoint()
        with tempfile.TemporaryDirectory() as raw_root:
            proc = Path(raw_root)
            (proc / "net").mkdir()
            tcp_header = (
                "sl local_address rem_address st tx_queue rx_queue tr tm->when "
                "retrnsmt uid timeout inode\n"
            )
            (proc / "net/tcp").write_text(
                tcp_header
                + "0: 0100007F:D431 00000000:0000 0A 0:0 0:0 0 1000 0 12345\n",
                encoding="ascii",
            )
            process = proc / "4242"
            (process / "fd").mkdir(parents=True)
            (process / "cmdline").write_bytes(b"\0".join(part.encode() for part in command) + b"\0")
            (process / "exe").symlink_to(observer_v1.PYTHON_EXECUTABLE)
            fields = ["S", *[str(index) for index in range(4, 23)]]
            fields[19] = "987654"
            (process / "stat").write_text(
                "4242 (owned bridge) " + " ".join(fields) + "\n",
                encoding="ascii",
            )
            (process / "fd/3").symlink_to("socket:[12345]")
            (process / "fd/4").symlink_to("/dev/ttyACM0")
            receipt = observer_v1.probe_bridge_identity(
                endpoint,
                expected_pid=4242,
                expected_command=command,
                proc_root=proc,
            )
            self.assertEqual(receipt["bridgeProcessPid"], 4242)
            self.assertEqual(receipt["bridgeProcessStartTicks"], 987654)
            self.assertEqual(receipt["listenerSocketInode"], 12345)

            foreign = proc / "5000/fd"
            foreign.mkdir(parents=True)
            (foreign / "3").symlink_to("socket:[12345]")
            with self.assertRaisesRegex(contract.ContractError, "ownership"):
                observer_v1.probe_bridge_identity(
                    endpoint,
                    expected_pid=4242,
                    expected_command=command,
                    proc_root=proc,
                )
            (foreign / "3").unlink()
            foreign.rmdir()
            (proc / "5000").rmdir()
            for child in (process / "fd").iterdir():
                child.unlink()
            (process / "fd").rmdir()
            (process / "cmdline").unlink()
            (process / "exe").unlink()
            (process / "stat").unlink()
            process.rmdir()
            (proc / "net/tcp").write_text(tcp_header, encoding="ascii")
            observer_v1.prove_bridge_absent(
                pid=4242,
                listener_inode=12345,
                selected_realpath="/dev/ttyACM0",
                proc_root=proc,
            )

    def test_bridge_source_is_inside_the_generated_source_package(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(
                    owner.REVALIDATION
                    / "build_a90_boot_only_f1_source_package_v1.py"
                ),
                "--check",
            ],
            cwd=REPO,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        raw = owner.SOURCE_PACKAGE_PATH.read_bytes()
        self.assertEqual(
            (len(raw), sha(raw)),
            owner.SOURCE_PACKAGE_SPEC,
        )
        self.assertEqual(owner.helper_runtime_digest(), owner.HELPER_RUNTIME_CLOSURE_SHA256)

    def test_owned_bridge_uses_held_source_and_proves_bounded_teardown(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH, "helper-package"
        )
        bindings = owner.ExecutionBindings({"helper-package": artifact})
        process = FakeBridgeProcess()
        launch: dict[str, Any] = {}
        teardown: dict[str, Any] = {}

        def popen(command: tuple[str, ...], **kwargs: Any) -> FakeBridgeProcess:
            launch.update(command=command, kwargs=kwargs)
            return process

        def process_probe(
            endpoint: dict[str, Any], *, expected_pid: int, expected_command: tuple[str, ...]
        ) -> dict[str, Any]:
            self.assertEqual(endpoint, bridge_endpoint())
            self.assertEqual(expected_pid, process.pid)
            self.assertEqual(expected_command, launch["command"])
            return bridge_receipt(process.pid)

        def teardown_probe(**kwargs: Any) -> None:
            teardown.update(kwargs)

        try:
            with tempfile.TemporaryDirectory() as raw_root:
                lifecycle = owner.OwnedBridgeLifecycle(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=popen,
                    endpoint_probe=lambda: bridge_endpoint(),
                    listener_absence_probe=lambda: None,
                    process_probe=process_probe,
                    teardown_probe=teardown_probe,
                )
                receipt = lifecycle.start(readiness_timeout_sec=1)
                command = launch["command"]
                self.assertEqual(command[0:4], (str(owner.PYTHON_EXECUTABLE), "-I", "-c", FakeFdExec.PROGRAM))
                self.assertEqual(command[4], str(artifact.fd))
                self.assertIn(owner.SOURCE_PACKAGE_SPEC[1], command)
                self.assertEqual(launch["kwargs"]["pass_fds"], (artifact.fd,))
                self.assertIs(launch["kwargs"]["close_fds"], True)
                self.assertEqual(receipt["bridgeProcessPid"], process.pid)
                closed = lifecycle.close()
                self.assertEqual(process.terminated, 1)
                self.assertEqual(process.killed, 0)
                self.assertIs(closed["forced"], False)
                self.assertEqual(
                    teardown,
                    {
                        "pid": process.pid,
                        "listener_inode": 12345,
                        "selected_realpath": "/dev/ttyACM0",
                    },
                )
                self.assertRegex(closed["stdoutSha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(closed["stderrSha256"], r"^[0-9a-f]{64}$")
        finally:
            bindings.close()

    def test_owned_bridge_readiness_failure_reaps_and_never_retries_launch(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH, "helper-package"
        )
        bindings = owner.ExecutionBindings({"helper-package": artifact})
        process = FakeBridgeProcess()
        launches = 0
        absence_checks = 0
        moments = iter((0.0, 0.0, 2.0))

        def popen(_command: tuple[str, ...], **_kwargs: Any) -> FakeBridgeProcess:
            nonlocal launches
            launches += 1
            return process

        def no_listener() -> None:
            nonlocal absence_checks
            absence_checks += 1

        try:
            with tempfile.TemporaryDirectory() as raw_root:
                lifecycle = owner.OwnedBridgeLifecycle(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=popen,
                    endpoint_probe=lambda: bridge_endpoint(),
                    listener_absence_probe=no_listener,
                    process_probe=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                        contract.ContractError("not ready")
                    ),
                    monotonic=lambda: next(moments),
                    sleep=lambda _seconds: None,
                )
                with self.assertRaisesRegex(contract.ContractError, "timed out"):
                    lifecycle.start(readiness_timeout_sec=1)
                self.assertEqual(launches, 1)
                self.assertEqual(process.terminated, 1)
                self.assertTrue(lifecycle.closed)
                self.assertEqual(absence_checks, 2)
        finally:
            bindings.close()

    def test_owned_bridge_forces_reap_but_never_claims_graceful_close(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH, "helper-package"
        )
        bindings = owner.ExecutionBindings({"helper-package": artifact})
        process = FakeBridgeProcess(wait_timeout_once=True)
        try:
            with tempfile.TemporaryDirectory() as raw_root:
                lifecycle = owner.OwnedBridgeLifecycle(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=lambda *_args, **_kwargs: process,
                    endpoint_probe=lambda: bridge_endpoint(),
                    listener_absence_probe=lambda: None,
                    process_probe=lambda *_args, **_kwargs: bridge_receipt(process.pid),
                    teardown_probe=lambda **_kwargs: None,
                )
                lifecycle.start(readiness_timeout_sec=1)
                closed = lifecycle.close(timeout_sec=0.1)
                self.assertIs(closed["forced"], True)
                self.assertEqual(process.terminated, 1)
                self.assertEqual(process.killed, 1)
                self.assertEqual(closed["returncode"], -9)
        finally:
            bindings.close()

    def test_owned_bridge_teardown_uncertainty_is_terminal_and_closes_logs(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH, "helper-package"
        )
        bindings = owner.ExecutionBindings({"helper-package": artifact})
        process = FakeBridgeProcess()
        try:
            with tempfile.TemporaryDirectory() as raw_root:
                lifecycle = owner.OwnedBridgeLifecycle(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=lambda *_args, **_kwargs: process,
                    endpoint_probe=lambda: bridge_endpoint(),
                    listener_absence_probe=lambda: None,
                    process_probe=lambda *_args, **_kwargs: bridge_receipt(process.pid),
                    teardown_probe=lambda **_kwargs: (_ for _ in ()).throw(
                        contract.ContractError("bridge teardown is unproved")
                    ),
                )
                lifecycle.start(readiness_timeout_sec=1)
                with self.assertRaisesRegex(contract.ContractError, "unproved"):
                    lifecycle.close()
                self.assertTrue(lifecycle.closed)
                self.assertEqual(lifecycle.stdout_fd, -1)
                self.assertEqual(lifecycle.stderr_fd, -1)
                with self.assertRaisesRegex(contract.ContractError, "cannot be closed"):
                    lifecycle.close()
        finally:
            bindings.close()

    def test_owned_bridge_unreaped_after_kill_is_terminal_and_closes_logs(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH, "helper-package"
        )
        bindings = owner.ExecutionBindings({"helper-package": artifact})
        process = FakeBridgeProcess(wait_timeout_always=True)
        try:
            with tempfile.TemporaryDirectory() as raw_root:
                lifecycle = owner.OwnedBridgeLifecycle(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=lambda *_args, **_kwargs: process,
                    endpoint_probe=lambda: bridge_endpoint(),
                    listener_absence_probe=lambda: None,
                    process_probe=lambda *_args, **_kwargs: bridge_receipt(process.pid),
                    teardown_probe=lambda **_kwargs: self.fail(
                        "unreaped process must not enter absence proof"
                    ),
                )
                lifecycle.start(readiness_timeout_sec=1)
                with self.assertRaises(subprocess.TimeoutExpired):
                    lifecycle.close(timeout_sec=0.1)
                self.assertTrue(lifecycle.closed)
                self.assertEqual(process.terminated, 1)
                self.assertEqual(process.killed, 1)
                self.assertEqual(lifecycle.stdout_fd, -1)
                self.assertEqual(lifecycle.stderr_fd, -1)
                with self.assertRaisesRegex(contract.ContractError, "cannot be closed"):
                    lifecycle.close()
        finally:
            bindings.close()

    def test_owned_bridge_rejects_duplicate_start_and_duplicate_close(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH, "helper-package"
        )
        bindings = owner.ExecutionBindings({"helper-package": artifact})
        process = FakeBridgeProcess()
        try:
            with tempfile.TemporaryDirectory() as raw_root:
                lifecycle = owner.OwnedBridgeLifecycle(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=lambda *_args, **_kwargs: process,
                    endpoint_probe=lambda: bridge_endpoint(),
                    listener_absence_probe=lambda: None,
                    process_probe=lambda *_args, **_kwargs: bridge_receipt(process.pid),
                    teardown_probe=lambda **_kwargs: None,
                )
                lifecycle.start(readiness_timeout_sec=1)
                with self.assertRaisesRegex(contract.ContractError, "not fresh"):
                    lifecycle.start(readiness_timeout_sec=1)
                lifecycle.close()
                with self.assertRaisesRegex(contract.ContractError, "cannot be closed"):
                    lifecycle.close()
        finally:
            bindings.close()

    def test_source_package_binds_two_held_files_without_staging(self) -> None:
        artifacts = owner.bind_source_package()
        try:
            self.assertEqual(set(artifacts), {"helper-fd-exec", "helper-package"})
            self.assertEqual(
                artifacts["helper-package"].identity["sha256"],
                owner.SOURCE_PACKAGE_SPEC[1],
            )
            self.assertEqual(
                artifacts["helper-fd-exec"].identity["sha256"],
                owner.FD_EXEC_SPEC[1],
            )
        finally:
            for artifact in artifacts.values():
                artifact.close()
        self.assertFalse(hasattr(owner, "stage_runtime_sources"))
        self.assertFalse(hasattr(owner, "bind_runtime_sources"))

    def test_held_source_rejects_tamper_and_symlink_then_seals_bytes(self) -> None:
        raw = owner.SOURCE_PACKAGE_PATH.read_bytes()
        digest = sha(raw)
        for mutation in ("tamper", "symlink"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw_root:
                root = Path(raw_root)
                path = root / "package.py"
                path.write_bytes(raw)
                os.chmod(path, 0o600)
                if mutation == "tamper":
                    path.write_bytes(raw[:-1] + b"X")
                elif mutation == "symlink":
                    target = root / "target.py"
                    path.rename(target)
                    path.symlink_to(target)
                with self.assertRaises(contract.ContractError):
                    owner.HeldSourceArtifact.open(
                        role="test-package",
                        path=path,
                        expected_size=len(raw),
                        expected_sha256=digest,
                    )

    def test_owned_command_producer_executes_only_fixed_fd_bound_commands(self) -> None:
        artifact = FakeHeldSource(
            owner.SOURCE_PACKAGE_PATH,
            "helper-package",
        )
        bindings = owner.ExecutionBindings(
            {"helper-package": artifact}
        )
        launches: list[tuple[tuple[str, ...], dict[str, Any]]] = []

        def popen(command: tuple[str, ...], **kwargs: Any) -> FakeCommandProcess:
            label = command[-2]
            expected = dict(owner.OBSERVATION_COMMANDS)[label]
            launches.append((command, kwargs))
            return FakeCommandProcess(
                kwargs["stdout"],
                {
                    "command": list(expected),
                    "rc": 0,
                    "status": "ok",
                    "text": "bounded-result\n",
                },
            )

        try:
            with tempfile.TemporaryDirectory() as raw_root:
                producer = owner.OwnedCommandProducer(
                    bindings,
                    Path(raw_root),
                    FakeFdExec,
                    popen_factory=popen,
                    process_group_exists=lambda _pid: False,
                )
                for label, expected in owner.OBSERVATION_COMMANDS:
                    receipt = producer.run(label, timeout_sec=5)
                    self.assertEqual(receipt["command"], list(expected))
                    self.assertEqual(receipt["rc"], 0)
                self.assertEqual(len(launches), 4)
                for command, kwargs in launches:
                    self.assertEqual(command[0:4], (
                        str(owner.PYTHON_EXECUTABLE), "-I", "-c", FakeFdExec.PROGRAM
                    ))
                    self.assertEqual(kwargs["pass_fds"], (artifact.fd,))
                    self.assertIs(kwargs["close_fds"], True)
                with self.assertRaisesRegex(contract.ContractError, "consumed"):
                    producer.run("version", timeout_sec=5)
                with self.assertRaisesRegex(contract.ContractError, "unknown"):
                    producer.run("arbitrary", timeout_sec=5)
        finally:
            bindings.close()

    def test_source_package_requires_fd_execution_and_rejects_unknown_mode(self) -> None:
        bootstrap = owner.SOURCE_PACKAGE_PATH
        direct = subprocess.run(
            [str(owner.PYTHON_EXECUTABLE), "-I", str(bootstrap), "unknown"],
            cwd="/",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(direct.returncode, 0)
        self.assertIn("inherited-FD execution", direct.stderr)

        artifact = owner.HeldSourceArtifact.open(
            role="helper-package",
            path=bootstrap,
            expected_size=owner.SOURCE_PACKAGE_SPEC[0],
            expected_sha256=owner.SOURCE_PACKAGE_SPEC[1],
        )
        try:
            # Use the real reviewed loader for this integration check.
            fd_artifact = owner.HeldSourceArtifact.open(
                role="helper-fd-exec",
                path=owner.FD_EXEC_PATH,
                expected_size=owner.FD_EXEC_SPEC[0],
                expected_sha256=owner.FD_EXEC_SPEC[1],
            )
            try:
                fd_exec = owner._load_exact_python_module(fd_artifact, "fd_exec_test")
                command = fd_exec.bootstrap_command(
                    owner.PYTHON_EXECUTABLE,
                    artifact.fd,
                    bootstrap,
                    artifact.identity["size"],
                    artifact.identity["sha256"],
                    ("unknown",),
                )
                completed = subprocess.run(
                    command,
                    cwd="/",
                    env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
                    pass_fds=(artifact.fd,),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            finally:
                fd_artifact.close()
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("mode is unknown", completed.stderr)
        finally:
            artifact.close()

    def test_source_package_exposes_only_fixed_bridge_command_and_flash_modes(self) -> None:
        artifacts = owner.bind_source_package()
        package = artifacts["helper-package"]
        try:
            fd_exec = owner._load_exact_python_module(
                artifacts["helper-fd-exec"], "fd_exec_package_modes_test"
            )
            cases = (
                (("bridge", "--help"), 0, "serial_tcp_bridge.py"),
                (("command", "unknown", "5"), 1, "unknown command"),
                (("flash", "--help"), 0, "native_init_flash.py"),
            )
            for arguments, expected_rc, expected_text in cases:
                with self.subTest(arguments=arguments):
                    command = fd_exec.bootstrap_command(
                        owner.PYTHON_EXECUTABLE,
                        package.fd,
                        package.path,
                        package.identity["size"],
                        package.identity["sha256"],
                        arguments,
                    )
                    completed = subprocess.run(
                        command,
                        cwd="/",
                        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
                        pass_fds=(package.fd,),
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, expected_rc)
                    self.assertIn(expected_text, completed.stdout + completed.stderr)
        finally:
            for artifact in artifacts.values():
                artifact.close()

    def test_fd_loader_rejects_an_unsealed_regular_package_fd(self) -> None:
        package = FakeHeldSource(owner.SOURCE_PACKAGE_PATH, "helper-package")
        fd_exec_artifact = owner.HeldSourceArtifact.open(
            role="helper-fd-exec",
            path=owner.FD_EXEC_PATH,
            expected_size=owner.FD_EXEC_SPEC[0],
            expected_sha256=owner.FD_EXEC_SPEC[1],
        )
        try:
            fd_exec = owner._load_exact_python_module(
                fd_exec_artifact, "fd_exec_unsealed_test"
            )
            command = fd_exec.bootstrap_command(
                owner.PYTHON_EXECUTABLE,
                package.fd,
                package.path,
                package.identity["size"],
                package.identity["sha256"],
                ("flash", "--help"),
            )
            completed = subprocess.run(
                command,
                cwd="/",
                env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
                pass_fds=(package.fd,),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("sealed source capability", completed.stderr)
        finally:
            package.close()
            fd_exec_artifact.close()

    def test_owned_command_producer_rejects_mismatched_or_timed_out_result(self) -> None:
        for scenario in ("mismatch", "timeout"):
            with self.subTest(scenario=scenario):
                artifact = FakeHeldSource(
                    owner.SOURCE_PACKAGE_PATH,
                    "helper-package",
                )
                bindings = owner.ExecutionBindings(
                    {"helper-package": artifact}
                )
                killed: list[tuple[int, int]] = []

                def popen(_command: tuple[str, ...], **kwargs: Any) -> FakeCommandProcess:
                    return FakeCommandProcess(
                        kwargs["stdout"],
                        {
                            "command": ["status"],
                            "rc": 0,
                            "status": "ok",
                            "text": "wrong\n",
                        },
                        timeout=scenario == "timeout",
                    )

                try:
                    with tempfile.TemporaryDirectory() as raw_root:
                        producer = owner.OwnedCommandProducer(
                            bindings,
                            Path(raw_root),
                            FakeFdExec,
                            popen_factory=popen,
                            process_group_exists=lambda _pid: False,
                            kill_group=lambda pid, sig: killed.append((pid, sig)),
                        )
                        with self.assertRaises(contract.ContractError):
                            producer.run("version", timeout_sec=5)
                        if scenario == "timeout":
                            self.assertEqual(killed, [(5252, signal.SIGKILL)])
                finally:
                    bindings.close()

    def test_observation_session_requires_four_receipts_and_always_closes_bridge(self) -> None:
        source = observed_input()

        class Bridge:
            def __init__(self) -> None:
                self.closed = 0

            def start(self, *, readiness_timeout_sec: int) -> dict[str, Any]:
                self.readiness_timeout_sec = readiness_timeout_sec
                return source["bridge"]

            def close(self, *, timeout_sec: float) -> dict[str, Any]:
                self.closed += 1
                self.close_timeout_sec = timeout_sec
                return {}

        class Commands:
            def __init__(self, *, fail_on: str | None = None) -> None:
                self.labels: list[str] = []
                self.fail_on = fail_on

            def run(self, label: str, *, timeout_sec: int) -> dict[str, Any]:
                self.labels.append(label)
                if label == self.fail_on:
                    raise contract.ContractError("command failed")
                key = "bootId" if label == "boot-id" else label
                return source[key]

        bridge = Bridge()
        commands = Commands()
        session = owner.OwnedObservationSession(bridge, commands)
        health = session.observe(
            manifest()["expectedStart"],
            recovery_available=True,
            bridge_timeout_sec=7,
            command_timeout_sec=8,
        )
        self.assertEqual(health.version, "0.11.192")
        self.assertEqual(
            commands.labels, [label for label, _command in owner.OBSERVATION_COMMANDS]
        )
        self.assertEqual(bridge.closed, 1)
        self.assertEqual(bridge.readiness_timeout_sec, 7)
        self.assertEqual(bridge.close_timeout_sec, 5.0)

        failing_bridge = Bridge()
        failing = owner.OwnedObservationSession(
            failing_bridge, Commands(fail_on="status")
        )
        with self.assertRaisesRegex(contract.ContractError, "command failed"):
            failing.observe(
                manifest()["expectedStart"],
                recovery_available=True,
                bridge_timeout_sec=7,
                command_timeout_sec=8,
            )
        self.assertEqual(failing_bridge.closed, 1)

    def test_resident_qualification_is_external_and_exact(self) -> None:
        self.assertTrue(contract.RESIDENT_QUALIFICATION_SCHEMA.endswith("-v2"))
        expected = manifest()["expectedStart"]
        qualification = {
            "schema": contract.RESIDENT_QUALIFICATION_SCHEMA,
            "capability": contract.CAPABILITY,
            "version": expected["version"],
            "build": expected["build"],
            "installTerminalSha256": "d" * 64,
            "deviceSafetyState": "RESIDENT_HEALTHY",
            "disposition": "QUALIFIED_INSTALLED_RESIDENT",
        }
        self.assertEqual(
            contract.validate_resident_qualification(qualification, expected),
            qualification,
        )
        with self.assertRaises(contract.ContractError):
            contract.validate_resident_qualification(
                {**qualification, "ownerClosureSha256": "f" * 64}, expected
            )
        for field, value in (
            ("version", "0.11.191"),
            ("installTerminalSha256", False),
            ("deviceSafetyState", "HEALTH_PENDING"),
        ):
            hostile = copy.deepcopy(qualification)
            hostile[field] = value
            with self.assertRaises(contract.ContractError):
                contract.validate_resident_qualification(hostile, expected)

    def test_recovery_qualification_is_external_and_exact(self) -> None:
        self.assertTrue(contract.RECOVERY_QUALIFICATION_SCHEMA.endswith("-v2"))
        item = manifest()
        qualification = {
            "schema": contract.RECOVERY_QUALIFICATION_SCHEMA,
            "capability": contract.CAPABILITY,
            "plan": item["recovery"]["plan"],
            "rollbackSha256": item["rollback"]["sha256"],
            "physicalRecoveryDemonstrated": True,
            "disposition": "QUALIFIED_PHYSICAL_RECOVERY",
        }
        self.assertEqual(
            contract.validate_recovery_qualification(qualification, item),
            qualification,
        )
        with self.assertRaises(contract.ContractError):
            contract.validate_recovery_qualification(
                {**qualification, "ownerClosureSha256": "f" * 64}, item
            )
        for field, value in (
            ("plan", "OTHER"),
            ("rollbackSha256", "f" * 64),
            ("physicalRecoveryDemonstrated", 1),
            ("disposition", "PENDING"),
        ):
            hostile = copy.deepcopy(qualification)
            hostile[field] = value
            with self.subTest(field=field), self.assertRaises(contract.ContractError):
                contract.validate_recovery_qualification(hostile, item)

    def test_hazard_qualification_is_owner_independent_but_exact(self) -> None:
        self.assertTrue(contract.QUALIFICATION_SCHEMA.endswith("-v2"))
        qualification = {
            "schema": contract.QUALIFICATION_SCHEMA,
            "capability": contract.CAPABILITY,
            "hazardId": "RKP_CFP_DISABLED_RESIDENT",
            "disposition": "ACCEPTED_FOR_ATTENDED_F1",
        }
        self.assertEqual(
            contract.validate_hazard_qualification(
                qualification, "RKP_CFP_DISABLED_RESIDENT"
            ),
            qualification,
        )
        with self.assertRaises(contract.ContractError):
            contract.validate_hazard_qualification(
                {**qualification, "ownerClosureSha256": "f" * 64},
                "RKP_CFP_DISABLED_RESIDENT",
            )
        for field, value in (
            ("hazardId", "OTHER"),
            ("disposition", "PENDING"),
        ):
            hostile = copy.deepcopy(qualification)
            hostile[field] = value
            with self.assertRaises(contract.ContractError):
                contract.validate_hazard_qualification(
                    hostile, "RKP_CFP_DISABLED_RESIDENT"
                )

    def test_bound_artifact_rejects_indirection_links_mode_and_swap(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            os.chmod(root, 0o700)
            path = root / "candidate.img"
            path.write_bytes(b"candidate")
            os.chmod(path, 0o600)
            item = contract.BoundArtifact.open(
                role="candidate",
                path=path,
                expected_size=9,
                expected_sha256=sha(b"candidate"),
                anchor=root,
                expected_uid=os.getuid(),
                expected_gid=os.getgid(),
            )
            replacement = root / "replacement.img"
            replacement.write_bytes(b"different")
            os.chmod(replacement, 0o600)
            os.replace(replacement, path)
            with self.assertRaisesRegex(contract.ContractError, "pathname"):
                item.checkpoint()
            item.close()

            direct = root / "direct.img"
            direct.write_bytes(b"x")
            os.chmod(direct, 0o600)
            hardlink = root / "hard.img"
            os.link(direct, hardlink)
            with self.assertRaisesRegex(contract.ContractError, "link count"):
                contract.BoundArtifact.open(
                    role="candidate",
                    path=direct,
                    expected_size=1,
                    expected_sha256=sha(b"x"),
                    anchor=root,
                    expected_uid=os.getuid(),
                    expected_gid=os.getgid(),
                )
            symlink = root / "symlink.img"
            symlink.symlink_to(direct)
            with self.assertRaises(OSError):
                contract.BoundArtifact.open(
                    role="candidate",
                    path=symlink,
                    expected_size=1,
                    expected_sha256=sha(b"x"),
                    anchor=root,
                    expected_uid=os.getuid(),
                    expected_gid=os.getgid(),
                )
            hardlink.unlink()
            os.chmod(direct, 0o666)
            with self.assertRaisesRegex(contract.ContractError, "writable"):
                contract.BoundArtifact.open(
                    role="candidate",
                    path=direct,
                    expected_size=1,
                    expected_sha256=sha(b"x"),
                    anchor=root,
                    expected_uid=os.getuid(),
                    expected_gid=os.getgid(),
                )

    def test_journal_binds_filename_chain_head_and_one_shot_counts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            journal = contract.Journal(
                Path(raw_root) / "journal",
                "a90-boot-only-f1-20260817-01",
                "1" * 64,
            )
            journal.append("PREPARED", {})
            journal.append("APPROVED", {})
            self.assertEqual([row["state"] for row in journal.read()], ["PREPARED", "APPROVED"])
            (journal.directory / "foreign.tmp").write_text("x", encoding="ascii")
            with self.assertRaisesRegex(contract.ContractError, "unexpected namespace"):
                journal.read()
            (journal.directory / "foreign.tmp").unlink()
            journal.head_path.unlink()
            with self.assertRaisesRegex(contract.ContractError, "without a durable head"):
                journal.read()

        with tempfile.TemporaryDirectory() as raw_root:
            journal = contract.Journal(
                Path(raw_root) / "journal",
                "a90-boot-only-f1-20260817-02",
                "2" * 64,
            )
            journal.append("PREPARED", {})
            original = journal.directory / "0000-PREPARED.json"
            renamed = journal.directory / "0000-APPROVED.json"
            original.rename(renamed)
            with self.assertRaisesRegex(contract.ContractError, "filename/state"):
                journal.read()

    def test_success_terminal_rejects_cross_manifest_and_health_substitution(self) -> None:
        item = manifest()
        raw = contract.canonical_file_bytes(item)
        run_id = "a90-boot-only-f1-20260817-01"
        namespace = f"boot-only-f1-v1-{sha(raw)}-{run_id}"
        final = snapshot(
            item["candidate"]["version"],
            item["candidate"]["build"],
            item["candidate"]["sha256"],
        )
        payload = owner.build_success_payload(
            item, sha(raw), run_id, namespace, "a" * 64, final
        )
        contract.validate_terminal_payload(
            payload, item, sha(raw), run_id=run_id, journal_namespace=namespace
        )
        for field, replacement in (
            ("candidateSha256", "f" * 64),
            ("observedVersion", "other"),
            ("finalHealth", "HEALTH_PENDING"),
        ):
            hostile = copy.deepcopy(payload)
            hostile[field] = replacement
            with self.assertRaises(contract.ContractError):
                contract.validate_terminal_payload(
                    hostile,
                    item,
                    sha(raw),
                    run_id=run_id,
                    journal_namespace=namespace,
                )

    def test_result_consumer_rejects_proof_and_attempt_substitution(self) -> None:
        valid = {
            "schema": contract.RESULT_SCHEMA,
            "status": contract.SUCCESS_TERMINAL,
            "experimentProof": "PROVED",
            "deviceSafetyState": "RESIDENT_HEALTHY",
            "candidateAttemptCount": 1,
            "rollbackAttemptCount": 0,
            "candidateReplay": False,
            "terminalPayloadSha256": "a" * 64,
        }
        contract.validate_result(valid)
        for field, replacement in (
            ("experimentProof", "NO_PROOF_OBSERVER"),
            ("rollbackAttemptCount", 1),
            ("candidateAttemptCount", True),
            ("candidateReplay", True),
        ):
            hostile = copy.deepcopy(valid)
            hostile[field] = replacement
            with self.assertRaises(contract.ContractError):
                contract.validate_result(hostile)


class OwnerStateMachineTests(unittest.TestCase):
    def _engine(
        self,
        root: Path,
        backend: FakeBackend,
    ) -> tuple[owner.OwnerEngine, dict[str, Any], str, str]:
        item = manifest()
        raw = contract.canonical_file_bytes(item)
        run_id = "a90-boot-only-f1-20260817-01"
        namespace = f"boot-only-f1-v1-{sha(raw)}-{run_id}"
        bindings = fake_bindings()
        engine = owner.OwnerEngine(
            manifest_raw=raw,
            manifest=item,
            run_id=run_id,
            journal_namespace=namespace,
            run_directory=root / run_id,
            backend=backend,
            bindings=bindings,
        )
        nonce = "fresh-attended-nonce"
        expires = "2026-08-17T23:59:59Z"
        binding = owner._approval_binding(
            item,
            sha(raw),
            run_id,
            namespace,
            backend.source,
            nonce,
            expires,
            bindings,
        )
        binding_sha = sha(contract.canonical_json(binding))
        token = contract.approval_token(binding_sha)
        approval = {
            "schema": contract.APPROVAL_SCHEMA,
            "binding": binding,
            "bindingSha256": binding_sha,
            "token": token,
            "consumed": False,
        }
        return engine, approval, token, expires

    def test_candidate_success_is_one_candidate_zero_rollback(self) -> None:
        item = manifest()
        source = snapshot(
            item["expectedStart"]["version"],
            item["expectedStart"]["build"],
            item["expectedStart"]["residentQualificationSha256"],
        )
        final = snapshot(
            item["candidate"]["version"],
            item["candidate"]["build"],
            item["candidate"]["sha256"],
        )
        backend = FakeBackend(source, final)
        with tempfile.TemporaryDirectory() as raw_root:
            engine, approval, token, expires = self._engine(Path(raw_root), backend)
            result = engine.execute(
                approval,
                token,
                nonce="fresh-attended-nonce",
                expires_at=expires,
                now="2026-08-17T12:00:00Z",
            )
            self.assertEqual(result["status"], contract.SUCCESS_TERMINAL)
            self.assertEqual((backend.candidate_calls, backend.rollback_calls), (1, 0))
            with self.assertRaisesRegex(contract.ContractError, "empty journal"):
                engine.execute(
                    approval,
                    token,
                    nonce="fresh-attended-nonce",
                    expires_at=expires,
                    now="2026-08-17T12:00:00Z",
                )

    def test_candidate_failure_rolls_back_once_and_keeps_no_proof(self) -> None:
        item = manifest()
        source = snapshot(
            item["expectedStart"]["version"],
            item["expectedStart"]["build"],
            item["expectedStart"]["residentQualificationSha256"],
        )
        final = snapshot(
            item["rollback"]["version"],
            item["rollback"]["build"],
            item["rollback"]["sha256"],
        )
        backend = FakeBackend(source, final, candidate_rc=1)
        with tempfile.TemporaryDirectory() as raw_root:
            engine, approval, token, expires = self._engine(Path(raw_root), backend)
            result = engine.execute(
                approval,
                token,
                nonce="fresh-attended-nonce",
                expires_at=expires,
                now="2026-08-17T12:00:00Z",
            )
            self.assertEqual(result["status"], contract.ROLLBACK_TERMINAL)
            self.assertEqual(result["experimentProof"], "NO_PROOF_OBSERVER")
            self.assertEqual((backend.candidate_calls, backend.rollback_calls), (1, 1))

    def test_live_candidate_process_blocks_rollback(self) -> None:
        item = manifest()
        source = snapshot(
            item["expectedStart"]["version"],
            item["expectedStart"]["build"],
            item["expectedStart"]["residentQualificationSha256"],
        )
        backend = FakeBackend(source, source, candidate_quiescent=False)
        with tempfile.TemporaryDirectory() as raw_root:
            engine, approval, token, expires = self._engine(Path(raw_root), backend)
            result = engine.execute(
                approval,
                token,
                nonce="fresh-attended-nonce",
                expires_at=expires,
                now="2026-08-17T12:00:00Z",
            )
            self.assertEqual(result["status"], contract.RECOVERY_TERMINAL)
            self.assertEqual(result["rollbackAttemptCount"], 0)
            self.assertEqual(backend.rollback_calls, 0)

    def test_pre_intent_target_or_boot_drift_stops_without_candidate(self) -> None:
        item = manifest()
        first = snapshot(
            item["expectedStart"]["version"],
            item["expectedStart"]["build"],
            item["expectedStart"]["residentQualificationSha256"],
        )

        class DriftBackend(FakeBackend):
            def preflight(self, _manifest: dict[str, Any]) -> owner.LiveSnapshot:
                self.preflight_calls += 1
                if self.preflight_calls == 1:
                    return self.source
                return owner.LiveSnapshot(**{**self.source.__dict__, "boot_id": "other-boot"})

        backend = DriftBackend(first, first)
        with tempfile.TemporaryDirectory() as raw_root:
            engine, approval, token, expires = self._engine(Path(raw_root), backend)
            with self.assertRaisesRegex(contract.ContractError, "binding drifted"):
                engine.execute(
                    approval,
                    token,
                    nonce="fresh-attended-nonce",
                    expires_at=expires,
                    now="2026-08-17T12:00:00Z",
                )
            self.assertEqual(backend.candidate_calls, 0)

    def test_production_execute_is_hard_disabled(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(OWNER_PATH), "execute", "/nonexistent", "--operator-attended"],
            cwd=REPO,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("live execution remains blocked", completed.stderr)
        source = OWNER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("a90_v3403_f1_orchestrator", source)
        self.assertFalse(owner.LIVE_EXECUTION_ENABLED)
        self.assertIn(
            "STABLE_SOURCE_PACKAGE_BRIDGE_COMMAND_CORE_PRESENT",
            owner.IMPLEMENTATION_STATUS,
        )
        self.assertIn("RECOVERY_BINDING_AND_RESUME_ABSENT", owner.IMPLEMENTATION_STATUS)
        with tempfile.TemporaryDirectory() as raw_root:
            with self.assertRaisesRegex(contract.ContractError, "H0-disabled"):
                owner.SubprocessBackend(fake_bindings(), Path(raw_root))
        self.assertEqual(owner.helper_runtime_digest(), owner.HELPER_RUNTIME_CLOSURE_SHA256)


if __name__ == "__main__":
    unittest.main()
