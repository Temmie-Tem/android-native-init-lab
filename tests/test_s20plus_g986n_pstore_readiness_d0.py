import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import contextlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_pstore_readiness_d0.py"
SPEC = importlib.util.spec_from_file_location("s20_pstore_test", SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
H = M.health
BOOT = "12345678-1234-1234-1234-123456789abc"


def values():
    result = dict(H.EXPECTED_ROOT_OUTPUT)
    for key in M.HEX_READS:
        if key.startswith("dt_"):
            data = {"dt_compatible": b"ramoops\0", "dt_reg": bytes.fromhex("000000009fa000000000000000100000")}.get(key, bytes.fromhex("00040000"))
        elif key == "backend":
            data = b"ramoops\n"
        elif key == "pmsg_class_dev":
            data = b"506:0\n"
        elif key == "watchdog_pet_time":
            data = b"9360\n"
        elif key == "watchdog_user_pet_enabled":
            data = b"0\n"
        else:
            data = b"1048576\n" if key == "ram_mem_size" else b"262144\n"
        result[key] = "hex:" + data.hex()
        if key.endswith("status"):
            result[key] = "absent"
    result.update(ram_driver="ramoops", pmsg_node="char:1fa:0:1", pstore_mount="mounted")
    result.update({key: "regular:123:1" for key in M.META_READS})
    return result


def transcript(**changes):
    data = values()
    data.update(changes)
    return "".join(f"{key}={data[key]}\n" for key in M.OUTPUT_KEYS).encode()


def inventory(extra=""):
    return ("List of devices attached\n"
            "S20SERIAL device usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
            "S22SERIAL device usb:3-3 product:g0qksx model:SM_S906N device:g0q transport_id:2\n" + extra)


def snapshot(**changes):
    data = dict(model="SM-G986N", device="y2q", product_name="y2qksx", incremental="G986NKSS8IYC2", boot_completed="1", bootanim="stopped", selinux="Enforcing", boot_id=BOOT)
    data.update(changes)
    return "".join(f"{key}={data[key]}\n" for key in H.PUBLIC_SNAPSHOT_KEYS).encode()


class FakeBackend:
    def __init__(self, root=None, inventories=None, snapshots=None):
        self.root = (0, transcript(), b"") if root is None else root
        self.inventories = iter(inventories or [inventory(), inventory()])
        self.snapshots = iter(snapshots or [snapshot(), snapshot()])
        self.calls = []

    def tool_receipt(self):
        return dict(path=H.EXPECTED_ADB_PATH, device=1, inode=2, mtime_ns=3, size=H.EXPECTED_ADB_SIZE, sha256=H.EXPECTED_ADB_SHA256)

    def run(self, argv, timeout, maximum):
        self.calls.append((argv, timeout, maximum))
        if argv[-2:] == ["devices", "-l"]:
            return 0, next(self.inventories).encode(), b""
        if argv[-1] == "get-devpath":
            return 0, b"usb:3-2.1\n", b""
        if "exec-out" in argv:
            return 0, next(self.snapshots), b""
        if "su" in argv:
            return self.root
        raise AssertionError(argv)


class ReadinessTests(unittest.TestCase):
    def collect(self, recorder):
        with mock.patch.object(M, "require_active"):
            return M.collect(recorder)

    def test_complete_metadata_never_claims_retention_or_pid1(self):
        backend = FakeBackend()
        result = self.collect(H.CommandRecorder(backend))
        self.assertEqual(result["readiness"], "METADATA_READY_RETENTION_UNPROVED")
        self.assertFalse(result["retention_proved"])
        self.assertFalse(result["native_pid1_proved"])
        self.assertFalse(result["log_contents_read"])
        self.assertEqual(result["host_command_count"], 6)
        self.assertEqual(result["root_command_count"], 1)
        self.assertEqual(result["s22plus_command_count"], 0)
        self.assertEqual(result["a90_command_count"], 0)
        encoded = json.dumps(result)
        for private in ("S20SERIAL", "S22SERIAL", BOOT, "usb:3-2.1"):
            self.assertNotIn(private, encoded)
        self.assertEqual(len(backend.calls), 6)

    def test_missing_records_are_not_readiness_failure(self):
        facts = M.parse_root((0, transcript(**{k: "unavailable" for k in M.META_READS}), b""))
        self.assertTrue(facts["metadata_ready"])

    def test_not_ready_is_a_valid_observation(self):
        for changes in (
            {"backend": "unavailable"}, {"pstore_mount": "unmounted"},
            {"pstore_mount": "conflict"}, {"pmsg_node": "char:1fb:0:1"},
            {"ram_driver": "mismatch"}, {"ram_pmsg_size": "hex:" + b"0\n".hex()},
            {"dt_status": "hex:" + b"disabled\0".hex()},
            {"dt_status": "unreadable"}, {"pmsg_class_dev": "unavailable"},
            {"dt_status": "unavailable"},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(M.parse_root((0, transcript(**changes), b""))["metadata_ready"])

    def test_unsafe_or_noncanonical_fields_fail_closed(self):
        for changes in (
            {"uid": "2000"}, {"dt_reg": "indirect"}, {"dt_compatible": "oversized"},
            {"backend": "hex:0G"}, {"ram_pmsg_size": "hex:" + b"262144\0\n".hex()},
            {"pmsg_class_dev": "hex:" + b"4096:0\n".hex()},
            {"watchdog_user_pet_enabled": "hex:" + b"2\n".hex()},
            {"last_kmsg": "regular:67108865:1"}, {"pmsg_record": "regular:123:2"},
            {"pmsg_node": "indirect"}, {"pstore_mount": "oversized"},
        ):
            with self.subTest(changes=changes), self.assertRaises(Exception):
                M.parse_root((0, transcript(**changes), b""))
        good = transcript()
        for output in (good[:-1], good + b"extra=1\n", good.replace(b"\n", b"\r\n"), good.replace(b"uid=0", b"uid=0\0")):
            with self.subTest(output=output[:20]), self.assertRaises(Exception):
                M.parse_root((0, output, b""))

    def test_bad_command_envelopes_rejected(self):
        for value in ((True, transcript(), b""), (0, transcript(), b"warning"), (1, transcript(), b""), (0, b"x" * 8193, b""), (0, "text", b"")):
            with self.subTest(value=str(value)[:30]), self.assertRaises(Exception):
                M.parse_root(value)

    def test_target_ambiguity_stops_before_selected_reads(self):
        for text in ("List of devices attached\n", inventory("SECOND device usb:3-4 product:y2qksx model:SM_G986N device:y2q\n"), inventory().replace("S20SERIAL device", "S20SERIAL offline"), inventory().replace("device:y2q ", "device:wrong ")):
            backend = FakeBackend(inventories=[text])
            with self.assertRaises(Exception):
                self.collect(H.CommandRecorder(backend))
            self.assertEqual(len(backend.calls), 1)

    def test_pre_and_post_boot_and_final_inventory_drift(self):
        for snapshots, inventories, count in (
            ([snapshot(incremental="wrong")], None, 3),
            ([snapshot(), snapshot(boot_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")], None, 5),
            (None, [inventory(), inventory().replace("usb:3-2.1", "usb:3-2.2")], 6),
        ):
            backend = FakeBackend(snapshots=snapshots, inventories=inventories)
            with self.assertRaises(Exception):
                self.collect(H.CommandRecorder(backend))
            self.assertEqual(len(backend.calls), count)

    def test_dormant_cli_and_backend_have_zero_contact(self):
        with mock.patch.object(M, "ACTIVE", False), mock.patch.object(M, "allocate_evidence", side_effect=AssertionError), mock.patch.object(H.base, "bounded_command", side_effect=AssertionError), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(M.main(["--connected"]), 2)
            with self.assertRaises(M.ReadinessError):
                M.FixedBackend()
            with self.assertRaises(M.ReadinessError):
                M.collect(H.CommandRecorder(FakeBackend()))

    def test_contract_and_source_must_agree(self):
        section = (M.CONTRACT_SECTION + "\n\nStatus: **BINDING - PSTORE READINESS D0 ACTIVE**\n"
                   + "Runner-Normalized-SHA256: `" + M.source_receipt()["normalized_sha256"] + "`\n"
                   + "Root-Script-SHA256: `" + M.digest(M.ROOT_SCRIPT.encode()) + "`\n")
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, "repo_root", return_value=Path(temp)), mock.patch.object(M, "ACTIVE", True):
            contract = Path(temp) / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(section)
            M.require_active()
            for bad in ("", section + section, section.replace("ACTIVE**", "DORMANT**"), section.replace(M.digest(M.ROOT_SCRIPT.encode()), "0" * 64)):
                contract.write_text(bad)
                with self.assertRaises(Exception):
                    M.require_active()

    def test_fixed_backend_rejects_arbitrary_commands_and_replay(self):
        fake = FakeBackend()
        with mock.patch.object(M, "require_active"), mock.patch.object(M, "bounded_capture", side_effect=fake.run), mock.patch.object(H.base, "tool_receipt", side_effect=lambda _: fake.tool_receipt()):
            backend = M.FixedBackend()
            for argv in ([H.EXPECTED_ADB_PATH, "shell", "su"], [H.EXPECTED_ADB_PATH, "devices"]):
                with self.assertRaises(M.ReadinessError):
                    backend.run(argv, 10.0, 32768)
            self.assertEqual(fake.calls, [])
            self.collect(H.CommandRecorder(backend))
            with self.assertRaises(M.ReadinessError):
                backend.run([H.EXPECTED_ADB_PATH, "devices", "-l"], 10.0, 32768)
            self.assertEqual(len(fake.calls), 6)

    def test_bounded_capture_preserves_partial_timeout_and_overflow_digests(self):
        for payload, timeout, maximum, reason in (
            ("import os,time; os.write(1,b'partial-root-fixture\\n'); time.sleep(5)", 0.2, 128, "timeout"),
            ("import os; os.write(1,b'X'*10000)", 2, 32, "output_limit"),
            ("import os; os.write(2,b'E'*10000)", 2, 32, "output_limit"),
        ):
            with self.subTest(reason=reason), mock.patch.object(M, "require_active"), self.assertRaises(M.CaptureClosed) as caught:
                M.bounded_capture([sys.executable, "-c", payload], timeout, maximum)
            capture = caught.exception.capture
            self.assertEqual(capture["stop_reason"], reason)
            self.assertLessEqual(capture["stdout_size"] + capture["stderr_size"], maximum)
            self.assertFalse(capture["raw_published"])
            if reason == "timeout":
                self.assertEqual(capture["stdout_sha256"], M.digest(b"partial-root-fixture\n"))

    def test_root_capture_failure_reaches_private_terminal_without_retry(self):
        class TimedOutBackend(FakeBackend):
            def run(self, argv, timeout, maximum):
                if "su" in argv:
                    self.calls.append((argv, timeout, maximum))
                    return M.bounded_capture([sys.executable, "-c", "import os,time; os.write(1,b'partial-root-fixture\\n'); time.sleep(5)"], 0.2, maximum)
                return super().run(argv, timeout, maximum)
        backend = TimedOutBackend()
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, "repo_root", return_value=Path(temp)), mock.patch.object(M, "require_active"), mock.patch.object(M, "FixedBackend", return_value=backend), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(M.main(["--connected"]), 1)
            result = json.loads(next((Path(temp) / M.PRIVATE_ROOT).glob("*/failure.json")).read_text())
        self.assertEqual(result["host_command_count"], 4)
        self.assertEqual(result["root_command_count"], 1)
        self.assertEqual(result["root_transcript_digest"]["stdout_sha256"], M.digest(b"partial-root-fixture\n"))
        self.assertEqual(result["last_command_capture"]["stop_reason"], "timeout")
        self.assertEqual(len(backend.calls), 4)

    def test_host_evidence_uses_own_namespace_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, "repo_root", return_value=Path(temp)):
            with M.allocate_evidence() as evidence:
                evidence.publish_json("result.json", {"test": 1})
                with self.assertRaises(Exception):
                    evidence.publish_json("result.json", {"test": 2})
                self.assertEqual(json.loads((evidence.path / "result.json").read_text()), {"test": 1})
            self.assertFalse((Path(temp) / H.FIXED_PRIVATE_ROOT).exists())

    def test_indirect_evidence_root_rejected(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, "repo_root", return_value=Path(temp)):
            root = Path(temp)
            (root / "foreign").mkdir()
            (root / "workspace").symlink_to(root / "foreign", target_is_directory=True)
            with self.assertRaises(Exception):
                M.allocate_evidence()

    def test_failure_retains_only_digests_and_actual_prefix(self):
        backend = FakeBackend(root=(1, b"secret-target-output", b"private-error"))
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(M, "repo_root", return_value=Path(temp)), mock.patch.object(M, "require_active"), mock.patch.object(M, "FixedBackend", return_value=backend), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(M.main(["--connected"]), 1)
            path = next((Path(temp) / M.PRIVATE_ROOT).glob("*/failure.json"))
            raw = path.read_bytes()
            self.assertNotIn(b"secret-target-output", raw)
            self.assertNotIn(b"private-error", raw)
            self.assertNotIn("secret-target-output", output.getvalue())
            result = json.loads(raw)
            self.assertEqual(result["host_command_count"], 4)
            self.assertEqual(result["root_command_count"], 1)
            self.assertFalse(result["root_transcript_digest"]["raw_published"])
            self.assertEqual(len(backend.calls), 4)

    def test_shell_argument_survives_adb_shell_join(self):
        self.assertEqual(shlex.split("su -c " + M.ROOT_ARGUMENT), ["su", "-c", M.ROOT_SCRIPT])
        self.assertEqual(H.PUBLIC_SHELL_ARGUMENT, H.PUBLIC_SNAPSHOT_SCRIPT)

    def shell_fixture(self, root):
        script = M.ROOT_SCRIPT
        defaults = values()
        mapping = {}
        for key, path in M.HEX_READS.items():
            dest = root / path.lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            mapping[path] = str(dest)
            if defaults[key].startswith("hex:"):
                dest.write_bytes(bytes.fromhex(defaults[key][4:]))
        for path in M.META_READS.values():
            dest = root / path.lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"LOG-CONTENT-MUST-NOT-BE-READ")
            mapping[path] = str(dest)
        for path, content in (("/proc/self/attr/current", b"u:r:magisk:s0\n"), ("/proc/1/attr/current", b"u:r:init:s0\n")):
            dest = root / path.lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            mapping[path] = str(dest)
        pid1 = root / "proc/1/exe"
        pid1.symlink_to("/system/bin/init")
        mapping["/proc/1/exe"] = str(pid1)
        driver = root / "sys/bus/platform/drivers/ramoops"
        driver.mkdir(parents=True)
        link = root / M.LINK_READS["ram_driver"].lstrip("/")
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(driver, target_is_directory=True)
        mapping[M.LINK_READS["ram_driver"]] = str(link)
        mapping["/sys/bus/platform/drivers/ramoops"] = str(driver)
        mounts = root / "proc/self/mounts"
        pstore = root / "sys/fs/pstore"
        mounts.write_text(f"pstore {pstore} pstore rw 0 0\n")
        mapping["/proc/self/mounts"] = str(mounts)
        mapping["/sys/fs/pstore"] = str(pstore)
        # A real host character node is stat'ed only; no root or mknod needed.
        mapping["/dev/pmsg0"] = "/dev/null"
        (root / M.HEX_READS["pmsg_class_dev"].lstrip("/")).write_bytes(b"1:3\n")
        tools = root / "tools"
        tools.mkdir()
        for name in ("stat", "od", "tr", "head", "cat", "readlink"):
            mapping["/system/bin/" + name] = shutil.which(name)
        for name, body in (("id", "printf '0\\n'"), ("getenforce", "printf 'Enforcing\\n'"), ("magisk", "if [ \"$1\" = -v ]; then printf '30.7:MAGISK:R\\n'; else printf '30700\\n'; fi")):
            dest = tools / name
            dest.write_text("#!/bin/sh\n" + body + "\n")
            dest.chmod(0o755)
            mapping[("/data/adb/magisk/" if name == "magisk" else "/system/bin/") + name] = str(dest)
        # Replace each original path once, longest first, without rewriting a
        # replacement that itself contains the original path as a suffix.
        pattern = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
        return pattern.sub(lambda match: mapping[match.group()], script), mapping

    def test_real_shell_producer_and_parser_with_fixed_fixture_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            script, _ = self.shell_fixture(Path(temp))
            result = subprocess.run(["/bin/sh", "-c", script], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(b"LOG-CONTENT", result.stdout)
            self.assertTrue(M.parse_root((result.returncode, result.stdout, result.stderr))["metadata_ready"])

    def test_real_shell_rejects_symlink_fifo_and_oversized_metadata(self):
        for kind in ("symlink", "fifo", "oversized"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                script, mapping = self.shell_fixture(root)
                path = Path(mapping[M.HEX_READS["backend"]])
                path.unlink()
                if kind == "symlink":
                    path.symlink_to(root / "missing")
                elif kind == "fifo":
                    os.mkfifo(path)
                else:
                    path.write_bytes(b"A" * 65)
                result = subprocess.run(["/bin/sh", "-c", script], capture_output=True, timeout=10)
                with self.assertRaises(Exception):
                    M.parse_root((result.returncode, result.stdout, result.stderr))


if __name__ == "__main__":
    unittest.main()
