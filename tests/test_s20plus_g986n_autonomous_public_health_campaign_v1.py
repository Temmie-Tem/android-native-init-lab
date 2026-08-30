from __future__ import annotations

import copy
import contextlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_campaign_v1.py"
)
CURRENT_RECOVERY = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load test module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CAMPAIGN = load_module(SOURCE, "_s20plus_campaign_v1_test")
_ASSERTIONS = unittest.TestCase()


def expect_raises(exception, match=None):
    if match is None:
        return _ASSERTIONS.assertRaises(exception)
    return _ASSERTIONS.assertRaisesRegex(exception, match)


def fixture_tool(module):
    return {
        "path": module.ADB_PATH,
        "device": 41,
        "inode": 42,
        "mtime_ns": 43,
        "size": module.ADB_SIZE,
        "sha256": module.ADB_SHA256,
    }


def fixture_server(module, tool):
    return {
        "schema": module.ADB_SERVER_RECEIPT_SCHEMA,
        "socket_spec": module.ADB_SERVER_SOCKET,
        "socket_inode": 51,
        "pid": 52,
        "pid_start_ticks": 53,
        "uid": os.getuid(),
        "pidfd_held": True,
        "continuous_identity_checks": True,
        "executable": tool,
        "provenance_proven": True,
    }


def fixture_recovery_binding(module):
    return {
        "schema": "s20plus_g986n_autonomous_public_health_recovery_precursors_v1",
        "status": "PHASE_A_QUALIFIED_PRECURSORS_NOT_OPERATIONAL",
        "binding_complete": False,
        "phase_b_exact_binding_required": True,
        "loader": {
            "name": module.EXPECTED_LOADER_NAME,
            "size": module.EXPECTED_LOADER_SIZE,
            "sha256": module.EXPECTED_LOADER_SHA256,
            "normalized_sha256": module.EXPECTED_LOADER_NORMALIZED_SHA256,
        },
        "core": {
            "name": module.EXPECTED_CORE_NAME,
            "size": module.EXPECTED_CORE_SIZE,
            "sha256": module.EXPECTED_CORE_SHA256,
            "normalized_sha256": module.EXPECTED_CORE_NORMALIZED_SHA256,
        },
        "manifest": {
            "name": module.EXPECTED_MANIFEST_NAME,
            "size": module.EXPECTED_MANIFEST_SIZE,
            "sha256": module.EXPECTED_MANIFEST_SHA256,
        },
    }


def fixture_producer_binding(module):
    return {
        "schema": "s20plus_g986n_autonomous_public_health_campaign_v1_runner_binding",
        "status": "BOUND",
        "normalized_sha256": module.EXPECTED_SELF_NORMALIZED_SHA256,
        "binding_complete": True,
    }


def fixture_clock(module):
    return {
        "schema": module.CLOCK_BINDING_SCHEMA,
        "host_boot_id_sha256": "8" * 64,
        "realtime_origin_ns": 1_700_000_000_000_000_000,
        "boottime_origin_ns": 10_000_000_000,
        "monotonic_origin_ns": 9_000_000_000,
        "logical_origin_sec": 1_700_000_000,
        "caller_supplied_time": False,
    }


def fixture_clock_sample(module, clock, delta_seconds=6):
    delta = delta_seconds * 1_000_000_000
    return {
        "schema": module.CLOCK_SAMPLE_SCHEMA,
        "host_boot_id_sha256": clock["host_boot_id_sha256"],
        "realtime_ns": clock["realtime_origin_ns"] + delta,
        "boottime_ns": clock["boottime_origin_ns"] + delta,
        "monotonic_ns": clock["monotonic_origin_ns"] + delta,
        "logical_sec": clock["logical_origin_sec"] + delta_seconds,
        "projection_skew_ns": 0,
        "reversed": False,
    }


def fixture_properties(module):
    properties = {key: "observed" for key in module.PROPERTY_KEYS if key != "boot_id"}
    properties.update(
        {
            "model": module.TARGET["model"],
            "device": module.TARGET["device"],
            "product_name": module.TARGET["product"],
            "build_product": module.TARGET["device"],
            "incremental": module.TARGET["build"],
            "fingerprint": (
                "samsung/y2qksx/y2q:13/TP1A.220624.014/"
                "G986NKSS8IYC2:user/release-keys"
            ),
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
            "shell_identity": (
                "uid=2000(shell) gid=2000(shell) groups=2000(shell),1003(graphics)"
            ),
        }
    )
    return properties


def fixture_health(module, tool, serial, devpath, boot_id):
    inventory_text = (
        "List of devices attached\n"
        f"{serial} device {devpath} product:y2qksx model:SM_G986N device:y2q\n"
    )
    rows = module.parse_inventory(inventory_text)
    return {
        "schema": module.HEALTH_SCHEMA,
        "version": module.HEALTH_VERSION,
        "mode": "connected-read-only",
        "target": {
            "model": module.TARGET["model"],
            "adb_serial_sha256": module.sha256_bytes(serial.encode()),
            "usb_topology_sha256": module.sha256_bytes(devpath.encode()),
            "other_serial_sha256": [],
            "inventory_sha256": module.sha256_bytes(
                json.dumps(module._sanitized_inventory(rows), sort_keys=True).encode()
            ),
        },
        "properties": fixture_properties(module),
        "boot_id_sha256": module.sha256_bytes(boot_id.encode()),
        "usb_debugging_verified": True,
        "adb_authorization_state": "device",
        "host_tool": {
            **tool,
            "version_output_sha256": module.sha256_bytes(b"adb-version"),
        },
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "verdict": module.HEALTH_VERDICT,
    }


def complete_model(campaign):
    serial = "R58MTEST123"
    devpath = "usb:1-2.3"
    boot_id = "12345678-1234-1234-1234-123456789abc"
    tool = fixture_tool(campaign)
    server = fixture_server(campaign, tool)
    clock = fixture_clock(campaign)
    producer_binding = fixture_producer_binding(campaign)
    recovery_binding = fixture_recovery_binding(campaign)
    intent = campaign.model_opening_intent(
        campaign_id="a" * 32,
        session_id="b" * 32,
        created_at=clock["logical_origin_sec"],
        activation_binding_candidate_sha256="c" * 64,
        producer_binding=producer_binding,
        recovery_binding=recovery_binding,
        clock_binding=clock,
        adb_client=tool,
        adb_server=server,
    )
    intent_raw = campaign.canonical_bytes(intent)
    snapshot_values = fixture_properties(campaign)
    snapshot_values["boot_id"] = boot_id
    snapshot = (
        "\n".join(f"{key}={snapshot_values[key]}" for key in campaign.PROPERTY_KEYS)
        + "\n"
    ).encode()
    outputs = (
        b"adb-version\n",
        (
            b"List of devices attached\n"
            + serial.encode()
            + b" device usb:1-2.3 product:y2qksx model:SM_G986N device:y2q\n"
        ),
        devpath.encode() + b"\n",
        snapshot,
        snapshot,
        (
            b"List of devices attached\n"
            + serial.encode()
            + b" device usb:1-2.3 product:y2qksx model:SM_G986N device:y2q\n"
        ),
    )
    evidence = {}
    predecessor = campaign.sha256_bytes(intent_raw)
    for ordinal, stdout in enumerate(outputs, 1):
        stderr = b""
        receipt = campaign.model_opening_command_receipt(
            intent=intent,
            ordinal=ordinal,
            serial=serial,
            predecessor_sha256=predecessor,
            stdout=stdout,
            stderr=stderr,
            started_at=clock["logical_origin_sec"] + ordinal,
            completed_at=clock["logical_origin_sec"] + ordinal,
            retained_at=clock["logical_origin_sec"] + ordinal,
            published_at=clock["logical_origin_sec"] + ordinal,
        )
        receipt_raw = campaign.canonical_bytes(receipt)
        evidence[f"cmd-{ordinal:02d}.stdout.bin"] = stdout
        evidence[f"cmd-{ordinal:02d}.stderr.bin"] = stderr
        evidence[f"cmd-{ordinal:02d}.receipt.json"] = receipt_raw
        predecessor = campaign.sha256_bytes(receipt_raw)
    health = fixture_health(campaign, tool, serial, devpath, boot_id)
    evidence["health.json"] = campaign.canonical_bytes(health)
    clock_sample = fixture_clock_sample(campaign, clock)
    source = {
        "target": dict(campaign.TARGET),
        "serial_sha256": campaign.sha256_bytes(serial.encode()),
        "topology_sha256": campaign.sha256_bytes(devpath.encode()),
        "boot_id_sha256": campaign.sha256_bytes(boot_id.encode()),
        "healthy_android": True,
        "foreign_guard_present": False,
    }
    usb = {
        "schema": campaign.USB_GENERATION_SCHEMA,
        "topology_sha256": source["topology_sha256"],
        "sysfs_device": 60,
        "sysfs_inode": 61,
        "busnum": 1,
        "devnum": 2,
        "usbfs_device": 62,
        "usbfs_inode": 63,
        "usbfs_rdev": 64,
        "held_descriptors": True,
        "event_monitor_overflow": False,
        "generation_continuous": True,
    }
    result = campaign.model_opening_result(
        intent=intent,
        intent_raw=intent_raw,
        evidence=evidence,
        selected_serial=serial,
        clock_sample=clock_sample,
        usb_generation=usb,
    )
    result_raw = campaign.canonical_bytes(result)
    forward = campaign.model_forward_nodes(
        result,
        result_raw,
        opening_intent=intent,
        opening_intent_raw=intent_raw,
        opening_evidence=evidence,
        selected_serial=serial,
    )
    binding = campaign.model_campaign_binding(
        opening_intent=intent,
        opening_intent_raw=intent_raw,
        opening_result=result,
        opening_result_raw=result_raw,
        opening_evidence=evidence,
        selected_serial=serial,
        forward_nodes=forward,
    )
    return {
        "serial": serial,
        "devpath": devpath,
        "tool": tool,
        "server": server,
        "clock": clock,
        "clock_sample": clock_sample,
        "usb": usb,
        "intent": intent,
        "intent_raw": intent_raw,
        "evidence": evidence,
        "result": result,
        "result_raw": result_raw,
        "forward": forward,
        "binding": binding,
    }


def test_render_only_and_every_operational_gate_false(campaign):
    plan = campaign.render_plan()
    assert plan["cli"] == ["--render-plan"]
    assert not any(plan["gates"].values())
    assert plan["gates"]["executor_implemented"] is False
    assert plan["device_commands"] == []
    assert plan["device_effects"] == []
    assert plan["callbacks"] == []
    assert plan["backends"] == []
    with expect_raises(campaign.CampaignV1Error, match="inactive"):
        campaign.attended_open_and_read()


def test_even_all_true_gates_reach_only_the_unimplemented_owner_stub(campaign):
    gate_names = (
        "CAMPAIGN_V1_QUALIFIED",
        "OPENING_ACTIVE",
        "READ_PRODUCER_ACTIVE",
        "RECOVERY_BUNDLE_BOUND",
        "RECOVERY_SCANNER_ROTATED",
        "RECOVERY_FINALIZER_ROTATED",
        "ADB_CLIENT_EXEC_ACTIVE",
        "EXECUTOR_IMPLEMENTED",
        "SAME_PROCESS_HANDOFF_IMPLEMENTED",
        "ADB_SERVER_PROVENANCE_PROVEN",
        "USB_GENERATION_PROVEN",
        "TRUSTED_CLOCK_PROVEN",
        "TARGET_COORDINATION_ACTIVE",
        "CROSS_CODE_COORDINATION_ACTIVE",
        "CONTRACT_ACTIVE",
        "MECHANICAL_ACTIVATION",
        "LIVE_AUTHORITY",
    )
    original = {name: getattr(campaign, name) for name in gate_names}
    try:
        for name in gate_names:
            setattr(campaign, name, True)
        with expect_raises(campaign.CampaignV1Error, match="not activated"):
            campaign.attended_open_and_read()
    finally:
        for name, value in original.items():
            setattr(campaign, name, value)


def test_parser_exposes_no_connected_or_caller_surface(campaign):
    parser = campaign.build_parser()
    assert parser.parse_args(["--render-plan"]).render_plan is True
    with contextlib.redirect_stderr(io.StringIO()):
        with expect_raises(SystemExit):
            parser.parse_args(["--attended-open-and-read"])
        with expect_raises(SystemExit):
            parser.parse_args(["--serial", "x"])


def test_exact_cap_arithmetic_and_file_count(campaign):
    assert campaign.OPENING_INTENT_MAX_BYTES == 16 * 1024
    assert campaign.OPENING_RESULT_MAX_BYTES == 16 * 1024
    assert campaign.OPENING_EVIDENCE_RESERVATION_BYTES == 512 * 1024
    assert campaign.OPENING_DIRECTORY_MAX_BYTES == 544 * 1024
    assert campaign.COMPLETED_TOTAL_MAX_BYTES == 1_441_792
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    assert len(sequence) == 52 == campaign.COMPLETED_TOTAL_FILE_COUNT
    assert len(set(sequence)) == 52


def test_exact_two_phase_twelve_command_plan(campaign):
    plan = campaign.render_plan()
    assert plan["phase_order"] == ["attended-opening", "ordinal-1-read"]
    assert plan["planned_total_host_adb_invocations"] == 12
    assert plan["planned_total_selected_target_commands"] == 6
    assert plan["other_target_commands"] == 0
    assert plan["same_process_12_command_closure_proven"] is False
    assert plan["opening_command_executor_implemented"] is False
    assert plan["ordinal1_read_executor_implemented"] is False
    assert [item["ordinal"] for item in campaign.FIXED_TRANSCRIPT] == list(range(1, 7))
    assert campaign.FIXED_TRANSCRIPT[0]["argv"] == ["ADB", "version"]
    assert campaign.FIXED_TRANSCRIPT[-1]["argv"] == ["ADB", "devices", "-l"]


def test_publication_is_raw_then_stderr_then_receipt_and_guard_first(campaign):
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    assert sequence[4:7] == (
        "leaf/opening-v1/cmd-01.stdout.bin",
        "leaf/opening-v1/cmd-01.stderr.bin",
        "leaf/opening-v1/cmd-01.receipt.json",
    )
    assert sequence[25].endswith("base/active-campaign.json")
    assert sequence[26].endswith("/opening.json")
    assert sequence[27].endswith("/session-opening.json")
    read_one = sequence[31:34]
    assert read_one[0].endswith("cmd-01.stdout.bin")
    assert read_one[1].endswith("cmd-01.stderr.bin")
    assert read_one[2].endswith("cmd-01.receipt.json")


def test_complete_models_are_strict_and_within_caps(campaign, complete_model):
    model = complete_model
    assert len(model["intent_raw"]) <= campaign.OPENING_INTENT_MAX_BYTES
    assert len(model["result_raw"]) <= campaign.OPENING_RESULT_MAX_BYTES
    binding_raw = campaign.canonical_bytes(model["binding"])
    assert len(binding_raw) <= campaign.CAMPAIGN_BINDING_MAX_BYTES
    assert tuple(model["forward"]) == campaign.FORWARD_NODE_ORDER
    assert model["binding"]["forward_publication_order"][0] == "active-campaign.json"
    assert model["binding"]["shared_active_action_created"] is False
    assert model["binding"]["operational_authority"] is False
    assert model["intent"]["operational_recovery_bound"] is False
    assert model["intent"]["recovery_binding"]["binding_complete"] is False


def test_precursor_and_producer_identities_are_exact_not_self_certified(
    campaign, complete_model
):
    bad_producer = copy.deepcopy(complete_model["intent"]["producer_binding"])
    bad_producer["normalized_sha256"] = "f" * 64
    with expect_raises(campaign.CampaignV1Error, match="producer identity"):
        campaign.validate_producer_binding(bad_producer)
    for part, field, value in (
        ("loader", "normalized_sha256", "f" * 64),
        ("core", "normalized_sha256", "f" * 64),
        ("manifest", "sha256", "f" * 64),
        ("loader", "name", "wrong.py"),
    ):
        forged = copy.deepcopy(complete_model["intent"]["recovery_binding"])
        forged[part][field] = value
        with expect_raises(campaign.CampaignV1Error, match="binding differs"):
            campaign.validate_recovery_binding(forged)


def test_strict_json_rejects_duplicate_noncanonical_and_nonfinite(campaign):
    with expect_raises(campaign.CampaignV1Error):
        campaign.parse_canonical_json(b'{"a":1,"a":1}\n', "duplicate", 100)
    with expect_raises(campaign.CampaignV1Error):
        campaign.parse_canonical_json(b'{"a": 1}\n', "spacing", 100)
    with expect_raises(campaign.CampaignV1Error):
        campaign.parse_canonical_json(b'{"a":NaN}\n', "nan", 100)


def test_opening_authority_is_unverified_nonbankable_requirement(
    campaign, complete_model, field, value
):
    forged = copy.deepcopy(complete_model["intent"])
    forged["authority"][field] = value
    raw = campaign.canonical_bytes(forged)
    with expect_raises(campaign.CampaignV1Error, match="semantics"):
        campaign.validate_opening_intent(forged, raw)


def test_opening_intent_has_no_serial_boot_or_token(campaign, complete_model):
    intent = complete_model["intent"]
    assert intent["source_identity"] is None
    raw = complete_model["intent_raw"]
    assert complete_model["serial"].encode() not in raw
    assert b"approval_token" not in raw


def test_evidence_missing_or_predecessor_forgery_rejected(campaign, complete_model):
    missing = dict(complete_model["evidence"])
    missing.pop("cmd-04.stderr.bin")
    with expect_raises(campaign.CampaignV1Error, match="19-file"):
        campaign.validate_opening_evidence(
            intent=complete_model["intent"],
            intent_raw=complete_model["intent_raw"],
            evidence=missing,
            selected_serial=complete_model["serial"],
        )


def test_health_is_rederived_from_raw_returns(campaign, complete_model):
    forged = dict(complete_model["evidence"])
    health = json.loads(forged["health.json"])
    health["boot_id_sha256"] = "f" * 64
    forged["health.json"] = campaign.canonical_bytes(health)
    with expect_raises(campaign.CampaignV1Error, match="exact derivation"):
        campaign.validate_opening_evidence(
            intent=complete_model["intent"],
            intent_raw=complete_model["intent_raw"],
            evidence=forged,
            selected_serial=complete_model["serial"],
        )


def test_raw_snapshot_and_usb_token_drift_cannot_be_hidden_by_health(
    campaign, complete_model
):
    forged = dict(complete_model["evidence"])
    forged["cmd-05.stdout.bin"] = forged["cmd-05.stdout.bin"].replace(
        b"boot_completed=1", b"boot_completed=0"
    )
    receipt = json.loads(forged["cmd-05.receipt.json"])
    receipt["stdout_size"] = len(forged["cmd-05.stdout.bin"])
    receipt["stdout_sha256"] = campaign.sha256_bytes(forged["cmd-05.stdout.bin"])
    forged["cmd-05.receipt.json"] = campaign.canonical_bytes(receipt)
    # Receipt 6 must acknowledge the changed predecessor to demonstrate that
    # coherent rehashing still cannot turn unhealthy raw bytes into PASS.
    receipt6 = json.loads(forged["cmd-06.receipt.json"])
    receipt6["predecessor_sha256"] = campaign.sha256_bytes(
        forged["cmd-05.receipt.json"]
    )
    forged["cmd-06.receipt.json"] = campaign.canonical_bytes(receipt6)
    with expect_raises(campaign.CampaignV1Error):
        campaign.validate_opening_evidence(
            intent=complete_model["intent"],
            intent_raw=complete_model["intent_raw"],
            evidence=forged,
            selected_serial=complete_model["serial"],
        )

    duplicate_usb = dict(complete_model["evidence"])
    duplicate_usb["cmd-02.stdout.bin"] = duplicate_usb["cmd-02.stdout.bin"].replace(
        b"usb:1-2.3 ", b"usb:1-2.3 usb:1-2.3 "
    )
    receipt2 = json.loads(duplicate_usb["cmd-02.receipt.json"])
    receipt2["stdout_size"] = len(duplicate_usb["cmd-02.stdout.bin"])
    receipt2["stdout_sha256"] = campaign.sha256_bytes(
        duplicate_usb["cmd-02.stdout.bin"]
    )
    duplicate_usb["cmd-02.receipt.json"] = campaign.canonical_bytes(receipt2)
    predecessor = campaign.sha256_bytes(duplicate_usb["cmd-02.receipt.json"])
    for ordinal in range(3, 7):
        item = json.loads(duplicate_usb[f"cmd-{ordinal:02d}.receipt.json"])
        item["predecessor_sha256"] = predecessor
        raw = campaign.canonical_bytes(item)
        duplicate_usb[f"cmd-{ordinal:02d}.receipt.json"] = raw
        predecessor = campaign.sha256_bytes(raw)
    with expect_raises(campaign.CampaignV1Error, match="duplicated"):
        campaign.validate_opening_evidence(
            intent=complete_model["intent"],
            intent_raw=complete_model["intent_raw"],
            evidence=duplicate_usb,
            selected_serial=complete_model["serial"],
        )


def test_snapshot_requires_exact_order_final_lf_and_no_cr(campaign, complete_model):
    snapshot = complete_model["evidence"]["cmd-04.stdout.bin"].decode()
    campaign.parse_snapshot(snapshot)
    with expect_raises(campaign.CampaignV1Error, match="LF-terminated"):
        campaign.parse_snapshot(snapshot[:-1])
    with expect_raises(campaign.CampaignV1Error, match="LF-terminated"):
        campaign.parse_snapshot(snapshot.replace("\n", "\r\n"))
    lines = snapshot.splitlines()
    lines[0], lines[1] = lines[1], lines[0]
    with expect_raises(campaign.CampaignV1Error, match="field differs"):
        campaign.parse_snapshot("\n".join(lines) + "\n")


def test_predecessor_forgery_is_rejected(campaign, complete_model):
    forged = dict(complete_model["evidence"])
    receipt = json.loads(forged["cmd-03.receipt.json"])
    receipt["predecessor_sha256"] = "f" * 64
    forged["cmd-03.receipt.json"] = campaign.canonical_bytes(receipt)
    with expect_raises(campaign.CampaignV1Error, match="predecessor"):
        campaign.validate_opening_evidence(
            intent=complete_model["intent"],
            intent_raw=complete_model["intent_raw"],
            evidence=forged,
            selected_serial=complete_model["serial"],
        )


def test_result_and_forward_models_reopen_exact_raw_evidence(campaign, complete_model):
    forged_evidence = dict(complete_model["evidence"])
    forged_evidence["health.json"] = forged_evidence["health.json"].replace(
        b'"boot_id_sha256":"', b'"boot_id_sha256":"f', 1
    )
    with expect_raises(campaign.CampaignV1Error):
        campaign.validate_opening_result(
            complete_model["result"],
            complete_model["result_raw"],
            complete_model["intent"],
            complete_model["intent_raw"],
            forged_evidence,
            complete_model["serial"],
        )
    with expect_raises(campaign.CampaignV1Error):
        campaign.model_forward_nodes(
            complete_model["result"],
            complete_model["result_raw"],
            opening_intent=complete_model["intent"],
            opening_intent_raw=complete_model["intent_raw"],
            opening_evidence=forged_evidence,
            selected_serial=complete_model["serial"],
        )


def test_campaign_binding_commits_guard_first_forward_bytes(campaign, complete_model):
    binding = complete_model["binding"]
    assert tuple(binding["forward_commitments"]) == campaign.FORWARD_NODE_ORDER
    for name, payload in complete_model["forward"].items():
        assert binding["forward_commitments"][name] == campaign.sha256_bytes(payload)
    forged_forward = dict(complete_model["forward"])
    forged_forward["active-campaign.json"] += b"x"
    with expect_raises(campaign.CampaignV1Error):
        campaign.model_campaign_binding(
            opening_intent=complete_model["intent"],
            opening_intent_raw=complete_model["intent_raw"],
            opening_result=complete_model["result"],
            opening_result_raw=complete_model["result_raw"],
            opening_evidence=complete_model["evidence"],
            selected_serial=complete_model["serial"],
            forward_nodes=forged_forward,
        )


def test_forward_nodes_pass_unchanged_recovery_oracle_chain(complete_model):
    recovery = load_module(CURRENT_RECOVERY, "_current_recovery_forward_oracle_test")
    nodes = complete_model["forward"]
    guard_raw = nodes["active-campaign.json"]
    opening_raw = nodes["opening.json"]
    session_raw = nodes["session-opening.json"]
    accounting_raw = nodes["accounting-opening.json"]
    lease_raw = nodes["public-health-read-lease-000001.json"]
    intent_raw = nodes["read-intent-000001.json"]
    guard = recovery.parse_canonical_json(
        guard_raw, "guard", recovery.STRUCTURAL_CAPS["active-campaign.json"]
    )
    opening = recovery.parse_canonical_json(
        opening_raw, "opening", recovery.STRUCTURAL_CAPS["opening.json"]
    )
    session = recovery.parse_canonical_json(
        session_raw,
        "session",
        recovery.STRUCTURAL_CAPS["session-opening.json"],
    )
    allocation = recovery.validate_base_allocation(
        guard, guard_raw, opening, opening_raw, session, session_raw
    )
    accounting = recovery.parse_canonical_json(
        accounting_raw,
        "accounting",
        recovery.STRUCTURAL_CAPS["accounting-opening.json"],
    )
    recovery.validate_accounting_opening(
        accounting,
        accounting_raw,
        allocation,
        guard_raw,
        opening_raw,
        session_raw,
    )
    lease = recovery.parse_canonical_json(
        lease_raw,
        "lease",
        recovery.STRUCTURAL_CAPS["public-health-read-lease-000001.json"],
    )
    recovery.validate_lease(
        lease, lease_raw, accounting, accounting_raw, session, session_raw
    )
    intent = recovery.parse_canonical_json(
        intent_raw,
        "intent",
        recovery.STRUCTURAL_CAPS["read-intent-000001.json"],
    )
    recovery.validate_intent(
        intent,
        intent_raw,
        lease,
        lease_raw,
        accounting,
        accounting_raw,
        guard_raw,
        opening_raw,
        session_raw,
    )


def test_every_exact_cut_prefix_is_accepted_but_never_replay_authority(campaign):
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    for count in range(53):
        cut = campaign.classify_publication_cut(
            campaign_id="a" * 32,
            session_id="b" * 32,
            present_in_publication_order=sequence[:count],
        )
        assert cut["present_count"] == count
        assert cut["opening_replay_authorized"] is False
        assert cut["read_replay_authorized"] is False
        assert cut["new_process_device_commands_authorized"] is False
        assert cut["durable_content_validated"] is False
        assert cut["process_capability_issued"] is False
        assert cut["future_finalizer_only_resume_authorized"] is False
        assert cut["shared_active_action_created_by_campaign"] is False
        assert cut["next_node"] is None
        assert cut["campaign_parked"] is (count >= 4)


def test_cut_classifier_rejects_gap_reorder_duplicate_and_foreign(campaign):
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    hostile = (
        sequence[:5] + (sequence[6],),
        sequence[:4] + (sequence[5], sequence[4]),
        sequence[:5] + (sequence[4],),
        sequence[:5] + ("leaf/foreign",),
    )
    for present in hostile:
        with expect_raises(campaign.CampaignV1Error, match="gap"):
            campaign.classify_publication_cut(
                campaign_id="a" * 32,
                session_id="b" * 32,
                present_in_publication_order=present,
            )


def test_active_action_yields_before_intent_and_parks_after_intent(campaign):
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    before = campaign.classify_publication_cut(
        campaign_id="a" * 32,
        session_id="b" * 32,
        present_in_publication_order=sequence[:3],
        shared_active_action_present=True,
    )
    assert before["status"] == "FOREIGN_ACTIVE_ACTION_ZERO_COMMAND_YIELD"
    assert before["campaign_attempt_consumed"] is False
    after = campaign.classify_publication_cut(
        campaign_id="a" * 32,
        session_id="b" * 32,
        present_in_publication_order=sequence[:4],
        shared_active_action_present=True,
    )
    assert after["status"] == "FOREIGN_ACTIVE_ACTION_APPEARED_CONSUMED_ATTEMPT_PARKED"
    assert after["campaign_parked"] is True
    assert after["recovery_bypass_preserved"] is True


def test_sequence_never_creates_shared_active_action(campaign):
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    assert not any("routine-actions/active-action.json" in name for name in sequence)
    assert campaign.render_plan()["coordination"]["creates_shared_active_action"] is False


def test_phase_a_exposes_no_read_capability_factory_and_durable_intent_grants_zero_commands(
    campaign,
):
    assert not hasattr(campaign, "_model_capability_fixture")
    assert not hasattr(campaign, "_consume_process_capability")
    sequence = campaign.publication_sequence("a" * 32, "b" * 32)
    read_intent_index = next(
        index for index, name in enumerate(sequence) if name.endswith("read-intent-000001.json")
    )
    cut = campaign.classify_publication_cut(
        campaign_id="a" * 32,
        session_id="b" * 32,
        present_in_publication_order=sequence[: read_intent_index + 1],
    )
    assert cut["status"] == (
        "READ_INTENT_DURABLE_NO_COMMAND_AUTHORITY_PHASE_B_HANDOFF_REQUIRED"
    )
    assert cut["new_process_device_commands_authorized"] is False
    assert cut["same_process_handoff_implemented"] is False
    assert cut["durable_nodes_authorize_read_commands"] is False


def test_opening_activation_binding_is_unverified_candidate(campaign, complete_model):
    intent = complete_model["intent"]
    assert intent["activation_binding_candidate_sha256"] == "c" * 64
    assert intent["activation_binding_verified"] is False
    assert intent["authority"]["operational_authority"] is False
    alternate = copy.deepcopy(intent)
    alternate["activation_binding_candidate_sha256"] = "f" * 64
    validated = campaign.validate_opening_intent(
        alternate, campaign.canonical_bytes(alternate)
    )
    assert validated["activation_binding_verified"] is False
    assert validated["authority"]["operational_authority"] is False
    forged = copy.deepcopy(intent)
    forged["activation_binding_verified"] = True
    with expect_raises(campaign.CampaignV1Error, match="semantics"):
        campaign.validate_opening_intent(forged, campaign.canonical_bytes(forged))


def test_campaign_binding_keeps_same_process_handoff_unresolved(
    campaign, complete_model
):
    binding = complete_model["binding"]
    assert binding["same_process_handoff_required"] is True
    assert binding["same_process_handoff_implemented"] is False
    assert binding["durable_nodes_authorize_read_commands"] is False
    assert binding["total_opening_to_read_freshness_proven"] is False
    forged = copy.deepcopy(binding)
    forged["same_process_handoff_implemented"] = True
    with expect_raises(campaign.CampaignV1Error, match="semantics"):
        campaign.validate_campaign_binding(
            forged,
            campaign.canonical_bytes(forged),
            complete_model["intent"],
            complete_model["intent_raw"],
            complete_model["result"],
            complete_model["result_raw"],
            complete_model["evidence"],
            complete_model["serial"],
            complete_model["forward"],
        )


def test_clock_reboot_reversal_and_large_skew_rejected(campaign, complete_model):
    binding = complete_model["clock"]
    sample = complete_model["clock_sample"]
    for mutation in (
        {"host_boot_id_sha256": "f" * 64},
        {"boottime_ns": binding["boottime_origin_ns"] - 1},
        {"monotonic_ns": binding["monotonic_origin_ns"] - 1},
        {"reversed": True},
        {
            "realtime_ns": sample["realtime_ns"] + 6_000_000_000,
            "projection_skew_ns": 6_000_000_000,
        },
    ):
        forged = {**sample, **mutation}
        with expect_raises(campaign.CampaignV1Error, match="clock sample"):
            campaign.validate_clock_sample(binding, forged)


def test_logical_opening_receipt_chain_accepts_300_and_rejects_later_offsets(
    campaign, complete_model
):
    def evidence_with_last_offset(offset):
        evidence = dict(complete_model["evidence"])
        predecessor = campaign.sha256_bytes(complete_model["intent_raw"])
        for ordinal in range(1, 7):
            receipt_name = f"cmd-{ordinal:02d}.receipt.json"
            receipt = campaign.parse_canonical_json(
                evidence[receipt_name],
                "logical-window receipt",
                campaign.OPENING_RECEIPT_MAX_BYTES,
            )
            logical_time = (
                complete_model["intent"]["created_at"]
                + (offset if ordinal == 6 else ordinal)
            )
            for key in (
                "execution_started_at",
                "execution_completed_at",
                "return_retained_at",
                "receipt_published_at",
            ):
                receipt[key] = logical_time
            receipt["predecessor_sha256"] = predecessor
            evidence[receipt_name] = campaign.canonical_bytes(receipt)
            predecessor = campaign.sha256_bytes(evidence[receipt_name])
        return evidence

    campaign.validate_opening_evidence(
        intent=complete_model["intent"],
        intent_raw=complete_model["intent_raw"],
        evidence=evidence_with_last_offset(300),
        selected_serial=complete_model["serial"],
    )
    for offset in (301, 172_806):
        with expect_raises(campaign.CampaignV1Error):
            campaign.validate_opening_evidence(
                intent=complete_model["intent"],
                intent_raw=complete_model["intent_raw"],
                evidence=evidence_with_last_offset(offset),
                selected_serial=complete_model["serial"],
            )


def test_server_and_usb_receipts_fail_closed(campaign, complete_model):
    bad_server = copy.deepcopy(complete_model["server"])
    bad_server["provenance_proven"] = False
    with expect_raises(campaign.CampaignV1Error, match="provenance"):
        campaign.validate_adb_server_receipt(bad_server)
    source = complete_model["result"]["source_identity"]
    bad_usb = copy.deepcopy(complete_model["usb"])
    bad_usb["event_monitor_overflow"] = True
    with expect_raises(campaign.CampaignV1Error, match="generation"):
        campaign.validate_usb_generation(bad_usb, source)
    bad_usb = copy.deepcopy(complete_model["usb"])
    bad_usb["topology_sha256"] = "f" * 64
    with expect_raises(campaign.CampaignV1Error, match="generation"):
        campaign.validate_usb_generation(bad_usb, source)


def test_phase_a_explicitly_does_not_claim_server_usb_clock_or_executor(campaign):
    plan = campaign.render_plan()
    for gate in (
        "adb_server_provenance_proven",
        "usb_generation_proven",
        "trusted_clock_proven",
        "executor_implemented",
        "cross_code_coordination_active",
    ):
        assert plan["gates"][gate] is False
    assert "ADB-server-provenance" in plan["unresolved_activation_gates"]


def test_current_recovery_scanner_rejects_future_opening_and_binding(tmp_path):
    recovery = load_module(CURRENT_RECOVERY, "_current_recovery_campaign_reject_test")
    for future_name, is_directory in (("opening-v1", True), ("campaign-binding.json", False)):
        root = tmp_path / future_name.replace(".", "-")
        root.mkdir(mode=0o700)
        if is_directory:
            (root / future_name).mkdir(mode=0o700)
        else:
            (root / future_name).write_bytes(b"{}\n")
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with expect_raises(recovery.RecoveryV1Error, match="campaign or foreign"):
                recovery._require_preinstall_leaf(descriptor, b"core", b"manifest\n")
        finally:
            os.close(descriptor)


def test_status_and_gate_normalization_only(campaign):
    source = SOURCE.read_bytes()
    baseline = campaign.normalized_source_sha256(source)
    assert baseline == campaign.EXPECTED_SELF_NORMALIZED_SHA256
    rotated = source.replace(
        b"CAMPAIGN_V1_QUALIFIED = False", b"CAMPAIGN_V1_QUALIFIED = True", 1
    )
    assert campaign.normalized_source_sha256(rotated) == baseline
    logic_mutation = source.replace(b"READ_EVIDENCE_RESERVATION_BYTES = 512", b"READ_EVIDENCE_RESERVATION_BYTES = 511", 1)
    assert campaign.normalized_source_sha256(logic_mutation) != baseline
    full_rotation = source.replace(
        campaign.EXPECTED_CORE_SHA256.encode(), b"f" * 64, 1
    ).replace(b"EXPECTED_CORE_SIZE = 162_875", b"EXPECTED_CORE_SIZE = 162_876", 1)
    assert campaign.normalized_source_sha256(full_rotation) == baseline
    logic_identity_mutation = source.replace(
        campaign.EXPECTED_CORE_NORMALIZED_SHA256.encode(), b"e" * 64, 1
    )
    assert campaign.normalized_source_sha256(logic_identity_mutation) != baseline


_PARAMETER_CASES = {
    "test_opening_authority_is_unverified_nonbankable_requirement": (
        {
            "field": "fresh_direct_attended_post_activation_required",
            "value": False,
        },
        {"field": "requirement_verified_in_phase_a", "value": True},
        {"field": "preactivation_consent_accepted", "value": True},
        {"field": "standing_consent_accepted", "value": True},
        {"field": "reusable", "value": True},
        {"field": "operational_authority", "value": True},
    ),
}


def _invoke_contract_test(function, parameters):
    signature = inspect.signature(function)
    with tempfile.TemporaryDirectory(prefix="s20-campaign-v1-test-") as temporary:
        fixtures = {
            "campaign": CAMPAIGN,
            "complete_model": complete_model(CAMPAIGN),
            "tmp_path": Path(temporary),
            **parameters,
        }
        arguments = []
        for name in signature.parameters:
            if name not in fixtures:
                raise AssertionError(f"unknown unittest fixture {name}")
            arguments.append(fixtures[name])
        function(*arguments)


class CampaignV1ContractTests(unittest.TestCase):
    """Stdlib runner for the 32 methods / 37 hostile model cases."""


def _make_unittest_method(function):
    def method(self):
        cases = _PARAMETER_CASES.get(function.__name__, ({},))
        for index, parameters in enumerate(cases):
            with self.subTest(case=index, **parameters):
                _invoke_contract_test(function, parameters)

    method.__name__ = function.__name__
    method.__doc__ = function.__doc__
    return method


_CONTRACT_TEST_FUNCTIONS = tuple(
    value
    for name, value in tuple(globals().items())
    if name.startswith("test_") and inspect.isfunction(value)
)
_EXPANDED_CASE_COUNT = sum(
    len(_PARAMETER_CASES.get(function.__name__, ({},)))
    for function in _CONTRACT_TEST_FUNCTIONS
)
if len(_CONTRACT_TEST_FUNCTIONS) != 32 or _EXPANDED_CASE_COUNT != 37:
    raise RuntimeError("stdlib conversion lost a hostile model test case")
for _function in _CONTRACT_TEST_FUNCTIONS:
    setattr(
        CampaignV1ContractTests,
        _function.__name__,
        _make_unittest_method(_function),
    )


if __name__ == "__main__":
    unittest.main()
