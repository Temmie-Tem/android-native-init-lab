#!/usr/bin/env python3
"""V627 bounded post-180 service-74/WLAN-PD observer.

This proof reuses the V598/v100 modem-holder WLFW readback path that reproduced
warning-free native service-notifier 180. It extends only the live observation
classification around post-180 service-notifier 74, WLAN-PD, and WLFW service
69. It does not write DSP boot nodes, open esoc0, start service-manager, start
Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP, change routes, or
ping externally.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

import native_wifi_modem_holder_wlfw_readback_v598 as v598


base = v598.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v627-post-180-observer")
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v627-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v627 post-180 service74 observer only; "
    "no DSP boot-node writes, no esoc0, no service-manager, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

MIN_POST_180_WINDOW_SEC = 25.0

TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
POST_180_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_binder_failure", re.compile(r"cnss-daemon.*binder: .*transaction failed|cnss-daemon.*ioctl .* returned -22", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request\(\) called for already added request|Reference count mismatch", re.I)),
)

TIMELINE = tuple(name for name, _ in POST_180_PATTERNS)

_orig_parse_args = base.parse_args
_orig_run_live = base.run_live
_orig_decide = base.decide
_orig_render_summary = base.render_summary


@dataclass(frozen=True)
class DmesgEvent:
    marker: str
    timestamp: float | None
    line: str


def _line_time(line: str) -> float | None:
    match = TS_RE.match(base.ANSI_RE.sub("", line).strip())
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def _events(text: str) -> list[DmesgEvent]:
    events: list[DmesgEvent] = []
    for raw_line in text.splitlines():
        line = base.ANSI_RE.sub("", raw_line).strip()
        if not line:
            continue
        for marker, pattern in POST_180_PATTERNS:
            if pattern.search(line):
                events.append(DmesgEvent(marker, _line_time(line), line))
    return events


def _counts(events: list[DmesgEvent]) -> dict[str, int]:
    counts = {marker: 0 for marker in TIMELINE}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def _first(events: list[DmesgEvent]) -> dict[str, DmesgEvent]:
    found: dict[str, DmesgEvent] = {}
    for event in events:
        found.setdefault(event.marker, event)
    return found


def _event_time(found: dict[str, DmesgEvent], marker: str) -> float | None:
    event = found.get(marker)
    return event.timestamp if event else None


def _delta_ms(found: dict[str, DmesgEvent], newer: str, older: str) -> float | None:
    newer_time = _event_time(found, newer)
    older_time = _event_time(found, older)
    if newer_time is None or older_time is None:
        return None
    return round((newer_time - older_time) * 1000.0, 3)


def _first_line(found: dict[str, DmesgEvent], marker: str) -> str:
    event = found.get(marker)
    return event.line if event else "missing"


def _last_timestamp(events: list[DmesgEvent]) -> float | None:
    timestamps = [event.timestamp for event in events if event.timestamp is not None]
    return max(timestamps) if timestamps else None


def _post_180_window_sec(found: dict[str, DmesgEvent], events: list[DmesgEvent]) -> float | None:
    service_180_time = _event_time(found, "service_notifier_180")
    last_time = _last_timestamp(events)
    if service_180_time is None or last_time is None:
        return None
    return round(max(0.0, last_time - service_180_time), 3)


def _post_180_summary(text: str, qrtr_readback: dict[str, Any]) -> dict[str, Any]:
    events = _events(text)
    found = _first(events)
    counts = _counts(events)
    readback_service_events = int(qrtr_readback.get("service_events") or 0)
    return {
        "min_required_window_sec": MIN_POST_180_WINDOW_SEC,
        "observed_post_180_window_sec": _post_180_window_sec(found, events),
        "counts": counts,
        "deltas_ms": {
            "service_notifier_180_to_service_notifier_74": _delta_ms(found, "service_notifier_74", "service_notifier_180"),
            "service_notifier_180_to_wlan_pd": _delta_ms(found, "wlan_pd", "service_notifier_180"),
            "service_notifier_180_to_wlfw_start": _delta_ms(found, "wlfw_start", "service_notifier_180"),
            "service_notifier_180_to_qmi_server_connected": _delta_ms(found, "qmi_server_connected", "service_notifier_180"),
            "service_notifier_180_to_cnss_diag_netlink": _delta_ms(found, "cnss_diag_netlink", "service_notifier_180"),
            "service_notifier_180_to_cnss_daemon_netlink": _delta_ms(found, "cnss_daemon_netlink", "service_notifier_180"),
            "service_notifier_180_to_binder_failure": _delta_ms(found, "cnss_daemon_binder_failure", "service_notifier_180"),
        },
        "first_lines": {
            marker: _first_line(found, marker)
            for marker in (
                "service_notifier_180",
                "service_notifier_74",
                "wlan_pd",
                "wlfw_start",
                "qmi_server_connected",
                "cnss_diag_netlink",
                "cnss_daemon_netlink",
                "cnss_daemon_binder_failure",
                "kernel_warning",
            )
        },
        "timeline_rows": [
            [
                marker,
                str(counts.get(marker, 0)),
                "" if marker not in found or found[marker].timestamp is None else f"{found[marker].timestamp:.6f}",
                _first_line(found, marker),
            ]
            for marker in TIMELINE
        ],
        "wlfw_qrtr_readback_service_events": readback_service_events,
        "wlfw_qrtr_readback_end_of_list": int(qrtr_readback.get("end_of_list") or 0),
        "wlfw_qrtr_readback_timeouts": int(qrtr_readback.get("timeouts") or 0),
        "wlfw_qrtr_readback_qmi_attempted": int(qrtr_readback.get("qmi_attempted") or 0),
        "events": [asdict(event) for event in events],
    }


def parse_args() -> base.argparse.Namespace:
    args = _orig_parse_args()
    if args.companion_runtime_sec == 18:
        args.companion_runtime_sec = 30
    args.holder_sec = max(args.holder_sec, args.companion_runtime_sec + 45)
    return args


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _orig_run_live(args, store, steps, mount_preflight)
    result["post_180_observer"] = _post_180_summary(
        str(result.get("dmesg_delta") or ""),
        result.get("qrtr_readback") or {},
    )
    return result


def _safe_readback(live: dict[str, Any]) -> tuple[bool, str]:
    readback = live.get("qrtr_readback") or {}
    if int(readback.get("qmi_attempted") or 0) != 0:
        return False, f"unexpected qmi_attempted={readback.get('qmi_attempted')}"
    if readback.get("send_attempted") != "1":
        return False, "WLFW QRTR readback send path did not execute"
    return True, "readback clean"


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v627-post-180-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V401/V490, run V627 preflight, then bounded live observer",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v627-preflight-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blockers before V627",
            False,
        )
    if args.command == "preflight":
        return (
            "v627-post-180-observer-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V627 post-180 observer live proof",
            False,
        )
    if not base.approved(args):
        return (
            "v627-post-180-observer-approval-required",
            True,
            "exact approval phrase required; no live command executed",
            "rerun with exact V627 approval",
            False,
        )
    if not live:
        return "v627-review-required", False, "missing live result", "inspect runner failure", True

    decision, pass_ok, reason, next_step, live_executed = _orig_decide(args, checks, live)
    if not pass_ok:
        return decision.replace("v598", "v627"), pass_ok, reason, next_step, live_executed

    readback_ok, readback_reason = _safe_readback(live)
    if not readback_ok:
        return (
            "v627-readback-guard-failed",
            False,
            readback_reason,
            "stop and inspect helper before any further Wi-Fi live action",
            True,
        )

    observer = live.get("post_180_observer") or {}
    counts = observer.get("counts") or {}
    window = observer.get("observed_post_180_window_sec")
    readback_service_events = int(observer.get("wlfw_qrtr_readback_service_events") or 0)

    if counts.get("kernel_warning", 0) > 0:
        return (
            "v627-kernel-warning",
            False,
            "kernel WARNING/reference mismatch appeared during post-180 observer",
            "do not repeat this live path until dmesg is reviewed",
            True,
        )
    if counts.get("service_notifier_180", 0) == 0:
        return (
            "v627-service180-regression",
            False,
            "V598/v100 path did not reproduce service-notifier 180 in this run",
            "refresh fresh-boot V401/V490/helper-v100 state before another lower gate",
            True,
        )
    if counts.get("service_notifier_74", 0) > 0 or counts.get("wlan_pd", 0) > 0 or readback_service_events > 0:
        return (
            "v627-post-180-lower-publication-advanced",
            True,
            (
                f"service74={counts.get('service_notifier_74', 0)} "
                f"wlan_pd={counts.get('wlan_pd', 0)} "
                f"wlfw_service_events={readback_service_events}"
            ),
            "advance to bounded WLFW/QMI readiness proof; still block HAL scan/connect until wlan0 or FW-ready appears",
            True,
        )
    if window is None or float(window) < MIN_POST_180_WINDOW_SEC:
        return (
            "v627-post-180-window-insufficient",
            False,
            f"service 180 appeared but post-180 observation window was {window}s",
            "rerun with longer companion_runtime_sec before changing lower services",
            True,
        )
    return (
        "v627-post-180-service74-missing",
        True,
        (
            f"service-notifier 180 reproduced, but service 74/WLAN-PD/WLFW service 69 remained absent "
            f"for {window}s after 180"
        ),
        "classify lower service 74 publisher dependency before HAL/qcwlanstate/connect",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        "# V627 Post-180 Service-74/WLAN-PD Observer",
        1,
    )
    live = manifest.get("live") or {}
    observer = live.get("post_180_observer") or {}
    counts = observer.get("counts") or {}
    return "\n".join([
        text,
        "",
        "## V627 Post-180 Observer",
        "",
        f"- min_required_window_sec: `{observer.get('min_required_window_sec', MIN_POST_180_WINDOW_SEC)}`",
        f"- observed_post_180_window_sec: `{observer.get('observed_post_180_window_sec')}`",
        f"- service_notifier_180: `{counts.get('service_notifier_180', 0)}`",
        f"- service_notifier_74: `{counts.get('service_notifier_74', 0)}`",
        f"- wlan_pd: `{counts.get('wlan_pd', 0)}`",
        f"- qmi_server_connected: `{counts.get('qmi_server_connected', 0)}`",
        f"- wlan_fw_ready: `{counts.get('wlan_fw_ready', 0)}`",
        f"- wlan0: `{counts.get('wlan0', 0)}`",
        f"- kernel_warning: `{counts.get('kernel_warning', 0)}`",
        f"- wlfw_qrtr_readback_service_events: `{observer.get('wlfw_qrtr_readback_service_events', 0)}`",
        f"- wlfw_qrtr_readback_end_of_list: `{observer.get('wlfw_qrtr_readback_end_of_list', 0)}`",
        f"- wlfw_qrtr_readback_qmi_attempted: `{observer.get('wlfw_qrtr_readback_qmi_attempted', 0)}`",
        "",
        "## Post-180 Deltas",
        "",
        base.markdown_table(
            ["key", "ms"],
            [[key, str(value)] for key, value in (observer.get("deltas_ms") or {}).items()],
        ),
        "",
        "## Post-180 First Lines",
        "",
        base.markdown_table(
            ["marker", "line"],
            [[key, value] for key, value in (observer.get("first_lines") or {}).items()],
        ),
        "",
        "## Post-180 Timeline",
        "",
        base.markdown_table(
            ["marker", "count", "first_ts", "first_line"],
            observer.get("timeline_rows") or [],
        ),
    ])


base.parse_args = parse_args
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
