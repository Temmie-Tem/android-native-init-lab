"""Host-only tests for exact attended A90 obsolete-rootfs cleanup."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
import tempfile
import time
import types
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from _loader import load_script


cleanup = load_script(
    "workspace/public/src/scripts/server-distro/"
    "a90_obsolete_rootfs_cleanup_v1.py"
)


def image_record(
    fixed: object,
    inode: int,
    host: Path | None,
) -> object:
    bound = (
        cleanup.legacy.BoundFile(host, cleanup.IMAGE_SIZE, fixed.sha256)
        if host is not None
        else None
    )
    return cleanup.ImageRecord(
        role=fixed.role,
        device_path=fixed.device_path,
        size=cleanup.IMAGE_SIZE,
        blocks=4194312,
        mode=cleanup.IMAGE_MODE,
        nlink=1,
        st_dev=179,
        st_ino=inode,
        sha256=fixed.sha256,
        host_preservation=bound,
    )


class ObsoleteRootfsCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.run_id = "a90-sd-cleanup-20260803-01"
        self.run_dir = self.base / self.run_id
        self.run_dir.mkdir()
        self.host0 = self.base / "host0.img"
        self.host1 = self.base / "host1.img"
        self.host0.write_bytes(b"a")
        self.host1.write_bytes(b"b")
        self.fixed_selected = (
            cleanup.FixedImage(
                "obsolete-a90-v3403-debian-f1-20260731-01",
                "/mnt/sdext/a90/runtime/"
                "debian-bookworm-arm64-d3-sysvinit-v3403-keyed-"
                "20260731-01.img",
                "3b971848c1c6586d089a2897a45edbed21fc9918374a3c56810cf1d1b0305f2e",
                self.host0,
            ),
            cleanup.FixedImage(
                "obsolete-a90-v3403-debian-f1-20260731-03",
                "/mnt/sdext/a90/runtime/"
                "debian-bookworm-arm64-d3-sysvinit-v3403-keyed-"
                "20260731-03.img",
                "1bd23fddde41114512ce32b47a5cc30861c075b0544766b38f29df4e054af2d5",
                self.host1,
            ),
        )
        self.inventory = self.run_dir / "inventory.json"
        self.inventory.write_text(
            '{"captured_epoch_sec": %d}\n' % int(time.time()),
            encoding="utf-8",
        )
        self.selected = (
            image_record(self.fixed_selected[0], 101, self.host0),
            image_record(self.fixed_selected[1], 102, self.host1),
        )
        self.protected = (
            image_record(cleanup.FIXED_PROTECTED[0], 103, None),
            image_record(cleanup.FIXED_PROTECTED[1], 104, None),
        )
        bridge_digest, bridge_state = cleanup.legacy.hash_open_regular(
            cleanup.SERIAL_TCP_BRIDGE
        )
        self.bridge_process = {
            "pid": 123,
            "start_epoch_sec": (
                bridge_state.st_mtime_ns + 999_999_999
            )
            // 1_000_000_000
            + 100,
            "script_path": str(cleanup.SERIAL_TCP_BRIDGE),
            "script_sha256": bridge_digest,
            "script_mtime_ns": bridge_state.st_mtime_ns,
            "argv_sha256": "3" * 64,
            "forbidden_options_absent": True,
            "matching_processes": 1,
            "local_endpoint": "127.0.0.1:54321",
        }
        recovery_manifest = cleanup.legacy.BoundFile(
            self.base / "recovery-manifest.json", 1, "4" * 64
        )
        recovery_rollback = cleanup.legacy.BoundFile(
            self.base / "rollback.img", 1, "5" * 64
        )
        restoration_evidence = (
            (
                cleanup.legacy.BoundFile(self.base / "m0", 1, "6" * 64),
                cleanup.legacy.BoundFile(self.base / "r0", 1, "7" * 64),
            ),
            (
                cleanup.legacy.BoundFile(self.base / "m1", 1, "8" * 64),
                cleanup.legacy.BoundFile(self.base / "r1", 1, "9" * 64),
            ),
        )
        self.spec = cleanup.CleanupSpec(
            manifest_path=self.run_dir / "manifest.json",
            manifest_sha256="a" * 64,
            run_id=self.run_id,
            selected_run_ids=(
                "a90-v3403-debian-f1-20260731-01",
                "a90-v3403-debian-f1-20260731-03",
            ),
            inventory=cleanup.legacy.BoundFile(
                self.inventory,
                self.inventory.stat().st_size,
                "b" * 64,
            ),
            bridge_realpath="/dev/ttyACM0",
            bridge_process=self.bridge_process,
            selected=self.selected,
            protected=self.protected,
            source_closure={
                "runner": cleanup.legacy.BoundFile(
                    cleanup.RUNNER,
                    1,
                    "c" * 64,
                ),
                "transport": cleanup.legacy.BoundFile(
                    cleanup.A90CTL,
                    1,
                    "d" * 64,
                ),
                "restoration_staging": cleanup.legacy.BoundFile(
                    cleanup.STAGING_RUNNER,
                    1,
                    "e" * 64,
                ),
                "restoration_tcpctl_host": cleanup.legacy.BoundFile(
                    cleanup.TCPCTL_HOST,
                    1,
                    "f" * 64,
                ),
            },
            f1_result=cleanup.legacy.BoundFile(Path("/private/f1"), 1, "e" * 64),
            d1_result=cleanup.legacy.BoundFile(Path("/private/d1"), 1, "f" * 64),
            display_confirmation=cleanup.legacy.BoundFile(
                Path("/private/display"),
                1,
                "1" * 64,
            ),
            recovery_manifest=recovery_manifest,
            recovery_rollback=recovery_rollback,
            recovery_profile=cleanup.RECOVERY_PROFILE,
            recovery_serial_sha256="a" * 64,
            recovery_observer_device="192.0.2.2",
            restoration_evidence=restoration_evidence,
        )
        self.private_patch = mock.patch.object(
            cleanup,
            "PRIVATE_BASE",
            self.base,
        )
        self.private_root_patch = mock.patch.object(
            cleanup,
            "PRIVATE_ROOT",
            self.base,
        )
        self.private_patch.start()
        self.private_root_patch.start()

    def tearDown(self) -> None:
        self.private_root_patch.stop()
        self.private_patch.stop()
        self.temp.cleanup()

    def test_source_contract_audit_passes(self) -> None:
        self.assertEqual(cleanup.source_contract_issues(), [])

    def test_max_selected_cleanup_is_one_bounded_fixed_arg_frame(self) -> None:
        selected = []
        for index in range(cleanup.MAX_SELECTED):
            kind = 3 + index % 4
            name = (
                "debian-bookworm-arm64-phase2-display-v3406-keyed"
                if kind == 6
                else f"debian-bookworm-arm64-d3-sysvinit-v340{kind}-keyed"
            )
            selected.append(
                replace(
                    self.selected[0],
                    role=f"obsolete-max-{index}",
                    device_path=(
                        f"/mnt/sdext/a90/runtime/{name}-"
                        f"20260801-{index + 1:02d}.img"
                    ),
                    st_ino=4294967295 - index,
                )
            )
        spec = replace(self.spec, selected=tuple(selected))
        command = cleanup._cleanup_command(spec)
        self.assertEqual(len(command), 8)
        self.assertLessEqual(
            cleanup._command_wire_bytes(command),
            cleanup.MAX_CMDV1X_WIRE_BYTES,
        )
        self.assertEqual(command[4].count("/bin/busybox rm --"), 1)
        selectors = cleanup._cleanup_args(spec)[1].split(",")
        self.assertEqual(len(selectors), cleanup.MAX_SELECTED)
        self.assertEqual(
            [cleanup._cleanup_selector_path(value) for value in selectors],
            [item.device_path for item in selected],
        )

    def test_unbounded_script_stops_before_remote_contact(self) -> None:
        with (
            mock.patch.object(cleanup, "_remote") as remote,
            self.assertRaisesRegex(cleanup.ContractError, "bounded cmdv1x frame"),
        ):
            cleanup._run_script("x " * 2000, 1.0, "oversized regression")
        remote.assert_not_called()

    def test_split_preflight_has_final_dispatch_window_recheck(self) -> None:
        source = inspect.getsource(cleanup.execute_cleanup)
        self.assertLess(
            source.index("_read_cleanup_preflight(spec)"),
            source.index("_revalidate_dispatch_window(spec)"),
        )
        self.assertLess(
            source.index("_revalidate_dispatch_window(spec)"),
            source.index("transaction_dir.mkdir"),
        )
        gate = inspect.getsource(cleanup._revalidate_dispatch_window)
        for token in (
            "_inventory_age(spec)",
            "_find_target()",
            "_require_bridge(realpath)",
            "_revalidate_source_closure(spec)",
            "_revalidate_recovery_binding(spec)",
            "_health()",
        ):
            self.assertIn(token, gate)

    def test_restore_baseline_health_cannot_pass(self) -> None:
        common = {
            "cleanup_result_sha256": "0" * 64,
            "restore_indexes": [0, 1],
            "reserve_count": 2,
            "transfer_count": 2,
            "publish_count": 2,
            "response_proven": True,
            "error": None,
            "reconciliation": {
                "selected": ["exact", "exact"],
                "stages": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
                "restored_inodes": [777, 888],
            },
            "reconciliation_error": None,
            "health_error": None,
            "resumed_from_durable_restore": False,
            "observation_bridge_process": self.bridge_process,
        }
        baseline = cleanup._restore_result_value(
            self.spec,
            final_health={"proven": True, "state": "BASELINE_HEALTHY"},
            **common,
        )
        resident = cleanup._restore_result_value(
            self.spec,
            final_health={"proven": True, "state": "RESIDENT_HEALTHY"},
            **common,
        )
        self.assertEqual(
            baseline["outcome"],
            "RECOVERY_PENDING_PARKED_RESTORE_NO_RETRY",
        )
        self.assertEqual(
            resident["outcome"],
            "PASS_EXACT_OBSOLETE_ROOTFS_RESTORED",
        )

    def test_dynamic_selected_and_exact_protected_contract(self) -> None:
        self.assertGreaterEqual(cleanup.MAX_SELECTED, 13)
        self.assertEqual(len(cleanup.FIXED_PROTECTED), 2)
        self.assertIsNotNone(
            cleanup.SELECTION_RUN_ID_RE.fullmatch(
                "a90-v3406-debian-display-f1-20260801-10"
            )
        )
        self.assertIsNotNone(
            cleanup.SELECTABLE_DEVICE_PATH_RE.fullmatch(
                self.fixed_selected[0].device_path
            )
        )
        self.assertTrue(
            cleanup.FIXED_PROTECTED[-1].device_path.endswith(
                "v3406-keyed-20260803-04.img"
            )
        )

    def _selection_fixture(
        self,
        run_id: str,
        device_path: str,
        sha256: str,
    ) -> Path:
        run_dir = self.base / run_id
        (run_dir / "staging-live").mkdir(parents=True)
        host = run_dir / "rootfs.img"
        with host.open("wb") as stream:
            stream.truncate(cleanup.IMAGE_SIZE)
        host.chmod(0o600)
        prepared = run_dir / "prepared-manifest.json"
        prepared.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "debian_rootfs": {
                        "keyed_source": {
                            "local_path": str(host),
                            "device_path": device_path,
                            "size": cleanup.IMAGE_SIZE,
                            "sha256": sha256,
                        }
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        prepared.chmod(0o600)
        prepared_sha = hashlib.sha256(prepared.read_bytes()).hexdigest()
        result = run_dir / "staging-live" / "result.json"
        result.write_text(
            json.dumps(
                {
                    "schema": "a90_v3403_absent_only_staging_adapter_v1",
                    "status": "PASS_ABSENT_ONLY_ROOTFS_STAGED",
                    "run_id": run_id,
                    "manifest_sha256": prepared_sha,
                    "rootfs": {
                        "device_path": device_path,
                        "size": cleanup.IMAGE_SIZE,
                        "sha256": sha256,
                    },
                    "publication": {
                        "primitive": "hardlink-no-clobber",
                        "stage_dir_removed": True,
                        "candidate_allowed": True,
                    },
                    "safety": {
                        "flash": False,
                        "mount": False,
                        "reboot": False,
                        "switch_root": False,
                        "userdata_touched": False,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result.chmod(0o600)
        return host

    def test_selection_is_derived_from_exact_successful_staging_receipt(self) -> None:
        run_id = "a90-v3406-debian-display-f1-20260801-10"
        device_path = (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-"
            "20260801-10.img"
        )
        host = self._selection_fixture(run_id, device_path, "1" * 64)
        selected = cleanup._selection_sources([run_id])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].fixed.device_path, device_path)
        self.assertEqual(selected[0].host_path, host)

    def test_selection_rejects_current_or_incident_protected_path(self) -> None:
        run_id = "a90-v3406-debian-display-f1-20260801-10"
        self._selection_fixture(
            run_id,
            cleanup.FIXED_PROTECTED[-1].device_path,
            cleanup.FIXED_PROTECTED[-1].sha256,
        )
        with self.assertRaisesRegex(cleanup.ContractError, "not an exact"):
            cleanup._selection_sources([run_id])

    def test_three_image_scripts_and_reconciliation_are_dynamic(self) -> None:
        third = replace(
            self.selected[1],
            role="obsolete-third",
            device_path=(
                "/mnt/sdext/a90/runtime/"
                "debian-bookworm-arm64-d3-sysvinit-v3405-keyed-"
                "20260731-01.img"
            ),
            st_ino=105,
        )
        spec = replace(
            self.spec,
            selected=self.selected + (third,),
            selected_run_ids=self.spec.selected_run_ids
            + ("a90-v3405-debian-f1-20260731-01",),
            restoration_evidence=self.spec.restoration_evidence
            + (self.spec.restoration_evidence[-1],),
        )
        script = cleanup._cleanup_script(spec)
        self.assertEqual(script.count("/bin/busybox rm --"), 1)
        self.assertIn("selected_absent=$#", script)
        self.assertEqual(len(cleanup._cleanup_args(spec)[1].split(",")), 3)
        self.assertLessEqual(
            cleanup._command_wire_bytes(cleanup._cleanup_command(spec)),
            cleanup.MAX_CMDV1X_WIRE_BYTES,
        )
        with (
            mock.patch.object(
                cleanup,
                "_read_selected_state",
                side_effect=["absent", "present", "absent"],
            ),
            mock.patch.object(cleanup, "_read_exact_image"),
            mock.patch.object(
                cleanup,
                "_run_script",
                return_value=(
                    "A90CLEAN_FS_STATE work=absent blocks=10 "
                    "used=2 available=8"
                ),
            ),
        ):
            value = cleanup._read_reconciliation(spec)
        self.assertEqual(value["selected"], ["absent", "present", "absent"])

    def test_source_closure_covers_transport_observer_and_recovery(self) -> None:
        paths = cleanup._expected_source_paths()
        required = {
            "runner",
            "transport",
            "legacy_cleanup_primitives",
            "resident_health_parser",
            "serial_tcp_bridge",
            "observation_pipeline",
            "serial_lock",
            "transition_contract",
            "workspace_bootstrap",
            "restoration_staging",
            "restoration_tcpctl_host",
            "restoration_evidence_helper",
            "common_contract",
            "target_contract",
            "risk_tiers",
        }
        self.assertTrue(required.issubset(paths))
        self.assertEqual(paths["serial_tcp_bridge"], cleanup.SERIAL_TCP_BRIDGE)
        self.assertEqual(paths["restoration_staging"], cleanup.STAGING_RUNNER)
        self.assertEqual(paths["restoration_tcpctl_host"], cleanup.TCPCTL_HOST)
        for role, path in cleanup.resident_d1.SOURCE_PATHS.items():
            self.assertEqual(paths[f"d1_recovery_{role}"], path.resolve())

    def test_cleanup_script_has_one_nonrecursive_unlink(self) -> None:
        value = cleanup._cleanup_script(self.spec)
        self.assertEqual(value.count("/bin/busybox rm --"), 1)
        self.assertNotIn("rm -r", value)
        self.assertNotIn("rm -f", value)
        selectors = cleanup._cleanup_args(self.spec)[1].split(",")
        self.assertEqual(len(selectors), len(self.selected))
        self.assertEqual(
            [cleanup._cleanup_selector_path(item) for item in selectors],
            [item.device_path for item in self.selected],
        )
        for item in self.protected:
            self.assertNotIn(item.device_path, value)
        self.assertIn(cleanup.WORK_PATH, value)

    def test_validation_rejects_staging_and_binds_inodes(self) -> None:
        filesystem = cleanup._preflight_filesystem_script(self.spec)
        self.assertIn(".a90-stage-*", filesystem)
        self.assertIn(".a90-d1-stage-*", filesystem)
        for item in self.selected + self.protected:
            args = cleanup._image_exact_args(item, "test")
            self.assertTrue(
                any(f"|{item.st_dev}|{item.st_ino}" in value for value in args)
            )
            self.assertIn(item.sha256, args)
        guards = "\n".join(
            cleanup._selected_use_guard_scripts(self.selected[0], "selected-0")
        )
        for token in (
            "[0-9]*/mountinfo",
            "block/loop*/loop/backing_file",
            "[0-9]*/fd/*",
            "[0-9]*/root",
        ):
            self.assertIn(token, guards)

    def _guard_fixture(self) -> tuple[object, Path, Path, Path, str]:
        root = self.base / "guard"
        sd_mount = root / "sd"
        proc_root = root / "proc"
        sys_root = root / "sys"
        sd_mount.mkdir(parents=True)
        (proc_root / "self").mkdir(parents=True)
        (proc_root / "1" / "fd").mkdir(parents=True)
        (sys_root / "block").mkdir(parents=True)
        first = sd_mount / "first.img"
        second = sd_mount / "second.img"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        first_state = first.stat()
        second_state = second.stat()
        selected = (
            replace(
                self.selected[0],
                device_path=str(first),
                st_dev=first_state.st_dev,
                st_ino=first_state.st_ino,
            ),
            replace(
                self.selected[1],
                device_path=str(second),
                st_dev=second_state.st_dev,
                st_ino=second_state.st_ino,
            ),
        )
        spec = replace(self.spec, selected=selected)
        devno = f"{os.major(first_state.st_dev)}:{os.minor(first_state.st_dev)}"
        baseline = f"1 0 {devno} / {sd_mount} rw - ext4 /dev/fake rw\n"
        (proc_root / "self" / "mountinfo").write_text(baseline, encoding="utf-8")
        (proc_root / "1" / "mountinfo").write_text(baseline, encoding="utf-8")
        (proc_root / "1" / "root").symlink_to(root)
        script = "\n".join(
            script
            for index, item in enumerate(spec.selected)
            for script in cleanup._selected_use_guard_scripts(
                    item,
                    f"selected-{index}",
                    proc_root=str(proc_root),
                    sys_root=str(sys_root),
                    sd_mount=str(sd_mount),
            )
        )
        return spec, proc_root, sys_root, first, script

    def test_use_guard_accepts_unreferenced_files(self) -> None:
        _, _, _, _, script = self._guard_fixture()
        result = subprocess.run(
            ["dash"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("A90CLEAN_USE_MOUNT tag=selected-0 exact=1", result.stdout)

    def test_use_guard_rejects_other_namespace_bind_mount(self) -> None:
        spec, proc_root, _, first, script = self._guard_fixture()
        other = proc_root / "2"
        (other / "fd").mkdir(parents=True)
        (other / "root").symlink_to(self.base)
        devno = f"{os.major(first.stat().st_dev)}:{os.minor(first.stat().st_dev)}"
        relative_root = "/" + first.relative_to(first.parent).as_posix()
        (other / "mountinfo").write_text(
            f"2 1 {devno} {relative_root} /other rw - ext4 /dev/fake rw\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["dash"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 62, result.stderr)
        self.assertEqual(spec.selected[0].device_path, str(first))

    def test_use_guard_rejects_other_namespace_parent_bind_mount(self) -> None:
        _, proc_root, _, first, script = self._guard_fixture()
        other = proc_root / "2"
        (other / "fd").mkdir(parents=True)
        (other / "root").symlink_to(self.base)
        devno = f"{os.major(first.stat().st_dev)}:{os.minor(first.stat().st_dev)}"
        (other / "mountinfo").write_text(
            f"2 1 {devno} / /other rw - ext4 /dev/fake rw\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["dash"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 62, result.stderr)

    def test_use_guard_rejects_open_selected_inode(self) -> None:
        _, proc_root, _, first, script = self._guard_fixture()
        fd_link = proc_root / "1" / "fd" / "7"
        fd_link.symlink_to(first)
        result = subprocess.run(
            ["dash"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 63, result.stderr)

    def test_use_guard_rejects_loop_backing_file(self) -> None:
        _, _, sys_root, first, script = self._guard_fixture()
        loop = sys_root / "block" / "loop0" / "loop"
        loop.mkdir(parents=True)
        (loop / "backing_file").write_text(str(first) + "\n", encoding="utf-8")
        result = subprocess.run(
            ["dash"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 64, result.stderr)

    def test_inventory_parser_accepts_exact_four_records(self) -> None:
        lines = ["WORK_ABSENT=1"]
        fixed_images = self.fixed_selected + cleanup.FIXED_PROTECTED
        for index, fixed in enumerate(fixed_images):
            lines.append(
                "A90CLEAN_IMG|%s|%d|4194312|600|1|179|%d|%s"
                % (
                    fixed.device_path,
                    cleanup.IMAGE_SIZE,
                    100 + index,
                    fixed.sha256,
                )
            )
        lines.append("A90CLEAN_DF|61408048|56516584|1765452")
        records, filesystem = cleanup._parse_inventory(
            "\n".join(lines),
            fixed_images,
        )
        self.assertEqual([item["role"] for item in records], [
            item.role for item in fixed_images
        ])
        self.assertEqual(filesystem["available"], 1765452)

    def test_inventory_parser_rejects_third_or_wrong_path(self) -> None:
        text = (
            "WORK_ABSENT=1\n"
            "A90CLEAN_IMG|/mnt/sdext/a90/runtime/other.img|2147483648|"
            "4194312|600|1|179|1|" + "a" * 64 + "\n"
            "A90CLEAN_DF|1|1|1"
        )
        with self.assertRaisesRegex(cleanup.ContractError, "shape"):
            cleanup._parse_inventory(text, self.fixed_selected + cleanup.FIXED_PROTECTED)

    def test_inventory_uses_bounded_per_image_frames(self) -> None:
        scripts = [cleanup._inventory_work_script(), cleanup._inventory_df_script()]
        scripts.extend(
            cleanup._inventory_image_script(index, fixed)
            for index, fixed in enumerate(
                self.fixed_selected + cleanup.FIXED_PROTECTED
            )
        )
        self.assertTrue(
            all(
                0 < len(script.encode("utf-8"))
                <= cleanup.MAX_INVENTORY_FRAME_SCRIPT_BYTES
                for script in scripts
            )
        )
        self.assertTrue(all(script.count("sha256sum") <= 1 for script in scripts))

    def test_oversized_inventory_frame_stops_before_transport(self) -> None:
        with (
            mock.patch.object(cleanup, "_remote") as remote,
            self.assertRaisesRegex(cleanup.ContractError, "reviewed bound"),
        ):
            cleanup._bounded_inventory_read(
                "x" * (cleanup.MAX_INVENTORY_FRAME_SCRIPT_BYTES + 1),
                1.0,
                "oversized",
            )
        remote.assert_not_called()

    def _bridge_proc(self, *extra: str) -> Path:
        proc_root = self.base / "bridge-proc"
        process = proc_root / "123"
        process.mkdir(parents=True)
        capture = self.base / "logs" / "bridge" / "capture.raw"
        argv = [
            str(Path(cleanup.sys.executable).resolve()),
            str(cleanup.SERIAL_TCP_BRIDGE),
            "--host",
            cleanup.a90ctl.DEFAULT_HOST,
            "--port",
            str(cleanup.a90ctl.DEFAULT_PORT),
            "--device",
            str(cleanup.BRIDGE_DEVICE),
            "--device-glob",
            str(cleanup.BRIDGE_DEVICE)
            + ",/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*",
            "--capture",
            str(capture),
            "--expect-realpath",
            "/dev/ttyACM0",
            *extra,
        ]
        (process / "cmdline").write_bytes(
            b"\0".join(item.encode("utf-8") for item in argv) + b"\0"
        )
        return proc_root

    def test_bridge_binding_accepts_only_canonical_generation(self) -> None:
        proc_root = self._bridge_proc()
        with mock.patch.object(
            cleanup,
            "_process_start_epoch_sec",
            return_value=int(time.time()),
        ):
            value = cleanup._require_bridge("/dev/ttyACM0", proc_root)
        self.assertEqual(value["pid"], 123)
        self.assertEqual(value["script_path"], str(cleanup.SERIAL_TCP_BRIDGE))
        self.assertTrue(value["forbidden_options_absent"])

    def test_bridge_binding_rejects_dangerous_extra_option(self) -> None:
        proc_root = self._bridge_proc("--allow-device-change", "ignored")
        with (
            mock.patch.object(
                cleanup,
                "_process_start_epoch_sec",
                return_value=int(time.time()),
            ),
            self.assertRaisesRegex(cleanup.ContractError, "exactly one"),
        ):
            cleanup._require_bridge("/dev/ttyACM0", proc_root)

    def test_bridge_binding_rejects_source_changed_in_start_second(self) -> None:
        value = dict(self.bridge_process)
        value["script_sha256"] = cleanup._bound(
            cleanup.SERIAL_TCP_BRIDGE,
            private=False,
        ).sha256
        value["script_mtime_ns"] = 100_000_000_001
        value["start_epoch_sec"] = 100
        with (
            mock.patch.object(
                cleanup.legacy,
                "hash_open_regular",
                return_value=(
                    value["script_sha256"],
                    types.SimpleNamespace(st_mtime_ns=value["script_mtime_ns"]),
                ),
            ),
            self.assertRaisesRegex(cleanup.ContractError, "not exact"),
        ):
            cleanup._validated_bridge_process(value)

    def test_manifest_record_rejects_bool_as_inode(self) -> None:
        fixed = cleanup.FIXED_PROTECTED[0]
        value = {
            "role": fixed.role,
            "device_path": fixed.device_path,
            "size": cleanup.IMAGE_SIZE,
            "blocks": 4194312,
            "mode": "600",
            "nlink": 1,
            "st_dev": 179,
            "st_ino": True,
            "sha256": fixed.sha256,
        }
        with self.assertRaisesRegex(cleanup.ContractError, "exact integer"):
            cleanup._record_from_manifest(value, fixed, selected=False)

    def test_manifest_outside_exact_run_path_is_rejected(self) -> None:
        outside = self.base / "outside.json"
        outside.write_text(
            '{"run_id":"a90-sd-cleanup-20260803-01"}\n',
            encoding="utf-8",
        )
        outside.chmod(0o600)
        digest = hashlib.sha256(outside.read_bytes()).hexdigest()
        with self.assertRaisesRegex(cleanup.ContractError, "header"):
            cleanup.load_manifest(outside, digest)

    def test_failed_target_identification_leaves_no_empty_run_dir(self) -> None:
        run_id = "a90-sd-cleanup-20260803-02"
        output = self.base / run_id / "inventory.json"
        with (
            mock.patch.object(
                cleanup,
                "_selection_sources",
                return_value=(types.SimpleNamespace(fixed=self.fixed_selected[0]),),
            ),
            mock.patch.object(
                cleanup,
                "_find_target",
                side_effect=cleanup.ContractError("identity mismatch"),
            ),
            self.assertRaisesRegex(cleanup.ContractError, "identity mismatch"),
        ):
            cleanup.capture_inventory(
                run_id,
                output,
                ["a90-v3403-debian-f1-20260731-01"],
            )
        self.assertFalse(output.parent.exists())

    def test_inventory_capture_rejects_noncanonical_filename(self) -> None:
        run_id = "a90-sd-cleanup-20260803-02"
        output = self.base / run_id / "other.json"
        with self.assertRaisesRegex(cleanup.ContractError, "exact private run"):
            cleanup.capture_inventory(run_id, output, [])

    def test_attendance_is_required_before_any_effect(self) -> None:
        with self.assertRaisesRegex(cleanup.ContractError, "attended-only"):
            cleanup.execute_cleanup(
                self.spec,
                approval="x",
                transaction_dir=self.run_dir / "live",
                operator_attended=False,
            )

    def test_stale_inventory_stops_before_target_contact(self) -> None:
        self.inventory.write_text(
            '{"captured_epoch_sec": %d}\n'
            % (int(time.time()) - cleanup.MAX_INVENTORY_AGE_SEC - 1),
            encoding="utf-8",
        )
        with (
            mock.patch.object(
                cleanup,
                "prepare_approval",
                return_value={"approval_token": "compat"},
            ) as prepare,
            mock.patch.object(
                cleanup,
                "_consume_approval",
                return_value={
                    "approval_binding_sha256": cleanup.legacy.json_sha256(
                        cleanup._approval_binding(self.spec)
                    )
                },
            ),
            mock.patch.object(cleanup, "_find_target") as find_target,
            self.assertRaisesRegex(cleanup.ContractError, "stale"),
        ):
            cleanup.execute_cleanup(
                self.spec,
                approval=None,
                transaction_dir=self.run_dir / "live",
                operator_attended=True,
            )
        prepare.assert_called_once_with(self.spec)
        find_target.assert_not_called()

    def _execute(
        self,
        *,
        dispatch: object,
        reconciliation: dict[str, object] | BaseException,
        final_health: object = None,
    ) -> tuple[dict[str, object], object]:
        def host_hash(path: Path) -> tuple[str, object]:
            expected = (
                self.selected[0].sha256
                if path == self.host0
                else self.selected[1].sha256
            )
            return expected, types.SimpleNamespace(st_size=cleanup.IMAGE_SIZE)

        run_script = mock.Mock(side_effect=[dispatch])
        health_tail = {"proven": True} if final_health is None else final_health
        reconciliation_kwargs = (
            {"side_effect": reconciliation}
            if isinstance(reconciliation, BaseException)
            else {"return_value": reconciliation}
        )
        with (
            mock.patch.object(
                cleanup,
                "_consume_approval",
                return_value={
                    "approval_binding_sha256": cleanup.legacy.json_sha256(
                        cleanup._approval_binding(self.spec)
                    )
                },
            ),
            mock.patch.object(
                cleanup,
                "_find_target",
                return_value=("/dev/ttyACM0", cleanup.USB_SERIAL_SHA256),
            ),
            mock.patch.object(
                cleanup,
                "_require_bridge",
                return_value=self.bridge_process,
            ),
            mock.patch.object(cleanup, "_revalidate_source_closure"),
            mock.patch.object(
                cleanup,
                "_revalidate_recovery_availability",
                return_value={"available": True},
            ),
            mock.patch.object(
                cleanup,
                "_read_cleanup_preflight",
                return_value={
                    "blocks": 61408048,
                    "used": 56516584,
                    "available": 1765452,
                },
            ),
            mock.patch.object(
                cleanup,
                "_revalidate_dispatch_window",
                return_value=(
                    "/dev/ttyACM0",
                    self.bridge_process,
                    {"proven": True},
                ),
            ),
            mock.patch.object(
                cleanup,
                "_health",
                side_effect=[
                    {"proven": True},
                    health_tail,
                ],
            ),
            mock.patch.object(cleanup, "_run_script", run_script),
            mock.patch.object(
                cleanup,
                "_read_reconciliation",
                **reconciliation_kwargs,
            ),
            mock.patch.object(
                cleanup.legacy,
                "hash_open_regular",
                side_effect=host_hash,
            ),
        ):
            result = cleanup.execute_cleanup(
                self.spec,
                approval="exact",
                transaction_dir=self.run_dir / "live",
                operator_attended=True,
            )
        return result, run_script

    def test_success_dispatches_once_and_closes_healthy(self) -> None:
        result, dispatch = self._execute(
            dispatch="A90CLEAN_UNLINKED exact=1 selected_absent=2",
            reconciliation={
                "selected": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
                "filesystem_kib": {"available": 5960000},
            },
        )
        self.assertEqual(
            result["outcome"],
            "PASS_EXACT_HOST_RECOVERABLE_ROOTFS_SET_UNLINKED",
        )
        self.assertEqual(result["dispatch_count"], 1)
        self.assertFalse(result["cleanup_retransmitted"])
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(
            cleanup._validated_existing_cleanup_result(
                self.spec,
                self.run_dir / "live" / "result.json",
            ),
            result,
        )

    def test_ambiguous_dispatch_is_never_retried(self) -> None:
        result, dispatch = self._execute(
            dispatch=TimeoutError("lost response"),
            reconciliation={
                "selected": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
                "filesystem_kib": {"available": 5960000},
            },
        )
        self.assertEqual(
            result["outcome"],
            "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE",
        )
        self.assertEqual(dispatch.call_count, 1)
        self.assertFalse(result["cleanup_retransmitted"])

    def test_partial_effect_parks_without_retry(self) -> None:
        result, _ = self._execute(
            dispatch=TimeoutError("lost response"),
            reconciliation={
                "selected": ["absent", "present"],
                "protected": "exact",
                "work": "absent",
            },
        )
        self.assertEqual(
            result["outcome"],
            "RECOVERY_PENDING_PARKED_PARTIAL_NO_RETRY",
        )
        self.assertFalse(result["cleanup_retransmitted"])

    def test_missing_final_health_parks_without_retry(self) -> None:
        result, dispatch = self._execute(
            dispatch="A90CLEAN_UNLINKED exact=1 selected_absent=2",
            reconciliation={
                "selected": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
                "filesystem_kib": {"available": 5960000},
            },
            final_health=cleanup.ContractError("health unavailable"),
        )
        self.assertEqual(result["outcome"], "RECOVERY_PENDING_PARKED_NO_RETRY")
        self.assertEqual(dispatch.call_count, 1)
        self.assertFalse(result["cleanup_retransmitted"])

    def test_reconciliation_failure_parks_without_retry(self) -> None:
        result, dispatch = self._execute(
            dispatch=TimeoutError("lost response"),
            reconciliation=cleanup.ContractError("protected drift"),
        )
        self.assertEqual(result["outcome"], "RECOVERY_PENDING_PARKED_NO_RETRY")
        self.assertEqual(dispatch.call_count, 1)
        self.assertFalse(result["cleanup_retransmitted"])

    def test_unbounded_free_space_gain_cannot_pass(self) -> None:
        result, _ = self._execute(
            dispatch="A90CLEAN_UNLINKED exact=1 selected_absent=2",
            reconciliation={
                "selected": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
                "filesystem_kib": {"available": 1765453},
            },
        )
        self.assertEqual(result["outcome"], "RECOVERY_PENDING_PARKED_NO_RETRY")
        self.assertFalse(result["free_space_proven"])

    def _write_cleanup_result(self, outcome: str) -> Path:
        path = self.run_dir / "live" / "result.json"
        bridge = dict(self.bridge_process)
        bridge["script_sha256"] = cleanup._bound(
            cleanup.SERIAL_TCP_BRIDGE,
            private=False,
        ).sha256
        reconciliation = (
            {
                "selected": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
                "filesystem_kib": {"available": 5960000},
            }
            if outcome.startswith("PASS_")
            else {
                "selected": ["unknown", "unknown"],
                "protected": "unknown",
                "work": "unknown",
            }
        )
        value = cleanup._cleanup_result_value(
            self.spec,
            approval_binding_sha256=cleanup.legacy.json_sha256(
                cleanup._approval_binding(self.spec)
            ),
            before_filesystem={
                "blocks": 61408048,
                "used": 56516584,
                "available": 1765452,
            },
            response_proven=outcome
            == "PASS_EXACT_HOST_RECOVERABLE_ROOTFS_SET_UNLINKED",
            dispatch_error=None,
            reconciliation=reconciliation,
            reconciliation_error=None,
            final_health={"proven": True},
            health_error=None,
            resumed_from_durable_dispatch=False,
            observation_bridge_process=bridge,
        )
        self.assertEqual(value["outcome"], outcome)
        cleanup.legacy.write_private_json_exclusive(
            path,
            value,
        )
        return path

    def _write_dispatched_cleanup_journal(self) -> Path:
        live = self.run_dir / "live"
        live.mkdir(mode=0o700)
        live.chmod(0o700)
        approval_binding_sha256 = cleanup.legacy.json_sha256(
            cleanup._approval_binding(self.spec)
        )
        cleanup.legacy.write_private_json_exclusive(
            live / "intent.json",
            {
                "schema": "a90_attended_sd_exact_rootfs_cleanup_intent_v1",
                "created_utc": "2026-08-03T00:00:00Z",
                "run_id": self.run_id,
                "manifest_sha256": self.spec.manifest_sha256,
                "approval_binding_sha256": approval_binding_sha256,
                "target": {
                    "bridge_realpath": self.spec.bridge_realpath,
                    "usb_serial_sha256": cleanup.USB_SERIAL_SHA256,
                    "bridge": self.spec.bridge_process,
                },
                "before_health": {"proven": True},
                "before_filesystem_kib": {
                    "blocks": 61408048,
                    "used": 56516584,
                    "available": 1765452,
                },
                "recovery_available": {"proven": True},
                "selected_paths": [
                    item.device_path for item in self.spec.selected
                ],
                "protected_paths": [
                    item.device_path for item in self.spec.protected
                ],
                "unlink_dispatch_count_max": 1,
                "unlink_retry_forbidden": True,
            },
        )
        cleanup.legacy.write_private_json_exclusive(
            live / "dispatch-started.json",
            {
                "schema": "a90_attended_sd_exact_rootfs_cleanup_dispatch_v1",
                "created_utc": "2026-08-03T00:00:01Z",
                "run_id": self.run_id,
                "dispatch_count": 1,
                "cleanup_command_sha256": cleanup.legacy.json_sha256(
                    {"argv": cleanup._cleanup_command(self.spec)}
                ),
                "approval_consumed": True,
                "retry_forbidden": True,
            },
        )
        return live

    @staticmethod
    def _rewrite_private_record(path: Path, value: dict[str, object]) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        path.chmod(0o600)

    def test_cleanup_result_rejects_boolean_dispatch_count(self) -> None:
        path = self._write_cleanup_result("RECOVERY_PENDING_PARKED_NO_RETRY")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["dispatch_count"] = True
        self._rewrite_private_record(path, value)
        with self.assertRaisesRegex(cleanup.ContractError, "not exact"):
            cleanup._validated_existing_cleanup_result(self.spec, path)

    def test_cleanup_result_rejects_integer_boolean_impersonation(self) -> None:
        base_path = self._write_cleanup_result(
            "RECOVERY_PENDING_PARKED_NO_RETRY"
        )
        base = json.loads(base_path.read_text(encoding="utf-8"))
        mutations = {
            "device_write": 1,
            "payload_transfer": 0,
            "partition_write": 0,
            "flash": 0,
            "other_target_commands": False,
            "free_space_proven": 0,
            "free_gain_kib": False,
            "free_gain_bounds_kib": [False, 4259848],
        }
        for index, (field, replacement) in enumerate(mutations.items()):
            with self.subTest(field=field):
                value = json.loads(json.dumps(base))
                value[field] = replacement
                path = self.base / f"cleanup-bool-{index}.json"
                cleanup.legacy.write_private_json_exclusive(path, value)
                with self.assertRaisesRegex(cleanup.ContractError, "not exact"):
                    cleanup._validated_existing_cleanup_result(self.spec, path)

    def test_cleanup_resume_result_rejects_numeric_flags(self) -> None:
        base_path = self._write_cleanup_result(
            "RECOVERY_PENDING_PARKED_NO_RETRY"
        )
        base = json.loads(base_path.read_text(encoding="utf-8"))
        base["resumed_from_durable_dispatch"] = True
        base["resume_device_write"] = False
        base["recovery_available"] = {"proven": False}
        for index, field in enumerate(("resume_device_write", "proven")):
            with self.subTest(field=field):
                value = json.loads(json.dumps(base))
                if field == "proven":
                    value["recovery_available"]["proven"] = 0
                else:
                    value[field] = 0
                path = self.base / f"cleanup-resume-bool-{index}.json"
                cleanup.legacy.write_private_json_exclusive(path, value)
                with self.assertRaisesRegex(
                    cleanup.ContractError,
                    "flags are not exact",
                ):
                    cleanup._validated_existing_cleanup_result(self.spec, path)

    def test_restore_result_rejects_integer_boolean_impersonation(self) -> None:
        cleanup_sha = "a" * 64
        base = cleanup._restore_result_value(
            self.spec,
            cleanup_result_sha256=cleanup_sha,
            restore_indexes=[0],
            reserve_count=0,
            transfer_count=0,
            publish_count=0,
            response_proven=False,
            error={"type": "test", "message": "parked"},
            reconciliation={
                "selected": ["absent", "exact"],
                "stages": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
            },
            reconciliation_error=None,
            final_health={"proven": True},
            health_error=None,
            resumed_from_durable_restore=False,
            observation_bridge_process=self.bridge_process,
        )
        mutations = {
            "payload_transfer": 0,
            "partition_write": 0,
            "flash": 0,
            "other_target_commands": False,
            "response_proven": 0,
            "transfer_retransmitted": 0,
            "publish_retransmitted": 0,
        }
        for index, (field, replacement) in enumerate(mutations.items()):
            with self.subTest(field=field):
                value = json.loads(json.dumps(base))
                value[field] = replacement
                path = self.base / f"restore-bool-{index}.json"
                cleanup.legacy.write_private_json_exclusive(path, value)
                with self.assertRaisesRegex(cleanup.ContractError, "not exact"):
                    cleanup._validated_existing_restore_result(
                        self.spec,
                        path,
                        cleanup_sha,
                    )

    def test_restore_resume_result_rejects_numeric_flags(self) -> None:
        cleanup_sha = "b" * 64
        value = cleanup._restore_result_value(
            self.spec,
            cleanup_result_sha256=cleanup_sha,
            restore_indexes=[0],
            reserve_count=0,
            transfer_count=0,
            publish_count=0,
            response_proven=False,
            error={"type": "test", "message": "parked"},
            reconciliation={
                "selected": ["absent", "exact"],
                "stages": ["absent", "absent"],
                "protected": "exact",
                "work": "absent",
            },
            reconciliation_error=None,
            final_health={"proven": True},
            health_error=None,
            resumed_from_durable_restore=True,
            observation_bridge_process=self.bridge_process,
        )
        value["resume_device_write"] = False
        value["recovery_available"] = {"proven": False}
        for index, field in enumerate(("resume_device_write", "proven")):
            with self.subTest(field=field):
                mutated = json.loads(json.dumps(value))
                if field == "proven":
                    mutated["recovery_available"]["proven"] = 0
                else:
                    mutated[field] = 0
                path = self.base / f"restore-resume-bool-{index}.json"
                cleanup.legacy.write_private_json_exclusive(path, mutated)
                with self.assertRaisesRegex(
                    cleanup.ContractError,
                    "flags are not exact",
                ):
                    cleanup._validated_existing_restore_result(
                        self.spec,
                        path,
                        cleanup_sha,
                    )

    def test_resume_rejects_boolean_unlink_limit_before_target(self) -> None:
        live = self._write_dispatched_cleanup_journal()
        path = live / "intent.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["unlink_dispatch_count_max"] = True
        self._rewrite_private_record(path, value)
        with (
            mock.patch.object(cleanup, "_find_target") as find_target,
            self.assertRaisesRegex(cleanup.ContractError, "intent is not exact"),
        ):
            cleanup.resume_dispatched_cleanup(self.spec, transaction_dir=live)
        find_target.assert_not_called()

    def test_resume_rejects_boolean_dispatch_count_before_target(self) -> None:
        live = self._write_dispatched_cleanup_journal()
        path = live / "dispatch-started.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["dispatch_count"] = True
        self._rewrite_private_record(path, value)
        with (
            mock.patch.object(cleanup, "_find_target") as find_target,
            self.assertRaisesRegex(cleanup.ContractError, "dispatch is not exact"),
        ):
            cleanup.resume_dispatched_cleanup(self.spec, transaction_dir=live)
        find_target.assert_not_called()

    def test_resume_dispatched_cleanup_is_read_only_and_allows_bridge_repair(
        self,
    ) -> None:
        live = self._write_dispatched_cleanup_journal()
        repaired_bridge = dict(self.bridge_process)
        repaired_bridge["pid"] = 999
        repaired_bridge["start_epoch_sec"] = (
            self.bridge_process["start_epoch_sec"] + 1
        )
        with (
            mock.patch.object(
                cleanup,
                "_find_target",
                return_value=("/dev/ttyACM0", cleanup.USB_SERIAL_SHA256),
            ),
            mock.patch.object(
                cleanup,
                "_require_bridge",
                return_value=repaired_bridge,
            ),
            mock.patch.object(cleanup, "_revalidate_source_closure"),
            mock.patch.object(
                cleanup,
                "_revalidate_recovery_availability",
                side_effect=cleanup.ContractError("NCM temporarily absent"),
            ),
            mock.patch.object(
                cleanup,
                "_read_reconciliation",
                return_value={
                    "selected": ["absent", "absent"],
                    "protected": "exact",
                    "work": "absent",
                    "filesystem_kib": {"available": 5960000},
                },
            ) as reconciliation,
            mock.patch.object(
                cleanup,
                "_health",
                return_value={"proven": True},
            ) as health,
            mock.patch.object(cleanup, "execute_cleanup") as execute,
        ):
            result = cleanup.resume_dispatched_cleanup(
                self.spec,
                transaction_dir=live,
            )
        self.assertEqual(
            result["outcome"],
            "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE",
        )
        self.assertTrue(result["resumed_from_durable_dispatch"])
        self.assertFalse(result["cleanup_retransmitted"])
        self.assertFalse(result["resume_device_write"])
        self.assertFalse(result["recovery_available"]["proven"])
        self.assertEqual(result["observation_bridge_process"]["pid"], 999)
        self.assertEqual(reconciliation.call_count, 1)
        self.assertEqual(health.call_count, 1)
        execute.assert_not_called()

    def test_resume_requires_durable_dispatch_before_target_contact(self) -> None:
        live = self.run_dir / "live"
        live.mkdir(mode=0o700)
        live.chmod(0o700)
        with (
            mock.patch.object(cleanup, "_find_target") as find_target,
            self.assertRaises((FileNotFoundError, cleanup.ContractError)),
        ):
            cleanup.resume_dispatched_cleanup(
                self.spec,
                transaction_dir=live,
            )
        find_target.assert_not_called()

    def test_restore_rejects_nonparked_cleanup_result_before_contact(self) -> None:
        result_path = self._write_cleanup_result(
            "PASS_EXACT_HOST_RECOVERABLE_ROOTFS_SET_UNLINKED"
        )
        with (
            mock.patch.object(cleanup, "_find_target") as find_target,
            self.assertRaisesRegex(cleanup.ContractError, "does not authorize"),
        ):
            cleanup.execute_restore(
                self.spec,
                cleanup_result_path=result_path,
                transaction_dir=self.run_dir / "live" / "restore",
                operator_attended=True,
            )
        find_target.assert_not_called()

    def test_restore_reconciliation_preserves_partial_exact_state(self) -> None:
        with (
            mock.patch.object(
                cleanup,
                "_read_restore_selected_state",
                side_effect=[("exact", "absent", 777), ("absent", "present", 0)],
            ),
            mock.patch.object(cleanup, "_read_exact_image"),
            mock.patch.object(
                cleanup,
                "_run_script",
                return_value=(
                    "A90CLEAN_FS_STATE work=absent blocks=10 "
                    "used=2 available=8"
                ),
            ),
        ):
            value = cleanup._restore_reconciled(self.spec)
        self.assertEqual(value["selected"], ["exact", "absent"])
        self.assertEqual(value["stages"], ["absent", "present"])
        self.assertEqual(value["restored_inodes"], [777, 0])

    def test_restore_reconcile_shell_reports_exact_and_absent(self) -> None:
        runtime = self.base / "restore-shell"
        runtime.mkdir()
        first = runtime / "first.img"
        second = runtime / "second.img"
        protected0 = runtime / "protected0.img"
        protected1 = runtime / "protected1.img"
        for path, payload in (
            (first, b"a"),
            (protected0, b"b"),
            (protected1, b"c"),
        ):
            path.write_bytes(payload)
            path.chmod(0o600)

        def record(template: object, path: Path, payload: bytes) -> object:
            state = path.stat()
            return replace(
                template,
                device_path=str(path),
                size=1,
                mode="600",
                nlink=1,
                st_dev=state.st_dev,
                st_ino=state.st_ino,
                sha256=hashlib.sha256(payload).hexdigest(),
            )

        selected = (
            record(self.selected[0], first, b"a"),
            replace(
                self.selected[1],
                device_path=str(second),
                size=1,
                mode="600",
                nlink=1,
                st_dev=first.stat().st_dev,
                sha256=hashlib.sha256(b"z").hexdigest(),
            ),
        )
        script = cleanup._restore_selected_state_script()
        outputs = []
        for index, item in enumerate(selected):
            completed = subprocess.run(
                [
                    "dash",
                    "-c",
                    script,
                    "a90-rootfs-gc",
                    item.device_path,
                    f"regular file|1|600|1|{item.st_dev}",
                    item.sha256,
                    f"selected-{index}",
                    str(runtime / f"stage{index}"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            outputs.append(completed.stdout)
        self.assertIn("selected=exact stage=absent", outputs[0])
        self.assertIn("selected=absent stage=absent ino=0", outputs[1])

    def test_restore_publish_timeout_is_never_retried(self) -> None:
        result_path = self._write_cleanup_result(
            "RECOVERY_PENDING_PARKED_NO_RETRY"
        )
        scripts = mock.Mock(
            side_effect=[
                "A90STAGE_PRECHECK exact=1",
                "A90STAGE_RESERVE ready=1",
                "A90STAGE_PAYLOAD verified=1",
                TimeoutError("publish response lost"),
            ]
        )
        completed = types.SimpleNamespace(
            returncode=0,
            stdout="transfer complete",
            stderr="",
        )
        repaired_bridge = dict(self.bridge_process)
        repaired_bridge["pid"] = 456
        repaired_bridge["start_epoch_sec"] = (
            self.bridge_process["start_epoch_sec"] + 1
        )
        repaired_bridge["script_sha256"] = cleanup._bound(
            cleanup.SERIAL_TCP_BRIDGE,
            private=False,
        ).sha256
        with (
            mock.patch.object(
                cleanup,
                "_find_target",
                return_value=("/dev/ttyACM0", cleanup.USB_SERIAL_SHA256),
            ),
            mock.patch.object(
                cleanup,
                "_require_bridge",
                return_value=repaired_bridge,
            ),
            mock.patch.object(cleanup, "_revalidate_source_closure"),
            mock.patch.object(
                cleanup,
                "_revalidate_recovery_availability",
                return_value={"available": True},
            ),
            mock.patch.object(
                cleanup,
                "_recovery_health",
                side_effect=[
                    {"proven": True, "state": "RESIDENT_HEALTHY"},
                    {"proven": True, "state": "RESIDENT_HEALTHY"},
                ],
            ),
            mock.patch.object(
                cleanup,
                "_read_reconciliation",
                return_value={
                    "selected": ["absent", "absent"],
                    "protected": "exact",
                    "work": "absent",
                },
            ),
            mock.patch.object(cleanup, "_run_script", scripts),
            mock.patch.object(
                cleanup,
                "_restore_reconciled",
                side_effect=cleanup.ContractError("not exact"),
            ),
            mock.patch.object(cleanup.subprocess, "run", return_value=completed) as run,
        ):
            result = cleanup.execute_restore(
                self.spec,
                cleanup_result_path=result_path,
                transaction_dir=self.run_dir / "live" / "restore",
                operator_attended=True,
            )
        self.assertEqual(
            result["outcome"],
            "RECOVERY_PENDING_PARKED_RESTORE_NO_RETRY",
        )
        self.assertEqual(result["publish_count"], 1)
        self.assertFalse(result["publish_retransmitted"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(scripts.call_count, 4)
        restore_intent = json.loads(
            (self.run_dir / "live" / "restore" / "0000-intent.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(restore_intent["manifest_bridge_process"]["pid"], 123)
        self.assertEqual(restore_intent["recovery_bridge_process"]["pid"], 456)

        (self.run_dir / "live" / "restore" / "result.json").unlink()
        resumed_bridge = dict(repaired_bridge)
        resumed_bridge["pid"] = 789
        resumed_bridge["start_epoch_sec"] = (
            repaired_bridge["start_epoch_sec"] + 1
        )
        with (
            mock.patch.object(
                cleanup,
                "_find_target",
                return_value=("/dev/ttyACM0", cleanup.USB_SERIAL_SHA256),
            ),
            mock.patch.object(
                cleanup,
                "_require_bridge",
                return_value=resumed_bridge,
            ),
            mock.patch.object(cleanup, "_revalidate_source_closure"),
            mock.patch.object(
                cleanup,
                "_revalidate_recovery_availability",
                return_value={"available": True},
            ),
            mock.patch.object(
                cleanup,
                "_restore_reconciled",
                return_value={
                    "selected": ["exact", "exact"],
                    "stages": ["absent", "absent"],
                    "protected": "exact",
                    "work": "absent",
                    "restored_inodes": [777, 888],
                },
            ) as reconcile,
            mock.patch.object(
                cleanup,
                "_recovery_health",
                return_value={"proven": True, "state": "RESIDENT_HEALTHY"},
            ) as health,
            mock.patch.object(cleanup.subprocess, "run") as resumed_transfer,
            mock.patch.object(cleanup, "_run_script") as resumed_remote,
        ):
            resumed = cleanup.resume_started_restore(
                self.spec,
                cleanup_result_path=result_path,
                transaction_dir=self.run_dir / "live" / "restore",
            )
        self.assertEqual(
            resumed["outcome"],
            "PASS_EXACT_OBSOLETE_ROOTFS_RESTORED_AFTER_AMBIGUOUS_RESPONSE",
        )
        self.assertTrue(resumed["resumed_from_durable_restore"])
        self.assertFalse(resumed["transfer_retransmitted"])
        self.assertFalse(resumed["publish_retransmitted"])
        self.assertFalse(resumed["resume_device_write"])
        self.assertEqual(resumed["reserve_count"], 1)
        self.assertEqual(resumed["transfer_count"], 1)
        self.assertEqual(resumed["publish_count"], 1)
        self.assertEqual(resumed["observation_bridge_process"]["pid"], 789)
        self.assertEqual(reconcile.call_count, 1)
        self.assertEqual(health.call_count, 1)
        resumed_transfer.assert_not_called()
        resumed_remote.assert_not_called()
        self.assertEqual(
            cleanup._validated_existing_restore_result(
                self.spec,
                self.run_dir / "live" / "restore" / "result.json",
                cleanup._bound(result_path, private=True).sha256,
            ),
            resumed,
        )

    def test_policy_delegation_is_narrow_and_present(self) -> None:
        agents = (cleanup.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        target = (
            cleanup.REPO_ROOT
            / "docs"
            / "operations"
            / "targets"
            / "A90_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        tiers = (
            cleanup.REPO_ROOT
            / "docs"
            / "operations"
            / "DEVICE_ACTION_RISK_TIERS.md"
        ).read_text(encoding="utf-8")
        self.assertIn("storage-artifact cleanup sub-capability", agents)
        self.assertIn(
            "A90_ATTENDED_SD_ROOTFS_GC_V2",
            target,
        )
        self.assertIn("single-link regular", target)
        self.assertIn("at most 32", target)
        self.assertIn("per-set review", target)
        self.assertIn("host-process loss", target)
        self.assertIn("never repeats reserve", target)
        self.assertIn("unlinking named target-owned files", tiers)


if __name__ == "__main__":
    unittest.main()
