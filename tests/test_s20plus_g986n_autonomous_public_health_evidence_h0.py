import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_evidence_h0.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_autonomous_public_health_evidence_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load_module()


def digest_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_counters(operations=0, consumed=0, reserved=0):
    return {
        "read_operations": operations,
        "private_evidence_bytes_consumed": consumed,
        "private_evidence_bytes_reserved": reserved,
    }


def control_counters(
    *, normal=0, roundtrips=0, entries=None, returns=None, reserved=None
):
    entries = roundtrips if entries is None else entries
    returns = entries if returns is None else returns
    unresolved = entries - returns
    reserved = unresolved if reserved is None else reserved
    return {
        "control_transactions": normal + roundtrips,
        "component_effects_consumed": normal + entries + returns,
        "component_effects_reserved": reserved,
        "normal_reboots": normal,
        "download_roundtrips": roundtrips,
        "roundtrip_entries": entries,
        "roundtrip_returns": returns,
    }


class Fixture:
    campaign_id = "a" * 32
    session_id = "b" * 32
    serial = "R58NTEST0001"
    devpath = "usb:1-2.3"
    boot_id = "11111111-2222-3333-4444-555555555555"
    opened_at = 1_000
    campaign_expiry = opened_at + M.COORDINATOR_CAMPAIGN_DURATION_SECONDS
    session_expiry = opened_at + M.COORDINATOR_SESSION_DURATION_SECONDS

    @classmethod
    def source(cls, *, serial=None, devpath=None, boot_id=None):
        serial = cls.serial if serial is None else serial
        devpath = cls.devpath if devpath is None else devpath
        boot_id = cls.boot_id if boot_id is None else boot_id
        return {
            "target": copy.deepcopy(M.TARGET),
            "serial_sha256": digest_text(serial),
            "topology_sha256": digest_text(devpath),
            "boot_id_sha256": digest_text(boot_id),
            "healthy_android": True,
            "foreign_guard_present": False,
        }

    @classmethod
    def allocation(
        cls,
        *,
        current_time=1_010,
        source=None,
        child_control=None,
        campaign_control=None,
        current_head=None,
    ):
        source = copy.deepcopy(source or cls.source())
        child_control = copy.deepcopy(child_control or control_counters())
        campaign_control = copy.deepcopy(campaign_control or control_counters())
        opening = {
            "schema": M.COORDINATOR_SCHEMA,
            "kind": "campaign-opening",
            "campaign_id": cls.campaign_id,
            "session_id": cls.session_id,
            "target": copy.deepcopy(M.TARGET),
            "policy_binding_sha256": M.COORDINATOR_BINDING_SHA256,
            "coordinator_normalized_sha256": M.COORDINATOR_NORMALIZED_SHA256,
            "source_identity": copy.deepcopy(source),
            "opened_at": cls.opened_at,
            "expires_at": cls.campaign_expiry,
            "campaign_counters": control_counters(),
            "child_counters": control_counters(),
            "predecessor_sha256": M.ZERO_HASH,
            "attended_opening": True,
            "no_replay": True,
            "f1_intent": False,
            "approval_consumed": False,
            "partition_transfer": False,
        }
        opening_raw = M.canonical_bytes(opening)
        session = {
            "schema": M.COORDINATOR_SCHEMA,
            "kind": "session-opening",
            "campaign_id": cls.campaign_id,
            "session_id": cls.session_id,
            "target": copy.deepcopy(M.TARGET),
            "policy_binding_sha256": M.COORDINATOR_BINDING_SHA256,
            "coordinator_normalized_sha256": M.COORDINATOR_NORMALIZED_SHA256,
            "source_identity": copy.deepcopy(source),
            "opened_at": cls.opened_at,
            "expires_at": cls.session_expiry,
            "campaign_counters": control_counters(),
            "child_counters": control_counters(),
            "predecessor_sha256": M.sha256_bytes(opening_raw),
            "no_replay": True,
        }
        session_raw = M.canonical_bytes(session)
        guard = {
            "schema": M.COORDINATOR_SCHEMA,
            "kind": "campaign-guard",
            "phase": "allocation-claimed",
            "campaign_id": cls.campaign_id,
            "session_id": cls.session_id,
            "target": copy.deepcopy(M.TARGET),
            "policy_binding_sha256": M.COORDINATOR_BINDING_SHA256,
            "coordinator_normalized_sha256": M.COORDINATOR_NORMALIZED_SHA256,
            "source_identity": copy.deepcopy(source),
            "opened_at": cls.opened_at,
            "expires_at": cls.campaign_expiry,
            "opening_sha256": M.sha256_bytes(opening_raw),
            "session_opening_sha256": M.sha256_bytes(session_raw),
            "opening": copy.deepcopy(opening),
            "session": copy.deepcopy(session),
            "campaign_counters": control_counters(),
            "child_counters": control_counters(),
            "no_replay": True,
            "f1_intent": False,
            "approval_consumed": False,
            "partition_transfer": False,
        }
        guard_raw = M.canonical_bytes(guard)
        allocation = {
            "campaign_id": cls.campaign_id,
            "session_id": cls.session_id,
            "target": copy.deepcopy(M.TARGET),
            "guard": guard,
            "guard_raw": guard_raw,
            "opening": opening,
            "opening_raw": opening_raw,
            "session": session,
            "session_raw": session_raw,
        }
        head = copy.deepcopy(current_head or session)
        head_raw = M.canonical_bytes(head)
        context = {
            "campaign_id": cls.campaign_id,
            "session_id": cls.session_id,
            "phase": "healthy-normal",
            "expired": False,
            "session_expired": False,
            "current_time": current_time,
            "campaign_expires_at": cls.campaign_expiry,
            "session_expires_at": cls.session_expiry,
            "current_ordinal": campaign_control["download_roundtrips"],
            "source_identity": copy.deepcopy(source),
            "endpoint": None,
            "predecessor_sha256": M.sha256_bytes(head_raw),
            "child_counters": child_control,
            "campaign_counters": campaign_control,
            "terminal": None,
            "f1_intent": False,
            "approval_consumed": False,
            "partition_transfer": False,
            "no_replay": True,
            "pending_intent_issued_at": None,
        }
        return allocation, context, M.canonical_bytes(context), head, head_raw

    @classmethod
    def accounting_opening(cls, **kwargs):
        allocation, context, context_raw, head, head_raw = cls.allocation(**kwargs)
        opening = M.model_accounting_opening(
            allocation,
            context,
            context_raw,
            head,
            head_raw,
            context["current_time"],
        )
        return allocation, opening, M.canonical_bytes(opening)

    @classmethod
    def context_for_head(cls, opening, head, current_time):
        context = copy.deepcopy(opening["first_current_context"])
        context["current_time"] = current_time
        context["source_identity"] = copy.deepcopy(opening["source_identity"])
        context["predecessor_sha256"] = M.sha256_bytes(M.canonical_bytes(head))
        return context

    @classmethod
    def lease(cls, opening, opening_raw, state, *, issued_at=1_020, head=None):
        head = copy.deepcopy(head or opening["first_coordinator_head"])
        context = cls.context_for_head(opening, head, issued_at)
        previous_child = copy.deepcopy(state["child_counters"])
        previous_campaign = copy.deepcopy(state["campaign_counters"])
        lease = {
            "schema": M.COORDINATOR_LEASE_SCHEMA,
            "kind": "public-health-read-lease",
            "issued_at": issued_at,
            "campaign_id": opening["campaign_id"],
            "session_id": opening["session_id"],
            "target": copy.deepcopy(M.TARGET),
            "action": "public-health",
            "read_ordinal": state["read_ordinal"] + 1,
            "accounting_opening_sha256": M.sha256_bytes(opening_raw),
            "coordinator_context": context,
            "coordinator_context_sha256": M.sha256_bytes(M.canonical_bytes(context)),
            "coordinator_head": head,
            "coordinator_head_sha256": M.sha256_bytes(M.canonical_bytes(head)),
            "source_identity": copy.deepcopy(context["source_identity"]),
            "previous_evidence_result_sha256": state[
                "previous_evidence_result_sha256"
            ],
            "previous_coordinator_complete_sha256": state[
                "previous_coordinator_complete_sha256"
            ],
            "previous_child_counters": previous_child,
            "previous_campaign_counters": previous_campaign,
            "child_counters": M.reserve_counters(
                previous_child, M.CHILD_LIMITS, "fixture child"
            ),
            "campaign_counters": M.reserve_counters(
                previous_campaign, M.CAMPAIGN_LIMITS, "fixture campaign"
            ),
            "reservation_bytes": M.READ_RESERVATION_BYTES,
            "expected_host_tool": M.expected_host_tool(),
            "attempt_consumed": True,
            "replay_authorized": False,
            "controls_blocked": True,
            "terminal_blocked": True,
            "completion_required": True,
        }
        raw = M.canonical_bytes(lease)
        M.validate_future_lease(lease, raw, opening, opening_raw, state, issued_at)
        intent = M.mirror_read_intent(
            lease, raw, opening, opening_raw, issued_at
        )
        return lease, raw, intent, M.canonical_bytes(intent)

    @classmethod
    def snapshot(cls, *, boot_id=None, overrides=None, fill="fixture"):
        values = {key: fill for key in M.PROPERTY_KEYS}
        values.update(
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product_name": "y2qksx",
                "build_product": "y2q",
                "fingerprint": (
                    "samsung/y2qksx/y2q:13/TP1A.220624.014/"
                    "G986NKSS8IYC2:user/release-keys"
                ),
                "incremental": "G986NKSS8IYC2",
                "boot_completed": "1",
                "bootanim": "stopped",
                "selinux": "Enforcing",
                "shell_identity": "uid=2000(shell) gid=2000(shell) groups=2000(shell)",
                "boot_id": boot_id or cls.boot_id,
            }
        )
        values.update(overrides or {})
        return ("\n".join(f"{key}={values[key]}" for key in M.PROPERTY_KEYS) + "\n").encode()

    @classmethod
    def records(
        cls,
        intent,
        *,
        serial=None,
        devpath=None,
        boot_id=None,
        inventory=None,
        final_inventory=None,
        snapshot=None,
        second_snapshot=None,
    ):
        serial = cls.serial if serial is None else serial
        devpath = cls.devpath if devpath is None else devpath
        inventory = inventory or (
            "List of devices attached\n"
            f"{serial} device product:y2qksx model:SM_G986N device:y2q "
            "transport_id:1\n"
        ).encode()
        final_inventory = inventory if final_inventory is None else final_inventory
        snapshot = snapshot or cls.snapshot(boot_id=boot_id)
        second_snapshot = snapshot if second_snapshot is None else second_snapshot
        adb = M.expected_host_tool()["path"]
        argvs = [
            [adb, "version"],
            [adb, "devices", "-l"],
            [adb, "-s", serial, "get-devpath"],
            [adb, "-s", serial, "exec-out", "sh", "-c", M.REMOTE_SNAPSHOT],
            [adb, "-s", serial, "exec-out", "sh", "-c", M.REMOTE_SNAPSHOT],
            [adb, "devices", "-l"],
        ]
        outputs = [
            b"Android Debug Bridge version 1.0.41\n",
            inventory,
            (devpath + "\n").encode(),
            snapshot,
            second_snapshot,
            final_inventory,
        ]
        tool = {
            "path": adb,
            "device": 11,
            "inode": 22,
            "mtime_ns": 33,
            "size": M.expected_host_tool()["size"],
            "sha256": M.expected_host_tool()["sha256"],
        }
        result = []
        for index, (argv, output, template) in enumerate(
            zip(argvs, outputs, M.FIXED_TRANSCRIPT, strict=True), 1
        ):
            started = intent["lease_observed_at"] + (index - 1) * 2
            result.append(
                {
                    "ordinal": index,
                    "argv": argv,
                    "timeout_sec": template["timeout_sec"],
                    "max_bytes": template["max_bytes"],
                    "returncode": 0,
                    "stdout": output,
                    "stderr": b"",
                    "host_tool_before": copy.deepcopy(tool),
                    "host_tool_after": copy.deepcopy(tool),
                    "execution_started_at": started,
                    "execution_completed_at": started,
                    "return_retained_at": started + 1,
                    "receipt_published_at": started + 1,
                }
            )
        return result

    @classmethod
    def bundle(cls, *, issued_at=1_020, completed_at=1_040, cut=None):
        _, opening, opening_raw = cls.accounting_opening()
        state = M.initial_protocol_state(opening, opening_raw)
        lease, lease_raw, intent, intent_raw = cls.lease(
            opening, opening_raw, state, issued_at=issued_at
        )
        records = cls.records(intent)
        receipts = M.build_command_receipts(intent_raw, records)
        result = M.model_validated_read_result(
            opening,
            opening_raw,
            state,
            lease,
            lease_raw,
            intent["lease_observed_at"],
            intent,
            intent_raw,
            records,
            receipts,
            completed_at,
            cut,
        )
        result_raw = M.canonical_bytes(result)
        completion = M.model_future_completion(result, result_raw, completed_at)
        return {
            "opening": opening,
            "opening_raw": opening_raw,
            "state": state,
            "lease": lease,
            "lease_raw": lease_raw,
            "intent": intent,
            "intent_raw": intent_raw,
            "records": records,
            "receipts": receipts,
            "result": result,
            "result_raw": result_raw,
            "completion": completion,
            "completion_raw": M.canonical_bytes(completion),
        }


def reject(callable_, *args, **kwargs):
    with unittest.TestCase().assertRaises(M.EvidenceH0Error):
        callable_(*args, **kwargs)


class AtomicHarness:
    """Test-only atomic/no-follow simulation; production has no writer."""

    @staticmethod
    def walk(path):
        path = Path(path)
        descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            components = path.parts[1:]
            for index, component in enumerate(components):
                child = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
                os.close(descriptor)
                descriptor = child
                info = os.fstat(descriptor)
                if index == len(components) - 1 and (
                    not stat.S_ISDIR(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o700
                    or info.st_uid != os.getuid()
                    or info.st_gid != os.getgid()
                ):
                    raise RuntimeError("test harness directory identity differs")
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    @classmethod
    def publish(cls, parent, name, payload, hook=None):
        if name not in M.EVIDENCE_NAMES or type(payload) is not bytes:
            raise RuntimeError("test harness publication request differs")
        descriptor = cls.walk(parent)
        pending = ".pending-" + name
        temporary = -1
        try:
            before = os.fstat(descriptor)
            temporary = os.open(
                pending,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o400,
                dir_fd=descriptor,
            )
            os.write(temporary, payload)
            os.fsync(temporary)
            os.close(temporary)
            temporary = -1
            if hook is not None:
                hook()
            check = cls.walk(parent)
            try:
                current = os.fstat(check)
            finally:
                os.close(check)
            if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
                raise RuntimeError("test harness parent was replaced")
            os.link(
                pending,
                name,
                src_dir_fd=descriptor,
                dst_dir_fd=descriptor,
                follow_symlinks=False,
            )
            os.unlink(pending, dir_fd=descriptor)
            os.fsync(descriptor)
        finally:
            if temporary >= 0:
                os.close(temporary)
            try:
                os.unlink(pending, dir_fd=descriptor)
            except FileNotFoundError:
                pass
            os.close(descriptor)

    @classmethod
    def validate_file(cls, parent, name, payload):
        descriptor = cls.walk(parent)
        try:
            child = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=descriptor)
            try:
                info = os.fstat(child)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o400
                    or info.st_nlink != 1
                    or info.st_uid != os.getuid()
                    or info.st_gid != os.getgid()
                    or os.read(child, len(payload) + 1) != payload
                ):
                    raise RuntimeError("test harness evidence identity differs")
            finally:
                os.close(child)
        finally:
            os.close(descriptor)


class S20PlusAutonomousPublicHealthEvidenceH0Test(unittest.TestCase):
    def test_render_plan_is_permanently_dormant_and_commandless(self):
        plan = M.render_plan()
        self.assertEqual(plan["status"], M.STATUS)
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_PUBLIC_HEALTH_EVIDENCE_PASS_GO_NOT_ACTIVE",
        )
        self.assertFalse(plan["evidence_active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["mechanically_activatable"])
        self.assertFalse(plan["coordinator_integrated"])
        self.assertTrue(plan["permanent_h0_only"])
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["device_effects"], [])
        self.assertEqual(plan["root_commands"], [])
        self.assertFalse(plan["command_execution_backend"])
        self.assertFalse(plan["private_filesystem_writer"])
        self.assertEqual(plan["timestamp_provenance"], "numeric-model-only")
        self.assertFalse(plan["durable_publication_order_proven"])
        self.assertEqual(plan["read_reservation_bytes"], 524_288)
        self.assertEqual(plan["byte_proof"]["total_max"], 507_904)

    def test_source_has_no_command_module_or_private_writer_surface(self):
        source = SCRIPT.read_text()
        for token in (
            "importlib.util",
            "import subprocess",
            "subprocess.",
            "Popen(",
            "exec(",
            "observe_once(",
            "bounded_command(",
            ".collect(",
            "fixture_token",
            "durable_write",
            "mkdir(",
        ):
            self.assertNotIn(token, source)
        modules = {
            name: value.__name__
            for name, value in vars(M).items()
            if isinstance(value, types.ModuleType)
        }
        self.assertNotIn("subprocess", modules.values())
        self.assertNotIn("importlib", modules.values())
        with self.assertRaises(TypeError):
            M.SOURCE_SPECS["health"]["path"] = Path("/tmp/foreign")

    def test_live_stubs_reject_before_any_source_or_private_open(self):
        old = (
            M.EVIDENCE_ACTIVE,
            M.LIVE_AUTHORITY,
            M.MECHANICALLY_ACTIVATABLE,
            M.COORDINATOR_INTEGRATED,
        )
        try:
            M.EVIDENCE_ACTIVE = True
            M.LIVE_AUTHORITY = True
            M.MECHANICALLY_ACTIVATABLE = True
            M.COORDINATOR_INTEGRATED = True
            with mock.patch.object(M, "_open", side_effect=AssertionError("opened")):
                for function in (
                    M.begin_live_read,
                    M.record_live_return,
                    M.complete_live_read,
                ):
                    with self.subTest(function=function.__name__), self.assertRaises(
                        M.EvidenceH0Error
                    ):
                        function()
        finally:
            (
                M.EVIDENCE_ACTIVE,
                M.LIVE_AUTHORITY,
                M.MECHANICALLY_ACTIVATABLE,
                M.COORDINATOR_INTEGRATED,
            ) = old

    def test_cli_is_exact_render_plan_only(self):
        good = subprocess.run(
            ["python3", str(SCRIPT), "--render-plan"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)["device_commands"], [])
        for option in ([], ["--r"], ["--render"], ["--connected"], ["--run-dir", "/tmp/x"]):
            bad = subprocess.run(
                ["python3", str(SCRIPT), *option],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            with self.subTest(option=option):
                self.assertNotEqual(bad.returncode, 0)

    def test_canonical_json_rejects_duplicates_noncanonical_and_bool_integer(self):
        value = {"a": 1, "b": [True, None]}
        raw = M.canonical_bytes(value)
        self.assertEqual(M.parse_canonical_json(raw, "fixture"), value)
        for hostile in (
            b'{"a":1,"a":2}\n',
            b'{"b":2, "a":1}\n',
            b'{"a":NaN}\n',
            b'{"a":1}',
        ):
            with self.subTest(hostile=hostile), self.assertRaises(M.EvidenceH0Error):
                M.parse_canonical_json(hostile, "hostile")
        with self.assertRaises(M.EvidenceH0Error):
            M.reserve_counters(
                {
                    "read_operations": False,
                    "private_evidence_bytes_consumed": 0,
                    "private_evidence_bytes_reserved": 0,
                },
                M.CHILD_LIMITS,
                "bool",
            )

    def test_source_and_self_receipts_are_exact(self):
        receipts = M.source_receipts()
        self.assertEqual(set(receipts), {"owner", "coordinator", "health", "inventory"})
        for label in ("coordinator", "health", "inventory"):
            data = Path(receipts[label]["path"]).read_bytes()
            self.assertEqual(len(data), receipts[label]["size"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipts[label]["sha256"])
            self.assertEqual(receipts[label]["sha256"], M.SOURCE_SPECS[label]["sha256"])
        owner = SCRIPT.read_bytes()
        self.assertEqual(receipts["owner"]["sha256"], hashlib.sha256(owner).hexdigest())
        self.assertEqual(
            receipts["owner"]["normalized_sha256"], M.normalized_self_sha256(owner)
        )

    def test_strict_allocation_and_accounting_opening_preserve_current_bytes(self):
        allocation, opening, opening_raw = Fixture.accounting_opening()
        validated = M.validate_accounting_opening(opening, opening_raw)
        self.assertEqual(validated, opening)
        self.assertEqual(opening["recorded_at"], 1_010)
        self.assertEqual(
            opening["coordinator_guard_sha256"],
            M.sha256_bytes(allocation["guard_raw"]),
        )
        self.assertEqual(
            opening["first_coordinator_head_sha256"],
            opening["first_current_context"]["predecessor_sha256"],
        )
        self.assertTrue(opening["attended_opening"])
        self.assertFalse(opening["command_execution_backend"])

    def test_initial_session_starts_both_scopes_zero_and_rejects_naked_carry(self):
        allocation, opening, opening_raw = Fixture.accounting_opening()
        state = M.initial_protocol_state(opening, opening_raw)
        self.assertEqual(state["child_counters"], read_counters())
        self.assertEqual(state["campaign_counters"], read_counters())
        self.assertEqual(state["previous_coordinator_complete_sha256"], M.ZERO_HASH)
        self.assertFalse(state["campaign_parked"])
        hostile = copy.deepcopy(allocation)
        hostile["initial_campaign_read_counters"] = read_counters(1, 1)
        with self.assertRaises(M.EvidenceH0Error):
            M.model_accounting_opening(
                hostile,
                opening["first_current_context"],
                M.canonical_bytes(opening["first_current_context"]),
                opening["first_coordinator_head"],
                M.canonical_bytes(opening["first_coordinator_head"]),
                opening["recorded_at"],
            )

    def test_hostile_guard_opening_session_and_raw_bytes_reject(self):
        allocation, context, context_raw, head, head_raw = Fixture.allocation()
        mutations = (
            ("opening", "attended_opening", False),
            ("opening", "policy_binding_sha256", "e" * 64),
            ("opening", "predecessor_sha256", "e" * 64),
            ("session", "expires_at", Fixture.campaign_expiry + 1),
            ("session", "no_replay", False),
            ("guard", "phase", "foreign"),
            ("guard", "f1_intent", True),
        )
        for node_name, key, value in mutations:
            hostile = copy.deepcopy(allocation)
            hostile[node_name][key] = value
            hostile[node_name + "_raw"] = M.canonical_bytes(hostile[node_name])
            with self.subTest(node=node_name, key=key), self.assertRaises(
                M.EvidenceH0Error
            ):
                M.model_accounting_opening(
                    hostile, context, context_raw, head, head_raw, context["current_time"]
                )
        hostile = copy.deepcopy(allocation)
        hostile["guard_raw"] = b"{}\n"
        with self.assertRaises(M.EvidenceH0Error):
            M.model_accounting_opening(
                hostile, context, context_raw, head, head_raw, context["current_time"]
            )

    def test_forged_accounting_hash_time_or_current_head_rejects(self):
        allocation, opening, opening_raw = Fixture.accounting_opening()
        for key, value in (
            ("coordinator_guard_sha256", "f" * 64),
            ("first_current_context_sha256", "f" * 64),
            ("attended_opening", False),
        ):
            hostile = copy.deepcopy(opening)
            hostile[key] = value
            with self.subTest(key=key), self.assertRaises(M.EvidenceH0Error):
                M.validate_accounting_opening(hostile, M.canonical_bytes(hostile))
        allocation2, context, context_raw, head, head_raw = Fixture.allocation()
        with self.assertRaises(M.EvidenceH0Error):
            M.model_accounting_opening(
                allocation2, context, context_raw, head, head_raw, context["current_time"] + 1
            )
        arbitrary = {"kind": "invented", "value": 1}
        context["predecessor_sha256"] = M.sha256_bytes(M.canonical_bytes(arbitrary))
        with self.assertRaises(M.EvidenceH0Error):
            M.model_accounting_opening(
                allocation2,
                context,
                M.canonical_bytes(context),
                arbitrary,
                M.canonical_bytes(arbitrary),
                context["current_time"],
            )
        forged_session = copy.deepcopy(head)
        forged_session["opened_at"] += 1
        context = copy.deepcopy(context)
        context["predecessor_sha256"] = M.sha256_bytes(
            M.canonical_bytes(forged_session)
        )
        with self.assertRaises(M.EvidenceH0Error):
            M.model_accounting_opening(
                allocation2,
                context,
                M.canonical_bytes(context),
                forged_session,
                M.canonical_bytes(forged_session),
                context["current_time"],
            )

    def test_counter_equations_bounds_and_507904_settlement_cap(self):
        reserved = M.reserve_counters(read_counters(), M.CHILD_LIMITS, "child")
        self.assertEqual(reserved["read_operations"], 1)
        self.assertEqual(reserved["private_evidence_bytes_reserved"], 524_288)
        settled = M.settle_counters(
            reserved, M.TOTAL_EVIDENCE_PROOF_MAX_BYTES, M.CHILD_LIMITS, "child"
        )
        self.assertEqual(settled["private_evidence_bytes_reserved"], 0)
        self.assertEqual(
            settled["private_evidence_bytes_consumed"],
            M.TOTAL_EVIDENCE_PROOF_MAX_BYTES,
        )
        with self.assertRaises(M.EvidenceH0Error):
            M.settle_counters(
                reserved,
                M.TOTAL_EVIDENCE_PROOF_MAX_BYTES + 1,
                M.CHILD_LIMITS,
                "child",
            )
        for hostile in (
            read_counters(operations=1, consumed=507_905),
            read_counters(operations=2, consumed=507_905, reserved=524_288),
        ):
            with self.assertRaises(M.EvidenceH0Error):
                M.validate_counters(hostile, M.CAMPAIGN_LIMITS, "undercounted")
        full_child = read_counters(
            operations=64,
            consumed=M.CHILD_LIMITS["private_evidence_bytes_max"],
        )
        with self.assertRaises(M.EvidenceH0Error):
            M.reserve_counters(full_child, M.CHILD_LIMITS, "full child")
        _, opening, opening_raw = Fixture.accounting_opening()
        impossible = M.initial_protocol_state(opening, opening_raw)
        impossible["campaign_counters"] = read_counters(operations=1)
        impossible["previous_coordinator_complete_sha256"] = "a" * 64
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_protocol_state(impossible)
        for ordinal, parked in ((1, False), (2, True)):
            naked = {
                "read_ordinal": ordinal,
                "previous_evidence_result_sha256": "b" * 64,
                "previous_coordinator_complete_sha256": "c" * 64,
                "child_counters": read_counters(ordinal, 1),
                "campaign_counters": read_counters(ordinal, 1),
                "campaign_parked": parked,
            }
            with self.subTest(ordinal=ordinal, parked=parked), self.assertRaises(
                M.EvidenceH0Error
            ):
                M.validate_protocol_state(naked)

    def test_context_phase_expiry_control_maxima_and_cross_scope_reject(self):
        allocation, context, _, head, head_raw = Fixture.allocation()
        for mutate in (
            lambda value: value.update(phase="reboot-health-pending"),
            lambda value: value.update(expired=True),
            lambda value: value.update(pending_intent_issued_at=value["current_time"]),
            lambda value: value["child_counters"].update(control_transactions=17),
            lambda value: value["child_counters"].update(
                control_transactions=1,
                component_effects_consumed=1,
                normal_reboots=1,
            ),
        ):
            hostile = copy.deepcopy(context)
            mutate(hostile)
            with self.assertRaises(M.EvidenceH0Error):
                M.model_accounting_opening(
                    allocation,
                    hostile,
                    M.canonical_bytes(hostile),
                    head,
                    head_raw,
                    hostile["current_time"],
                )

    def test_exact_future_lease_and_intent_mirror_validate(self):
        _, opening, opening_raw = Fixture.accounting_opening()
        state = M.initial_protocol_state(opening, opening_raw)
        lease, lease_raw, intent, intent_raw = Fixture.lease(
            opening, opening_raw, state
        )
        self.assertEqual(
            M.validate_future_lease(
                lease, lease_raw, opening, opening_raw, state, lease["issued_at"]
            ),
            lease,
        )
        self.assertEqual(
            M.validate_mirrored_intent(
                intent, intent_raw, lease, lease_raw, opening, opening_raw
            ),
            intent,
        )
        self.assertEqual(intent["coordinator_lease_sha256"], M.sha256_bytes(lease_raw))
        self.assertTrue(intent["attempt_consumed"])
        self.assertFalse(intent["replay_authorized"])

    def test_lease_stale_head_identity_counter_one_scope_and_park_reject(self):
        _, opening, opening_raw = Fixture.accounting_opening()
        state = M.initial_protocol_state(opening, opening_raw)
        lease, _, _, _ = Fixture.lease(opening, opening_raw, state)
        hostile_values = (
            ("issued_at", lease["issued_at"] - 1),
            ("coordinator_head_sha256", "f" * 64),
            ("source_identity", Fixture.source(boot_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")),
            ("reservation_bytes", 1),
            ("controls_blocked", False),
        )
        for key, value in hostile_values:
            hostile = copy.deepcopy(lease)
            hostile[key] = value
            with self.subTest(key=key), self.assertRaises(M.EvidenceH0Error):
                M.validate_future_lease(
                    hostile,
                    M.canonical_bytes(hostile),
                    opening,
                    opening_raw,
                    state,
                    lease["issued_at"],
                )
        hostile = copy.deepcopy(lease)
        hostile["campaign_counters"]["private_evidence_bytes_reserved"] = 0
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_future_lease(
                hostile,
                M.canonical_bytes(hostile),
                opening,
                opening_raw,
                state,
                lease["issued_at"],
            )
        drifted = copy.deepcopy(lease)
        drifted_source = Fixture.source(
            boot_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        )
        drifted["source_identity"] = drifted_source
        drifted["coordinator_context"]["source_identity"] = copy.deepcopy(
            drifted_source
        )
        drifted["coordinator_context_sha256"] = M.sha256_bytes(
            M.canonical_bytes(drifted["coordinator_context"])
        )
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_future_lease(
                drifted,
                M.canonical_bytes(drifted),
                opening,
                opening_raw,
                state,
                lease["issued_at"],
            )
        parked = copy.deepcopy(state)
        parked["campaign_parked"] = True
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_future_lease(
                lease, M.canonical_bytes(lease), opening, opening_raw, parked, lease["issued_at"]
            )

    def test_late_mirror_cannot_model_post_expiry_commands(self):
        _, opening, opening_raw = Fixture.accounting_opening()
        state = M.initial_protocol_state(opening, opening_raw)
        lease, lease_raw, _, _ = Fixture.lease(opening, opening_raw, state)
        late = M.mirror_read_intent(
            lease,
            lease_raw,
            opening,
            opening_raw,
            Fixture.session_expiry + 1,
        )
        records = Fixture.records(late)
        with self.assertRaises(M.EvidenceH0Error):
            M.build_command_receipts(M.canonical_bytes(late), records)

    def test_command_receipts_bind_actual_invocation_timing_raw_and_predecessor(self):
        bundle = Fixture.bundle()
        receipts = bundle["receipts"]
        self.assertEqual(len(receipts), 6)
        predecessor = M.sha256_bytes(bundle["intent_raw"])
        for ordinal, ((receipt, raw), record, template) in enumerate(
            zip(receipts, bundle["records"], M.FIXED_TRANSCRIPT, strict=True), 1
        ):
            self.assertEqual(receipt["ordinal"], ordinal)
            self.assertEqual(receipt["predecessor_sha256"], predecessor)
            self.assertEqual(receipt["argv_sha256"], M.sha256_bytes(M.canonical_bytes(record["argv"])))
            self.assertEqual(receipt["timeout_sec"], template["timeout_sec"])
            self.assertEqual(receipt["max_bytes"], 65_536)
            self.assertEqual(receipt["return_retained_at"], record["return_retained_at"])
            self.assertEqual(receipt["receipt_published_at"], record["receipt_published_at"])
            self.assertLessEqual(len(raw), M.COMMAND_RECEIPT_MAX_BYTES)
            predecessor = M.sha256_bytes(raw)

    def test_hostile_actual_argv_timeout_order_time_and_preparse_bound_reject(self):
        bundle = Fixture.bundle()
        for index, key, value in (
            (2, "ordinal", 9),
            (2, "argv", ["/bin/true"]),
            (3, "timeout_sec", 11),
            (4, "max_bytes", 1),
            (4, "execution_started_at", Fixture.session_expiry),
            (5, "execution_completed_at", 0),
        ):
            records = copy.deepcopy(bundle["records"])
            records[index][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(M.EvidenceH0Error):
                M.build_command_receipts(bundle["intent_raw"], records)
        records = copy.deepcopy(bundle["records"])
        records[1]["stdout"] = b"x" * (M.RAW_PAIR_MAX_BYTES + 1)
        with mock.patch.object(M, "parse_inventory", side_effect=AssertionError("parsed")):
            with self.assertRaises(M.EvidenceH0Error):
                M.build_command_receipts(bundle["intent_raw"], records)

    def test_tool_drift_raw_hash_and_receipt_chain_forgery_reject(self):
        bundle = Fixture.bundle()
        records = copy.deepcopy(bundle["records"])
        records[3]["host_tool_after"]["inode"] += 1
        with self.assertRaises(M.EvidenceH0Error):
            M.build_command_receipts(bundle["intent_raw"], records)
        records = copy.deepcopy(bundle["records"])
        records[4]["host_tool_before"]["inode"] += 1
        records[4]["host_tool_after"]["inode"] += 1
        with self.assertRaises(M.EvidenceH0Error):
            M.build_command_receipts(bundle["intent_raw"], records)
        receipts = list(copy.deepcopy(bundle["receipts"]))
        receipts[2][0]["predecessor_sha256"] = "f" * 64
        receipts[2] = (receipts[2][0], M.canonical_bytes(receipts[2][0]))
        with self.assertRaises(M.EvidenceH0Error):
            M.derive_health_result(bundle["intent"], bundle["records"], receipts)

    def test_pure_retained_parser_never_reads_current_adb_or_spawns(self):
        bundle = Fixture.bundle()
        real_open = M._open

        def guarded_open(path, *args, **kwargs):
            if str(path) == M.expected_host_tool()["path"]:
                raise AssertionError("current ADB opened")
            return real_open(path, *args, **kwargs)

        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawned")):
            with mock.patch.object(M, "_open", side_effect=guarded_open):
                result = M.model_validated_read_result(
                    bundle["opening"],
                    bundle["opening_raw"],
                    bundle["state"],
                    bundle["lease"],
                    bundle["lease_raw"],
                    bundle["intent"]["lease_observed_at"],
                    bundle["intent"],
                    bundle["intent_raw"],
                    bundle["records"],
                    bundle["receipts"],
                    bundle["result"]["completed_at"],
                    None,
                )
                health = M.derive_health_result(
                    bundle["intent"], bundle["records"], bundle["receipts"]
                )
        self.assertEqual(result, bundle["result"])
        self.assertEqual(result["source_identity"]["serial_sha256"], Fixture.source()["serial_sha256"])
        self.assertEqual(result["device_command_count_by_owner"], 0)
        self.assertEqual(health["other_target_command_count"], 0)

    def test_pure_parser_matches_the_pinned_inventory_reference_fixture(self):
        inventory_path = M.SOURCE_SPECS["inventory"]["path"]
        spec = importlib.util.spec_from_file_location(
            "s20plus_g986n_inventory_reference_test_only", inventory_path
        )
        inventory = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(inventory)
        bundle = Fixture.bundle()
        records = bundle["records"]
        queued = iter(records)

        def fake_command(argv, timeout, maximum):
            record = next(queued)
            self.assertEqual(argv, record["argv"])
            self.assertEqual(timeout, record["timeout_sec"])
            self.assertEqual(maximum, record["max_bytes"])
            return record["returncode"], record["stdout"], record["stderr"]

        tool = copy.deepcopy(records[0]["host_tool_before"])
        with mock.patch.object(inventory, "tool_receipt", return_value=tool):
            with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawned")):
                reference = inventory.collect(command=fake_command)
        parsed = M.derive_health_result(
            bundle["intent"], bundle["records"], bundle["receipts"]
        )
        self.assertEqual(parsed, reference)

    def test_same_model_foreign_serial_topology_boot_and_snapshot_drift_reject(self):
        bundle = Fixture.bundle()
        cases = (
            {"serial": "R58NFOREIGN002"},
            {"devpath": "usb:9-9"},
            {"boot_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            {"snapshot": Fixture.snapshot(overrides={"selinux": "Permissive"})},
            {"snapshot": Fixture.snapshot(overrides={"incremental": "WRONG"})},
        )
        for values in cases:
            records = Fixture.records(bundle["intent"], **values)
            receipts = M.build_command_receipts(bundle["intent_raw"], records)
            with self.subTest(values=values), self.assertRaises(M.EvidenceH0Error):
                M.derive_health_result(bundle["intent"], records, receipts)
        changed_final = (
            "List of devices attached\n"
            f"{Fixture.serial} offline product:y2qksx model:SM_G986N device:y2q\n"
        ).encode()
        records = Fixture.records(bundle["intent"], final_inventory=changed_final)
        receipts = M.build_command_receipts(bundle["intent_raw"], records)
        with self.assertRaises(M.EvidenceH0Error):
            M.derive_health_result(bundle["intent"], records, receipts)

    def test_many_foreign_rows_expand_health_before_any_result_model(self):
        bundle = Fixture.bundle()
        rows = [
            "List of devices attached",
            f"{Fixture.serial} device product:y2qksx model:SM_G986N device:y2q",
        ]
        rows.extend(f"F{index:04d} device" for index in range(1_100))
        inventory = ("\n".join(rows) + "\n").encode()
        self.assertLessEqual(len(inventory), M.RAW_PAIR_MAX_BYTES)
        records = Fixture.records(bundle["intent"], inventory=inventory)
        receipts = M.build_command_receipts(bundle["intent_raw"], records)
        with self.assertRaisesRegex(M.EvidenceH0Error, "health result exceeds"):
            M.model_validated_read_result(
                bundle["opening"],
                bundle["opening_raw"],
                bundle["state"],
                bundle["lease"],
                bundle["lease_raw"],
                bundle["intent"]["lease_observed_at"],
                bundle["intent"],
                bundle["intent_raw"],
                records,
                receipts,
                bundle["result"]["completed_at"],
                None,
            )

    def test_exact_19_file_manifest_and_byte_charge(self):
        bundle = Fixture.bundle()
        result = bundle["result"]
        names = [item["name"] for item in result["evidence_files"]]
        self.assertEqual(names, list(M.EVIDENCE_NAMES))
        self.assertEqual(len(names), 19)
        self.assertEqual(
            result["actual_evidence_bytes"],
            sum(item["size"] for item in result["evidence_files"]),
        )
        self.assertLessEqual(result["actual_evidence_bytes"], 507_904)
        self.assertEqual(
            result["evidence_set_sha256"],
            M.sha256_bytes(M.canonical_bytes(result["evidence_files"])),
        )
        self.assertEqual(
            result["child_counters"]["private_evidence_bytes_consumed"],
            result["actual_evidence_bytes"],
        )
        self.assertEqual(result["child_counters"]["private_evidence_bytes_reserved"], 0)

    def test_forged_manifest_result_or_completion_cannot_settle(self):
        bundle = Fixture.bundle()
        hostile = copy.deepcopy(bundle["result"])
        hostile["evidence_files"][0]["size"] += 1
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_read_result_model(hostile, M.canonical_bytes(hostile))
        hostile = copy.deepcopy(bundle["result"])
        hostile["child_counters"]["private_evidence_bytes_consumed"] += 1
        hostile_raw = M.canonical_bytes(hostile)
        completion = copy.deepcopy(bundle["completion"])
        completion["evidence_result_sha256"] = M.sha256_bytes(hostile_raw)
        completion["child_counters"] = copy.deepcopy(hostile["child_counters"])
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_future_completion(
                completion,
                M.canonical_bytes(completion),
                hostile,
                hostile_raw,
                bundle["lease"],
                bundle["lease_raw"],
                bundle["intent"],
                bundle["intent_raw"],
                bundle["opening"],
                bundle["opening_raw"],
                bundle["state"],
                bundle["intent"]["lease_observed_at"],
                bundle["records"],
                bundle["receipts"],
            )

    def test_completion_settles_parked_and_forbids_next_read_or_double_settlement(self):
        bundle = Fixture.bundle()
        validated = M.validate_future_completion(
            bundle["completion"],
            bundle["completion_raw"],
            bundle["result"],
            bundle["result_raw"],
            bundle["lease"],
            bundle["lease_raw"],
            bundle["intent"],
            bundle["intent_raw"],
            bundle["opening"],
            bundle["opening_raw"],
            bundle["state"],
            bundle["intent"]["lease_observed_at"],
            bundle["records"],
            bundle["receipts"],
        )
        self.assertEqual(validated, bundle["completion"])
        state = M.advance_protocol_state(
            bundle["state"],
            bundle["result"],
            bundle["result_raw"],
            bundle["completion"],
            bundle["completion_raw"],
            bundle["lease"],
            bundle["lease_raw"],
            bundle["intent"],
            bundle["intent_raw"],
            bundle["opening"],
            bundle["opening_raw"],
            bundle["intent"]["lease_observed_at"],
            bundle["records"],
            bundle["receipts"],
        )
        self.assertEqual(state["read_ordinal"], 1)
        self.assertTrue(state["campaign_parked"])
        self.assertEqual(bundle["completion"]["completion_mode"], "permanent-h0-parked")
        self.assertFalse(bundle["completion"]["controls_unblocked"])
        with self.assertRaises(M.EvidenceH0Error):
            Fixture.lease(
                bundle["opening"],
                bundle["opening_raw"],
                state,
                issued_at=bundle["completion"]["completed_at"] + 1,
                head=bundle["completion"],
            )
        with self.assertRaises(M.EvidenceH0Error):
            M.advance_protocol_state(
                state,
                bundle["result"],
                bundle["result_raw"],
                bundle["completion"],
                bundle["completion_raw"],
                bundle["lease"],
                bundle["lease_raw"],
                bundle["intent"],
                bundle["intent_raw"],
                bundle["opening"],
                bundle["opening_raw"],
                bundle["intent"]["lease_observed_at"],
                bundle["records"],
                bundle["receipts"],
            )

    def test_expiry_and_drift_complete_only_zero_command_then_park(self):
        after_expiry = Fixture.bundle(completed_at=Fixture.session_expiry + 1)
        self.assertTrue(after_expiry["result"]["reporting_after_expiry_or_drift"])
        self.assertIsNone(after_expiry["result"]["reporting_cut_at"])
        self.assertTrue(after_expiry["completion"]["campaign_parked"])
        state = M.advance_protocol_state(
            after_expiry["state"],
            after_expiry["result"],
            after_expiry["result_raw"],
            after_expiry["completion"],
            after_expiry["completion_raw"],
            after_expiry["lease"],
            after_expiry["lease_raw"],
            after_expiry["intent"],
            after_expiry["intent_raw"],
            after_expiry["opening"],
            after_expiry["opening_raw"],
            after_expiry["intent"]["lease_observed_at"],
            after_expiry["records"],
            after_expiry["receipts"],
        )
        self.assertTrue(state["campaign_parked"])
        with self.assertRaises(M.EvidenceH0Error):
            Fixture.lease(
                after_expiry["opening"],
                after_expiry["opening_raw"],
                state,
                issued_at=1_100,
                head=after_expiry["completion"],
            )
        drift = Fixture.bundle(completed_at=1_050, cut=1_045)
        self.assertTrue(drift["result"]["reporting_after_expiry_or_drift"])
        too_early = max(record["return_retained_at"] for record in drift["records"]) - 1
        with self.assertRaises(M.EvidenceH0Error):
            M.model_validated_read_result(
                drift["opening"],
                drift["opening_raw"],
                drift["state"],
                drift["lease"],
                drift["lease_raw"],
                drift["intent"]["lease_observed_at"],
                drift["intent"],
                drift["intent_raw"],
                drift["records"],
                drift["receipts"],
                1_050,
                too_early,
            )
        normal = Fixture.bundle()
        later = M.model_future_completion(
            normal["result"],
            normal["result_raw"],
            Fixture.session_expiry + 1,
        )
        self.assertEqual(later["completion_mode"], "permanent-h0-parked")
        self.assertTrue(later["campaign_parked"])
        hostile = copy.deepcopy(later)
        hostile["completion_mode"] = "same-invocation"
        hostile["controls_unblocked"] = True
        hostile["terminal_unblocked"] = True
        hostile["campaign_parked"] = False
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_future_completion(
                hostile,
                M.canonical_bytes(hostile),
                normal["result"],
                normal["result_raw"],
                normal["lease"],
                normal["lease_raw"],
                normal["intent"],
                normal["intent_raw"],
                normal["opening"],
                normal["opening_raw"],
                normal["state"],
                normal["intent"]["lease_observed_at"],
                normal["records"],
                normal["receipts"],
            )

    def test_receipt_six_must_be_published_before_a_reporting_cut(self):
        bundle = Fixture.bundle(completed_at=1_050, cut=1_045)
        records = copy.deepcopy(bundle["records"])
        records[-1]["receipt_published_at"] = 1_046
        receipts = M.build_command_receipts(bundle["intent_raw"], records)
        with self.assertRaises(M.EvidenceH0Error):
            M.model_validated_read_result(
                bundle["opening"],
                bundle["opening_raw"],
                bundle["state"],
                bundle["lease"],
                bundle["lease_raw"],
                bundle["intent"]["lease_observed_at"],
                bundle["intent"],
                bundle["intent_raw"],
                records,
                receipts,
                1_050,
                1_045,
            )

    def test_reporting_cut_states_never_replay_or_grant_next_action(self):
        base = dict(
            lease_present=True,
            intent_present=True,
            published_evidence_names=[],
            result_present=False,
            coordinator_complete_present=False,
            expired_or_drifted=False,
        )
        partial = M.classify_reporting_cut(**base)
        self.assertEqual(partial["status"], "UNCERTAIN_CONSUMED")
        self.assertTrue(partial["reservation_retained"])
        self.assertFalse(partial["replay_authorized"])
        complete_returns = M.classify_reporting_cut(
            **{**base, "published_evidence_names": list(M.RETURN_NAMES)}
        )
        self.assertTrue(complete_returns["zero_command_resume"])
        awaiting = M.classify_reporting_cut(
            **{
                **base,
                "published_evidence_names": list(M.EVIDENCE_NAMES),
                "result_present": True,
            }
        )
        self.assertEqual(awaiting["status"], "AWAITING_COORDINATOR_COMPLETE")
        complete = M.classify_reporting_cut(
            **{
                **base,
                "published_evidence_names": list(M.EVIDENCE_NAMES),
                "result_present": True,
                "coordinator_complete_present": True,
            }
        )
        self.assertTrue(complete["completion_must_be_revalidated_before_settlement"])
        self.assertTrue(complete["reservation_retained"])
        self.assertFalse(complete["settled_consumed"])
        for hostile in (
            {**base, "lease_present": False, "intent_present": True},
            {**base, "result_present": True},
            {**base, "lease_present": 1},
        ):
            with self.assertRaises(M.EvidenceH0Error):
                M.classify_reporting_cut(**hostile)

    def test_ledger_grammar_ordinals_limits_and_exact_read_namespace(self):
        names = M.ledger_relative_names(Fixture.campaign_id, Fixture.session_id, 1)
        self.assertEqual(names["root_children"], ["campaigns"])
        self.assertEqual(len(names["read_children"]), 19)
        self.assertEqual(
            names["campaign"], "campaign-" + digest_text(Fixture.campaign_id)
        )
        campaigns = [names["campaign"]]
        sessions = [names["session"]]
        validated = M.validate_ledger_namespace(
            campaign_id=Fixture.campaign_id,
            session_id=Fixture.session_id,
            read_count=1,
            root_children=["campaigns"],
            campaign_directories=campaigns,
            campaign_children=["sessions"],
            session_directories=sessions,
            session_children=names["session_children"],
            read_children_by_ordinal={1: list(M.EVIDENCE_NAMES)},
        )
        self.assertEqual(validated, names)
        with self.assertRaises(M.EvidenceH0Error):
            M.ledger_relative_names(Fixture.campaign_id, Fixture.session_id, 2)
        with self.assertRaises(M.EvidenceH0Error):
            M.validate_ledger_namespace(
                campaign_id=Fixture.campaign_id,
                session_id=Fixture.session_id,
                read_count=1,
                root_children=["campaigns", "foreign"],
                campaign_directories=campaigns,
                campaign_children=["sessions"],
                session_directories=sessions,
                session_children=names["session_children"],
                read_children_by_ordinal={1: list(M.EVIDENCE_NAMES)},
            )

    def test_test_only_atomic_harness_no_replace_modes_links_and_parent_swap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixed"
            campaign = root / "campaigns" / ("campaign-" + digest_text(Fixture.campaign_id))
            parent = campaign / "sessions" / ("session-" + digest_text(Fixture.session_id)) / "read-000001"
            parent.mkdir(parents=True, mode=0o700)
            for ancestor in (root, root / "campaigns", campaign, campaign / "sessions", parent.parent, parent):
                ancestor.chmod(0o700)
            payload = b"retained bytes"
            AtomicHarness.publish(parent, "cmd-01.stdout.bin", payload)
            AtomicHarness.validate_file(parent, "cmd-01.stdout.bin", payload)
            with self.assertRaises(FileExistsError):
                AtomicHarness.publish(parent, "cmd-01.stdout.bin", payload)
            os.link(parent / "cmd-01.stdout.bin", parent / "hardlink")
            with self.assertRaises(RuntimeError):
                AtomicHarness.validate_file(parent, "cmd-01.stdout.bin", payload)
            os.unlink(parent / "hardlink")

            moved = parent.with_name("read-000001-moved")

            def swap_parent():
                parent.rename(moved)
                parent.mkdir(mode=0o700)

            with self.assertRaisesRegex(RuntimeError, "parent was replaced"):
                AtomicHarness.publish(parent, "cmd-01.stderr.bin", b"", swap_parent)
            self.assertFalse((parent / "cmd-01.stderr.bin").exists())
            self.assertFalse((moved / "cmd-01.stderr.bin").exists())

    def test_test_only_harness_rejects_ancestor_symlink_and_mode_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            actual = base / "actual"
            actual.mkdir(mode=0o700)
            indirect = base / "indirect"
            indirect.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(OSError):
                AtomicHarness.walk(indirect)
            actual.chmod(0o755)
            with self.assertRaises(RuntimeError):
                AtomicHarness.walk(actual)


if __name__ == "__main__":
    unittest.main()
