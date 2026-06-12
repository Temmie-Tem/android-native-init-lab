"""Regression tests for reusable USB NCM transport helpers."""

import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

ncm = load_revalidation("a90_ncm_transport")


def a90_item(ifname="enxa90", *, link_local="", interface_number="02"):
    return {
        "ifname": ifname,
        "driver": ncm.A90_USB_NCM_DRIVER,
        "usb_vendor": ncm.A90_USB_VENDOR_ID,
        "usb_product": ncm.A90_USB_PRODUCT_ID,
        "link_local": link_local,
        "interface_number": interface_number,
    }


def command_result(*, ok=True, rc=0, stdout="", stderr=""):
    return {"ok": ok, "rc": rc, "stdout": stdout, "stderr": stderr, "command": ["cmd"]}


class BasicHelpers(unittest.TestCase):
    def test_parse_key_values_env_flag_sha_and_scoped_ipv6(self):
        parsed = ncm.parse_key_values("[skip]\na=1\na=2\n no equals \n b = spaced \n")
        self.assertEqual(parsed, {"a": "2", "b": "spaced"})

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.bin"
            path.write_bytes(b"abc")
            self.assertEqual(ncm.sha256_file(path), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

        with mock.patch.dict(os.environ, {"A90_FLAG": "yes", "A90_OFF": "0"}, clear=True):
            self.assertTrue(ncm.env_flag("A90_FLAG"))
            self.assertFalse(ncm.env_flag("A90_OFF"))
            self.assertFalse(ncm.env_flag("MISSING"))

        with mock.patch.object(ncm.socket, "if_nametoindex", return_value=7):
            self.assertEqual(ncm.scoped_ipv6_bind_tuple("fe80::1234%ncm0", "ncm0", 99), ("fe80::1234", 99, 0, 7))
        self.assertEqual(ncm.scoped_ipv6_bind_tuple("2001:db8::1", "ncm0", 1), ("2001:db8::1", 1, 0, 0))

    def test_write_compact_step_supports_log_store_and_plain_store(self):
        class LogStore:
            def __init__(self, root: Path):
                self.run_dir = root

            def write_log(self, category, name, text):
                path = self.run_dir / category / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                return path

        class TextStore:
            def __init__(self):
                self.writes = {}

            def write_text(self, path, text):
                self.writes[path] = text

        with tempfile.TemporaryDirectory() as tmp:
            steps = []
            ncm.write_compact_step(LogStore(Path(tmp)), steps, "step", command=["echo", 1], ok=True, rc=0, stdout="out", stderr="err")
            self.assertEqual(steps[0]["stdout_file"], "host/step.stdout.txt")
            self.assertEqual((Path(tmp) / "host/step.stdout.txt").read_text(encoding="utf-8"), "out")

        text_store = TextStore()
        steps = []
        ncm.write_compact_step(text_store, steps, "plain", command=["cmd"], ok=False, rc=1, stdout="out")
        self.assertEqual(steps[0]["stdout_file"], "logs/host/plain.stdout.txt")
        self.assertEqual(text_store.writes["logs/host/plain.stdout.txt"], "out")


class HostNetdevHelpers(unittest.TestCase):
    def test_is_a90_candidates_sort_and_safe_ifname(self):
        ready_late = a90_item("z", link_local="fe80::2", interface_number="03")
        ready_main = a90_item("a", link_local="fe80::1", interface_number="02")
        no_ll = a90_item("b")
        non_a90 = {**a90_item("c", link_local="fe80::3"), "usb_product": "ffff"}

        self.assertTrue(ncm.is_a90_ncm_netdev(ready_main))
        self.assertFalse(ncm.is_a90_ncm_netdev(non_a90))
        self.assertEqual(ncm.host_ncm_candidates([ready_late, no_ll, ready_main, non_a90], require_link_local=True), [ready_main, ready_late])
        self.assertEqual(ncm.host_ncm_candidates([ready_late, no_ll, ready_main], require_link_local=False), [ready_main, ready_late, no_ll])

        self.assertTrue(ncm.safe_host_ifname("enx566c.b8:d2-17_e9"))
        self.assertFalse(ncm.safe_host_ifname("../bad"))
        self.assertFalse(ncm.safe_host_ifname("bad name"))

    def test_host_netdev_snapshot_merges_ip_json_sysfs_and_udev_metadata(self):
        ip_json = """
        [
          {"ifname":"enxa90","operstate":"UP","address":"aa:bb","addr_info":[
            {"family":"inet","local":"192.168.7.1"},
            {"family":"inet6","local":"fe80::1"}
          ]},
          {"ifname":"lo","addr_info":[]}
        ]
        """
        with mock.patch.object(ncm, "run_command", return_value=command_result(stdout=ip_json)), \
             mock.patch.object(ncm, "netdev_driver_for", side_effect=lambda ifname: ncm.A90_USB_NCM_DRIVER if ifname == "enxa90" else ""), \
             mock.patch.object(ncm, "usb_attrs_for_netdev", side_effect=lambda ifname: {
                 "idVendor": "04e8", "idProduct": "6861", "manufacturer": "Samsung", "product": "NCM", "serial": "SER",
                 "bInterfaceClass": "02", "bInterfaceSubClass": "0d", "bInterfaceProtocol": "00", "bInterfaceNumber": "02", "interface": "NCM",
             } if ifname == "enxa90" else {}), \
             mock.patch.object(ncm, "udev_properties_for_netdev", return_value={}), \
             mock.patch.object(ncm, "cdc_ncm_sysfs_snapshot", return_value={"tx_max": "16384"}):
            snapshot = ncm.host_netdev_snapshot()

        self.assertEqual(len(snapshot), 2)
        self.assertTrue(snapshot[0]["a90_ncm"])
        self.assertEqual(snapshot[0]["link_local"], "fe80::1")
        self.assertEqual(snapshot[0]["ipv4"], ["192.168.7.1"])
        self.assertEqual(snapshot[0]["cdc_ncm"], {"tx_max": "16384"})

    def test_host_netdev_snapshot_returns_empty_on_command_or_json_failure(self):
        with mock.patch.object(ncm, "run_command", return_value=command_result(ok=False, rc=1)):
            self.assertEqual(ncm.host_netdev_snapshot(), [])
        with mock.patch.object(ncm, "run_command", return_value=command_result(stdout="not-json")):
            self.assertEqual(ncm.host_netdev_snapshot(), [])


class HostLinkLocalRepair(unittest.TestCase):
    def test_nmcli_connection_for_device_and_repair_early_exits(self):
        with mock.patch.object(ncm, "run_command", return_value=command_result(stdout="profile\n")):
            self.assertEqual(ncm.nmcli_connection_for_device("enxa90"), "profile")
        with mock.patch.object(ncm, "run_command", return_value=command_result(ok=False, rc=1)):
            self.assertEqual(ncm.nmcli_connection_for_device("enxa90"), "")

        ready = [a90_item(link_local="fe80::1")]
        self.assertEqual(ncm.host_linklocal_repair_nmcli(reason="unit", before=ready)["reason"], "already-ready")
        self.assertEqual(ncm.host_linklocal_repair_nmcli(reason="unit", before=[])["reason"], "host-a90-ncm-interface-not-found")
        with mock.patch.object(ncm.shutil, "which", return_value=None):
            self.assertEqual(ncm.host_linklocal_repair_nmcli(reason="unit", before=[a90_item()])["reason"], "nmcli-not-found")

    def test_host_linklocal_repair_rejects_foreign_connection_and_runs_nmcli_success(self):
        before = [a90_item("enxa90")]
        after = [a90_item("enxa90", link_local="fe80::1")]
        with mock.patch.object(ncm.shutil, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(ncm, "nmcli_connection_for_device", return_value="foreign"):
            foreign = ncm.host_linklocal_repair_nmcli(reason="unit", before=before)
        self.assertEqual(foreign["reason"], "foreign-active-nm-connection")

        with mock.patch.object(ncm.shutil, "which", return_value="/usr/bin/nmcli"), \
             mock.patch.object(ncm, "nmcli_connection_for_device", return_value=""), \
             mock.patch.object(ncm, "run_command", side_effect=[
                 command_result(ok=False, rc=10, stderr="missing profile"),
                 command_result(ok=True, rc=0, stdout="added"),
                 command_result(ok=True, rc=0, stdout="up"),
             ]) as run_command, \
             mock.patch.object(ncm, "host_netdev_snapshot", return_value=after), \
             mock.patch.object(ncm.time, "sleep"):
            repaired = ncm.host_linklocal_repair_nmcli(reason="unit", before=before)

        self.assertTrue(repaired["ok"])
        self.assertEqual(repaired["reason"], "ok")
        self.assertEqual(repaired["ifname"], "enxa90")
        self.assertEqual(repaired["host_link_local"], "fe80::1")
        self.assertEqual(run_command.call_count, 3)
        self.assertEqual(repaired["commands"][0]["command"], ["nmcli", "connection", "delete", ncm.DEFAULT_NM_PROFILE])


class SecretAndArchiveValidation(unittest.TestCase):
    def test_secret_scanners_detect_patterns_across_chunk_boundaries(self):
        self.assertEqual(ncm.scan_secret_bytes(b"abcSECRETdef", {"psk": b"SECRET"}), ["psk"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret.bin"
            path.write_bytes(b"A" * (ncm.SECRET_SCAN_CHUNK_BYTES - 2) + b"SE" + b"CRET")
            self.assertEqual(ncm.scan_secret_file(path, {"psk": b"SECRET"}), ["psk"])
            handle = io.BytesIO(b"hello SECRET world")
            self.assertEqual(ncm.scan_secret_stream(handle, {"psk": b"SECRET"}, max_bytes=64), ["psk"])

    def write_tgz(self, path: Path, entries: dict[str, bytes]) -> None:
        with tarfile.open(path, "w:gz") as tar:
            for name, data in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

    def test_validate_uploaded_archive_accepts_valid_redacted_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "logs.tgz"
            self.write_tgz(archive, {"logs/connect-result.txt": b"decision=ok\n", "logs/status.txt": b"safe"})

            result = ncm.validate_uploaded_archive(archive, secret_patterns={"psk": b"SECRET"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "ok")
        self.assertIn("logs/connect-result.txt", result["entries"])
        self.assertEqual(result["connect_result_text"], "decision=ok\n")

    def test_validate_uploaded_archive_rejects_forbidden_entries_and_deletes_secret_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            forbidden = Path(tmp) / "forbidden.tgz"
            self.write_tgz(forbidden, {"connect_config.txt": b"nope"})
            forbidden_result = ncm.validate_uploaded_archive(forbidden)
            self.assertFalse(forbidden_result["ok"])
            self.assertEqual(forbidden_result["reason"], "forbidden-entry")
            self.assertTrue(forbidden.exists())

            secret = Path(tmp) / "secret.tgz"
            self.write_tgz(secret, {"logs/result.txt": b"contains SECRET"})
            secret_result = ncm.validate_uploaded_archive(secret, secret_patterns={"psk": b"SECRET"})
            self.assertFalse(secret_result["ok"])
            self.assertEqual(secret_result["reason"], "secret-hit")
            self.assertEqual(secret_result["secret_hits"], ["psk"])
            self.assertTrue(secret_result["archive_deleted"])
            self.assertFalse(secret.exists())

    def test_validate_uploaded_archive_handles_missing_bad_empty_and_large_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = ncm.validate_uploaded_archive(Path(tmp) / "missing.tgz")
            self.assertEqual(missing["reason"], "archive-missing")

            bad = Path(tmp) / "bad.tgz"
            bad.write_text("not tar", encoding="utf-8")
            bad_result = ncm.validate_uploaded_archive(bad)
            self.assertTrue(str(bad_result["reason"]).startswith("tar-validate-failed:"))

            empty = Path(tmp) / "empty.tgz"
            with tarfile.open(empty, "w:gz"):
                pass
            self.assertEqual(ncm.validate_uploaded_archive(empty)["reason"], "empty-tar")

            large = Path(tmp) / "large.tgz"
            with tarfile.open(large, "w:gz") as tar:
                info = tarfile.TarInfo("logs/large.bin")
                info.size = 4
                tar.addfile(info, io.BytesIO(b"data"))
            with mock.patch.object(ncm, "MAX_ARCHIVE_MEMBER_SCAN_BYTES", 3):
                self.assertEqual(ncm.validate_uploaded_archive(large)["reason"], "member-too-large")


if __name__ == "__main__":
    unittest.main()
