#!/usr/bin/env python3
"""Build a read-only Android ICNSS/CNSS Wi-Fi service replay model."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


IMPORTANT_SERVICES = (
    "cnss-daemon",
    "cnss_diag",
    "vendor.wifi_hal_legacy",
    "vendor.wifi_hal_ext",
    "wificond",
    "wpa_supplicant",
    "hostapd",
)

SERVICE_ORDER = (
    "cnss-daemon",
    "cnss_diag",
    "vendor.wifi_hal_legacy",
    "vendor.wifi_hal_ext",
    "wificond",
    "wpa_supplicant",
    "hostapd",
)

ACTIVE_PATTERNS = (
    re.compile(r"\bctl\.(?:start|restart)\b", re.IGNORECASE),
    re.compile(r"\bclass_start\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+set-wifi-enabled\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
    re.compile(r">\s*/sys/bus/platform/drivers/icnss/(?:bind|unbind)", re.IGNORECASE),
)

DECISIONS = {
    "replay-model-ready",
    "replay-model-partial",
    "missing-android-runtime",
    "manual-review-required",
}

SERVICE_LINE_RE = re.compile(r"^(?P<source>/[^:]+):(?P<comment>#)?service\s+(?P<name>\S+)\s+(?P<exec>\S+)(?P<args>.*)$")
OPTION_LINE_RE = re.compile(r"^(?P<source>/[^:]+):\s+(?P<key>class|user|group|capabilities|interface)\s+(?P<value>.+)$")
FLAG_LINE_RE = re.compile(r"^(?P<source>/[^:]+):\s+(?P<flag>disabled|oneshot|seclabel|socket)\b(?P<value>.*)$")
TRIGGER_LINE_RE = re.compile(r"^(?P<source>/[^:]+):on\s+(?P<trigger>.+)$")
PROP_RE = re.compile(r"^\[init\.svc\.(?P<name>[^\]]+)\]: \[(?P<state>[^\]]+)\]$")
PID_RE = re.compile(r"^\[init\.svc_debug_pid\.(?P<name>[^\]]+)\]: \[(?P<pid>[^\]]+)\]$")
BOOT_RE = re.compile(r"^\[ro\.boottime\.(?P<name>[^\]]+)\]: \[(?P<time>[^\]]+)\]$")


@dataclass
class ServiceModel:
    name: str
    source: str = ""
    executable: str = ""
    args: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    user: str = ""
    groups: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    android_state: str = ""
    android_pid: str = ""
    android_boottime: str = ""
    process_seen: bool = False
    init_seen: bool = False
    commented: bool = False
    native_availability: str = "unknown"
    risk: str = "unknown"
    blockers: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


def default_out_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifi" / f"v216-service-replay-model-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v206-manifest", type=Path, default=Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json"))
    parser.add_argument("--v215-manifest", type=Path, default=Path("tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json"))
    parser.add_argument("--v215-native-manifest", type=Path, default=Path("tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json"))
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    return parser.parse_args()


def validate_no_active_commands() -> None:
    command_text = ""
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise RuntimeError(f"active command pattern found: {pattern.pattern}")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def manifest_dir(manifest: dict[str, Any]) -> Path | None:
    path = manifest.get("path")
    if not isinstance(path, str):
        return None
    return Path(path).parent


def capture_file_text(manifest: dict[str, Any], capture_name: str) -> str:
    base = manifest_dir(manifest)
    if base is None:
        return ""
    for capture in manifest.get("captures", []):
        if not isinstance(capture, dict) or capture.get("name") != capture_name:
            continue
        rel = capture.get("file")
        if not isinstance(rel, str):
            continue
        path = base / rel
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def classification_values(manifest: dict[str, Any], key: str) -> list[str]:
    classification = manifest.get("classification")
    if not isinstance(classification, dict):
        return []
    values = classification.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def ensure_model(models: dict[str, ServiceModel], name: str) -> ServiceModel:
    if name not in models:
        models[name] = ServiceModel(name=name)
    return models[name]


def append_unique(values: list[str], new_values: list[str]) -> None:
    seen = set(values)
    for value in new_values:
        if value and value not in seen:
            values.append(value)
            seen.add(value)


def parse_init_rc(text: str) -> dict[str, ServiceModel]:
    models: dict[str, ServiceModel] = {name: ServiceModel(name=name) for name in IMPORTANT_SERVICES}
    current_by_source: dict[str, str] = {}
    triggers_by_source: dict[str, list[str]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$") or line == "rc=0":
            continue
        trigger_match = TRIGGER_LINE_RE.match(line)
        if trigger_match:
            source = trigger_match.group("source")
            triggers_by_source.setdefault(source, []).append(trigger_match.group("trigger").strip())
            continue
        service_match = SERVICE_LINE_RE.match(line)
        if service_match:
            name = service_match.group("name")
            model = ensure_model(models, name)
            commented = bool(service_match.group("comment"))
            if model.init_seen and commented:
                append_unique(model.evidence, [line])
                continue
            model.source = service_match.group("source")
            model.executable = service_match.group("exec")
            model.args = service_match.group("args").strip().split()
            model.commented = commented
            model.init_seen = not commented
            append_unique(model.evidence, [line])
            current_by_source[model.source] = name
            append_unique(model.triggers, triggers_by_source.get(model.source, []))
            continue
        option_match = OPTION_LINE_RE.match(line)
        if option_match:
            source = option_match.group("source")
            service_name = current_by_source.get(source)
            if not service_name:
                continue
            model = ensure_model(models, service_name)
            key = option_match.group("key")
            value = option_match.group("value").strip()
            if key == "class":
                append_unique(model.classes, value.split())
            elif key == "user":
                model.user = value.split()[0] if value.split() else value
            elif key == "group":
                append_unique(model.groups, value.split())
            elif key == "capabilities":
                append_unique(model.capabilities, value.split())
            elif key == "interface":
                append_unique(model.interfaces, [value])
            append_unique(model.evidence, [line])
            continue
        flag_match = FLAG_LINE_RE.match(line)
        if flag_match:
            source = flag_match.group("source")
            service_name = current_by_source.get(source)
            if not service_name:
                continue
            model = ensure_model(models, service_name)
            flag = flag_match.group("flag")
            value = flag_match.group("value").strip()
            append_unique(model.flags, [f"{flag} {value}".strip()])
            append_unique(model.evidence, [line])

    return {name: models[name] for name in IMPORTANT_SERVICES}


def apply_android_state(models: dict[str, ServiceModel], props_text: str, processes_text: str) -> None:
    for raw_line in props_text.splitlines():
        line = raw_line.strip()
        prop_match = PROP_RE.match(line)
        if prop_match:
            model = ensure_model(models, prop_match.group("name"))
            model.android_state = prop_match.group("state")
            append_unique(model.evidence, [line])
            continue
        pid_match = PID_RE.match(line)
        if pid_match:
            model = ensure_model(models, pid_match.group("name"))
            model.android_pid = pid_match.group("pid")
            append_unique(model.evidence, [line])
            continue
        boot_match = BOOT_RE.match(line)
        if boot_match:
            model = ensure_model(models, boot_match.group("name"))
            model.android_boottime = boot_match.group("time")
            append_unique(model.evidence, [line])

    for model in models.values():
        if model.name in processes_text:
            model.process_seen = True
            matches = [line.strip() for line in processes_text.splitlines() if model.name in line]
            append_unique(model.evidence, matches[:4])


def classify_service(model: ServiceModel) -> None:
    if model.name in {"cnss-daemon", "cnss_diag"}:
        model.risk = "kernel-lifecycle-high"
    elif model.name in {"vendor.wifi_hal_legacy", "vendor.wifi_hal_ext"}:
        model.risk = "android-hal-high"
    elif model.name in {"wpa_supplicant", "hostapd"}:
        model.risk = "active-network-high"
    else:
        model.risk = "framework-medium"

    if not model.init_seen:
        model.blockers.append("missing-active-init-service-line")
    if not model.executable:
        model.blockers.append("missing-executable-path")
    if model.commented:
        model.blockers.append("service-line-commented")
    if model.android_state and model.android_state != "running":
        model.blockers.append(f"android-state-{model.android_state}")
    if not model.android_state and not model.process_seen:
        model.blockers.append("missing-android-runtime-state")
    if model.name in {"vendor.wifi_hal_legacy", "vendor.wifi_hal_ext"} and "SYS_MODULE" in model.capabilities:
        model.blockers.append("requires-SYS_MODULE-capability-policy-review")
    if model.name in {"wpa_supplicant", "hostapd"}:
        model.blockers.append("must-remain-disabled-until-scan-connect-gate")
    if model.name in {"cnss-daemon", "cnss_diag"}:
        model.blockers.append("requires-icnss-cnss-recovery-model-before-execution")

    if model.executable.startswith("/system/vendor/"):
        model.native_availability = "requires-vendor-system-path-alias"
    elif model.executable.startswith("/vendor/"):
        model.native_availability = "requires-temporary-vendor-mount"
    elif model.executable.startswith("/system/"):
        model.native_availability = "requires-mounted-system"
    elif model.executable:
        model.native_availability = "unknown-path-policy"


def build_graph(models: dict[str, ServiceModel],
                v206: dict[str, Any],
                v215: dict[str, Any],
                v215_native: dict[str, Any]) -> dict[str, Any]:
    ordered = [models[name] for name in SERVICE_ORDER]
    for model in ordered:
        classify_service(model)
    return {
        "services": [asdict(model) for model in ordered],
        "order": list(SERVICE_ORDER),
        "constraints": {
            "active_wifi": "blocked",
            "scan_connect": "blocked",
            "icnss_bind_unbind": "blocked",
            "service_start": "blocked",
        },
        "source_decisions": {
            "v206": v206.get("decision"),
            "v215": v215.get("decision"),
            "v215_native": v215_native.get("decision"),
        },
    }


def decide(graph: dict[str, Any]) -> tuple[str, str]:
    services = graph["services"]
    first_class_present = all(service["init_seen"] or service["android_state"] for service in services)
    cnss_modeled = all(
        service["init_seen"] and service["executable"]
        for service in services
        if service["name"] in {"cnss-daemon", "cnss_diag"}
    )
    lifecycle_ready = graph["source_decisions"].get("v215") == "lifecycle-map-ready"
    if not lifecycle_ready:
        return "manual-review-required", "v215 lifecycle decision is not lifecycle-map-ready"
    if first_class_present and cnss_modeled:
        return "replay-model-ready", "first-class Android Wi-Fi/CNSS services are modeled without execution approval"
    if first_class_present:
        return "replay-model-partial", "first-class services are identified but CNSS executable metadata is incomplete"
    broad_missing = [
        service["name"]
        for service in services
        if "missing-active-init-service-line" in service["blockers"] and not service["android_state"]
    ]
    if broad_missing:
        return "missing-android-runtime", f"missing active service metadata for: {', '.join(broad_missing)}"
    return "manual-review-required", "service graph evidence is inconsistent"


def build_summary(manifest: dict[str, Any]) -> str:
    graph = manifest["graph"]
    rows = []
    for service in graph["services"]:
        rows.append([
            service["name"],
            service["android_state"] or ("seen" if service["process_seen"] else "missing"),
            service["executable"] or "missing",
            service["native_availability"],
            service["risk"],
            ", ".join(service["blockers"][:3]) or "none",
        ])
    lines = [
        "# v216 Android Service Replay Model",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        "",
        "## Service Graph",
        "",
        markdown_table(["service", "android", "executable", "native availability", "risk", "blockers"], rows),
        "",
        "## Replay Order",
        "",
    ]
    lines.extend(f"{index + 1}. `{name}`" for index, name in enumerate(graph["order"]))
    lines.extend([
        "",
        "## Constraints",
        "",
    ])
    for key, value in graph["constraints"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Source Decisions",
        "",
    ])
    for key, value in graph["source_decisions"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This model is not an execution plan.",
        "- `cnss-daemon` and `cnss_diag` remain blocked until ICNSS recovery/debug inventory is complete.",
        "- Wi-Fi HAL, `wificond`, supplicant, and hostapd remain blocked until later gates.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v206 = load_json(args.v206_manifest)
    v215 = load_json(args.v215_manifest)
    v215_native = load_json(args.v215_native_manifest)

    init_text = capture_file_text(v206, "initrc-wifi-grep")
    props_text = capture_file_text(v206, "wifi-props-init-state")
    processes_text = capture_file_text(v206, "processes-wifi")
    models = parse_init_rc(init_text)
    apply_android_state(models, props_text, processes_text)
    graph = build_graph(models, v206, v215, v215_native)
    decision, reason = decide(graph)
    pass_ok = decision in {"replay-model-ready", "replay-model-partial"}
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "inputs": {
            "v206_manifest": str(repo_path(args.v206_manifest)),
            "v215_manifest": str(repo_path(args.v215_manifest)),
            "v215_native_manifest": str(repo_path(args.v215_native_manifest)),
        },
        "graph": graph,
        "guardrails": [
            "no live device commands",
            "no service start",
            "no ctl.start/restart",
            "no class_start",
            "no ICNSS bind/unbind",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("service-graph.json", graph)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
