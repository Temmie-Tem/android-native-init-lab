#!/usr/bin/env python3
"""Live proof for current_kernel_time64() x0/x1 struct-return lanes.

This driver is intentionally tied to the v1 call-pair image built by
build_kernel_tier2_repl_v1_call_pair.py.  That image keeps the normal v1 REPL
magic/op layout but prints post-call x0:x1 as `R%llx:%llx`.  The proof target is
one read-only no-argument function:

    struct timespec64 current_kernel_time64(void)

On arm64 the returned timespec64 is carried in x0/x1.  The earlier v1 proof
captured only x0; this proof captures both lanes from the same call.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
SCRIPT_DIR = Path(__file__).resolve().parent

import a90_repl  # noqa: E402
import a90ctl  # noqa: E402


DEFAULT_MAP = REPO_ROOT / "workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map"
DEFAULT_IMAGE = REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_call_pair.img"
DEFAULT_SOURCE_ROOT = a90_repl.DEFAULT_KERNEL_SOURCE_ROOT
PAIR_RE = re.compile(r"R([0-9a-fA-F]+):([0-9a-fA-F]+)")
TV_NSEC_MAX = 999_999_999
TARGET = "current_kernel_time64"
ANCHOR = "ktime_get_real_seconds"


def parse_pair_values(text: str) -> list[tuple[int, int]]:
    return [(int(left, 16), int(right, 16)) for left, right in PAIR_RE.findall(text)]


def pair_op_sh(buf: bytes,
               busybox: str = a90_repl.DEFAULT_BUSYBOX,
               *,
               tail_lines: int = 80,
               node: str = a90_repl.NODE) -> str:
    drain = "dmesg -c >/dev/null 2>/dev/null || dmesg >/dev/null 2>/dev/null"
    write = f"printf '{a90_repl.printf_octal(buf)}' > {node}"
    read = f"(dmesg -c 2>/dev/null || dmesg) | tail -n {int(tail_lines)}"
    return f"{drain}; {write}; {read}"


@dataclass
class PairReplConfig:
    host: str = a90ctl.DEFAULT_HOST
    port: int = a90ctl.DEFAULT_PORT
    busybox: str = a90_repl.DEFAULT_BUSYBOX
    timeout: float = 25.0
    dmesg_tail: int = 80
    settle_sec: float = 0.4
    safe_op_retries: int = 2
    retry_delay_sec: float = 0.2


class PairReplSession:
    def __init__(self, config: PairReplConfig):
        self.config = config

    def _run_sh(self, sh_str: str, *, allow_error: bool = False) -> str:
        argv = ["run", self.config.busybox, "sh", "-c", sh_str]
        result = a90_repl.transport.run_serial_command(
            argv,
            host=self.config.host,
            port=self.config.port,
            timeout=self.config.timeout,
        )
        if not result.get("ok") and not allow_error:
            raise a90_repl.ReplError(
                f"serial run failed: rc={result.get('rc')} "
                f"stderr={result.get('stderr')!r}"
            )
        return str(result.get("stdout") or "")

    def hide(self) -> None:
        try:
            a90ctl.bridge_exchange(
                self.config.host,
                self.config.port,
                "hide",
                min(self.config.timeout, 8.0),
                markers=(b"[busy]", b"[done]", b"[err]"),
            )
        except OSError:
            pass

    def set_panic_on_oops(self, value: int) -> None:
        self._run_sh(f"echo {int(value)} > /proc/sys/kernel/panic_on_oops")

    def _op_pairs(self,
                  op: int,
                  args: tuple[int, ...] = (),
                  *,
                  replay_safe: bool | None = None) -> list[tuple[int, int]]:
        buf = a90_repl.build_cmd_buffer(op, args)
        replay_safe = (op in a90_repl.REPLAY_SAFE_OPS) if replay_safe is None else replay_safe
        attempts = 1 + (max(0, self.config.safe_op_retries) if replay_safe else 0)
        samples: list[str] = []
        for attempt in range(attempts):
            text = self._run_sh(
                pair_op_sh(
                    buf,
                    self.config.busybox,
                    tail_lines=self.config.dmesg_tail,
                ),
                allow_error=True,
            )
            pairs = parse_pair_values(text)
            if pairs:
                return pairs
            samples.append(text[-160:].replace("\n", "\\n"))
            if attempt + 1 < attempts:
                self.hide()
                if self.config.retry_delay_sec > 0:
                    time.sleep(self.config.retry_delay_sec)
        raise a90_repl.ReplTransientNoiseError(
            f"no call-pair R output captured for op={op} after {attempts} attempt(s); "
            f"replay_safe={replay_safe}; stdout_tail_samples={samples!r}"
        )

    def slide(self) -> int:
        runtime_pc, _ignored = self._op_pairs(a90_repl.OP_SLIDE, ())[-1]
        return (runtime_pc - a90_repl.ADR_SELF_LINK_VADDR) & a90_repl.MASK64

    def call_runtime_pair(self, target_runtime: int, xargs: tuple[int, ...] = ()) -> tuple[int, int]:
        if len(xargs) > 8:
            raise ValueError(f"too many call args (max x0..x7): {len(xargs)}")
        args = (target_runtime & a90_repl.MASK64, *(value & a90_repl.MASK64 for value in xargs))
        return self._op_pairs(a90_repl.OP_CALL, args, replay_safe=False)[-1]


def static_gate(symbols: dict[str, a90_repl.Symbol],
                image: a90_repl.StaticImage,
                *,
                source_root: Path) -> tuple[int, int, list[dict[str, object]], dict[str, object], dict[str, a90_repl.VerifiedResolution]]:
    source = a90_repl.lookup_source_signature(TARGET, source_root=source_root)
    call_safety = dict(a90_repl.require_call_safety_for_call(symbols, image, TARGET, ()))
    call_safety["pair_harness_return_kind"] = "timespec64-x0-x1"
    call_safety["pair_harness_note"] = (
        "base classifier establishes no-argument SAFE-SCALAR callability; "
        "this call-pair REPL variant captures the second aggregate return lane"
    )
    if call_safety.get("tier") != a90_repl.CALL_PROOF_TARGETS[TARGET]["expected_tier"]:
        raise a90_repl.ReplError(f"{TARGET} call-safety tier is not the expected scalar tier")
    if not source.get("found") or source.get("pointer_arg_indices") != []:
        raise a90_repl.ReplError(f"{TARGET} source signature must be scalar-only")
    selected_signature = (
        source.get("selected", {}).get("signature")
        if isinstance(source.get("selected"), dict) else None
    )
    if selected_signature != a90_repl.CALL_PROOF_TARGETS[TARGET]["source_signature"]:
        raise a90_repl.ReplError(f"{TARGET} source signature did not select the timekeeping.h declaration")

    resolutions = {
        TARGET: a90_repl.resolve_verified(symbols, image, TARGET, purpose="call"),
        ANCHOR: a90_repl.resolve_verified(symbols, image, ANCHOR, purpose="call"),
    }
    target_link = a90_repl.require_verified_resolution(resolutions[TARGET], "call-pair target")
    anchor_link = a90_repl.require_verified_resolution(resolutions[ANCHOR], "call-pair anchor")
    next_symbol_name, expected_boundary = a90_repl.CURRENT_KERNEL_TIME64_NEXT_SYMBOL
    next_symbol = symbols.get(next_symbol_name)
    if next_symbol is None or next_symbol.vaddr - target_link != expected_boundary:
        raise a90_repl.ReplError(f"{TARGET} next-symbol boundary is not the expected 0x{expected_boundary:x}")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": TARGET,
            "resolution_method": resolutions[TARGET].method,
        },
        {
            "check": "static-anchor-c1-identity",
            "ok": True,
            "anchor": ANCHOR,
            "resolution_method": resolutions[ANCHOR].method,
        },
        {
            "check": "static-next-symbol-boundary",
            "ok": True,
            "next_symbol": next_symbol_name,
            "byte_size": f"0x{expected_boundary:x}",
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": selected_signature,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
        },
    ]
    observed_words = image.u32_words_at_vaddr(
        target_link, len(a90_repl.CURRENT_KERNEL_TIME64_EXPECTED_WORDS)
    )
    for index, expected in enumerate(a90_repl.CURRENT_KERNEL_TIME64_EXPECTED_WORDS):
        observed = observed_words[index]
        ok = observed == expected
        checks.append({
            "check": f"static-{TARGET}-word-{index:02d}",
            "ok": ok,
            "expected_word": f"0x{expected:08x}",
            "observed_word": f"0x{observed:08x}",
        })
        if not ok:
            raise a90_repl.ReplError(
                f"{TARGET} word {index} mismatch: observed 0x{observed:08x}, "
                f"expected 0x{expected:08x}"
            )
    source_evidence = a90_repl._source_row_evidence(source)
    source_evidence["aggregate_return_lanes"] = "arm64-small-struct-x0-x1"
    return target_link, anchor_link, checks, {
        "source_evidence": source_evidence,
        "call_safety": call_safety,
    }, resolutions


def run_pair_proof(session: PairReplSession,
                   symbols: dict[str, a90_repl.Symbol],
                   image: a90_repl.StaticImage,
                   *,
                   source_root: Path = DEFAULT_SOURCE_ROOT) -> tuple[dict[str, object], dict[str, object]]:
    target_link, anchor_link, checks, static_meta, resolutions = static_gate(
        symbols, image, source_root=source_root
    )

    private: dict[str, object] = {}
    returns: list[tuple[int, int]] = []
    case_results: list[dict[str, object]] = []
    slide = 0
    anchor_before = 0
    anchor_after = 0

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise a90_repl.ReplError("slide is not page-aligned; refusing to proceed")
        target_runtime = (target_link + slide) & a90_repl.MASK64
        anchor_runtime = (anchor_link + slide) & a90_repl.MASK64
        anchor_before, _anchor_before_x1 = session.call_runtime_pair(anchor_runtime, ())
        for index in range(a90_repl.CURRENT_KERNEL_TIME64_REPEAT_COUNT):
            tv_sec, tv_nsec = session.call_runtime_pair(target_runtime, ())
            returns.append((tv_sec, tv_nsec))
            nonnegative_time64 = tv_sec < (1 << 63)
            nsec_in_range = tv_nsec <= TV_NSEC_MAX
            nondecreasing = True
            delta_value: int | None = None
            delta_ok = True
            if index > 0:
                previous_sec, previous_nsec = returns[index - 1]
                previous_total = previous_sec * 1_000_000_000 + previous_nsec
                current_total = tv_sec * 1_000_000_000 + tv_nsec
                nondecreasing = current_total >= previous_total
                delta_value = current_total - previous_total if nondecreasing else previous_total - current_total
                delta_ok = nondecreasing and delta_value <= a90_repl.CURRENT_KERNEL_TIME64_MAX_SHORT_DELTA * 1_000_000_000
            case_results.append({
                "case": f"{TARGET}-timespec64-x0-x1-read-{index + 1}",
                "expected_return": "timespec64{x0=tv_sec,x1=tv_nsec}",
                "observed_tv_sec_x0": f"0x{tv_sec:x}",
                "observed_tv_nsec_x1": f"0x{tv_nsec:x}",
                "nonnegative_time64": nonnegative_time64,
                "tv_nsec_in_range": nsec_in_range,
                "nondecreasing": nondecreasing,
                "delta_nsec_from_previous": f"0x{delta_value:x}" if delta_value is not None else "n/a",
                "delta_within_bound": delta_ok,
                "within_anchor_range": False,
                "ok": False,
            })
            if not (nonnegative_time64 and nsec_in_range and nondecreasing and delta_ok):
                raise a90_repl.ReplError(
                    f"{TARGET}() return-pair failed local contract: "
                    f"tv_sec=0x{tv_sec:x} tv_nsec=0x{tv_nsec:x}"
                )
        anchor_after, _anchor_after_x1 = session.call_runtime_pair(anchor_runtime, ())
    finally:
        session.set_panic_on_oops(1)

    anchor_nondecreasing = anchor_after >= anchor_before
    anchor_delta = anchor_after - anchor_before if anchor_nondecreasing else anchor_before - anchor_after
    anchor_delta_ok = (
        anchor_nondecreasing and anchor_delta <= a90_repl.CURRENT_KERNEL_TIME64_MAX_SHORT_DELTA
    )
    for index, (tv_sec, _tv_nsec) in enumerate(returns):
        in_range = anchor_before <= tv_sec <= anchor_after if anchor_nondecreasing else False
        case_results[index]["anchor_before_x0"] = f"0x{anchor_before:x}"
        case_results[index]["anchor_after_x0"] = f"0x{anchor_after:x}"
        case_results[index]["within_anchor_range"] = in_range
        case_results[index]["ok"] = (
            bool(case_results[index]["nonnegative_time64"])
            and bool(case_results[index]["tv_nsec_in_range"])
            and bool(case_results[index]["nondecreasing"])
            and bool(case_results[index]["delta_within_bound"])
            and in_range
            and anchor_delta_ok
        )
    checks.append({
        "check": "current-kernel-time64-x0-x1-return-pair-contract",
        "ok": all(bool(case.get("ok")) for case in case_results),
        "case_count": len(case_results),
        "anchor_before": f"0x{anchor_before:x}",
        "anchor_after": f"0x{anchor_after:x}",
        "anchor_delta": f"0x{anchor_delta:x}",
        "anchor_delta_within_bound": anchor_delta_ok,
        "cases": case_results,
    })
    passed = all(bool(check.get("ok")) for check in checks)
    if not passed:
        raise a90_repl.ReplError(f"{TARGET} return-pair proof failed contract")

    first_sec, first_nsec = returns[0] if returns else (0, 0)
    summary = {
        "decision": f"a90-repl-live-call-proof-{TARGET}-return-pair-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": TARGET,
        "proof_status": "trusted-under-timespec64-x0-x1-return-pair-contract" if passed else "failed",
        "input_contract": "no arguments; kernel timekeeping xtime state is read-only",
        "return_contract": "arm64 struct timespec64 return captured as x0=tv_sec and x1=tv_nsec; tv_sec is realtime-anchor bounded and tv_nsec is 0..999999999",
        "case_results": case_results,
        "observed_first_tv_sec_x0": f"0x{first_sec:x}",
        "observed_first_tv_nsec_x1": f"0x{first_nsec:x}",
        "anchor_symbol": ANCHOR,
        "anchor_before_x0": f"0x{anchor_before:x}",
        "anchor_after_x0": f"0x{anchor_after:x}",
        "anchor_delta": f"0x{anchor_delta:x}",
        "all_tv_nsec_in_range": bool(returns) and all(tv_nsec <= TV_NSEC_MAX for _tv_sec, tv_nsec in returns),
        "all_returns_nondecreasing": all(bool(case.get("nondecreasing")) for case in case_results),
        "all_tv_sec_within_anchor_range": all(
            bool(case.get("within_anchor_range")) for case in case_results
        ),
        "repeat_count": len(returns),
        "source_evidence": static_meta["source_evidence"],
        "call_safety": static_meta["call_safety"],
        "resolutions": a90_repl._redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": TARGET,
            "status": "live-proven",
            "trusted_input_contract": "no-argument read-only timekeeping state",
            "return_contract": "timespec64 return pair x0/x1 captured by call-pair REPL variant",
            "observed_return_value": "x0 tv_sec and x1 tv_nsec passed same-call aggregate-return contract",
            "auto_call_policy": "same-session-call-pair-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        f"{TARGET}_runtime": f"0x{((target_link + slide) & a90_repl.MASK64):x}",
        f"{ANCHOR}_runtime": f"0x{((anchor_link + slide) & a90_repl.MASK64):x}",
        "return_pairs": [
            {"tv_sec_x0": f"0x{tv_sec:x}", "tv_nsec_x1": f"0x{tv_nsec:x}"}
            for tv_sec, tv_nsec in returns
        ],
        "anchor_before_pair": {"x0": f"0x{anchor_before:x}"},
        "anchor_after_pair": {"x0": f"0x{anchor_after:x}"},
    })
    return summary, private


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--dmesg-tail", type=int, default=80)
    parser.add_argument("--safe-op-retries", type=int, default=2)
    parser.add_argument("--retry-delay-sec", type=float, default=0.2)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args(argv)

    symbols = a90_repl.load_system_map(args.map)
    image = a90_repl.load_static_image(args.image)
    session = PairReplSession(
        PairReplConfig(
            host=args.host,
            port=args.port,
            timeout=args.timeout,
            dmesg_tail=args.dmesg_tail,
            safe_op_retries=args.safe_op_retries,
            retry_delay_sec=args.retry_delay_sec,
        )
    )
    summary, private = run_pair_proof(
        session,
        symbols,
        image,
        source_root=args.source_root,
    )
    if args.evidence_dir:
        write_json(args.evidence_dir / "current_kernel_time64_pair_summary.json", summary)
        write_json(args.evidence_dir / "current_kernel_time64_pair_private.json", private)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
