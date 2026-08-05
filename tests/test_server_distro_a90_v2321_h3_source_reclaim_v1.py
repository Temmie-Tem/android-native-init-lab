"""Host-only tests for exact V2321 H3 SD source reclaim."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


reclaim = load_script(
    "workspace/public/src/scripts/server-distro/"
    "a90_v2321_h3_source_reclaim_v1.py"
)


class V2321H3SourceReclaimTests(unittest.TestCase):
    def image(self, *, selected: bool) -> object:
        fixed = reclaim.SELECTED_FIXED if selected else reclaim.PROTECTED_FIXED
        return reclaim.gc.ImageRecord(
            role=fixed.role,
            device_path=fixed.device_path,
            size=reclaim.gc.IMAGE_SIZE,
            blocks=4194312,
            mode=reclaim.gc.IMAGE_MODE,
            nlink=1,
            st_dev=45825,
            st_ino=1054074 if selected else 1054075,
            sha256=fixed.sha256,
            host_preservation=(
                reclaim.legacy.BoundFile(
                    path=Path("/private/h3.img"),
                    size=reclaim.gc.IMAGE_SIZE,
                    sha256=reclaim.SELECTED_SHA256,
                )
                if selected
                else None
            ),
        )

    def spec(
        self,
        base: Path,
        run_id: str = "a90-v2321-h3-source-reclaim-20260805-01",
    ) -> object:
        (base / run_id).mkdir(parents=True, exist_ok=True)
        inventory = base / run_id / "inventory.json"
        return reclaim.Spec(
            manifest_path=base / run_id / "manifest.json",
            manifest_sha256="1" * 64,
            run_id=run_id,
            inventory=reclaim.legacy.BoundFile(inventory, 1, "2" * 64),
            bridge_realpath="/dev/ttyACM1",
            bridge_process={"generation": 1},
            selected=(self.image(selected=True),),
            protected=(self.image(selected=False),),
            source_closure={},
            evidence={},
            rollback=reclaim.legacy.BoundFile(
                Path("/private/rollback.img"),
                reclaim.ROLLBACK_SIZE,
                reclaim.ROLLBACK_SHA256,
            ),
            capability_dispatch_path=(
                base
                / reclaim.CAPABILITY_STATE_DIR
                / "dispatch-started.json"
            ),
            capability_expires_utc=reclaim.CAPABILITY_EXPIRES_UTC,
        )

    def test_fixed_selection_and_protection_are_distinct(self) -> None:
        self.assertNotEqual(reclaim.SELECTED_PATH, reclaim.PROTECTED_PATH)
        self.assertNotEqual(reclaim.SELECTED_SHA256, reclaim.PROTECTED_SHA256)
        self.assertEqual(reclaim.SELECTED_RUN_ID[-2:], "10")
        self.assertEqual(reclaim.PROTECTED_RUN_ID[-2:], "11")

    def test_cleanup_selector_round_trips_only_fixed_h3_path(self) -> None:
        item = self.image(selected=True)
        selector = reclaim.gc._cleanup_selector(item)
        self.assertEqual(reclaim.gc._cleanup_selector_path(selector), reclaim.SELECTED_PATH)
        command = reclaim.gc._cleanup_command(
            mock.Mock(selected=(item,), protected=(self.image(selected=False),))
        )
        self.assertLessEqual(
            reclaim.gc._command_wire_bytes(command),
            reclaim.gc.MAX_CMDV1X_WIRE_BYTES,
        )
        self.assertNotIn(reclaim.PROTECTED_PATH, command[-1])

    def test_record_rejects_identity_or_inode_drift(self) -> None:
        value = {
            "role": reclaim.SELECTED_FIXED.role,
            "device_path": reclaim.SELECTED_PATH,
            "size": reclaim.gc.IMAGE_SIZE,
            "blocks": 4194312,
            "mode": reclaim.gc.IMAGE_MODE,
            "nlink": 1,
            "st_dev": 45825,
            "st_ino": 1054074,
            "sha256": reclaim.SELECTED_SHA256,
        }
        self.assertEqual(
            reclaim._record(value, reclaim.SELECTED_FIXED, None).st_ino,
            1054074,
        )
        for field, replacement in (
            ("device_path", reclaim.PROTECTED_PATH),
            ("sha256", reclaim.PROTECTED_SHA256),
            ("nlink", 2),
            ("st_ino", 0),
        ):
            changed = dict(value)
            changed[field] = replacement
            with self.subTest(field=field), self.assertRaises(reclaim.ContractError):
                reclaim._record(changed, reclaim.SELECTED_FIXED, None)

    def test_current_bridge_binding_requires_assert_dtr_rts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            proc = base / "proc"
            pid = proc / "123"
            pid.mkdir(parents=True)
            capture = base / "private" / "logs" / "bridge" / "capture.log"
            argv = [
                reclaim.sys.executable,
                str(reclaim.gc.SERIAL_TCP_BRIDGE),
                "--host",
                reclaim.gc.a90ctl.DEFAULT_HOST,
                "--port",
                str(reclaim.gc.a90ctl.DEFAULT_PORT),
                "--device",
                str(reclaim.gc.BRIDGE_DEVICE),
                "--device-glob",
                (
                    str(reclaim.gc.BRIDGE_DEVICE)
                    + ",/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"
                ),
                "--capture",
                str(capture),
                "--expect-realpath",
                "/dev/ttyACM1",
                "--assert-dtr-rts",
            ]
            (pid / "cmdline").write_bytes(b"\0".join(x.encode() for x in argv) + b"\0")
            with (
                mock.patch.object(reclaim, "PRIVATE_ROOT", base / "private"),
                mock.patch.object(
                    reclaim.gc,
                    "_process_start_epoch_sec",
                    return_value=10**10,
                ),
            ):
                value = reclaim._require_bridge("/dev/ttyACM1", proc)
                self.assertTrue(value["assert_dtr_rts"])
                (pid / "cmdline").write_bytes(
                    b"\0".join(x.encode() for x in argv[:-1]) + b"\0"
                )
                with self.assertRaisesRegex(
                    reclaim.ContractError,
                    "exactly one current",
                ):
                    reclaim._require_bridge("/dev/ttyACM1", proc)

    def _execute(
        self,
        base: Path,
        *,
        dispatch: str | BaseException,
        reconciliation: dict | BaseException,
        final_health: dict | BaseException = {"proven": True},
    ) -> tuple[dict, mock.Mock]:
        spec = self.spec(base)
        proxy = reclaim._proxy(spec)
        health_values: list[object] = [
            {"proven": True},
            {"proven": True},
            final_health,
        ]

        def health() -> dict:
            value = health_values.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value

        run = mock.Mock()
        if isinstance(dispatch, BaseException):
            run.side_effect = dispatch
        else:
            run.return_value = dispatch
        reconcile_patch = (
            mock.patch.object(reclaim.gc, "_read_reconciliation", side_effect=reconciliation)
            if isinstance(reconciliation, BaseException)
            else mock.patch.object(
                reclaim.gc,
                "_read_reconciliation",
                return_value=reconciliation,
            )
        )
        with (
            mock.patch.object(reclaim, "PRIVATE_BASE", base),
            mock.patch.object(reclaim, "_inventory_age"),
            mock.patch.object(reclaim, "_revalidate_host"),
            mock.patch.object(
                reclaim,
                "_live_target",
                return_value=("/dev/ttyACM1", {"generation": 1}),
            ),
            mock.patch.object(reclaim, "_health", side_effect=health),
            mock.patch.object(
                reclaim.gc,
                "_read_cleanup_preflight",
                return_value={
                    "blocks": 61408048,
                    "used": 54419468,
                    "available": 3862568,
                },
            ),
            mock.patch.object(
                reclaim.gc,
                "_cleanup_command",
                return_value=["run", "fixed-cleanup"],
            ),
            mock.patch.object(reclaim.gc, "_cleanup_script", return_value="fixed"),
            mock.patch.object(reclaim.gc, "_cleanup_args", return_value=("45825", "6:20260805-10:1054074")),
            mock.patch.object(reclaim.gc, "_run_script", run),
            mock.patch.object(reclaim.gc, "_free_gain_bounds", return_value=(2030000, 2160000)),
            reconcile_patch,
        ):
            result = reclaim.execute(
                spec,
                base / spec.run_id / "live",
                operator_attended=True,
            )
        self.assertEqual(proxy.selected, spec.selected)
        return result, run

    def test_attendance_stops_before_target_or_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = self.spec(base)
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(reclaim, "_live_target") as target,
                self.assertRaisesRegex(reclaim.ContractError, "attended-only"),
            ):
                reclaim.execute(spec, base / spec.run_id / "live", False)
        target.assert_not_called()

    def test_expiry_stops_before_target_or_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = self.spec(base)
            expiry = int(
                reclaim.dt.datetime.strptime(
                    reclaim.CAPABILITY_EXPIRES_UTC,
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                .replace(tzinfo=reclaim.dt.UTC)
                .timestamp()
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(reclaim.time, "time", return_value=expiry),
                mock.patch.object(reclaim, "_live_target") as target,
                self.assertRaisesRegex(reclaim.ContractError, "expired"),
            ):
                reclaim.execute(
                    spec,
                    base / spec.run_id / "live",
                    operator_attended=True,
                )
        target.assert_not_called()

    def test_capture_expiry_after_reads_stops_before_inventory_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run_id = "a90-v2321-h3-source-reclaim-20260805-02"
            output = base / run_id / "inventory.json"
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(
                    reclaim,
                    "_require_not_expired",
                    side_effect=(None, reclaim.ContractError("expired")),
                ),
                mock.patch.object(reclaim, "_historical_evidence"),
                mock.patch.object(
                    reclaim.gc,
                    "_find_target",
                    return_value=("/dev/ttyACM1", reclaim.gc.USB_SERIAL_SHA256),
                ),
                mock.patch.object(reclaim, "_require_bridge", return_value={}),
                mock.patch.object(reclaim, "_health", return_value={"proven": True}),
                mock.patch.object(reclaim.gc, "_bounded_inventory_read", return_value=""),
                mock.patch.object(
                    reclaim.gc,
                    "_parse_inventory",
                    return_value=(
                        [{"role": "selected"}, {"role": "protected"}],
                        {"blocks": 1, "used": 1, "available": 1},
                    ),
                ),
                mock.patch.object(reclaim, "_stage_absence"),
                mock.patch.object(
                    reclaim.legacy, "write_private_json_exclusive"
                ) as write,
                self.assertRaisesRegex(reclaim.ContractError, "expired"),
            ):
                reclaim.capture_inventory(run_id, output)
            self.assertFalse(output.parent.exists())
            write.assert_not_called()

    def test_manifest_expiry_after_hashing_stops_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run_id = "a90-v2321-h3-source-reclaim-20260805-02"
            output = base / run_id / "manifest.json"
            inventory_bound = reclaim.legacy.BoundFile(
                base / run_id / "inventory.json", 1, "2" * 64
            )
            host = reclaim.legacy.BoundFile(Path("/private/h3.img"), 1, "3" * 64)
            rollback = reclaim.legacy.BoundFile(
                Path("/private/rollback.img"), reclaim.ROLLBACK_SIZE, reclaim.ROLLBACK_SHA256
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(
                    reclaim,
                    "_require_not_expired",
                    side_effect=(None, reclaim.ContractError("expired")),
                ),
                mock.patch.object(
                    reclaim,
                    "_load_inventory",
                    return_value=(
                        inventory_bound,
                        {
                            "run_id": run_id,
                            "target": {},
                            "images": [{"role": "selected"}, {"role": "protected"}],
                        },
                    ),
                ),
                mock.patch.object(
                    reclaim,
                    "_historical_evidence",
                    return_value=({"selected_host_preservation": host}, rollback),
                ),
                mock.patch.object(reclaim, "_source_paths", return_value={}),
                mock.patch.object(
                    reclaim.legacy, "write_private_json_exclusive"
                ) as write,
                self.assertRaisesRegex(reclaim.ContractError, "expired"),
            ):
                reclaim.build_manifest(
                    run_id,
                    inventory_bound.path,
                    inventory_bound.sha256,
                    output,
                )
            write.assert_not_called()

    def test_expiry_after_preflight_stops_before_intent_or_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = self.spec(base)
            expiry = int(
                reclaim.dt.datetime.strptime(
                    reclaim.CAPABILITY_EXPIRES_UTC,
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                .replace(tzinfo=reclaim.dt.UTC)
                .timestamp()
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(
                    reclaim.time,
                    "time",
                    side_effect=(expiry - 1, expiry),
                ),
                mock.patch.object(reclaim, "_inventory_age"),
                mock.patch.object(reclaim, "_revalidate_host"),
                mock.patch.object(
                    reclaim,
                    "_live_target",
                    return_value=("/dev/ttyACM1", {"generation": 1}),
                ),
                mock.patch.object(reclaim, "_health", return_value={"proven": True}),
                mock.patch.object(
                    reclaim.gc,
                    "_read_cleanup_preflight",
                    return_value={"blocks": 1, "used": 1, "available": 1},
                ),
                mock.patch.object(reclaim.gc, "_cleanup_command", return_value=["fixed"]),
                mock.patch.object(reclaim.gc, "_run_script") as effect,
                self.assertRaisesRegex(reclaim.ContractError, "expired"),
            ):
                reclaim.execute(
                    spec,
                    base / spec.run_id / "live",
                    operator_attended=True,
                )
            self.assertFalse((base / spec.run_id / "live").exists())
            self.assertFalse(spec.capability_dispatch_path.exists())
            effect.assert_not_called()

    def test_expiry_after_intent_stops_before_capability_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = self.spec(base)
            expiry = int(
                reclaim.dt.datetime.strptime(
                    reclaim.CAPABILITY_EXPIRES_UTC,
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                .replace(tzinfo=reclaim.dt.UTC)
                .timestamp()
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(
                    reclaim.time,
                    "time",
                    side_effect=(expiry - 1, expiry - 1, expiry),
                ),
                mock.patch.object(reclaim, "_inventory_age"),
                mock.patch.object(reclaim, "_revalidate_host"),
                mock.patch.object(
                    reclaim,
                    "_live_target",
                    return_value=("/dev/ttyACM1", {"generation": 1}),
                ),
                mock.patch.object(reclaim, "_health", return_value={"proven": True}),
                mock.patch.object(
                    reclaim.gc,
                    "_read_cleanup_preflight",
                    return_value={"blocks": 1, "used": 1, "available": 1},
                ),
                mock.patch.object(reclaim.gc, "_cleanup_command", return_value=["fixed"]),
                mock.patch.object(reclaim.gc, "_run_script") as effect,
                self.assertRaisesRegex(reclaim.ContractError, "expired"),
            ):
                reclaim.execute(
                    spec,
                    base / spec.run_id / "live",
                    operator_attended=True,
                )
            self.assertTrue((base / spec.run_id / "live" / "intent.json").is_file())
            self.assertFalse(spec.capability_dispatch_path.exists())
            self.assertFalse(
                (base / spec.run_id / "live" / "dispatch-started.json").exists()
            )
            effect.assert_not_called()

    def test_expiry_after_receipts_consumes_without_unlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = self.spec(base)
            expiry = int(
                reclaim.dt.datetime.strptime(
                    reclaim.CAPABILITY_EXPIRES_UTC,
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                .replace(tzinfo=reclaim.dt.UTC)
                .timestamp()
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(
                    reclaim.time,
                    "time",
                    side_effect=(expiry - 1, expiry - 1, expiry - 1, expiry),
                ),
                mock.patch.object(reclaim, "_inventory_age"),
                mock.patch.object(reclaim, "_revalidate_host"),
                mock.patch.object(
                    reclaim,
                    "_live_target",
                    return_value=("/dev/ttyACM1", {"generation": 1}),
                ),
                mock.patch.object(reclaim, "_health", return_value={"proven": True}),
                mock.patch.object(
                    reclaim.gc,
                    "_read_cleanup_preflight",
                    return_value={"blocks": 1, "used": 1, "available": 1},
                ),
                mock.patch.object(reclaim.gc, "_cleanup_command", return_value=["fixed"]),
                mock.patch.object(reclaim.gc, "_cleanup_script", return_value="fixed"),
                mock.patch.object(reclaim.gc, "_cleanup_args", return_value=("1", "2")),
                mock.patch.object(
                    reclaim.gc,
                    "_read_reconciliation",
                    return_value={
                        "selected": ["present"],
                        "protected": "exact",
                        "work": "absent",
                        "filesystem_kib": {"available": 1},
                    },
                ),
                mock.patch.object(reclaim.gc, "_run_script") as effect,
            ):
                result = reclaim.execute(
                    spec,
                    base / spec.run_id / "live",
                    operator_attended=True,
                )
            self.assertEqual(
                result["outcome"],
                "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK",
            )
            self.assertEqual(result["dispatch_count"], 0)
            self.assertFalse(result["device_write"])
            self.assertTrue(spec.capability_dispatch_path.is_file())
            self.assertTrue(
                (base / spec.run_id / "live" / "dispatch-started.json").is_file()
            )
            self.assertTrue(
                (base / spec.run_id / "live" / "effect-not-started.json").is_file()
            )
            effect.assert_not_called()

    def test_success_dispatches_once_and_preserves_h4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, dispatch = self._execute(
                Path(tmp),
                dispatch="A90CLEAN_UNLINKED exact=1 selected_absent=1",
                reconciliation={
                    "selected": ["absent"],
                    "protected": "exact",
                    "work": "absent",
                    "filesystem_kib": {"available": 5960000},
                },
            )
        self.assertEqual(result["outcome"], "PASS_H3_SOURCE_RECLAIMED")
        self.assertEqual(result["dispatch_count"], 1)
        self.assertFalse(result["cleanup_retransmitted"])
        dispatch.assert_called_once()

    def test_ambiguous_response_is_reconciled_without_retransmit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, dispatch = self._execute(
                Path(tmp),
                dispatch=TimeoutError("lost response"),
                reconciliation={
                    "selected": ["absent"],
                    "protected": "exact",
                    "work": "absent",
                    "filesystem_kib": {"available": 5960000},
                },
            )
        self.assertEqual(
            result["outcome"],
            "PASS_H3_SOURCE_RECLAIM_PROVEN_AFTER_AMBIGUOUS_RESPONSE",
        )
        self.assertEqual(dispatch.call_count, 1)
        self.assertFalse(result["cleanup_retransmitted"])

    def test_protected_drift_or_health_loss_parks_without_retry(self) -> None:
        cases = (
            (
                {
                    "selected": ["absent"],
                    "protected": "unknown",
                    "work": "absent",
                    "filesystem_kib": {"available": 5960000},
                },
                {"proven": True},
            ),
            (
                {
                    "selected": ["absent"],
                    "protected": "exact",
                    "work": "absent",
                    "filesystem_kib": {"available": 5960000},
                },
                reclaim.ContractError("health unavailable"),
            ),
        )
        for reconciliation, health in cases:
            with self.subTest(health=health), tempfile.TemporaryDirectory() as tmp:
                result, dispatch = self._execute(
                    Path(tmp),
                    dispatch="A90CLEAN_UNLINKED exact=1 selected_absent=1",
                    reconciliation=reconciliation,
                    final_health=health,
                )
                self.assertEqual(
                    result["outcome"], "RECOVERY_PENDING_PARKED_NO_RETRY"
                )
                self.assertEqual(dispatch.call_count, 1)
                self.assertFalse(result["cleanup_retransmitted"])

    def test_nonpass_consumes_capability_across_new_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result, _ = self._execute(
                base,
                dispatch=TimeoutError("lost response"),
                reconciliation={
                    "selected": ["present"],
                    "protected": "exact",
                    "work": "absent",
                    "filesystem_kib": {"available": 3862568},
                },
            )
            self.assertEqual(
                result["outcome"], "RECOVERY_PENDING_PARKED_NO_RETRY"
            )
            second = self.spec(
                base,
                "a90-v2321-h3-source-reclaim-20260805-02",
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(reclaim, "_live_target") as target,
                self.assertRaisesRegex(reclaim.ContractError, "already consumed"),
            ):
                reclaim.execute(
                    second,
                    base / second.run_id / "live",
                    operator_attended=True,
                )
        target.assert_not_called()

    def _resume_records(self, base: Path) -> tuple[object, Path, dict, list[str]]:
        spec = self.spec(base)
        live = base / spec.run_id / "live"
        live.mkdir(parents=True)
        before = {"blocks": 1, "used": 1, "available": 1}
        command = ["run", "fixed-cleanup"]
        reclaim.legacy.write_private_json_exclusive(
            live / "intent.json",
            {
                "manifest_sha256": spec.manifest_sha256,
                "before_filesystem_kib": before,
            },
        )
        dispatch = {
            "schema": "a90_v2321_h3_source_reclaim_dispatch_v1",
            "created_utc": "2026-08-05T00:00:00Z",
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            "selected_path": reclaim.SELECTED_PATH,
            "selected_sha256": reclaim.SELECTED_SHA256,
            "protected_path": reclaim.PROTECTED_PATH,
            "protected_sha256": reclaim.PROTECTED_SHA256,
            "cleanup_command_sha256": reclaim.legacy.json_sha256(
                {"argv": command}
            ),
            "dispatch_authorization_count": 1,
            "unlink_dispatch_count_max": 1,
            "retry_forbidden": True,
            "capability_consumed": True,
        }
        reclaim.legacy.write_private_json_exclusive(
            live / "dispatch-started.json", dispatch
        )
        reclaim.legacy.write_private_json_exclusive(
            spec.capability_dispatch_path, dispatch
        )
        return spec, live, before, command

    def test_resume_after_durable_dispatch_never_calls_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec, live, _, command = self._resume_records(base)
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(reclaim.gc, "PRIVATE_ROOT", base),
                mock.patch.object(reclaim.gc, "_cleanup_command", return_value=command),
                mock.patch.object(reclaim, "_revalidate_host"),
                mock.patch.object(reclaim, "_live_target"),
                mock.patch.object(
                    reclaim,
                    "_observe_after_dispatch",
                    return_value={"outcome": "PASS", "cleanup_retransmitted": False},
                ),
                mock.patch.object(reclaim.gc, "_run_script") as effect,
            ):
                result = reclaim.resume(spec, live)
        self.assertEqual(result["outcome"], "PASS")
        effect.assert_not_called()

    def test_resume_expired_marker_never_calls_effect_and_records_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec, live, _, command = self._resume_records(base)
            reclaim.legacy.write_private_json_exclusive(
                live / "effect-not-started.json",
                {
                    "schema": "a90_v2321_h3_source_reclaim_effect_not_started_v1",
                    "created_utc": "2026-08-06T00:00:00Z",
                    "run_id": spec.run_id,
                    "manifest_sha256": spec.manifest_sha256,
                    "reason": "capability-expired-before-unlink",
                    "dispatch_count": 0,
                    "device_write": False,
                    "capability_consumed": True,
                },
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(reclaim.gc, "PRIVATE_ROOT", base),
                mock.patch.object(reclaim.gc, "_cleanup_command", return_value=command),
                mock.patch.object(reclaim, "_revalidate_host"),
                mock.patch.object(reclaim, "_live_target"),
                mock.patch.object(
                    reclaim,
                    "_observe_expired_before_unlink",
                    return_value={
                        "outcome": "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK",
                        "dispatch_count": 0,
                        "device_write": False,
                    },
                ),
                mock.patch.object(reclaim.gc, "_run_script") as effect,
            ):
                result = reclaim.resume(spec, live)
            self.assertEqual(result["dispatch_count"], 0)
            self.assertFalse(result["device_write"])
            effect.assert_not_called()

    def test_existing_expired_result_requires_effect_not_started_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec, live, _, command = self._resume_records(base)
            reclaim.legacy.write_private_json_exclusive(
                live / "result.json",
                {
                    "schema": reclaim.RESULT_SCHEMA,
                    "run_id": spec.run_id,
                    "manifest_sha256": spec.manifest_sha256,
                    "outcome": "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK",
                    "capability_consumed": True,
                    "dispatch_count": 0,
                    "device_write": False,
                    "cleanup_retransmitted": False,
                },
            )
            with (
                mock.patch.object(reclaim, "PRIVATE_BASE", base),
                mock.patch.object(reclaim.gc, "PRIVATE_ROOT", base),
                mock.patch.object(reclaim.gc, "_cleanup_command", return_value=command),
                self.assertRaisesRegex(reclaim.ContractError, "existing reclaim result"),
            ):
                reclaim.resume(spec, live)

    def test_source_contains_no_flash_or_partition_primitive(self) -> None:
        source = Path(reclaim.__file__).read_text(encoding="utf-8")
        contract = reclaim.TARGET_CONTRACT.read_text(encoding="utf-8")
        self.assertNotIn("native_init_flash", source)
        self.assertNotIn("dd if=", source)
        self.assertNotIn("fastboot", source)
        self.assertIn("cleanup_retransmitted\": False", source)
        self.assertIn("_selected_use_guard_scripts", Path(reclaim.gc.__file__).read_text())
        self.assertIn(reclaim.CAPABILITY, contract)
        self.assertIn("one-use attended D1 sub-capability", contract)
        self.assertIn("no retransmission", contract)
        self.assertIn("retires", contract)


if __name__ == "__main__":
    unittest.main()
