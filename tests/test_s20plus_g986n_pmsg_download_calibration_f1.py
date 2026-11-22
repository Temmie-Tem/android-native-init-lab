"""Exact-route authorisation and stock IYC2 shell fixtures, host-only."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_pmsg_download_calibration_f1 as M
import test_s20plus_g986n_pmsg_device_shell_semantics as fixture


class OwnerState(unittest.TestCase):
    def test_physical_confirmation_is_bound_to_one_restore_and_the_source_topology(self):
        engine = Mock()
        engine.digest.side_effect = lambda value: str(value["type"])
        engine.B0F1Error = RuntimeError
        binding = {"topology_sha256": "topology"}
        prepared = {"marker": binding}
        arm = {"binding_sha256": "key", "type": "arm", "baseline": {"type": "baseline"},
               "marker_result_sha256": "write-result", "expires": 200}
        accepted = {"type": "write-result"}
        arrival = {"endpoint": {"topology_sha256": "topology"}, "baseline_sha256": "baseline",
                   "at": "1970-01-01T00:01:40+00:00"}
        engine.wait_download.return_value = arrival
        records = {"download-arm.json": arm}
        with (patch.object(M, "engine", engine, create=True),
              patch.object(M, "prepared_run", return_value=(prepared, "key")),
              patch.object(M, "read", side_effect=records.__getitem__),
              patch.object(M, "write", side_effect=records.__setitem__) as write,
              patch.object(M, "write_proof", return_value=accepted),
              patch.object(M, "exists", return_value=False) as exists,
              patch.object(M.time, "time", return_value=100), patch.object(M, "require_active"),
              patch.object(M, "finalize", return_value={"status": "F1_DONE"})):
            with self.assertRaises(M.Stop):
                M.confirm("wrong-token")
            engine.transfer_boot.assert_not_called()
            self.assertEqual(M.confirm(M.PHYSICAL + "arm"), {"status": "F1_DONE"})
            engine.transfer_boot.assert_called_once_with(M.RUN, "rollback", arrival["endpoint"], "key")
            self.assertEqual([call.args[0] for call in write.call_args_list],
                             ["download-intent.json", "download-arrival.json"])
            exists.side_effect = lambda name: name == "download-intent.json"
            with self.assertRaises(M.Stop):
                M.confirm(M.PHYSICAL + "arm")
            self.assertEqual(engine.transfer_boot.call_count, 1)

    def test_flipping_owner_flag_cannot_replace_common_authority(self):
        with patch.object(M, "ACTIVE", True):
            with self.assertRaisesRegex(M.Stop, "common and target calibration delegation"):
                M.require_active()

    def test_first_seen_boot_is_pinned_before_completion_even_after_offline(self):
        engine = Mock()
        serial, port = "fixture", "usb:1-1"
        engine.adb_devpath.return_value = port
        offline = ({"serial": serial, "state": "offline"},)
        online = ({"serial": serial, "state": "device"},)
        engine.adb_inventory.side_effect = [offline, online, online]
        engine.target_adb_rows.side_effect = [(), online, online]
        engine.exact_adb_row.return_value = online[0]
        engine.TARGET = {"model": "test", "device": "test", "product": "test", "incremental": "test"}
        first = {"boot_id": "transient-first", "boot_completed": "0", "bootanim": "running",
                 "model": "test", "device": "test", "product_name": "test", "incremental": "test",
                 "selinux": "Enforcing"}
        second = {**first, "boot_id": "later", "boot_completed": "1", "bootanim": "stopped"}
        engine._ordered_output.side_effect = [first, second]
        binding = {"serial_sha256": M.digest(serial.encode()), "topology_sha256": M.digest(port.encode()),
                   "source_boot_sha256": "source"}
        with (patch.object(M, "engine", engine, create=True), patch.object(M, "exists", return_value=False),
              patch.object(M, "write") as write, patch.object(M.time, "sleep")):
            with self.assertRaisesRegex(M.Stop, "changed boots"):
                M.wait_first_return(binding, "key")
        write.assert_called_once_with("first-observed-return.json", {
            "binding_sha256": "key", "boot_sha256": M.digest(first["boot_id"].encode())})

    def test_marker_is_fixed_and_source_boot_cannot_be_used_for_comparison(self):
        marker = M.warm.make_binding(fixture.V1.observation())
        self.assertEqual(len(M.warm.marker_bytes(marker)), 144)
        self.assertIn(b"/system/bin/cat >&4", M.writer_script(marker).encode())
        self.assertNotIn(M.warm.marker_line(marker), M.warm.probe_script(marker))
        with self.assertRaises(M.warm.MarkerError):
            M.reader_script(marker, marker["source_boot_sha256"])


@unittest.skipUnless(fixture.QEMU and fixture.DEVICE_SHELL.exists(), "private exact IYC2 shell fixture unavailable")
class StockShell(unittest.TestCase):
    def setUp(self):
        self.assertEqual(M.digest(fixture.DEVICE_SHELL.read_bytes()),
                         "617e248eb59aef8686884d931e17a354dd6b2b3430285c4da642d16a15285625")
        self.assertEqual(M.digest((fixture.DEVICE_BIN / "toybox").read_bytes()),
                         "320568f020278642b915c3fc9162105590a6a2e64d789b631b53e0df75303026")
        self.device = fixture.DeviceShellTests()

    def target_fixture(self, root, script, **kwargs):
        chosen = root / "chosen"
        chosen.mkdir()
        script = script.replace("/sys/firmware/devicetree/base/chosen", str(chosen))
        return self.device.device_fixture(root, script, **kwargs)

    def test_probe_and_exact_write_acceptance_without_marker_in_stdout(self):
        marker = M.warm.make_binding(fixture.V1.observation())
        for render, parse in ((M.probe_script, M.warm.parse_probe),
                              (M.writer_script, lambda result: M.warm.parse_write(result, marker))):
            with tempfile.TemporaryDirectory() as directory:
                script, _ = self.target_fixture(Path(directory), render(marker))
                result = self.device.run_device_shell(script)
                self.assertTrue(parse((result.returncode, result.stdout, result.stderr))["returned"])
                self.assertNotIn(M.warm.marker_line(marker).encode(), result.stdout)

    def test_write_failure_never_publishes_acceptance(self):
        observation = fixture.V1.observation()
        observation["facts"]["pmsg_node"]["minor"] = 7  # Fixture /dev/full, not a phone.
        marker = M.warm.make_binding(observation)
        with tempfile.TemporaryDirectory() as directory:
            script, mapping = self.target_fixture(Path(directory), M.writer_script(marker), sink="/dev/full")
            node = Path(mapping["/sys/devices/virtual/pmsg/pmsg0/dev"])
            node.write_text("1:7\n")
            result = self.device.run_device_shell(script)
            self.assertEqual(result.returncode, 66, result)
            self.assertNotIn(b"S20PMSG_WRITE_V1", result.stdout)

    def test_return_comparison_through_stock_shell(self):
        marker = M.warm.make_binding(fixture.V1.observation())
        raw_marker = M.warm.marker_bytes(marker)
        for contents, count in ((b"private\x00" + raw_marker, 1),
                                (raw_marker * 2, 2), (b"private\n", 0), (None, 0)):
            with tempfile.TemporaryDirectory() as directory:
                new = fixture.V1.NEW
                script, mapping = self.target_fixture(
                    Path(directory), M.reader_script(marker, new), boot="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
                node = Path(mapping["/sys/fs/pstore/pmsg-ramoops-0"])
                node.unlink()
                if contents is not None:
                    node.write_bytes(contents)
                result = self.device.run_device_shell(script)
                value = M.warm.parse_read((result.returncode, result.stdout, result.stderr))
                self.assertEqual(value["matches"], count)
                self.assertNotIn(b"private", result.stdout)
                self.assertNotIn(raw_marker, result.stdout)

    def test_reader_rejects_failed_producer_even_after_matching_bytes(self):
        marker = M.warm.make_binding(fixture.V1.observation())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, mapping = self.target_fixture(
                root, M.reader_script(marker, fixture.V1.NEW), boot="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            Path(mapping["/sys/fs/pstore/pmsg-ramoops-0"]).write_bytes(M.warm.marker_bytes(marker))
            head = fixture.DEVICE_BIN / "head"
            shim = root / "failed-head"
            shim.write_text(f"#!{fixture.DEVICE_SHELL}\n{head} \"$@\"\nexit 1\n")
            shim.chmod(0o700)
            result = self.device.run_device_shell(script.replace(str(head), str(shim)))
            self.assertEqual(result.returncode, 65, result)
            self.assertNotIn(b"S20PMSG_READ_V1", result.stdout)


if __name__ == "__main__":
    unittest.main()
