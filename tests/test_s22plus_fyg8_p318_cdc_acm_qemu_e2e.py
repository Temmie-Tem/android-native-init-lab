from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_cdc_acm_qemu_e2e.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_cdc_acm_qemu_e2e", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 QEMU E2E control")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318CdcAcmQemuE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / P318.DEFAULT_OUTPUT
        cls.result_data = (cls.output / "result.json").read_bytes()
        cls.log_data = (cls.output / "qemu-console.log").read_bytes()
        cls.sources = P318.current_source_data(ROOT)
        cls.value = P318.audit_current_output(
            repo=ROOT,
            guest_root=ROOT / P318.DEFAULT_GUEST_ROOT,
            qemu_root=ROOT / P318.DEFAULT_QEMU_ROOT,
            python_input=ROOT / P318.DEFAULT_PYTHON_INPUT,
            output=cls.output,
        )

    def test_real_observer_receives_exact_prebind_49_bytes_end_to_end(self):
        self.assertEqual(self.value["verdict"], P318.VERDICT)
        self.assertEqual(self.value["transport"]["banner_size"], 49)
        self.assertTrue(self.value["transport"]["accepted"])
        self.assertTrue(self.value["transport"]["dummy_hcd_transport"])
        self.assertTrue(
            self.value["transport"]["real_python_selector_open_read_receipt"]
        )
        self.assertTrue(self.value["transport"]["terminal_complete_line"])
        self.assertTrue(
            self.value["scope"]["dummy_hcd_to_real_python_end_to_end"]
        )
        self.assertFalse(self.value["scope"]["actual_root_udev_guard"])
        self.assertFalse(
            self.value["scope"]["poll_packbits_47_48_qualified_by_this_control"]
        )

    def test_terminal_requires_a_complete_line(self):
        complete = P318.PASS_LINE + b"\r\n"
        self.assertIn(complete, self.log_data)
        truncated = self.log_data.replace(complete, P318.PASS_LINE, 1)
        with self.assertRaisesRegex(
            P318.ControlError, "console markers|incomplete control tail"
        ):
            P318.audit_console(truncated, self.value["build"]["config"])

    def test_incomplete_control_tail_is_rejected(self):
        additions = (
            b"P318_QEMU result=FAIL",
            b"P318_QEMU observer=FAIL error=Attack",
            b"P318_QEMU result=PASS verdict=ATTACK banner_bytes=49",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                with self.assertRaisesRegex(P318.ControlError, "incomplete control tail"):
                    P318.audit_console(
                        self.log_data + addition,
                        self.value["build"]["config"],
                    )

    def test_terminal_multiplicity_is_rejected(self):
        additions = (
            P318.PASS_LINE,
            b"P318_QEMU result=PASS verdict=ATTACK banner_bytes=49",
            b"P318_QEMU result=UNKNOWN foo=1",
            b"P318_QEMU result=FAIL",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                with self.assertRaisesRegex(
                    P318.ControlError, "markers|multiplicity|failure"
                ):
                    P318.audit_console(
                        self.log_data + addition + b"\n",
                        self.value["build"]["config"],
                    )

    def test_post_terminal_kernel_panic_is_rejected(self):
        with self.assertRaisesRegex(P318.ControlError, "kernel panic"):
            P318.audit_console(
                self.log_data + b"Kernel panic - not syncing: fixture\n",
                self.value["build"]["config"],
            )

    def test_exact_nine_module_lines_are_required(self):
        first = b"P318_QEMU module=usb-common status=PASS\r\n"
        replacement = b"P318_QEMU module=usbcore status=PASS\r\n"
        mutations = (
            self.log_data.replace(first, b"", 1),
            self.log_data.replace(first, replacement, 1),
            self.log_data.replace(
                first,
                b"P318_QEMU module=unknown status=PASS\r\n",
                1,
            ),
            self.log_data.replace(first, first + first, 1),
        )
        for mutated in mutations:
            with self.subTest():
                with self.assertRaisesRegex(P318.ControlError, "module sequence"):
                    P318.audit_console(mutated, self.value["build"]["config"])

    def test_preserved_result_requires_the_complete_current_source_set(self):
        incomplete = dict(self.sources)
        incomplete.pop("controller")
        with self.assertRaisesRegex(P318.ControlError, "current source set"):
            P318.audit_preserved(
                result_data=self.result_data,
                log_data=self.log_data,
                current_sources=incomplete,
            )
        drifted = dict(self.sources)
        drifted["observer"] += b"\n"
        with self.assertRaisesRegex(P318.ControlError, "preserved source differs"):
            P318.audit_preserved(
                result_data=self.result_data,
                log_data=self.log_data,
                current_sources=drifted,
            )

    def test_guest_order_and_receipt_reopen_mutations_are_rejected(self):
        guest = self.sources["guest"]
        mutations = (
            guest.replace(b"write_all(tty_descriptor, banner)", b"write_once(tty_descriptor, banner)", 1),
            guest.replace(b"reopened = observer.validate_receipt(", b"reopened = observer.skip_receipt(", 1),
            guest.replace(b"wait_ready(ready_read, child)", b"skip_ready(ready_read, child)", 1),
        )
        for mutated in mutations:
            with self.subTest():
                with self.assertRaises(P318.ControlError):
                    P318.audit_guest_source(mutated)

    def test_signed_debian_index_binds_all_python_packages(self):
        supply = self.value["build"]["python_supply_chain"]
        self.assertTrue(supply["release_signature_verified"])
        self.assertTrue(supply["signed_index"]["inrelease_binds_packages"])
        self.assertEqual(set(supply["packages"]), set(P318.PYTHON_PACKAGES))
        for value in supply["packages"].values():
            self.assertEqual(value["architecture"], "arm64")
            self.assertEqual(value["sha256"], value["signed_record"]["SHA256"])
            self.assertEqual(str(value["size"]), value["signed_record"]["Size"])

    def test_signed_debian_index_binds_kernel_and_all_nine_modules(self):
        supply = self.value["build"]["guest_supply_chain"]
        self.assertTrue(supply["decompressed_packages_match_signed_index"])
        self.assertTrue(supply["source_inputs_match_execution_snapshot"])
        self.assertTrue(supply["loose_tree_matches_signed_package"])
        self.assertEqual(supply["kernel_package"]["signed_record"]["SHA256"], P318.KERNEL_PACKAGE["sha256"])
        self.assertEqual(supply["kernel_package"]["deb"]["sha256"], P318.KERNEL_PACKAGE["sha256"])
        self.assertEqual(set(supply["modules"]), set(P318.MODULES))
        for name in P318.MODULES:
            self.assertEqual(
                supply["modules"][name]["decompressed"],
                self.value["build"]["modules"][name]["decompressed"],
            )

        signed_packages = (
            self.output
            / "input-snapshots/python/source"
            / P318.PACKAGES_INDEX["filename"]
        ).read_bytes()
        with tempfile.TemporaryDirectory(prefix="p318-guest-no-provenance-") as temporary:
            loose_root = Path(temporary) / "root"
            loose_root.mkdir()
            with self.assertRaisesRegex(P318.ControlError, "Packages.xz.*unavailable"):
                P318.audit_guest_package_snapshot(
                    self.output / "input-snapshots/guest-package",
                    loose_root,
                    signed_packages,
                )

    def test_qemu_is_networkless_and_noninteractive(self):
        snapshot = self.value["build"]["qemu"]["execution_snapshot"]
        command, environment = P318.qemu_command(
            self.output / "input-snapshots/qemu",
            self.output,
            snapshot["interpreter_name"],
        )
        joined = " ".join(command)
        for clause in (
            "-display none",
            "-audio none",
            "-serial stdio",
            "-monitor none",
            "-nic none",
            "-no-user-config",
            "-nodefaults",
            "--unshare-all",
            "--clearenv",
            "--ro-bind",
            "rdinit=/init",
        ):
            self.assertIn(clause, joined)
        self.assertNotIn(" -L ", f" {joined} ")
        self.assertEqual(
            set(environment),
            {"LANG", "LC_ALL", "LD_LIBRARY_PATH", "PATH", "QEMU_MODULE_DIR", "TZ"},
        )
        self.assertNotIn("LD_PRELOAD", environment)
        self.assertNotIn("LD_AUDIT", environment)

    def test_qemu_execution_uses_only_the_snapshotted_loader_closure(self):
        qemu = self.value["build"]["qemu"]
        snapshot = qemu["execution_snapshot"]
        mapped = qemu["observed_mapped_files"]
        expected = {snapshot["binary"]["path"]} | {
            snapshot["loader_closure"][name]["path"]
            for name in snapshot["qemu_loader_names"]
        }
        self.assertEqual(set(mapped), expected)
        self.assertTrue(all(path.startswith(snapshot["root"] + "/") for path in mapped))
        self.assertIs(snapshot["module_directory_empty"], True)
        self.assertFalse(qemu["source"]["ambient_environment_inherited"])
        self.assertFalse(qemu["source"]["external_module_directory_used"])

        maps_data = (self.output / "qemu-proc-maps.log").read_bytes()
        removed_path = next(iter(snapshot["loader_closure"].values()))["path"]
        removed = b"\n".join(
            line
            for line in maps_data.split(b"\n")
            if removed_path.encode("utf-8") not in line
        )
        with self.assertRaisesRegex(P318.ControlError, "omit"):
            P318.audit_qemu_mapped_closure(snapshot, removed, self.output)

        drifted = json.loads(json.dumps(snapshot))
        drifted["binary"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(P318.ControlError, "identity"):
            P318.audit_qemu_mapped_closure(drifted, maps_data, self.output)

    def test_sandbox_launcher_and_empty_host_configuration_are_retained(self):
        qemu = self.value["build"]["qemu"]
        snapshot = qemu["execution_snapshot"]
        launcher_expected = {snapshot["sandbox_launcher"]["path"]} | {
            snapshot["loader_closure"][name]["path"]
            for name in snapshot["sandbox_launcher_loader_names"]
        }
        self.assertEqual(
            set(qemu["observed_launcher_mapped_files"]), launcher_expected
        )
        self.assertEqual(len(launcher_expected), 6)
        sandbox = qemu["sandbox"]
        self.assertTrue(sandbox["mount_namespace_isolated"])
        self.assertTrue(sandbox["network_namespace_isolated"])
        self.assertTrue(sandbox["execution_read_only"])
        self.assertTrue(sandbox["host_root_usr_absent"])
        self.assertEqual(
            sandbox["empty_configuration_directories"],
            ["/etc", "/run", "/sys", "/var"],
        )
        self.assertFalse(sandbox["host_kernel_runtime_interfaces_byte_frozen"])

    def test_execution_snapshot_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="p318-snapshot-mutation-") as temporary:
            path = Path(temporary) / "input.bin"
            path.write_bytes(b"verified execution bytes")
            expected = P318.identity(path)
            self.assertEqual(P318.require_receipt(path, expected, "fixture"), path.read_bytes())
            path.write_bytes(b"mutated execution bytes")
            with self.assertRaisesRegex(P318.ControlError, "identity"):
                P318.require_receipt(path, expected, "fixture")

    def test_strict_result_json_rejects_duplicates_and_bool_integer_aliases(self):
        duplicate = self.result_data.replace(
            b"{\n",
            (b'{\n  "schema": "' + P318.SCHEMA.encode("ascii") + b'",\n'),
            1,
        )
        accepted_integer = self.result_data.replace(b'"accepted": true', b'"accepted": 1', 1)
        actions_boolean = self.result_data.replace(b'"device_actions": 0', b'"device_actions": false', 1)
        for mutated in (duplicate, accepted_integer, actions_boolean):
            with self.subTest():
                with self.assertRaises(P318.ControlError):
                    P318.audit_preserved(
                        result_data=mutated,
                        log_data=self.log_data,
                        current_sources=self.sources,
                    )

    def test_result_json_reopens_from_the_exact_console_bytes(self):
        value = P318.strict_json_loads(self.result_data)
        self.assertEqual(value, self.value)
        mutated = self.log_data.replace(b"classification=accepted", b"classification=rejected", 1)
        with self.assertRaises(P318.ControlError):
            P318.audit_preserved(
                result_data=self.result_data,
                log_data=mutated,
                current_sources=self.sources,
            )


if __name__ == "__main__":
    unittest.main()
