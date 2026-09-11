"""H0 resident composition; does not register a candidate or activate a lane.

Share the frozen framing, root command engine, return preparation and DRM path.
Replace only their explicit lifetime/service seams. Historical P385 inputs are
read without mutation. Every replacement requires a unique current boundary.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import s22plus_native_source_v1 as common

ROOT = common.ROOT
NATIVE = common.NATIVE
TEMPLATES = NATIVE / "s22plus_resident_v1"
PROFILE = "native-resident-h0-v1"
PARTS = ("wire.h", "hud.inc.c.in", "lifecycle.inc.c.in", "collect.inc.c.in",
         "render.inc.c.in", "record.inc.c.in", "gem.inc.c.in")
PROVIDER = ROOT / 'workspace/public/src/kernel-modules/s22plus_max77705_telemetry_v3'
PROVIDER_PARTS = ('Makefile', 'telemetry_core.h', 's22plus_max77705_telemetry.c')


def replace(raw: bytes, before: bytes, after: bytes) -> bytes:
    if raw.count(before) != 1:
        raise common.SourceError("resident composition boundary differs: " + repr(before[:96]))
    return raw.replace(before, after, 1)


def section(raw: bytes, start: bytes, end: bytes, value: bytes) -> bytes:
    if raw.count(start) != 1 or raw.count(end) != 1:
        raise common.SourceError("resident section boundary differs")
    a, b = raw.index(start), raw.index(end)
    if a >= b:
        raise common.SourceError("resident section order differs")
    return raw[:a] + value + raw[b:]


def read(name: str) -> bytes:
    if name not in PARTS:
        raise common.SourceError("unknown resident source")
    return common._read(TEMPLATES / name)


def profile_contract() -> dict:
    return {"profile": PROFILE, "live_activation": False, "device_contact": False,
            "normal_service_lifetime_ms": None, "counter_width": 64,
            "command_session_ms": 600000, "clean_detach_required": True,
            "child_slots": 3, "respawn": False, "log_records": 64,
            "log_record_bytes": 768, "cpu_type_count": 13,
            "clock": "CLOCK_BOOTTIME", "command_stop": "latched-until-boot-end"}


def helper_template(identity: common.Identity) -> bytes:
    pieces = [read("hud.inc.c.in") if name == "hud.inc.c.in" else common._read(common.TEMPLATES / name)
              for name in common.HELPER_PARTS]
    raw = b"".join(piece + gap for piece, gap in zip(pieces, common.HELPER_SEPARATORS, strict=True))
    hooks = common._profile_hooks(common.BASELINE_PROFILE)
    hooks.pop(b"HUD_LOG_LIMIT")
    hooks[b"LOCAL_LIFECYCLE"] = read("lifecycle.inc.c.in")
    hooks[b"BASELINE_DECLARATIONS"] += b"static void resident_export_current(void);\n"
    hooks[b"CONSOLE_HUD_STOP"] = b"resident_abandon(&s);"
    hooks[b"LOCAL_ENTRY"] = replace(common._read(common.TEMPLATES / "baseline_entry.inc.c.in"),
        b"for(;;)p282_poll_delay();", b"for(;;){local_service();p282_poll_delay();}")
    raw = common._SLOT.sub(lambda m: hooks.get(m[1], m[0]), raw)
    raw = replace(raw, b"long rc=rc1_spawn(s,body,size,now);",
                  b"resident_export_current();long rc=rc1_spawn(s,body,size,now);")
    raw = replace(raw, b"struct timespec64 n={0};long rc=p241_clock_gettime(&n);",
                  b"struct timespec64 n={0};long rc=syscall6(113,7,(long)(uintptr_t)&n,0,0,0,0);")
    raw = replace(raw, b"if(rc)return rc;\n    *out=(uint64_t)n.tv_sec*1000U+(uint64_t)n.tv_nsec/1000000U;",
        b"if(rc)return rc;\n    if(n.tv_sec<0 || n.tv_nsec<0 || n.tv_nsec>=1000000000L ||\n"
        b"       (uint64_t)n.tv_sec>((uint64_t)-1-(uint64_t)n.tv_nsec/1000000U)/1000U)return -P260_EPROTO;\n"
        b"    *out=(uint64_t)n.tv_sec*1000U+(uint64_t)n.tv_nsec/1000000U;")
    return common._expand(raw, {
        b"NAMESPACE": identity.namespace.encode(), b"NAMESPACE_UPPER": identity.namespace.upper().encode(),
        b"RUN_ID_HEX": identity.run_id_hex.encode(),
        b"RUN_ID_ESCAPED": "".join(f"\\x{v:02x}" for v in identity.run_id_hex.encode()).encode(),
        b"AUTH_KEY_BYTES": common.AUTH_KEY_PLACEHOLDER})


def materialize_helper(identity: common.Identity, auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != 32:
        raise common.SourceError("authentication key must be exactly 32 bytes")
    return replace(helper_template(identity), common.AUTH_KEY_PLACEHOLDER,
                   b", ".join(f"0x{v:02x}U".encode() for v in auth_key))


def join_platform(runtime: bytes, identity: common.Identity, auth_key: bytes) -> bytes:
    local = common.join_platform(runtime, identity, auth_key, profile=common.LOCAL_PROFILE)
    local = replace(local, common._read(common.TEMPLATES / 'local_publish.inc.c.in'), publish_source())
    return replace(local, common.materialize_helper(identity, auth_key, profile=common.LOCAL_PROFILE),
                   materialize_helper(identity, auth_key))


def publish_source() -> bytes:
    return replace(common._read(common.TEMPLATES / 'local_publish.inc.c.in'),
                   b'for(;;)p282_poll_delay();', b'for(;;){local_service();p282_poll_delay();}')


def render_display(identity: common.Identity, modules) -> bytes:
    raw = common._read(common.TEMPLATES / "display.c.in")
    raw = replace(raw, b'if (clock_gettime(CLOCK_MONOTONIC, &t)) fail("clock");',
        b'if (clock_gettime(CLOCK_MONOTONIC, &t)) fail("clock");\n'
        b'    require(t.tv_sec>=0 && t.tv_nsec>=0 && t.tv_nsec<1000000000L &&\n'
        b'        (uint64_t)t.tv_sec<=((uint64_t)INT64_MAX-(uint64_t)t.tv_nsec/1000000)/1000,"clock-range");')
    raw = section(raw, b"static unsigned hud_mem_alloc,", b"struct buffer {", read("gem.inc.c.in"))
    raw = section(raw, b"#define STATUS_MEM 1U", b"struct status_cpu {", b'#include "s22plus_resident_v1/wire.h"\n')
    gauge = common._read(NATIVE / "s22plus_gauge_sample_v2.inc.c")
    gauge = replace(gauge, b"S22FG1 seq=", b"S22FGR1 seq=")
    gauge = replace(gauge, b"if(!s.sequence||s.sequence>601)", b"if(!s.sequence)")
    raw = section(raw, b'#include "s22plus_gauge_sample_v2.inc.c"',
                  b"/* Text-only immutable frame:", gauge + read("collect.inc.c.in"))
    raw = section(raw, b"static struct status_metrics hud_metrics;", b"static struct hud_snapshot hud_wait_snapshot",
                  read("render.inc.c.in"))
    raw = section(raw, b"static void hud_record(", b"static void hud_single_encoder(", read("record.inc.c.in"))
    raw = replace(raw, b'if(argc==3 && !strcmp(argv[1],"--collect-status"))return status_collect(argv[2]);',
        b'if(argc==3 && !strcmp(argv[1],"--collect-system"))return status_collect(argv[2],0);\n'
        b'    if(argc==3 && !strcmp(argv[1],"--collect-hardware"))return status_collect(argv[2],1);')
    raw = replace(raw, b"for(uint64_t token=2;token<=@@DISPLAY_FRAME_LIMIT@@;token++) {",
                  b"for(uint64_t token=2;;token++) {\n        require(token<UINT64_MAX,\"hud-token-exhausted\");")
    for name in (b"b", b"fresh"):
        raw = replace(raw, b"paint(&" + name + b",(unsigned)(view.uptime_ms/1000U>0xffffffffU?0xffffffffU:view.uptime_ms/1000U))",
                      b"paint(&" + name + b",view.uptime_ms/1000U)")
    raw = replace(raw, b"||values[0]>UINT32_MAX||!values[2]||values[2]>@@DISPLAY_FRAME_LIMIT@@", b"||!values[2]||values[2]==UINT64_MAX")
    raw = raw.replace(b"CLOCK_MONOTONIC", b"CLOCK_BOOTTIME")
    labels = ("CONSOLE: READY", "CONSOLE: BUSY", "CONSOLE: BLOCKED", "WAITING FOR AUTH",
              "COMMAND STOPPED", "COMMAND EXPIRED", "PREPARING", "COMMAND STOPPED", "CLOSING")
    states = b"((const char *const[]){" + b",".join(b'"'+s.encode()+b'"' for s in labels) + b"})[hud_console_state]"
    return common._expand(raw, {b"DISPLAY_VERSION": identity.display_version.encode(),
        b"MEMORY_CENSUS": common.memory_census(modules), b"DISPLAY_STATE_TEXT": states})


def source_files() -> tuple[Path, ...]:
    return tuple(sorted(set(common.source_files()) | {Path(__file__).resolve()} |
                        {TEMPLATES / name for name in PARTS} | {PROVIDER / name for name in PROVIDER_PARTS}))


def source_inventory() -> dict:
    return {str(p.relative_to(ROOT)): {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for p in source_files() for raw in [common._read(p)]}


def provider_sources() -> dict[str, bytes]:
    """Preserve the exact existing read-only binding/register/ABI surface.

    The new wire prefix separates boottime/64-bit samples from the consumed
    601-sample provider. Its source stays unchanged and is bound as an input.
    """
    files = {name: common._read(PROVIDER / name) for name in PROVIDER_PARTS}
    core = files['telemetry_core.h']
    core = replace(core, b'#define S22_TELEMETRY_MAX_SAMPLES 601U',
                   b'#define S22_TELEMETRY_MAX_SAMPLES (~0ULL)')
    core = replace(core, b'unsigned int sequence, valid;', b'unsigned long long sequence;\n    unsigned int valid;')
    core = replace(core, b'unsigned int attempts;', b'unsigned long long attempts;')
    files['telemetry_core.h'] = core
    wrapper = files['s22plus_max77705_telemetry.c']
    wrapper = replace(wrapper, b'now = ktime_to_ms(ktime_get());', b'now = ktime_to_ms(ktime_get_boottime());\n'
        b'    if (cached.sequence && now < cached_start_ms) { count = -EPROTO; state.stopped = -EPROTO; goto out; }\n'
        b'    if (state.attempts == S22_TELEMETRY_MAX_SAMPLES) { count = -EOVERFLOW; goto out; }')
    wrapper = replace(wrapper, b'S22FG1 seq=%u', b'S22FGR1 seq=%llu')
    wrapper = replace(wrapper, b'S22FGD1 probe=', b'S22FGRD1 probe=')
    wrapper = replace(wrapper, b'attempts=%u stopped=', b'attempts=%llu stopped=')
    files['s22plus_max77705_telemetry.c'] = wrapper
    return files
