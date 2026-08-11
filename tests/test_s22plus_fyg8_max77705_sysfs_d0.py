from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "s22plus_fyg8_max77705_sysfs_d0",
    SCRIPTS / "s22plus_fyg8_max77705_sysfs_d0.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.platform = root / "platform"
        self.i2c = root / "i2c"
        self.drivers = root / "drivers"
        self.modules = root / "proc-modules"
        for path in (self.platform, self.i2c, self.drivers):
            path.mkdir()
        self._populate()

    @staticmethod
    def _write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def _platform_device(self, name: str, compatible: str, driver: str) -> None:
        path = self.platform / name
        path.mkdir()
        self._write(path / "of_node/compatible", compatible.encode() + b"\0")
        self._write(path / "modalias", ("of:NfixtureT(null)C" + compatible + "\n").encode())
        self._write(path / "driver_override", b"(null)\n")
        driver_path = self.drivers / driver
        driver_path.mkdir(exist_ok=True)
        (path / "driver").symlink_to(driver_path)

    def _populate(self) -> None:
        for name in (
            "8c0000.qupv3_geni_se",
            "9c0000.qupv3_geni_se",
            "ac0000.qupv3_geni_se",
        ):
            self._platform_device(name, "qcom,qupv3-geni-se", "qupv3_geni_se")
        for name in ("800000.gpi_dma", "900000.gpi_dma", "a00000.gpi_dma"):
            self._platform_device(name, "qcom,gpi-dma", "gpi_dma")
        for name in (
            "880000.i2c",
            "884000.i2c",
            "888000.i2c",
            "980000.i2c",
            "984000.i2c",
            "988000.i2c",
            "990000.i2c",
            "994000.i2c",
            "a94000.i2c",
        ):
            self._platform_device(name, "qcom,i2c-geni", "i2c_geni")

        target = self.platform / "994000.i2c"
        adapter = target / "i2c-57"
        adapter.mkdir()
        self._write(adapter / "name", b"Geni-I2C\n")
        (self.i2c / "i2c-57").symlink_to(adapter)
        client = adapter / "57-0066"
        client.mkdir()
        self._write(client / "of_node/compatible", b"maxim,max77705\0")
        self._write(client / "modalias", b"of:Nmax77705T(null)Cmaxim,max77705\n")
        self._write(client / "name", b"max77705\n")
        max_driver = self.drivers / "max77705"
        max_driver.mkdir()
        (client / "driver").symlink_to(max_driver)
        (self.i2c / "57-0066").symlink_to(client)

        rows = []
        for name in (
            "msm_geni_se",
            "gpi",
            "i2c_msm_geni",
            "mfd_max77705",
            "pdic_max77705",
            "spu_verify",
        ):
            rows.append(f"{name} 4096 0 - Live 0x00000000")
        self.modules.write_text("\n".join(rows) + "\n", encoding="ascii")

    def run(self) -> bytes:
        script = module.build_snapshot_script(
            platform_root=str(self.platform),
            i2c_root=str(self.i2c),
            proc_modules=str(self.modules),
        )
        completed = subprocess.run(
            ["sh", "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        if completed.returncode or completed.stderr:
            raise AssertionError(
                f"fixture shell failed rc={completed.returncode}: {completed.stderr!r}"
            )
        return completed.stdout


class Max77705SysfsD0Tests(unittest.TestCase):
    def make_fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Fixture]:
        temporary = tempfile.TemporaryDirectory()
        return temporary, Fixture(Path(temporary.name))

    def test_exact_s22_selection_leaves_a90_as_other(self) -> None:
        text = """List of devices attached
A90SERIAL device product:a90 model:SM_A908N device:a90q transport_id:1
S22SERIAL device product:g0q model:SM_S906N device:g0q transport_id:2
"""
        selected = module.select_exact_s22(text)
        self.assertEqual(selected.serial, "S22SERIAL")
        self.assertEqual(selected.serial_sha256, hashlib.sha256(b"S22SERIAL").hexdigest())
        self.assertEqual(
            selected.other_serial_sha256,
            (hashlib.sha256(b"A90SERIAL").hexdigest(),),
        )

    def test_missing_wrong_and_ambiguous_s22_reject(self) -> None:
        cases = (
            "List of devices attached\n",
            "List of devices attached\nX device model:SM_S906B device:g0q\n",
            "List of devices attached\nA device model:SM_S906N device:g0q\nB device model:SM_S906N device:g0q\n",
            "List of devices attached\nA offline model:SM_S906N device:g0q\n",
        )
        for text in cases:
            with self.subTest(text=text), self.assertRaises(module.InventoryError):
                module.select_exact_s22(text)

    def test_real_shell_snapshot_and_parser_accept_exact_3_3_9(self) -> None:
        temporary, fixture = self.make_fixture()
        with temporary:
            result = module.parse_snapshot(fixture.run())
        self.assertEqual(result["platform"]["counts"], {"gpi": 3, "i2c": 9, "qupv3": 3})
        self.assertEqual(result["platform"]["total"], 15)
        self.assertEqual(len(result["platform"]["non_target_override_names"]), 12)
        self.assertEqual(result["platform"]["target_devices"]["i2c"], "994000.i2c")
        self.assertEqual(result["target_i2c"]["max77705_client"]["name"], "57-0066")
        self.assertEqual(result["target_i2c"]["max77705_client"]["driver_name"], "max77705")
        self.assertTrue(all(result["modules"]["substrate"].values()))
        self.assertTrue(all(result["modules"]["excluded"].values()))

    def test_snapshot_script_does_not_change_fixture_bytes_or_links(self) -> None:
        temporary, fixture = self.make_fixture()
        with temporary:
            before_files = {
                path.relative_to(fixture.root).as_posix(): path.read_bytes()
                for path in fixture.root.rglob("*")
                if path.is_file() and not path.is_symlink()
            }
            before_links = {
                path.relative_to(fixture.root).as_posix(): path.readlink().as_posix()
                for path in fixture.root.rglob("*")
                if path.is_symlink()
            }
            module.parse_snapshot(fixture.run())
            after_files = {
                path.relative_to(fixture.root).as_posix(): path.read_bytes()
                for path in fixture.root.rglob("*")
                if path.is_file() and not path.is_symlink()
            }
            after_links = {
                path.relative_to(fixture.root).as_posix(): path.readlink().as_posix()
                for path in fixture.root.rglob("*")
                if path.is_symlink()
            }
        self.assertEqual(after_files, before_files)
        self.assertEqual(after_links, before_links)

    def test_missing_override_rejects(self) -> None:
        temporary, fixture = self.make_fixture()
        with temporary:
            (fixture.platform / "8c0000.qupv3_geni_se/driver_override").unlink()
            with self.assertRaisesRegex(module.InventoryError, "driver_override"):
                module.parse_snapshot(fixture.run())

    def test_nondefault_override_rejects(self) -> None:
        temporary, fixture = self.make_fixture()
        with temporary:
            (fixture.platform / "8c0000.qupv3_geni_se/driver_override").write_text(
                "sentinel\n", encoding="ascii"
            )
            with self.assertRaisesRegex(module.InventoryError, "non-default"):
                module.parse_snapshot(fixture.run())

    def test_count_drift_rejects(self) -> None:
        temporary, fixture = self.make_fixture()
        with temporary:
            path = fixture.platform / "880000.i2c"
            (path / "driver").unlink()
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                else:
                    child.rmdir()
            path.rmdir()
            with self.assertRaisesRegex(module.InventoryError, "exactly 15"):
                module.parse_snapshot(fixture.run())

    def test_duplicate_target_and_malformed_path_reject(self) -> None:
        temporary, fixture = self.make_fixture()
        with temporary:
            payload = fixture.run()
            target_line = next(line for line in payload.splitlines() if line.startswith(b"T\t"))
            with self.assertRaisesRegex(module.InventoryError, "duplicated"):
                module.parse_snapshot(payload + target_line + b"\n")
            fields = payload.splitlines()[0].split(b"\t")
            fields[2] = b"2e2e2f657363617065"  # ../escape
            mutated = b"\t".join(fields) + b"\n" + b"\n".join(payload.splitlines()[1:]) + b"\n"
            with self.assertRaisesRegex(module.InventoryError, "unsafe path"):
                module.parse_snapshot(mutated)

    def test_oversized_and_malformed_output_reject(self) -> None:
        with self.assertRaisesRegex(module.InventoryError, "oversized"):
            module.parse_snapshot(b"X" * (module.MAX_SNAPSHOT_BYTES + 1))
        with self.assertRaisesRegex(module.InventoryError, "malformed"):
            module.parse_snapshot(b"P\t00\n")

    def test_safety_contract_has_only_read_surface(self) -> None:
        result = module.snapshot_safety_contract()
        self.assertEqual(result["result"], "pass")
        self.assertTrue(result["device_read_only"])
        self.assertTrue(all(result["forbidden_tokens_absent"].values()))
        self.assertTrue(all(result["required_reads_present"].values()))
        self.assertNotIn("finit_module", module.SNAPSHOT_SCRIPT)
        self.assertNotIn("/sys/bus/platform/drivers/", module.SNAPSHOT_SCRIPT)

    def test_collect_targets_only_selected_s22(self) -> None:
        temporary, fixture = self.make_fixture()
        calls: list[tuple[str, str]] = []
        s22 = module.AdbRow(
            "S22SERIAL", "device", frozenset({"model:SM_S906N", "device:g0q"})
        )
        a90 = module.AdbRow(
            "A90SERIAL", "device", frozenset({"model:SM_A908N", "device:a90q"})
        )
        selection = module.Selection(
            "S22SERIAL",
            hashlib.sha256(b"S22SERIAL").hexdigest(),
            (a90, s22),
            (hashlib.sha256(b"A90SERIAL").hexdigest(),),
        )

        class FakeClient:
            def __init__(self, *_args: object, **_kwargs: object):
                pass

            def receipt(self) -> dict[str, object]:
                return {"sha256": "a" * 64, "size": 1}

            def topology(self, serial: str) -> str:
                calls.append(("topology", serial))
                return "usb:1-1"

            def properties(self, serial: str) -> dict[str, str]:
                calls.append(("properties", serial))
                return {
                    "model": "SM-S906N",
                    "device": "g0q",
                    "incremental": "S906NKSS7FYG8",
                    "boot_completed": "1",
                    "bootanim": "stopped",
                }

            def root_health(self, serial: str) -> dict[str, str]:
                calls.append(("root_health", serial))
                return {"root": "uid=0(root)"}

        with temporary, tempfile.TemporaryDirectory(
            dir=ROOT / "workspace/private"
        ) as run_name:
            raw = fixture.run()
            run_dir = Path(run_name)
            profile = {"profile_id": "s22plus-fyg8", "target": {"download": {}}}
            usb = {
                "enumerated_devices": 1,
                "download_endpoint_count": 0,
                "snapshot_sha256": "b" * 64,
            }
            with (
                mock.patch.object(module.f1, "load_json", return_value=(profile, b"{}")),
                mock.patch.object(module.f1, "validate_profile"),
                mock.patch.object(module.d0, "AdbReadOnlyClient", FakeClient),
                mock.patch.object(module.d0, "usb_snapshot", return_value=usb),
                mock.patch.object(module.d0, "validate_health", return_value={"healthy": True}),
                mock.patch.object(module, "_host_android_usb_count", return_value=1),
                mock.patch.object(
                    module,
                    "read_adb_inventory",
                    side_effect=[("inventory", selection), ("inventory", selection)],
                ),
                mock.patch.object(
                    module,
                    "_root_snapshot",
                    side_effect=lambda _adb, serial: calls.append(("snapshot", serial)) or raw,
                ),
            ):
                result = module.collect(
                    ROOT,
                    ROOT / "unused-profile.json",
                    Path("/bin/true"),
                    run_dir,
                )
        self.assertEqual(result["a90_command_count"], 0)
        self.assertEqual(result["target_evidence"]["other_target_command_count"], 0)
        self.assertTrue(calls)
        self.assertEqual({serial for _operation, serial in calls}, {"S22SERIAL"})


if __name__ == "__main__":
    unittest.main()
