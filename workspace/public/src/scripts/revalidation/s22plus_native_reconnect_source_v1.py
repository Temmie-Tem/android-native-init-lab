"""Idle tty reacquisition over the frozen rc.9 thermal V3 composition.

Authentication, commands, telemetry and historical source identities remain
shared. This new profile alone changes the zero-byte OPEN transport owner.
"""
from pathlib import Path

import s22plus_native_thermal_source_v3 as previous

resident = previous.resident
common = resident.common
ROOT, NATIVE, PROFILE = previous.ROOT, previous.NATIVE, previous.PROFILE
THERMAL_PROFILE = previous.THERMAL_PROFILE
RECONNECT_PROFILE = 'idle-tty-reconnect-v1'
TEMPLATES = NATIVE/'s22plus_usb_reconnect_v1'
PARTS = ('transport.inc.c.in', 'entry.inc.c.in')
SAMPLE_MAGIC, VIEW_MAGIC = previous.SAMPLE_MAGIC, previous.VIEW_MAGIC
render_display = previous.render_display
provider_sources = previous.provider_sources
provider_files = previous.provider_files
core_source = previous.core_source
sensor_map = previous.sensor_map
wire_source = previous.wire_source


def upgrade_native(raw, identity):
    old = common._profile_hooks(common.BASELINE_PROFILE)[b'READ_ABSENT_PEER']
    new = resident.replace(old, b'amount=-EAGAIN;', b'return UR1_IDLE_LINK_LOST;')
    raw = resident.replace(raw, old, new)
    old_entry = resident.replace(common._read(common.TEMPLATES/'baseline_entry.inc.c.in'),
        b'for(;;)p282_poll_delay();', b'for(;;){local_service();p282_poll_delay();}')
    new_entry = common._read(TEMPLATES/'transport.inc.c.in')+b'\n'+common._read(TEMPLATES/'entry.inc.c.in')
    raw = resident.replace(raw, old_entry.replace(b'@@NAMESPACE@@', identity.namespace.encode()),
        new_entry.replace(b'@@NAMESPACE@@', identity.namespace.encode()))
    return b'#define UR1_IDLE_LINK_LOST (-4096L)\n'+raw


def helper_template(identity):
    return upgrade_native(previous.helper_template(identity), identity)


def materialize_helper(identity, key):
    return upgrade_native(previous.materialize_helper(identity, key), identity)


def profile_contract():
    return dict(previous.profile_contract(), reconnect_profile=RECONNECT_PROFILE,
        reconnect_scope='idle zero-byte OPEN only; initial or after completed DETACH',
        reconnect_retry_ms=1000, tty_vmin=1, tty_vtime=0,
        reconnect_preserves='boot identity, ordinal, nonce history, preparation, service, terminal latch',
        gadget_close_max_wait_ms=15000, host_ack_receipt_required=True)


def source_files():
    return tuple(sorted(set(previous.source_files()) | {Path(__file__)} |
        {TEMPLATES/name for name in PARTS}))
