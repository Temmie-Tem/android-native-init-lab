"""Sealed startup observation data; no device action or independent authority."""
from pathlib import Path
import functools
import hashlib
import json
import tarfile

import s22plus_debian_handoff_profile_v1 as handoff
from s22plus_native_records_v3 import require, verify

RC_SHA = "4d635aada7b8bc96bf84a7d9c7799b98125556d8919a9b32a3e8ab22ccb2b035"
RCS_SHA = "93ddb20455e8dc3ad6dcd9aa178bf908e0e1ae88afaa9a470d040e90c0846c0c"
MODULE_SHA = "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599"
LIMITS = dict(start_before_ms=8500, absolute_window_ms=15000, kernel_record_cap=28, script_record_cap=34,
              phase_budget_ms=2000, cleanup_reserve_ms=500, maximum_handovers=1,
              ring_request_kib=16, ring_maximum_kib=20)
# Slow generic full-root verification finishes after the physical startup
# window. This explicit VM-only adapter preserves raw BOOTTIME and all budgets.
# Diskless component fixtures use the physical limits, including late cleanup.
VM_TIMING = dict(start_before_ms=58500, absolute_window_ms=65000)
# id, event, exact module-local body, byte offset, selected signed registers.
# No kretprobe, SMC probe, memory fetch, instruction skip or register write.
PROBES = (
    (1, "timer_enter", "qcom_wdt_pet_task_wakeup", 0, ""),
    (2, "timer_wait_exit", "qcom_wdt_kthread", 0x160, ""),
    (3, "ping_enter", "qcom_wdt_kthread", 0x268, "cpu=%x22:s32"),
    (4, "ping_return", "qcom_wdt_kthread", 0x26c, "cpu=%x22:s32 rc=%x0:s32"),
    (5, "pet_enter", "qcom_wdt_kthread", 0x2c4, ""),
    (6, "pet_return", "qcom_wdt_kthread", 0x2c8, "rc=%x0:s32"),
    (7, "notifier_enter", "qcom_wdt_kthread", 0x2e4, ""),
    (8, "notifier_boundary", "qcom_wdt_kthread", 0x2e8, "rc=%x0:s32"),
    (9, "freeze_lock_enter", "qcom_wdt_kthread", 0x2f4, ""),
    (10, "freeze_lock_acquired", "qcom_wdt_kthread", 0x2f8, ""),
    (11, "timer_rearm_enter", "qcom_wdt_kthread", 0x310, ""),
    (12, "timer_rearm_return", "qcom_wdt_kthread", 0x314, "rc=%x0:s32"),
)
SCRIPTS = (
    "S01hostname.sh", "S01mountkernfs.sh", "S02udev", "S03mdev",
    "S03mountdevsubfs.sh", "S06kmod", "S07mount-configfs", "S07mountall.sh",
    "S08mountall-bootclean.sh", "S09brightness", "S09procps", "S09urandom",
    "S10networking", "S11mountnfs.sh", "S12mountnfs-bootclean.sh", "S13bootmisc.sh",
)


def transform(raw):
    require(hashlib.sha256(raw).hexdigest() == RC_SHA, "retained rc dispatcher differs")
    text = raw.decode()
    # One exclusive nonblocking datagram endpoint is assigned to fd3 by the
    # parent. Failed optional writes cannot change the saved service status.
    insert = """ap_count=0
ap_emit() {
    ap_count=$((ap_count + 1))
    printf '%s %s %s %s\\n' "$ap_count" "$1" "$2" "$3" >&3 2>/dev/null || :
}
ap_emit D 0 0
"""
    text = text.replace("umask 022\n", "umask 022\n\n" + insert, 1)
    old = '''\t\t\tfor script ; do
\t\t\t\t"$script" "$action"
\t\t\tdone'''
    cases = "\n".join(
        f"\t\t\t\t/etc/rcS.d/{name}) ap_id={i} ;;"
        for i, name in enumerate(SCRIPTS, 1)
    )
    new = '''\t\t\tap_status=0
\t\t\tfor script ; do
\t\t\t\tap_id=0
\t\t\t\tcase "$script" in
''' + cases + '''
\t\t\t\tesac
\t\t\t\t[ "$ap_id" -eq 0 ] || ap_emit B "$ap_id" 0
\t\t\t\t"$script" "$action" 3>&-
\t\t\t\tap_status=$?
\t\t\t\t[ "$ap_id" -eq 0 ] || ap_emit E "$ap_id" "$ap_status"
\t\t\tdone
\t\t\treturn "$ap_status"'''
    require(text.count(old) == 1, "serial dispatcher invocation differs")
    text = text.replace(old, new)
    replacements = {
        "stty onlcr 0>&1": "stty onlcr 0>&1 3>&-",
        ". /etc/default/rcS": ". /etc/default/rcS 3>&-",
        ". /lib/lsb/init-functions": ". /lib/lsb/init-functions 3>&-",
        "grep -wqs concurrency=none /proc/cmdline": "grep -wqs concurrency=none /proc/cmdline 3>&-",
        '$(uname)': '$(uname 3>&-)',
        "mount -t linprocfs linprocfs /proc": "mount -t linprocfs linprocfs /proc 3>&-",
        "mount -t proc linprocfs /proc": "mount -t proc linprocfs /proc 3>&-",
        "mount -t proc none /proc -ocompatible": "mount -t proc none /proc -ocompatible 3>&-",
        "mount -t proc none /proc\n": "mount -t proc none /proc 3>&-\n",
        "startpar -p 4 -t 20 -T 3 -M $1 -P $previous -R $runlevel":
            "startpar -p 4 -t 20 -T 3 -M $1 -P $previous -R $runlevel 3>&-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("trap - EXIT", "ap_emit X 0 0\n\ntrap - EXIT", 1)
    return text.encode()


@functools.lru_cache(maxsize=1)
def original_scripts():
    artifact, _, _ = handoff.prior_inputs()
    scripts = {}
    with tarfile.open(verify(artifact["rootfs"], maximum=256*1024**2), "r:*") as archive:
        for name, digest in (("usr/lib/init/rc", RC_SHA), ("usr/lib/init/rcS", RCS_SHA)):
            member = archive.getmember(name)
            require(member.isreg() and member.uid == member.gid == 0
                    and 0 < member.size <= 16384, "retained dispatcher metadata differs")
            with archive.extractfile(member) as stream:
                body = stream.read(member.size + 1)
            require(len(body) == member.size and hashlib.sha256(body).hexdigest() == digest,
                    "retained dispatcher bytes differ")
            scripts[name] = body
    require(scripts["usr/lib/init/rcS"].endswith(b"exec /etc/init.d/rc S\n"),
            "rcS is not the exact selected wrapper")
    return scripts


def definitions():
    return tuple(
        f"p:s22phase/{name} qcom_wdt_core:{symbol}+0x{offset:x}"
        + (" " + fields if fields else "") + "\n"
        for _, name, symbol, offset, fields in PROBES
    )


def dispatcher():
    return transform(original_scripts()["usr/lib/init/rc"])


def declaration():
    """One declaration shared by generated ARM64 code and H0 interpretation."""
    original = original_scripts()
    observed = dispatcher()
    return dict(
        schema="s22plus-autoboot-phase-declaration-v1",
        module_sha256=MODULE_SHA,
        probes=[dict(id=i, name=n, symbol=s, offset=o, fields=f, definition=d)
                for (i, n, s, o, f), d in zip(PROBES, definitions())],
        scripts=list(SCRIPTS),
        original={name: dict(size=len(body), sha256=hashlib.sha256(body).hexdigest())
                  for name, body in original.items()},
        dispatcher=dict(size=len(observed), sha256=hashlib.sha256(observed).hexdigest()),
        trace_group="s22phase", trace_instance="s22phase",
        trace_path="/run/s22-debian/phase-trace",
        dispatcher_path="/run/s22-debian/rc-observed",
        **LIMITS,
    )


def probe_header():
    """Public fixed producer data, also used by target-ABI parser tests."""
    lines = ["/* Generated from the exact retained rc and fixed phase declaration. */",
             "#define AP_PROBE_COUNT 12U", "#define AP_SCRIPT_COUNT 16U",
             "struct ap_probe { unsigned id,fields; const char *name,*definition,*readback,*symbol; };",
             "static const struct ap_probe ap_probes[]={"]
    for (i, name, symbol, offset, fields), definition in zip(PROBES, definitions()):
        mask = (1 if "cpu=" in fields else 0) | (2 if "rc=" in fields else 0)
        readback = f"p:s22phase/{name} qcom_wdt_core:{symbol}" + (f"+{offset}" if offset else "")
        readback += (" " + fields if fields else "") + "\n"
        body = f"{symbol}+0x{offset:x}/0x"
        lines.append(f"{{{i}U,{mask}U,{json.dumps(name)},{json.dumps(definition)},{json.dumps(readback)},{json.dumps(body)}}},")
    lines += ["};", 'static const char ap_module_suffix[]=" [qcom_wdt_core]";']
    lines += [f"#define AP_{name.upper()} {value}U" for name, value in LIMITS.items()]
    return ("\n".join(lines) + "\n").encode()


def header(*,virt=False):
    """Embed only the fixed RAM dispatcher and fixed probe declaration."""
    observed = dispatcher()
    probes = probe_header().decode()
    if virt:
        probes = '#ifndef S22_ROOT_INSPECT_VIRT_TEST\n#error "phase timing adapter is VM-only"\n#endif\n' + probes
        for name,value in VM_TIMING.items():
            probes = probes.replace(f"#define AP_{name.upper()} {LIMITS[name]}U",
                                    f"#define AP_{name.upper()} {value}U")
    lines = [probes, "static const unsigned char ap_dispatcher[]={" +
             ",".join(map(str, observed)) + "};"]
    for name, body in original_scripts().items():
        label = "rcs" if name.endswith("/rcS") else "rc"
        lines += [f"static const uint64_t ap_{label}_size={len(body)}ULL;",
                  f"static const uint8_t ap_{label}_sha[]={{" +
                  ",".join(map(str, hashlib.sha256(body).digest())) + "};"]
    return ("\n".join(lines) + "\n").encode()

