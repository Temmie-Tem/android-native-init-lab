"""v0.1.2-rc.3 observed model binding and optional native memory snapshots."""
from s22plus_fyg8_p380_namespace import load_predecessor
load_predecessor(globals())

# Optional diagnostics use stderr; stdout remains the unchanged HUD proof.
# No command budget, transport, qualification count or gauge criterion changes.
MEMORY_COMMAND = (
    b'm(){ echo "MEM_SNAPSHOT $1"; '
    b'for p in uptime meminfo 1/status; do echo "MEM_FILE $p"; '
    b'/bin/busybox head -c 8192 /proc/$p 2>&1; echo; done; '
    b'echo MEM_MODEL; /bin/busybox head -c 256 /proc/device-tree/model 2>&1; echo; '
    b'echo MEM_PS; /bin/busybox ps -o pid,ppid,vsz,rss,comm 2>&1 | '
    b'/bin/busybox head -c 16384; echo; echo MEM_END; }; '
)
_gauge_command = HUD_COMMAND
assert _gauge_command.endswith(b'/bin/busybox cat hud.log')
_wait = _gauge_command[:-len(b'/bin/busybox cat hud.log')]
# At least two one-second intervals separate the samples even if the gauge
# already has three fresh records. The existing twelve-iteration cap remains.
_wait = _wait.replace(b'[ "$(/bin/busybox awk', b'[ "$n" -ge 2 ] && [ "$(/bin/busybox awk', 1)
HUD_COMMAND = MEMORY_COMMAND + b'm early >&2; ' + _wait + b'm late >&2; /bin/busybox cat hud.log'
assert len(HUD_COMMAND) <= 1023
QUALIFICATION_COMMANDS = QUALIFICATION_COMMANDS[:-1] + (
    QualificationStep(6, 'fresh-gauge-hud-with-optional-memory-snapshots', HUD_COMMAND, b''),)
_memory_qualified = _qualified_step


def _qualified_step(row, step, events):
    if step.ordinal != 6:
        return _memory_qualified(row, step, events)
    # The authenticated stderr receipt is retained and replay-compared as usual.
    # Its optional memory values/availability cannot certify or reject the HUD.
    projected = dict(row, stderr=identity(b''))
    return _memory_qualified(projected, step, events)


_memory_audit = audit_binding


def audit_binding():
    value = _memory_audit()
    value.update(optional_memory_snapshots=2, memory_stream='authenticated-stderr',
                 memory_minimum_interval_seconds=2, memory_required_for_gauge=False)
    return value
