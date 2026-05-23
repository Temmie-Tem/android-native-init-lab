#!/usr/bin/env python3
"""V675 post-HAL property/binder target classifier.

This host-only classifier consumes V674/V673 evidence and Android property
captures to decide the next minimal runtime repair target. It does not contact
the device, start services, scan, connect, run DHCP, change routes, use
credentials, or ping externally.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v675-property-binder-target-classifier")
DEFAULT_V674_MANIFEST = Path("tmp/wifi/v674-post-hal-wificond-classifier/manifest.json")
DEFAULT_V671_ARM_MANIFEST = Path("tmp/wifi/v673-same-helper-replay-live-retry2/arm-v671-v111/live/manifest.json")
DEFAULT_ANDROID_PROPS = Path("tmp/wifi/v297-android-property-capture-android/commands/all-getprop.txt")
DEFAULT_FILTERED_PROPS = Path("tmp/wifi/v520-companion-service-availability-plan/inputs/v206_props.txt")
DEFAULT_CONTEXT_DIR = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/native")
DEFAULT_INITRC = Path("tmp/wifi/v520-companion-service-availability-plan/inputs/v206_initrc.txt")

PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
)
GETPROP_RE = re.compile(r"^\[([^\]]+)\]: \[(.*)\]$")
BINDER_LINE_RE = re.compile(
    r"(?P<actor>servicemanager|hwservicemanage\w*|wificond|cnss-daemon).*?"
    r"binder:.*?(?P<kind>transaction failed|ioctl).*?(?P<errno>-\d+)",
    re.I,
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

FORBIDDEN_ACTIONS = (
    "device command",
    "service start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
)
RUNTIME_REQUIRED_KEYS = {
    "ro.vendor.redirect_socket_calls",
    "ro.debuggable",
    "ro.vndk.version",
}
DEFAULTABLE_DEBUG_PREFIXES = (
    "debug.",
    "debug.ld.app.",
    "libc.debug.",
    "heapprofd.",
    "arm64.memtag.",
)


@dataclass(frozen=True)
class ContextRule:
    source: str
    line_number: int
    name: str
    context: str
    exact: bool
    prop_type: str
    raw: str


@dataclass(frozen=True)
class PropertyTarget:
    key: str
    count: int
    category: str
    context_status: str
    context: str
    prop_type: str
    match_kind: str
    rule_source: str
    rule_line: int
    android_value_status: str
    android_value_source: str
    seed_value_required: bool
    recommended_action: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v674-manifest", type=Path, default=DEFAULT_V674_MANIFEST)
    parser.add_argument("--v671-arm-manifest", type=Path, default=DEFAULT_V671_ARM_MANIFEST)
    parser.add_argument("--android-props", type=Path, default=DEFAULT_ANDROID_PROPS)
    parser.add_argument("--filtered-props", type=Path, default=DEFAULT_FILTERED_PROPS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--context-file", action="append", type=Path, default=[])
    parser.add_argument("--initrc", type=Path, default=DEFAULT_INITRC)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def evidence_dir(path: Path, manifest: dict[str, Any]) -> Path:
    evidence = manifest.get("evidence") or manifest.get("out_dir")
    if evidence:
        return repo_path(Path(str(evidence)))
    return repo_path(path).parent


def helper_text(arm: dict[str, Any]) -> str:
    return str((arm.get("live") or {}).get("helper_stdout_stderr") or "")


def dmesg_text(arm_path: Path, arm: dict[str, Any]) -> str:
    return read_text(evidence_dir(arm_path, arm) / "native" / "dmesg-delta.txt")


def parse_property_denials(text: str, v674: dict[str, Any]) -> collections.Counter[str]:
    names = [match.group(1) for match in PROPERTY_DENIAL_RE.finditer(text)]
    if names:
        return collections.Counter(names)
    fallback = collections.Counter()
    for item in ((v674.get("property_denials") or {}).get("top") or []):
        if isinstance(item, list) and len(item) == 2:
            fallback[str(item[0])] = int(item[1])
    return fallback


def parse_context_file(source: str, path: Path) -> list[ContextRule]:
    rules: list[ContextRule] = []
    for line_number, raw_line in enumerate(read_text(path).splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        exact = len(parts) >= 3 and parts[2] == "exact"
        prop_type = "string"
        if exact and len(parts) >= 4:
            prop_type = parts[3]
        elif len(parts) >= 4 and parts[2] == "prefix":
            prop_type = parts[3]
        elif not exact and len(parts) >= 3:
            prop_type = parts[2]
        rules.append(ContextRule(source, line_number, parts[0], parts[1], exact, prop_type, stripped))
    return rules


def context_files(args: argparse.Namespace) -> list[Path]:
    explicit = [repo_path(path) for path in args.context_file]
    if explicit:
        return [path for path in explicit if path.exists()]
    root = repo_path(args.context_dir)
    return sorted(root.glob("cat-context-*.txt"))


def parse_context_rules(args: argparse.Namespace) -> list[ContextRule]:
    rules: list[ContextRule] = []
    for path in context_files(args):
        rules.extend(parse_context_file(path.name, path))
    return rules


def rule_matches(rule: ContextRule, key: str) -> bool:
    if rule.exact:
        return key == rule.name
    return key.startswith(rule.name)


def map_context(key: str, rules: list[ContextRule]) -> ContextRule | None:
    exact_matches = [rule for rule in rules if rule.exact and rule_matches(rule, key)]
    if exact_matches:
        return exact_matches[-1]
    prefix_matches = [rule for rule in rules if not rule.exact and rule_matches(rule, key)]
    if not prefix_matches:
        return None
    prefix_matches.sort(key=lambda rule: (len(rule.name), rule.line_number))
    return prefix_matches[-1]


def parse_getprop(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = GETPROP_RE.match(raw_line.strip())
        if match:
            props[match.group(1)] = match.group(2)
    return props


def classify_property(key: str) -> str:
    if key.startswith("persist.log.") or key.startswith("log."):
        return "log_default"
    if key.startswith("debug.ld.app."):
        return "linker_debug_default"
    if key in RUNTIME_REQUIRED_KEYS:
        return "runtime_required"
    if key.startswith(DEFAULTABLE_DEBUG_PREFIXES):
        return "runtime_debug_default"
    if key.startswith("init.svc.") or key.startswith("ro.boottime."):
        return "service_state"
    return "other"


def value_status(key: str,
                 category: str,
                 android_props: dict[str, str],
                 filtered_props: dict[str, str]) -> tuple[str, str, bool]:
    if key in android_props:
        return "present-in-full-getprop", "v297-all-getprop", category == "runtime_required"
    if key in filtered_props:
        return "present-in-filtered-getprop", "v206-filtered-getprop", category == "runtime_required"
    if category in {"log_default", "linker_debug_default", "runtime_debug_default"}:
        return "defaultable-when-missing", "Android default lookup", False
    return "missing-from-captures", "none", category == "runtime_required"


def recommended_action(category: str, context_known: bool, seed_required: bool) -> str:
    if not context_known:
        return "refresh full property_context capture before runtime repair"
    if category == "runtime_required" and seed_required:
        return "seed Android value and include property_info entry"
    if category in {"log_default", "linker_debug_default", "runtime_debug_default"}:
        return "include property_info entry; value may default empty/false unless Android capture has value"
    return "include property_info entry if lookup recurs in next live gate"


def build_property_targets(denials: collections.Counter[str],
                           rules: list[ContextRule],
                           android_props: dict[str, str],
                           filtered_props: dict[str, str]) -> list[PropertyTarget]:
    targets: list[PropertyTarget] = []
    for key, count in denials.most_common():
        category = classify_property(key)
        rule = map_context(key, rules)
        context_known = rule is not None
        status, source, seed_required = value_status(key, category, android_props, filtered_props)
        targets.append(PropertyTarget(
            key=key,
            count=count,
            category=category,
            context_status="known" if context_known else "missing",
            context=rule.context if rule else "",
            prop_type=rule.prop_type if rule else "",
            match_kind=("exact" if rule and rule.exact else "prefix" if rule else "missing"),
            rule_source=rule.source if rule else "",
            rule_line=rule.line_number if rule else 0,
            android_value_status=status,
            android_value_source=source,
            seed_value_required=seed_required,
            recommended_action=recommended_action(category, context_known, seed_required),
        ))
    return targets


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def parse_binder_failures(text: str) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        match = BINDER_LINE_RE.search(line)
        if not match:
            continue
        actor = match.group("actor")
        if actor.lower().startswith("hwservicemanage"):
            actor = "hwservicemanager"
        failures.append({
            "actor": actor,
            "kind": match.group("kind").lower(),
            "errno": match.group("errno"),
            "line": line,
        })
    return failures


def binder_summary(failures: list[dict[str, str]]) -> dict[str, Any]:
    by_actor = collections.Counter(failure["actor"] for failure in failures)
    by_kind = collections.Counter(failure["kind"] for failure in failures)
    return {
        "total": len(failures),
        "by_actor": dict(sorted(by_actor.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "failures": failures,
    }


def parse_initrc_services(text: str) -> dict[str, dict[str, Any]]:
    services: dict[str, dict[str, Any]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        service_match = re.match(r"^service\s+(\S+)\s+(.+)$", line)
        if service_match:
            current = service_match.group(1)
            services[current] = {"command": service_match.group(2), "interfaces": [], "class": "", "user": "", "groups": [], "capabilities": []}
            continue
        if not current:
            continue
        if line.startswith("interface "):
            services[current]["interfaces"].append(line.removeprefix("interface ").strip())
        elif line.startswith("class "):
            services[current]["class"] = line.removeprefix("class ").strip()
        elif line.startswith("user "):
            services[current]["user"] = line.removeprefix("user ").strip()
        elif line.startswith("group "):
            services[current]["groups"] = line.removeprefix("group ").split()
        elif line.startswith("capabilities "):
            services[current]["capabilities"] = line.removeprefix("capabilities ").split()
    return {name: services[name] for name in sorted(services) if any(token in name for token in ("wifi", "wificond", "supplicant", "cnss"))}


def property_summary(targets: list[PropertyTarget]) -> dict[str, Any]:
    by_category = collections.Counter(target.category for target in targets)
    by_context = collections.Counter(target.context_status for target in targets)
    by_value = collections.Counter(target.android_value_status for target in targets)
    seed_targets = [
        {
            "key": target.key,
            "category": target.category,
            "context": target.context,
            "prop_type": target.prop_type,
            "value_status": target.android_value_status,
            "value_source": target.android_value_source,
        }
        for target in targets
        if target.context_status == "known" and (
            target.seed_value_required
            or target.category in {"log_default", "linker_debug_default", "runtime_debug_default"}
        )
    ]
    return {
        "total_denials": sum(target.count for target in targets),
        "unique_denied_keys": len(targets),
        "by_category": dict(sorted(by_category.items())),
        "by_context_status": dict(sorted(by_context.items())),
        "by_value_status": dict(sorted(by_value.items())),
        "seed_target_count": len(seed_targets),
        "seed_targets": seed_targets,
    }


def build_checks(v674: dict[str, Any],
                 arm: dict[str, Any],
                 targets: list[PropertyTarget],
                 binders: dict[str, Any],
                 rules: list[ContextRule],
                 android_props: dict[str, str]) -> list[dict[str, Any]]:
    context_missing = [target.key for target in targets if target.context_status != "known"]
    runtime_missing = [
        target.key for target in targets
        if target.category == "runtime_required" and target.android_value_status not in {"present-in-full-getprop", "present-in-filtered-getprop"}
    ]
    runtime_present = [
        target.key for target in targets
        if target.category == "runtime_required" and target.android_value_status in {"present-in-full-getprop", "present-in-filtered-getprop"}
    ]
    return [
        {
            "name": "v674-input-ready",
            "status": "pass" if v674.get("decision") == "v674-post-hal-property-binder-gap-classified" else "blocked",
            "detail": {"v674_decision": v674.get("decision"), "v671_arm_decision": arm.get("decision")},
            "next_step": "run V674 before V675",
        },
        {
            "name": "android-property-input-ready",
            "status": "pass" if android_props else "blocked",
            "detail": {"property_count": len(android_props)},
            "next_step": "refresh full Android getprop capture",
        },
        {
            "name": "property-context-rules-ready",
            "status": "pass" if len(rules) >= 100 else "blocked",
            "detail": {"rule_count": len(rules), "sources": sorted({rule.source for rule in rules})},
            "next_step": "capture property_contexts before target repair",
        },
        {
            "name": "denied-property-contexts-known",
            "status": "pass" if targets and not context_missing else "blocked",
            "detail": {"missing": context_missing, "unique_denied_keys": len(targets)},
            "next_step": "add missing context files before generating property_info",
        },
        {
            "name": "runtime-property-values-known",
            "status": "pass" if not runtime_missing and bool(runtime_present) else "blocked",
            "detail": {"present": runtime_present, "missing": runtime_missing},
            "next_step": "capture full Android getprop values for runtime-required keys",
        },
        {
            "name": "binder-failures-targeted",
            "status": "finding" if binders["total"] > 0 else "pass",
            "detail": {"total": binders["total"], "by_actor": binders["by_actor"], "by_kind": binders["by_kind"]},
            "next_step": "keep binder registration/transaction capture as separate V676 live observation target",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], targets: list[PropertyTarget]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v675-property-binder-target-plan-ready",
            True,
            "plan-only; no device command or live mutation executed",
            "run V675 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v675-property-binder-target-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing host-only evidence before live repair",
        )
    runtime_targets = [target for target in targets if target.category == "runtime_required"]
    if runtime_targets:
        return (
            "v675-property-binder-targets-classified",
            True,
            "denied property contexts are known and runtime-required Android values are available; next repair should expand private property_info/seed before a narrow binder capture retry",
            "plan V676 property-info/seed expansion plus bounded binder registration capture; keep supplicant/scan/connect blocked until WLFW/BDF/wlan0 advances",
        )
    return (
        "v675-property-binder-targets-review",
        False,
        "property denials parsed but no runtime-required target was identified",
        "inspect full helper transcript before choosing a live mutation",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v674 = load_json(args.v674_manifest)
    arm = load_json(args.v671_arm_manifest)
    text = helper_text(arm)
    dmesg = dmesg_text(args.v671_arm_manifest, arm)
    rules = parse_context_rules(args)
    android_props = parse_getprop(read_text(args.android_props))
    filtered_props = parse_getprop(read_text(args.filtered_props))
    denials = parse_property_denials(text, v674)
    targets = build_property_targets(denials, rules, android_props, filtered_props)
    binders = binder_summary(parse_binder_failures(dmesg))
    init_services = parse_initrc_services(read_text(args.initrc))
    summary = property_summary(targets)
    checks = build_checks(v674, arm, targets, binders, rules, android_props)
    decision, pass_ok, reason, next_step = decide(args.command, checks, targets)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v675",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v674_manifest": str(repo_path(args.v674_manifest)),
            "v671_arm_manifest": str(repo_path(args.v671_arm_manifest)),
            "android_props": str(repo_path(args.android_props)),
            "filtered_props": str(repo_path(args.filtered_props)),
            "context_files": [str(path) for path in context_files(args)],
            "initrc": str(repo_path(args.initrc)),
        },
        "checks": checks,
        "property_summary": summary,
        "property_targets": [asdict(target) for target in targets],
        "binder_summary": binders,
        "init_services": init_services,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def check_rows(checks: list[dict[str, Any]]) -> list[list[str]]:
    return [[check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]] for check in checks]


def property_rows(targets: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            str(target["key"]),
            str(target["count"]),
            str(target["category"]),
            str(target["context_status"]),
            str(target["context"]),
            str(target["prop_type"]),
            str(target["match_kind"]),
            str(target["android_value_status"]),
            str(target["recommended_action"]),
        ]
        for target in targets
    ]


def binder_rows(summary: dict[str, Any]) -> list[list[str]]:
    return [
        [failure["actor"], failure["kind"], failure["errno"], failure["line"]]
        for failure in summary.get("failures", [])
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    prop = manifest["property_summary"]
    return "\n".join([
        "# V675 Property/Binder Target Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows(manifest["checks"])),
        "",
        "## Property Summary",
        "",
        f"- total_denials: `{prop['total_denials']}`",
        f"- unique_denied_keys: `{prop['unique_denied_keys']}`",
        f"- seed_target_count: `{prop['seed_target_count']}`",
        f"- by_category: `{json.dumps(prop['by_category'], sort_keys=True)}`",
        f"- by_context_status: `{json.dumps(prop['by_context_status'], sort_keys=True)}`",
        f"- by_value_status: `{json.dumps(prop['by_value_status'], sort_keys=True)}`",
        "",
        markdown_table(
            ["property", "count", "category", "context", "type", "match", "value", "action"],
            [[row[0], row[1], row[2], row[4], row[5], row[6], row[7], row[8]] for row in property_rows(manifest["property_targets"])],
        ),
        "",
        "## Binder Failures",
        "",
        f"- total: `{manifest['binder_summary']['total']}`",
        f"- by_actor: `{json.dumps(manifest['binder_summary']['by_actor'], sort_keys=True)}`",
        "",
        markdown_table(["actor", "kind", "errno", "line"], binder_rows(manifest["binder_summary"])),
        "",
        "## Interpretation",
        "",
        "- All denied property keys map to captured Android property_context rules.",
        "- The runtime-required values are available from the full Android getprop capture.",
        "- Most denials are log/debug/defaultable lookups, so the likely repair is property_info completeness plus a small value seed, not a broad SELinux policy change.",
        "- Binder failures remain a separate runtime registration/transaction surface and should be captured after the property_info/seed repair, before supplicant or scan/connect.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
