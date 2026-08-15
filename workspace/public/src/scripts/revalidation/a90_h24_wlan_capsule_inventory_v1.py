#!/usr/bin/env python3
"""Generate the host-only H24 WLAN capsule dependency inventory.

This generator binds only public repository evidence.  It deliberately emits
UNPROVED for opaque binary/runtime edges that the H24 build manifest does not
bind.  It performs no device, transport, or private-input operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
DEFAULT_OUTPUT = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
    / "inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
)

SOURCE_RELS = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml",
    "workspace/public/src/native-init/helpers/a90_android_execns_probe.c",
    "workspace/public/src/native-init/v724/90_main.inc.c",
    "docs/archive/legacy/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V2033_WLANMDSP_TFTP_TRANSFER_COMPLETION_GAP_2026-06-04.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V2117_DUAL_RFS_LEAF_ANDROID_IDENTITY_HANDOFF_2026-06-05.md",
)

EXPECTED_SOURCE_SHA256 = {
    SOURCE_RELS[0]: "40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f",
    SOURCE_RELS[1]: "4e68735fa2acc06fa4c101d8dbab6380d7785c4d9c7edfe47448ab26031b57e2",
    SOURCE_RELS[2]: "2a6863c0fd5f1dc2559ccee45031e389c956d6e094d8602364fd1875b919128f",
    SOURCE_RELS[3]: "0212b18b2f76a88247300a55f9c670b18de15f69a488c62f1167304b3de1ebc2",
    SOURCE_RELS[4]: "b6a61a6b259b4dd29606bc29ed3f788c7479b0289a32f8b6e4252e2422aa2821",
    SOURCE_RELS[5]: "07dac305ae652c451135606d62f69479af756c3958e5e5798574dc6c426f71f3",
    SOURCE_RELS[6]: "345428d2284919776b67a3a88c40f9a4986002956a2f9d5488efe2c48dd033e3",
    SOURCE_RELS[7]: "caad3e832038f28de2febd4b2dd0742f093ab0b035d4b1d6db59032e595e20d2",
    SOURCE_RELS[8]: "a3f7b5b81c9cf9861c1e7a039d6f0f4102726c71cca8585e1228194ab6c59914",
}

COMMON_COMPOSITE_CLEANUP = {
    "method": "process-group TERM 1s, KILL 1s, direct wait, PGID absence",
    "evidenceState": "source-derived",
    "sourceAnchor": "a90_android_execns_probe.c:45424-45555",
    "completeDescendantClosure": False,
}


def _identity(
    uid: int,
    gid: int,
    groups: list[int],
    capabilities: list[str] | None,
    capability_status: str,
    note: str,
) -> dict[str, Any]:
    return {
        "uid": uid,
        "gid": gid,
        "supplementaryGroups": groups,
        "capabilities": capabilities,
        "capabilityStatus": capability_status,
        "note": note,
        "evidenceState": "source-derived",
    }


SYSTEM_MANAGER = _identity(
    1000,
    1000,
    [1000, 3009],
    None,
    "UNPROVED",
    "Source prints expected none but does not apply an explicit empty capset.",
)
QRTR = _identity(
    2906,
    2906,
    [],
    ["CAP_NET_BIND_SERVICE"],
    "SOURCE_DERIVED",
    "Capability is retained and raised ambient.",
)
PD_MAPPER = _identity(
    1000,
    1000,
    [],
    ["CAP_NET_BIND_SERVICE"],
    "SOURCE_DERIVED",
    "Capability is retained and raised ambient.",
)
ROOT_INIT = _identity(
    0,
    0,
    [],
    None,
    "UNPROVED",
    "H24 selects android-init-root mode; no exact capability reduction is proved.",
)
SYSTEM_EMPTY_CAPS = _identity(
    1000,
    1000,
    [],
    [],
    "SOURCE_DERIVED",
    "Source applies an explicit empty capability set.",
)
CNSS_DIAG = _identity(
    1000,
    1000,
    [1000, 1010, 3003, 1015, 1023, 2002],
    [],
    "SOURCE_DERIVED",
    "Source applies an explicit empty capability set.",
)
CNSS_DAEMON = _identity(
    1000,
    1000,
    [3003, 3005, 1010],
    ["CAP_NET_ADMIN"],
    "SOURCE_DERIVED",
    "Only CAP_NET_ADMIN is retained and raised ambient.",
)


COMPOSITE_CALL_RE = re.compile(
    r"composite_child_init\(&children\[child_count\+\+\],\s*"
    r'"([^"]+)",\s*"([^"]+)",\s*'
    r"(COMPOSITE_ID_[A-Z0-9_]+)\);"
)


def _between_once(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    return text[start_index : text.index(end, start_index + len(start))]


def _composite_calls(text: str) -> list[tuple[str, str, str]]:
    return COMPOSITE_CALL_RE.findall(text)


def derive_selected_composite_graph(
    helper_text: str | None = None,
) -> list[tuple[str, str, str]]:
    """Parse the exact H24-selected construction branches from helper source.

    This is intentionally a narrow, fail-closed parser for the frozen H24
    route.  It does not infer a graph from the published order string.
    """

    if helper_text is None:
        helper_text = (ROOT / SOURCE_RELS[1]).read_text()
    function = _between_once(
        helper_text,
        "static int run_wifi_companion_start_only_guarded",
        "static int run_wifi_companion_hal_order_start_only_guarded",
    )

    first_pair = _between_once(
        function,
        "    if (!android_order_pre_cnss_provider_observer &&\n"
        "        with_service_manager &&",
        "    if (!android_order_pre_cnss_provider_observer &&\n"
        "        !peripheral_manager_node_parity)",
    )
    first_pair = first_pair[: first_pair.index("        if (with_vnd_service_manager)")]

    qrtr_and_rfs = _between_once(
        function,
        "    if (!android_order_pre_cnss_provider_observer &&\n"
        "        !peripheral_manager_node_parity) {",
        "        if (qrtr_first_service_manager) {",
    )
    firmware_branch = (
        "        if (android_order_post_sysmon_observer ||\n"
        "            wlan_pd_firmware_serve_gate) {"
    )
    qrtr_only = qrtr_and_rfs[: qrtr_and_rfs.index(firmware_branch)]
    firmware_start = qrtr_and_rfs.index(firmware_branch)
    firmware_true = qrtr_and_rfs[
        firmware_start : qrtr_and_rfs.index("        } else {", firmware_start)
    ]

    service_object = _between_once(
        function,
        "        if (wlan_pd_service_window_trigger || "
        "wlan_pd_service_object_visible_trigger) {",
        "        if (wlan_pd_pm_service_window_trigger || "
        "wlan_pd_service_object_visible_trigger) {",
    )
    peripheral_manager = _between_once(
        function,
        "        if (wlan_pd_pm_service_window_trigger || "
        "wlan_pd_service_object_visible_trigger) {",
        "        if (!post_sysmon_observer) {",
    )
    peripheral_manager = peripheral_manager[
        : peripheral_manager.index("            if (wlan_pd_pm_service_window_trigger) {")
    ]
    cnss_tail = _between_once(
        function,
        "        if (!post_sysmon_observer) {",
        "    if (!android_order_pre_cnss_provider_observer &&\n"
        "        (cnss_first_delayed_service_manager || service74_gated_any)) {",
    )
    # H24 leaves A90_WIFI_TEST_BOOT_MACLOADER_PRE_CNSS at its source default 0.
    cnss_calls = [call for call in _composite_calls(cnss_tail) if call[0] != "macloader"]

    selected = (
        _composite_calls(first_pair)
        + _composite_calls(qrtr_only)
        + _composite_calls(firmware_true)
        + _composite_calls(service_object)
        + _composite_calls(peripheral_manager)
        + cnss_calls
    )
    if len(selected) != 13 or len({role for role, _, _ in selected}) != 11:
        raise ValueError("source-derived H24 graph is not 13 entries / 11 roles")
    return selected


def _component(
    instance_id: str,
    order: int,
    role: str,
    executable: str,
    argv: list[str],
    predicate: str,
    identity: dict[str, Any],
    ownership_plane: str,
    source_anchors: list[str],
    lifetime_note: str = "required alive and observable for persistent handoff",
) -> dict[str, Any]:
    return {
        "instanceId": instance_id,
        "order": order,
        "role": role,
        "kind": "composite-child",
        "executable": executable,
        "argv": argv,
        "launchPredicate": predicate,
        "identity": identity,
        "ownershipPlane": ownership_plane,
        "lifetime": {
            "requirement": lifetime_note,
            "evidenceState": "source-derived",
            "hardwareNecessity": "UNPROVED",
        },
        "cleanup": COMMON_COMPOSITE_CLEANUP,
        "sourceAnchors": source_anchors,
        "opaqueRuntimeDependencyStatus": "UNPROVED",
    }


def components(helper_text: str | None = None) -> list[dict[str, Any]]:
    first_pair = (
        "!android_order_pre_cnss_provider_observer && with_service_manager && "
        "!qrtr_first_service_manager && !cnss_first_delayed_service_manager && "
        "!service74_gated_any"
    )
    qrtr_outer = (
        "!android_order_pre_cnss_provider_observer && "
        "!peripheral_manager_node_parity"
    )
    service_object = (
        "wlan_pd_service_window_trigger || "
        "wlan_pd_service_object_visible_trigger"
    )
    pm_object = (
        "wlan_pd_pm_service_window_trigger || "
        "wlan_pd_service_object_visible_trigger"
    )
    described = [
        _component("servicemanager#1", 1, "servicemanager", "/system/bin/servicemanager", ["/system/bin/servicemanager"], first_pair, SYSTEM_MANAGER, "binder-registry", ["a90_android_execns_probe.c:58654-58666", "a90_android_execns_probe.c:7139-7175"]),
        _component("hwservicemanager#1", 2, "hwservicemanager", "/system/bin/hwservicemanager", ["/system/bin/hwservicemanager"], first_pair, SYSTEM_MANAGER, "binder-registry", ["a90_android_execns_probe.c:58654-58666", "a90_android_execns_probe.c:7139-7175"]),
        _component("qrtr_ns#1", 3, "qrtr_ns", "/vendor/bin/qrtr-ns", ["/vendor/bin/qrtr-ns", "-f"], qrtr_outer, QRTR, "qrtr-pd-rfs", ["a90_android_execns_probe.c:58674-58679", "a90_android_execns_probe.c:6834-6845", "a90_android_execns_probe.c:43679-43682"]),
        _component("pd_mapper#1", 4, "pd_mapper", "/vendor/bin/pd-mapper", ["/vendor/bin/pd-mapper"], f"{qrtr_outer} && wlan_pd_firmware_serve_gate", PD_MAPPER, "qrtr-pd-rfs", ["a90_android_execns_probe.c:58680-58693", "a90_android_execns_probe.c:6929-6940"]),
        _component("rmt_storage#1", 5, "rmt_storage", "/vendor/bin/rmt_storage", ["/vendor/bin/rmt_storage"], f"{qrtr_outer} && wlan_pd_firmware_serve_gate", ROOT_INIT, "qrtr-pd-rfs", ["a90_android_execns_probe.c:58680-58693", "a90_android_execns_probe.c:6848-6902"]),
        _component("tftp_server#1", 6, "tftp_server", "/vendor/bin/tftp_server", ["/vendor/bin/tftp_server"], f"{qrtr_outer} && wlan_pd_firmware_serve_gate", ROOT_INIT, "qrtr-pd-rfs", ["a90_android_execns_probe.c:58680-58693", "a90_android_execns_probe.c:6905-6926"]),
        _component("servicemanager#2", 7, "servicemanager", "/system/bin/servicemanager", ["/system/bin/servicemanager"], service_object, SYSTEM_MANAGER, "binder-registry", ["a90_android_execns_probe.c:58722-58735", "a90_android_execns_probe.c:7139-7175"]),
        _component("hwservicemanager#2", 8, "hwservicemanager", "/system/bin/hwservicemanager", ["/system/bin/hwservicemanager"], service_object, SYSTEM_MANAGER, "binder-registry", ["a90_android_execns_probe.c:58722-58735", "a90_android_execns_probe.c:7139-7175"]),
        _component("vndservicemanager#1", 9, "vndservicemanager", "/vendor/bin/vndservicemanager", ["/vendor/bin/vndservicemanager", "/dev/vndbinder"], service_object, SYSTEM_MANAGER, "binder-registry", ["a90_android_execns_probe.c:58722-58735", "a90_android_execns_probe.c:43674-43677"]),
        _component("pm_proxy_helper#1", 10, "pm_proxy_helper", "/vendor/bin/pm_proxy_helper", ["/vendor/bin/pm_proxy_helper"], pm_object, SYSTEM_EMPTY_CAPS, "peripheral-manager-provider", ["a90_android_execns_probe.c:58737-58745", "a90_android_execns_probe.c:6972-6981"]),
        _component("per_mgr#1", 11, "per_mgr", "/vendor/bin/pm-service", ["/vendor/bin/pm-service"], pm_object, SYSTEM_EMPTY_CAPS, "peripheral-manager-provider", ["a90_android_execns_probe.c:58737-58745", "a90_android_execns_probe.c:6972-7005"], "required alive and observable; requests I/O priority RT/4"),
        _component("cnss_diag#1", 12, "cnss_diag", "/vendor/bin/cnss_diag", ["/vendor/bin/cnss_diag", "-q", "-f", "-t", "HELIUM"], "!post_sysmon_observer", CNSS_DIAG, "diagnostic", ["a90_android_execns_probe.c:58753-58757", "a90_android_execns_probe.c:6699-6753"]),
        _component("cnss_daemon#1", 13, "cnss_daemon", "/vendor/bin/cnss-daemon", ["/vendor/bin/cnss-daemon", "-n", "-l"], "!post_sysmon_observer && !service74_gated_peripheral_manager_provider_first_cnss", CNSS_DAEMON, "wcnss-wmi-control", ["a90_android_execns_probe.c:58753-58769", "a90_android_execns_probe.c:6630-6697", "a90_android_execns_probe.c:43660-43664"]),
    ]
    derived = derive_selected_composite_graph(helper_text)
    if len(described) != len(derived):
        raise ValueError("source-derived graph and component metadata differ in length")
    for component, (role, executable, composite_identity) in zip(described, derived):
        if (component["role"], component["executable"]) != (role, executable):
            raise ValueError(
                "source-derived graph and component metadata disagree at "
                f"order {component['order']}"
            )
        component["compositeIdentity"] = composite_identity
        component["constructionEvidence"] = "source-parsed-selected-branch"
    return described


def auxiliary_components() -> list[dict[str, Any]]:
    return [
        {
            "instanceId": "property-service-shim#1",
            "role": "property-service-shim",
            "kind": "helper-managed-child",
            "executable": "forked helper body",
            "argv": [],
            "launchPredicate": (
                "cfg->property_root != NULL && "
                "is_wifi_companion_any_start_only_mode(cfg->mode) && "
                "cfg->allow_wifi_companion_start_only"
            ),
            "selectedPredicateEvaluation": {
                "propertyRoot": "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__",
                "mode": "wifi-companion-wlan-pd-service-object-visible-trigger-start-only",
                "allowWifiCompanionStartOnly": True,
                "result": True,
            },
            "launchContractState": "SOURCE_DERIVED_SELECTED_BRANCH",
            "identity": {
                "status": "UNPROVED",
                "note": "Inherits root helper identity; no identity/capability normalization.",
                "evidenceState": "source-derived",
            },
            "ownershipPlane": "property-write-compatibility",
            "interface": "/dev/socket/property_service AF_UNIX; SETPROP/SETPROP2 bounded ACK protocol",
            "lifetime": "poll loop until stop or 4096 requests; start mandatory, later liveness not equivalent to composite children",
            "cleanup": "drain, direct TERM 500ms, KILL 500ms, wait, close record FD, unlink socket",
            "sourceAnchors": ["a90_android_execns_probe.c:60957-60986", "a90_android_execns_probe.c:61126-61262", "a90_android_execns_probe.c:61264-61500"],
            "opaqueRuntimeDependencyStatus": "UNPROVED",
        },
        {
            "instanceId": "modem-holder#1",
            "role": "modem-holder",
            "kind": "helper-managed-child",
            "executable": "forked helper body",
            "argv": [],
            "launchPredicate": (
                "wlan_pd_firmware_serve_gate && "
                "(!wlan_pd_service_object_visible_trigger || "
                "wlan_pd_service_object_provider_seen)"
            ),
            "selectedPredicateEvaluation": {
                "wlanPdFirmwareServeGate": True,
                "wlanPdServiceObjectVisibleTrigger": True,
                "requiresProviderSeen": True,
            },
            "launchContractState": "SOURCE_DERIVED_SELECTED_BRANCH",
            "identity": {
                "status": "UNPROVED",
                "note": "Inherits root helper identity; no identity/capability normalization.",
                "evidenceState": "source-derived",
            },
            "ownershipPlane": "device-lifetime",
            "interface": "holds /dev/subsys_modem open indefinitely",
            "lifetime": "new session/chroot; persistent readiness requires direct PID alive",
            "cleanup": "process-group TERM 3s, KILL 10s, wait, close record FD, unlink projected node",
            "sourceAnchors": ["a90_android_execns_probe.c:29011-29266", "a90_android_execns_probe.c:59754-59767", "a90_android_execns_probe.c:58077-58099"],
            "opaqueRuntimeDependencyStatus": "UNPROVED",
        },
        {
            "instanceId": "wifi-helper#1",
            "role": "wifi-helper",
            "kind": "topology-owner",
            "executable": "/bin/a90_android_execns_probe",
            "argv": [
                "/bin/a90_android_execns_probe",
                "--system-root", "/mnt/system/system",
                "--vendor-block", "/dev/block/sda29",
                "--vendor-fstype", "ext4",
                "--mode", "wifi-companion-wlan-pd-service-object-visible-trigger-start-only",
                "--result-output-path", "/cache/native-init-wifi-test-boot-v2812-helper.result",
                "--timeout-sec", "120",
                "--property-root", "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__",
                "--null-device-mode", "dev-null",
                "--android-selinux-context-mode", "service-defaults",
                "--linkerconfig-mode", "copy-real",
                "--linkerconfig-source", "/cache/bin/a90_real_ld.config.txt",
                "--apex-libraries-source", "/cache/bin/a90_real_apex.libraries.config.txt",
                "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
                "--allow-wifi-companion-start-only",
                "--allow-cnss-start-only",
                "--allow-service-manager-start-only",
                "--allow-wlan-pd-service-object-visible-trigger",
                "--persistent-handoff",
                "--handoff-ready-output-path", "/cache/native-init-wifi-test-boot-v2812.ready",
            ],
            "environment": [
                "PATH=/bin:/cache/bin:/system/bin:/vendor/bin",
                "HOME=/",
                "TERM=vt100",
            ],
            "launchPredicate": (
                "A90_WIFI_TEST_BOOT=1 && A90_WIFI_TEST_BOOT_SUPERVISE_HELPER=0 && "
                "A90_WIFI_PERSISTENT_HANDOFF_V1=1 && disable-path-absent"
            ),
            "launchContract": {
                "tag": "wifi-v1393-test-boot",
                "stdioMode": "A90_RUN_STDIO_LOG_APPEND",
                "logPath": "/cache/native-init-wifi-test-boot-v2812.log",
                "setsid": True,
                "ignoreHupPipe": True,
                "killProcessGroup": True,
                "cancelable": False,
                "timeoutMs": 0,
                "stopTimeoutMs": 1000,
            },
            "launchContractState": "SOURCE_DERIVED_SELECTED_BRANCH",
            "identity": {"status": "UNPROVED", "note": "Exact post-fork privilege envelope is not a capsule contract.", "evidenceState": "source-derived"},
            "ownershipPlane": "backend-lifecycle-health-cleanup",
            "lifetime": "long-lived supervisor for composite children, shim, and holder",
            "cleanup": "current source cleanup is not a proved cgroup/descendant closure",
            "sourceAnchors": [
                "v724/90_main.inc.c:5106-5301",
                "v724/90_main.inc.c:5660-5765",
                "a90_android_execns_probe.c:3540-3605",
                "a90_android_execns_probe.c:58048-58099",
                "a90_android_execns_probe.c:58460-59800",
            ],
            "opaqueRuntimeDependencyStatus": "UNPROVED",
        },
    ]


def dependency_gates() -> list[dict[str, Any]]:
    gates = (
        ("H0D01", "exact-elf-closure", "OFFLINE_STATIC", "Exact bytes, SHA256, ELF class/interpreter, full DT_NEEDED closure, and every library byte are not bound for all eleven opaque roles.", "Exact regular-file manifest, recursive ELF closure, negative fixture, and independent review."),
        ("H0D02", "dynamic-dispatch", "HYBRID_STATIC_AND_OBSERVATION", "dlopen, executable dispatch, linker namespace, APEX aliases, and plugin/config-selected code paths are incomplete.", "Static dispatch inventory plus bounded runtime trace that fails on an unbound load or exec."),
        ("H0D03", "configuration", "HYBRID_STATIC_AND_OBSERVATION", "Every config, rc fragment, environment input, default, and read lifetime is not enumerated.", "Static input manifest plus bounded read trace and missing/extra/default negative fixtures."),
        ("H0D04", "property-read-write", "RUNTIME_OBSERVATION_AND_ABLATION", "Per-role property keys, contexts, defaults, reads, writes, ACK callers, and required semantics are not closed.", "Per-role bounded trace followed by one-factor property ablation; accept only PROPERTY_ABSENT_PROVED or PROPERTY_FINITE_SEED_PROVED."),
        ("H0D05", "binder", "RUNTIME_OBSERVATION_AND_ABLATION", "Per-role Binder device, context manager, service name, transaction, direction, and lifetime are not closed.", "Per-role transaction trace and one-factor manager/provider ablation with private/global endpoint negatives."),
        ("H0D06", "qrtr-qmi", "RUNTIME_OBSERVATION_AND_ABLATION", "QRTR service IDs, QMI clients/messages, producer-consumer edges, and cleanup ownership are not closed.", "Bounded QRTR/QMI message and service observation plus one-factor role ablation and cleanup proof."),
        ("H0D07", "device-kernel", "HYBRID_STATIC_AND_OBSERVATION", "Every device node, ioctl, sysfs/proc read/write, socket family/type/protocol, and kernel-object lifetime is not closed.", "Static syscall/path inventory plus bounded runtime observation, lifetime accounting, and forbidden-surface negatives."),
        ("H0D08", "firmware-rfs", "RUNTIME_OBSERVATION_AND_ABLATION", "Every firmware/RFS/persist path, served object, read/write direction, ownership, and cleanup rule is not closed.", "Bounded request/object trace plus one-factor RFS role ablation and exact residue cleanup proof."),
        ("H0D09", "writable-output", "RUNTIME_OBSERVATION", "All files, sockets, logs, caches, rename/fsync activity, bounds, and no-residue cleanup are not closed.", "Bounded runtime output trace with byte/rate limits and exact post-stop residue negatives."),
        ("H0D10", "sd-free-provenance", "SPLIT_PREEXECUTION_AND_POST_ABLATION_STATIC_FREEZE", "No public deterministic SD-free bootstrap superset is yet bound for a future corrected baseline, and the final retained binary, library, config, property seed, firmware/RFS input, and public metadata set lacks one deterministic SD-free compatibility-root manifest.", "Before any execution, prove one public deterministic no-SD bootstrap superset without copying the private whole snapshot; after the retained set is known, freeze one minimal no-SD compatibility-root manifest and provenance review."),
    )
    return [
        {
            "gateId": gate_id,
            "surface": surface,
            "retirementClass": retirement_class,
            "status": "UNPROVED",
            "blocker": blocker,
            "retirementEvidence": retirement_evidence,
            "wpH02DesignBlocking": False,
            "preExecutionRequirement": (
                "RETIRE_RELEVANT_ROW_BEFORE_EXECUTION"
                if retirement_class == "OFFLINE_STATIC"
                else "RETIRE_STATIC_HALF_FOR_RELEVANT_ROW_BEFORE_EXECUTION"
                if retirement_class == "HYBRID_STATIC_AND_OBSERVATION"
                else "BOUNDED_EXECUTION_PRODUCES_RETIREMENT_EVIDENCE_NOT_A_PRECONDITION"
                if retirement_class in {
                    "RUNTIME_OBSERVATION_AND_ABLATION",
                    "RUNTIME_OBSERVATION",
                }
                else "PROVE_SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_BEFORE_EXECUTION_THEN_FREEZE_RETAINED_SET_AFTER_ABLATION"
            ),
            **(
                {
                    "preExecutionHalf": {
                        "status": "UNPROVED",
                        "requiredTerminal": "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED",
                        "rule": "No future baseline or ablation identity may read the SD property snapshot or a copied private whole snapshot.",
                    },
                    "postAblationHalf": {
                        "status": "UNPROVED",
                        "acceptedTerminals": [
                            "PROPERTY_ABSENT_PROVED",
                            "PROPERTY_FINITE_SEED_PROVED",
                        ],
                        "rule": "Freeze only the retained-set minimum after one-factor evidence; the bootstrap superset is not production-minimality proof.",
                    },
                }
                if gate_id == "H0D10"
                else {}
            ),
            "liveExecutionAuthorized": False,
            "optionCImplementationBlocking": True,
        }
        for gate_id, surface, retirement_class, blocker, retirement_evidence in gates
    ]


def _pin(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"WP-H0-1 source must be a lexical regular file: {rel}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SOURCE_SHA256[rel]:
        raise ValueError(f"frozen WP-H0-1 source drift: {rel}")
    return {
        "path": rel,
        "bytes": len(data),
        "sha256": digest,
    }


def _require_source_contract() -> None:
    helper = (ROOT / SOURCE_RELS[1]).read_text()
    main = (ROOT / SOURCE_RELS[2]).read_text()
    manifest = (ROOT / SOURCE_RELS[0]).read_text()
    required_manifest = (
        "-DA90_WIFI_TEST_BOOT=1",
        "-DA90_WIFI_TEST_BOOT_SUPERVISE_HELPER=0",
        "-DA90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER=1",
        "-DA90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE=1",
        "-DA90_WIFI_PERSISTENT_HANDOFF_V1=1",
        "-DA90_WIFI_TEST_BOOT_HELPER_RESULT=\"/cache/native-init-wifi-test-boot-v2812-helper.result\"",
        "-DA90_WIFI_PERSISTENT_HANDOFF_READY=\"/cache/native-init-wifi-test-boot-v2812.ready\"",
        "-DA90_V1393_WIFI_TEST_TIMEOUT_SEC=\"120\"",
        "-DA90_V1393_WIFI_TEST_PROPERTY_ROOT=\"/mnt/sdext/a90/private-property-v317/v726/dev/__properties__\"",
    )
    required_helper = (
        '"servicemanager",\n                             "/system/bin/servicemanager"',
        '"hwservicemanager",\n                             "/system/bin/hwservicemanager"',
        '"qrtr_ns",\n                             "/vendor/bin/qrtr-ns"',
        '"pd_mapper",\n                                 "/vendor/bin/pd-mapper"',
        '"rmt_storage",\n                                 "/vendor/bin/rmt_storage"',
        '"tftp_server",\n                                 "/vendor/bin/tftp_server"',
        '"vndservicemanager",\n                                 "/vendor/bin/vndservicemanager"',
        '"pm_proxy_helper",\n                                 "/vendor/bin/pm_proxy_helper"',
        '"per_mgr",\n                                 "/vendor/bin/pm-service"',
        '"cnss_diag",\n                                 "/vendor/bin/cnss_diag"',
        '"cnss_daemon",\n                                     "/vendor/bin/cnss-daemon"',
        "load_precompiled_policy_for_pm_observer(paths, stdout_buf)",
        'bind_rw("/sys/fs/selinux", paths->sys_fs_selinux)',
        'write(enforce_fd, "0", 1)',
    )
    required_main = (
        '#define A90_V1393_WIFI_TEST_HELPER "/bin/a90_android_execns_probe"',
        '#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-service-object-visible-trigger-start-only"',
        '"--allow-wifi-companion-start-only"',
        '"--allow-cnss-start-only"',
        '"--allow-service-manager-start-only"',
        '"--allow-wlan-pd-service-object-visible-trigger"',
        '"--persistent-handoff"',
        '"--handoff-ready-output-path"',
        '.tag = "wifi-v1393-test-boot"',
        ".setsid = true",
        ".kill_process_group = true",
        ".timeout_ms = 0",
        ".stop_timeout_ms = 1000",
    )
    for token in required_manifest:
        if token not in manifest:
            raise ValueError(f"H24 manifest contract drift: {token}")
    for token in required_helper:
        if token not in helper:
            raise ValueError(f"H24 helper contract drift: {token}")
    for token in required_main:
        if token not in main:
            raise ValueError(f"H24 native launch contract drift: {token}")
    selected = components(helper)
    if len(selected) != 13 or len({item["role"] for item in selected}) != 11:
        raise ValueError("selected H24 graph is not 13 entries / 11 roles")
    topology_owner = auxiliary_components()[-1]
    if topology_owner["executable"] != "/bin/a90_android_execns_probe":
        raise ValueError("H24 topology-owner executable is not exact")
    if "--allow-qrtr-ns-readback" in topology_owner["argv"]:
        raise ValueError("H24 light-firmware-trace argv incorrectly includes QRTR readback")


def build_inventory() -> dict[str, Any]:
    _require_source_contract()
    helper = (ROOT / SOURCE_RELS[1]).read_text()
    derived_graph = derive_selected_composite_graph(helper)
    selected = components(helper)
    all_components = selected + auxiliary_components()
    return {
        "schema": "a90-h24-wlan-capsule-dependency-inventory-v1",
        "generatedDeterministically": True,
        "scope": {
            "target": "Samsung Galaxy A90 5G only",
            "residentReference": "H24 0.11.192 source-selected route",
            "purpose": "WP-H0-1 public-source dependency inventory and ownership-plane map",
            "doesNotProve": [
                "individual hardware necessity",
                "opaque runtime dependency closure",
                "cold relaunch",
                "Debian station ownership",
                "Option C feasibility",
            ],
        },
        "authority": {
            "tier": "H0",
            "candidateEligible": False,
            "deviceInstallAuthorized": False,
            "d0Authorized": False,
            "d1Authorized": False,
            "f1Authorized": False,
            "handoffAuthorized": False,
            "ufsMutationAuthorized": False,
            "privateInputRead": False,
            "deviceContact": False,
        },
        "sourcePins": [_pin(rel) for rel in SOURCE_RELS],
        "status": {
            "wpH01CompositeGraph": "COMPLETE_SOURCE_PARSED_FROZEN_H24_PATH",
            "wpH01AuxiliaryLaunchContracts": "COMPLETE_SOURCE_BOUND_FROZEN_H24_PATH",
            "wpH01PublicSourceInventory": "COMPLETE_FROZEN_H24_SELECTED_PATH_ONLY",
            "wpH01Overall": "PARTIAL_RUNTIME_CLOSURE_BLOCKED",
            "wpH01OpaqueRuntimeClosure": "BLOCKED_UNPROVED",
            "optionC": "H0_RESEARCH_ONLY_NOT_IMPLEMENTATION_ELIGIBLE",
            "strongestBlocker": "H24 does not bind exact bytes or complete transitive runtime dependencies for the eleven opaque service roles.",
        },
        "counts": {
            "compositeInstances": len(derived_graph),
            "uniqueCompositeRoles": len({role for role, _, _ in derived_graph}),
            "helperManagedChildrenOutsideComposite": 2,
            "topologyOwners": 1,
            "sourceAccountedProcessesBeforeStationPolicy": len(derived_graph) + 3,
        },
        "graphDerivation": {
            "method": "parse selected composite_child_init calls from frozen helper branches",
            "publishedOrderUsedAsAuthority": False,
            "metadataMismatchFailsClosed": True,
            "selectedCompositeTuples": [
                {"role": role, "executable": executable, "identity": identity}
                for role, executable, identity in derived_graph
            ],
        },
        "constructionDefects": {
            "duplicateRoles": {
                "servicemanager": ["servicemanager#1", "servicemanager#2"],
                "hwservicemanager": ["hwservicemanager#1", "hwservicemanager#2"],
            },
            "publishedOrderHidesDuplicates": True,
            "successorRule": "Reject every duplicate role, instance ID, executable identity, or cleanup identity before construction.",
        },
        "components": all_components,
        "ownershipPlanes": [
            {"plane": "backend lifecycle, health, and cleanup", "h24Owner": "native Wi-Fi helper", "optionCRequiredOwner": "Debian PID 1 platform manager", "status": "PROPOSED_UNPROVED"},
            {"plane": "privileged vendor actuation", "h24Owner": "root/native helper plus child identities", "optionCRequiredOwner": "separate non-remote capsule launcher", "status": "PROPOSED_UNPROVED"},
            {"plane": "station scan, association, and DHCP", "h24Owner": "native autoconnect path", "optionCRequiredOwner": "Debian station policy", "status": "UNPROVED"},
            {"plane": "network exposure and application service", "h24Owner": "native handoff plus Debian service", "optionCRequiredOwner": "Debian PID 1", "status": "PROPOSED_UNPROVED"},
            {"plane": "boot rollback and physical recovery", "h24Owner": "boot-only host/native recovery boundary", "optionCRequiredOwner": "unchanged external safety boundary", "status": "PERMANENT_BOUNDARY"},
        ],
        "historicalPublicEvidence": [
            {
                "claim": "A historical cnss-daemon binary was recorded as 95112 bytes with SHA256 bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc.",
                "evidenceState": "observed-historical",
                "h24Applicability": "UNPROVED",
                "source": "NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md",
            },
            {
                "claim": "Historical linker-list resolution included libcutils.so, libnl.so, libc++.so, libqmi_cci.so, libqmi_common_so.so, and libcld80211.so.",
                "evidenceState": "observed-historical",
                "h24Applicability": "UNPROVED",
                "source": "NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md",
            },
            {
                "claim": "Historical cnss-daemon reads included persist.vendor.cnss-daemon.debug_level and persist.vendor.cnss-daemon.kmsg_logging; its mapped flow reached WLFW QMI setup.",
                "evidenceState": "observed-historical",
                "h24Applicability": "UNPROVED",
                "source": "NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md",
            },
            {
                "claim": "Historical tftp_server evidence names readonly wlanmdsp.mbn and readwrite mcfg.tmp RFS paths.",
                "evidenceState": "observed-historical",
                "h24Applicability": "UNPROVED",
                "source": "NATIVE_INIT_V2033_WLANMDSP_TFTP_TRANSFER_COMPLETION_GAP_2026-06-04.md",
            },
            {
                "claim": "Historical Android-observed rmt_storage and tftp_server identities differ from H24's selected root-mode launch path.",
                "evidenceState": "observed-historical",
                "h24Applicability": "IDENTITY_CONFLICT_REQUIRES_RESOLUTION",
                "source": "NATIVE_INIT_V2117_DUAL_RFS_LEAF_ANDROID_IDENTITY_HANDOFF_2026-06-05.md",
            },
        ],
        "dependencyGates": dependency_gates(),
        "nextSequencingConstraint": {
            "wpH02Design": "ALLOWED_H0_ONLY_FROM_THIS_FROZEN_BLOCKER_REGISTRY",
            "beforeWpH02Execution": (
                "Retire the row-specific OFFLINE_STATIC or static half of HYBRID prerequisites; "
                "independently review the bounded observer/ablation mechanism and obtain separate live authority."
            ),
            "beforeOptionCImplementationOrPromotion": (
                "Retire H0D01 through H0D10 with each gate's declared evidence class; "
                "no single offline generation can retire runtime gates."
            ),
            "inputRule": "Private inputs remain outside this unit; any later bounded collection requires separate authority and public-safe metadata handling.",
            "failureRule": "Any unresolved edge keeps Option C H0-only and blocks candidate identity allocation.",
        },
    }


def canonical_text() -> str:
    return json.dumps(build_inventory(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", type=Path, metavar="PATH")
    group.add_argument("--write", type=Path, nargs="?", const=DEFAULT_OUTPUT, metavar="PATH")
    args = parser.parse_args()
    rendered = canonical_text()
    if args.check is not None:
        if args.check.read_text() != rendered:
            raise SystemExit(f"inventory drift: {args.check}")
        return 0
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered)
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
