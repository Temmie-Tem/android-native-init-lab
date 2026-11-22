"""Wire codec for the opt-in FYG8 boot timing experiment."""
import struct

MAGIC = b'S22LTM1!'
PROPERTY = 'codex,uniloader-timing-v1'
SIZE = 128
STAGES = ('guard_passed', 'fdt_prepared', 'copies_done', 'logm_returned', 'before_report_commit')


def seed(marker):
    identity = bytes.fromhex(marker)
    if len(identity) != 32:
        raise ValueError('invalid timing candidate identity')
    return MAGIC + struct.pack('>II', 1, 0) + identity + bytes(80)


def project(data, marker, armed):
    expected = seed(marker)
    if (type(data) is not bytes or len(data) != SIZE or data[:12] != expected[:12]
            or data[12:16] != b'\0\0\0\1' or data[16:48] != expected[16:48]
            or data[96:] != expected[96:]):
        raise ValueError('invalid or uncommitted boot timing report')
    mode, frequency, *ticks = struct.unpack_from('>II5Q', data, 48)
    if type(armed) is not bool or mode != int(armed) or frequency == 0 or ticks != sorted(ticks):
        raise ValueError('boot timing mode, frequency, or counter order differs')
    durations = {
        'guard_to_fdt_prepared': ticks[1] - ticks[0],
        'payload_and_final_fdt_copy': ticks[2] - ticks[1],
        'logm_branch_and_call': ticks[3] - ticks[2],
        'report_preparation': ticks[4] - ticks[3],
        'guard_to_report_commit_sample': ticks[4] - ticks[0],
    }
    return dict(logm_enabled=armed, counter_hz=frequency, stages=dict(zip(STAGES, ticks)),
                intervals_ns={k: v * 1_000_000_000 // frequency for k, v in durations.items()})
