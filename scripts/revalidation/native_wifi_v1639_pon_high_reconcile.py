#!/usr/bin/env python3
"""V1639 host-only reconciliation for V1638 missing explicit PON-high trace.

This does not run device commands.  It checks whether V1638 captured the natural
provider route, PON low, AP2MDM high, and zero MDM2AP/errfatal IRQ deltas, then
compares the event ordering against the eSoC provider source.  It intentionally
keeps the strict live label incomplete: inferred PON de-assert is not promoted to
the contract label without an explicit trace marker.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1638-natural-path-mdm2ap-irq-summary-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1639-pon-high-evidence-reconciliation"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1639_PON_HIGH_EVIDENCE_RECONCILIATION_2026-06-02.md"
PON_SOURCE = REPO_ROOT / "tmp" / "wifi" / "v766-icnss-qcacld-patch-apply-build" / "source" / "drivers" / "esoc" / "esoc-mdm-pon.c"
FOURX_SOURCE = REPO_ROOT / "tmp" / "wifi" / "v766-icnss-qcacld-patch-apply-build" / "source" / "drivers" / "esoc" / "esoc-mdm-4x.c"

TIME_RE = re.compile(r"\s(?P<time>\d+\.\d+):\s(?P<event>gpio_value:\s*(?P<gpio>\d+)\s+(?P<op>set|get)\s+(?P<value>[01])|gpio_direction:\s*(?P<dgpio>\d+)\s+out\s+\((?P<dvalue>[01])\)|pil_notif:.*fw=esoc0)")
KV_RE = re.compile(r"^([A-Za-z0-9_.:-]+)=(.*)$")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def parse_key_values(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = KV_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def int_field(fields: dict[str, str], key: str, default: int = -1) -> int:
    try:
        return int(fields.get(key, str(default)).strip())
    except (TypeError, ValueError):
        return default


def extract_events(window: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, float, str, str]] = set()
    for line in window.splitlines():
        match = TIME_RE.search(line)
        if not match:
            continue
        event_text = match.group("event")
        event: dict[str, Any] = {"time": float(match.group("time")), "raw": event_text}
        if "pil_notif" in event_text:
            event.update({"kind": "pil_esoc"})
        elif match.group("gpio"):
            event.update({
                "kind": "gpio_value",
                "gpio": int(match.group("gpio")),
                "op": match.group("op"),
                "value": int(match.group("value")),
            })
        else:
            event.update({
                "kind": "gpio_direction",
                "gpio": int(match.group("dgpio")),
                "op": "direction_out",
                "value": int(match.group("dvalue")),
            })
        key = (event["kind"], event["time"], str(event.get("gpio", "")), str(event.get("value", "")))
        if key not in seen:
            seen.add(key)
            events.append(event)
    return sorted(events, key=lambda item: item["time"])


def first_event(events: list[dict[str, Any]], *, kind: str | None = None, gpio: int | None = None, value: int | None = None, op: str | None = None) -> dict[str, Any] | None:
    for event in events:
        if kind is not None and event.get("kind") != kind:
            continue
        if gpio is not None and event.get("gpio") != gpio:
            continue
        if value is not None and event.get("value") != value:
            continue
        if op is not None and event.get("op") != op:
            continue
        return event
    return None


def source_contract() -> dict[str, Any]:
    pon_text = read_text(PON_SOURCE)
    fourx_text = read_text(FOURX_SOURCE)
    return {
        "pon_source": rel(PON_SOURCE),
        "fourx_source": rel(FOURX_SOURCE),
        "source_present": bool(pon_text and fourx_text),
        "sdx50m_toggle_soft_reset_present": "sdx50m_toggle_soft_reset" in pon_text,
        "toggle_calls_soft_reset_before_ap2mdm": "mdm_toggle_soft_reset(mdm, false);" in pon_text,
        "has_120ms_pon_assert_sleep": "usleep_range(120000, 180000);" in pon_text,
        "has_150ms_post_pon_sleep": "msleep(150);" in pon_text,
        "ap2mdm_after_sleep": "gpio_direction_output(MDM_GPIO(mdm, AP2MDM_STATUS), 1);" in pon_text,
        "queues_esoc_req_img": "esoc_clink_queue_request(ESOC_REQ_IMG" in pon_text,
        "provider_regulator_code_absent": not re.search(r"\b(regulator|vreg|supply)\b", pon_text + "\n" + fourx_text, re.IGNORECASE),
    }


def classify(evidence_dir: Path) -> dict[str, Any]:
    window_path = evidence_dir / "test-rc1-window-result.stdout.txt"
    manifest_path = evidence_dir / "manifest.json"
    report_path = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1638_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_HANDOFF_2026-06-02.md"
    window = read_text(window_path)
    manifest = json.loads(read_text(manifest_path) or "{}")
    fields = parse_key_values(window)
    events = extract_events(window)
    contract = source_contract()

    pil = first_event(events, kind="pil_esoc")
    pon_low = first_event(events, kind="gpio_value", gpio=1270, value=0, op="set")
    pon_high = first_event(events, gpio=1270, value=1, op="set") or first_event(events, gpio=1270, value=1, op="direction_out")
    ap2mdm = first_event(events, gpio=135, value=1)
    gpio142_irq_delta = int_field(fields, "mdm2ap_timing.gpio142_irq_delta")
    errfatal_irq_delta = int_field(fields, "mdm2ap_timing.errfatal_irq_delta")
    sample_count = int_field(fields, "mdm2ap_timing.sample_count", 0)
    parsed_ok = int_field(fields, "mdm2ap_timing.gpio142_irq_initial_parsed", 0) == 1 and int_field(fields, "mdm2ap_timing.errfatal_irq_initial_parsed", 0) == 1
    safety_zero = all(int_field(fields, key, 0) == 0 for key in fields if key.startswith("mdm2ap_timing.safety_"))

    timing_delta_ms = None
    pon_high_inferred = False
    if pon_low and ap2mdm:
        timing_delta_ms = round((ap2mdm["time"] - pon_low["time"]) * 1000, 3)
        pon_high_inferred = (
            contract["has_120ms_pon_assert_sleep"]
            and contract["has_150ms_post_pon_sleep"]
            and contract["ap2mdm_after_sleep"]
            and timing_delta_ms >= 250
        )

    strict_label = ((manifest.get("natural_path_observation") or {}).get("label") or "")
    decision = "v1639-pon-high-inferred-not-promoted"
    pass_ok = bool(
        strict_label == "natural-path-observation-incomplete"
        and pil
        and pon_low
        and ap2mdm
        and not pon_high
        and pon_high_inferred
        and gpio142_irq_delta == 0
        and errfatal_irq_delta == 0
        and parsed_ok
        and sample_count >= 120
        and safety_zero
    )
    if not pass_ok:
        decision = "v1639-pon-high-reconciliation-inconclusive"

    return {
        "cycle": "V1639",
        "decision": decision,
        "pass": pass_ok,
        "type": "host-only evidence reconciliation",
        "evidence_dir": rel(evidence_dir),
        "v1638_manifest": rel(manifest_path),
        "v1638_report": rel(report_path),
        "strict_v1638_label": strict_label,
        "events": {
            "pil_esoc_time": None if not pil else pil["time"],
            "pon_low_time": None if not pon_low else pon_low["time"],
            "pon_high_trace_time": None if not pon_high else pon_high["time"],
            "ap2mdm_time": None if not ap2mdm else ap2mdm["time"],
            "pon_low_to_ap2mdm_ms": timing_delta_ms,
        },
        "source_contract": contract,
        "irq_summary": {
            "gpio142_irq_delta": gpio142_irq_delta,
            "errfatal_irq_delta": errfatal_irq_delta,
            "sample_count": sample_count,
            "parsed_ok": parsed_ok,
            "safety_zero": safety_zero,
        },
        "classification": {
            "pon_high_inferred_from_source_order": pon_high_inferred,
            "promote_to_mdm2ap_silent": False,
            "reason": "PON de-assert is source-order inferred before AP2MDM, but the live contract required an explicit GPIO1270 high/de-assert trace marker.",
            "next_gate": "separate-decision bounded modem-rail/PMIC design; no live write executed here",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    events = result["events"]
    irq = result["irq_summary"]
    source = result["source_contract"]
    cls = result["classification"]
    return "\n".join([
        "# Native Init V1639 PON-high Evidence Reconciliation",
        "",
        "## Summary",
        "",
        "- Cycle: `V1639`",
        "- Type: host-only evidence reconciliation",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'INCONCLUSIVE'}",
        f"- V1638 strict label: `{result['strict_v1638_label']}`",
        f"- Evidence: `{result['evidence_dir']}`",
        "",
        "## Finding",
        "",
        "- V1638 captured esoc0 provider entry, GPIO1270/PON low/assert, GPIO135/AP2MDM assert, and complete zero IRQ deltas for GPIO142/MDM2AP plus mdm errfatal.",
        "- V1638 did not capture an explicit GPIO1270/PON high/de-assert trace marker, so the strict contract label remains incomplete.",
        "- Source order still matters: `mdm4x_do_first_power_on()` calls soft-reset/PON first, then waits, then drives AP2MDM high. Therefore the observed AP2MDM high is downstream of the PON de-assert path, but this is an inference rather than the explicit trace marker required by the live contract.",
        "",
        "## Evidence Timing",
        "",
        f"- esoc0 PIL time: `{events['pil_esoc_time']}`",
        f"- GPIO1270/PON low time: `{events['pon_low_time']}`",
        f"- GPIO1270/PON high trace time: `{events['pon_high_trace_time']}`",
        f"- GPIO135/AP2MDM high time: `{events['ap2mdm_time']}`",
        f"- PON-low to AP2MDM delta ms: `{events['pon_low_to_ap2mdm_ms']}`",
        "",
        "## IRQ Discriminator",
        "",
        f"- GPIO142/MDM2AP IRQ delta: `{irq['gpio142_irq_delta']}`",
        f"- mdm errfatal IRQ delta: `{irq['errfatal_irq_delta']}`",
        f"- sample count: `{irq['sample_count']}`",
        f"- parsed flags ok: `{irq['parsed_ok']}`",
        f"- safety markers zero: `{irq['safety_zero']}`",
        "",
        "## Source Contract",
        "",
        f"- source present: `{source['source_present']}`",
        f"- PON assert sleep 120-180 ms present: `{source['has_120ms_pon_assert_sleep']}`",
        f"- post-PON sleep 150 ms present: `{source['has_150ms_post_pon_sleep']}`",
        f"- AP2MDM after sleep present: `{source['ap2mdm_after_sleep']}`",
        f"- ESOC_REQ_IMG queue present: `{source['queues_esoc_req_img']}`",
        f"- provider regulator code absent: `{source['provider_regulator_code_absent']}`",
        "",
        "## Classification",
        "",
        f"- PON high inferred from source order: `{cls['pon_high_inferred_from_source_order']}`",
        f"- promote to `mdm2ap-silent-natural-path`: `{cls['promote_to_mdm2ap_silent']}`",
        f"- reason: {cls['reason']}",
        "",
        "## Next Gate",
        "",
        "No live mutation was performed. Do not spin another timing/window variant from this result. The next Wi-Fi-relevant blocker is below the natural eSoC path: a separately decided bounded modem-rail/PMIC investigation plan, with source/build-only and read-only preflight first, then explicit write-gate separation if selected.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args.evidence_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
