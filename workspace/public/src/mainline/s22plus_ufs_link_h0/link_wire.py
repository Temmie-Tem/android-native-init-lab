"""Offline decoding of the fixed ML030 late witness and module result."""
import hashlib
import hmac
import re
import struct

DOMAIN = b"G0Q-DEBIAN-DOWNLOAD-RAM-v1"
HEADER = struct.Struct("<8s32s32s32s16sQQ")
RESULT_SIZE = HEADER.size + 12 + 256 + 32
GAP_MS = 300000
END_MS = 540000
FLOOR_MS = 60000  # opt-in route-scope witness floor (guest BOOTTIME)
RECOVERY_TRIGGER_MS = 555000
RECOVERY_LAST_MS = 570000
RECOVERY_MODE = 'S22PLUS_UFS_V6_CHILD_RESTART2_V1'


def recovery_packet(key, identity, n0, nonce, boot, *, late=False):
    check(len(n0)==len(nonce)==32 and len(boot)==16 and any(n0) and any(nonce) and any(boot)
          and (n0!=nonce if late else n0==nonce), 'recovery identity fields')
    body=HEADER.pack(b'G040LIV1' if late else b'G040ARM1',identity,n0,nonce,boot,
                     RECOVERY_TRIGGER_MS,RECOVERY_LAST_MS)
    return body+tag(key,identity,22 if late else 21,body)


def recovery_arm(raw, key, identity, n0, nonce, boot, *, late=False):
    """A fresh child IPC reply, not proof that a future reboot will complete."""
    expected = recovery_packet(key,identity,n0,nonce,boot,late=late)
    check(hmac.compare_digest(raw, expected), 'automatic recovery arm binding')
    return dict(mode=RECOVERY_MODE, trigger_ms=RECOVERY_TRIGGER_MS, latest_syscall_ms=RECOVERY_LAST_MS,
                child_reply_observed=True, reboot_completion_proved=False)


def return_allowed(facts):
    return facts.get('normal_return') is True or facts.get('recovery_return') is True


try:
    from . import report_modes
except ImportError:  # imported as a top-level module beside its sources
    import report_modes

# Report schema per module report version, from the single declaration.
# Tags are report_modes.tag(version) from v4 (version << 28 through v15); v5's HCI snapshot is the only side branch.
REPORT_FIELDS = report_modes.FIELDS
HANDOFF, RESET_CONFIG, DISABLED_UCRDY, STALE_ACK = (report_modes.FIRST[k] for k in
    ('hce_handoff', 'reset_config', 'disabled_ucrdy', 'stale_uccs_ack'))
STORAGE_READ = report_modes.FIRST['storage_read']
STORAGE_HEADER = report_modes.FIRST['storage_header']
STORAGE_RESPONSE = report_modes.FIRST['storage_response']
CFG1, ORDERED_SELECTION, LINK_IRQ, UPSTREAM_LINK = (report_modes.FIRST[k] for k in
    ('cfg1_diagnostics', 'cfg1_ordered_selection', 'link_irq_diagnostics', 'upstream_link'))
# UIC error-code registers 0x38..0x48 (ufshci.h). PA/DL are reported raw;
# N/T/DME share one word: (code shift, code mask, error bit, reserved bit).
UEC_RAW = (('PA', 0x1f), ('DL', 0xffff))
UEC_PACKED = (('N', 0, 0x7, 16, 24), ('T', 3, 0x7f, 17, 25), ('DME', 10, 0x1, 18, 26))


def recovery_result(facts, raw, report_version):
    if report_version < HANDOFF:
        return facts
    return dict(facts, recovery_return=True, recovery_mode=RECOVERY_MODE,
                control_nonce=hashlib.sha256(raw).digest())
USB_REASONS = ('OK', 'USB_HELD', 'RUN_STATE', 'USB_NODE', 'USB_DEVICE', 'USB_LOCK',
               'USB_DRIVER', 'USB_DATA', 'USB_PM', 'ICC_NODE', 'ICC_PATH', 'ICC_LENGTH',
               'ICC_LOCK', 'ICC_REQUEST', 'BCM_GLOBAL_LOCK', 'BCM_VOTER', 'BCM_LOCK',
               'BCM_PENDING', 'BCM_UNKNOWN', 'BCM_VALUES', 'COVER_CEILING')
USB_LOCKS = {5, 12, 14, 16}
STAGE2_COMPONENTS = ('NONE', 'HCI', 'RESET', 'CORE', 'UNIPRO', 'VCC', 'VCCQ', 'REF_PAD', 'PARENT')
STAGE2_OPERATIONS = ('NONE', 'DEADLINE', 'UFS_VERSION', 'HW_VERSION', 'QUIESCENT',
                     'PIN_GUARD', 'SET_RATE', 'RATE_READBACK', 'GET_SUPPLY', 'BEFORE_LOAD',
                     'SET_LOAD', 'BEFORE_VOLTAGE', 'SET_VOLTAGE', 'BEFORE_ENABLE', 'ENABLE',
                     'VOLTAGE_READBACK', 'SEED_GET', 'SEED_DEADLINE', 'SEED_VOLTAGE',
                     'PARENT_READBACK', 'AFTER_SUPPLY', 'HANDOFF_ADMISSION',
                     'HANDOFF_DEADLINE', 'HANDOFF_DRIFT', 'HANDOFF_TIMEOUT', 'HANDOFF_STATE',
                     'ACK_DEADLINE', 'ACK_DRIFT', 'ACK_READBACK')
STAGE2_CHECKS = ('HCE', 'HCS', 'TRANSFER_DOORBELL', 'TASK_DOORBELL', 'TRANSFER_RUN',
                 'TASK_RUN', 'IRQ_ENABLE', 'IRQ_STATUS', 'AUTO_HIBERNATE', 'RESET_OUTPUT', 'RESET_HIGH')
RESET_CONFIG_CHECKS = STAGE2_CHECKS[:9] + ('RESET_CONFIG', 'RESET_LATCH_HIGH')
RESET_CTL_EXPECTED = 0x0000000b
HCI_SAMPLES = ('HCE', 'HCS', 'TRANSFER_DOORBELL', 'TASK_DOORBELL', 'IRQ_ENABLE', 'IRQ_STATUS')


def check(value, message):
    if not value:
        raise ValueError(message)


def tag(key, identity, kind, body):
    check(len(key) == len(identity) == 32, "key or identity length")
    return hmac.digest(key, DOMAIN + identity + bytes([kind]) + body, "sha256")


def frame(magic, kind, key, identity, first, second, boot, t0, t1, *, floor_ms=None):
    check(len(first) == len(second) == 32 and len(boot) == 16 and first != second and
          any(first) and any(second) and any(boot), "late identity fields")
    check(floor_ms is None or (type(floor_ms) is int and floor_ms == FLOOR_MS), "late witness floor")
    later = (t0 + GAP_MS <= t1) if floor_ms is None else (floor_ms <= t1 and t0 < t1)
    check(0 < t0 < 120000 and (t1 == 0 or (later and t1 < END_MS)), "late uptime fields")
    body = HEADER.pack(magic, identity, first, second, boot, t0, t1)
    return body + tag(key,identity,kind,body)


def witness(raw, key, identity, first, second, boot, t0, *, floor_ms=None):
    check(len(raw) == HEADER.size+32, "incomplete late witness")
    t1 = HEADER.unpack_from(raw)[-1]
    check(t1 > 0 and hmac.compare_digest(raw,frame(b"G030WIT1",17,key,identity,first,second,boot,t0,t1,
                                                   floor_ms=floor_ms)),
          "late witness authentication")
    return t1


def usb_diagnostics(values):
    rc, *_, usb, release, word, detail = values
    check(0 <= word < 1 << 24 and 0 <= detail < 1 << 32, 'USB report word range')
    code, first, attempts = word & 255, (word >> 8) & 255, word >> 16
    check(code < len(USB_REASONS) and first in ({0} | USB_LOCKS) and attempts <= 25,
          'USB reason or attempt range')
    check((attempts > 0 or (code in (2, 20) and first == 0)) and
          (attempts <= 1 or first in USB_LOCKS) and
          (code not in USB_LOCKS or first in USB_LOCKS) and
          (attempts != 1 or first == 0 or code in (2, 20) or first == code),
          'USB retry history')
    if code == 0:
        check(usb == release == 1 and detail == 0 and attempts > 0, 'USB successful coverage')
    else:
        check(rc < 0 and usb == release == 0 and not any(values[1:16]),
              'USB rejected before hardware')
        check(values[16] == 0 or (code == 2 and values[16] == rc), 'USB run-state error')
        fixed = {1:22, 3:19, 4:19, 5:16, 6:19, 7:19, 9:19, 11:22, 12:16,
                 13:16, 14:16, 15:19, 16:16, 17:16, 18:16, 19:16, 20:110}
        check(code not in fixed or rc == -fixed[code], 'USB branch errno')
        if code in USB_LOCKS or code in (1, 4, 15, 20):
            check(detail == 0, 'USB unexpected detail')
        elif code == 2:
            check(detail == rc % (1 << 32), 'USB run-state errno')
        elif code in (3, 6, 7):
            check(detail in (1, 2), 'USB identity detail')
        elif code == 8:
            check(detail == 0 and rc == -16 or detail >= (1 << 31) and detail == rc % (1 << 32),
                  'USB PM API return')
        elif code == 9:
            check(detail in (1, 2, 3), 'ICC missing-node detail')
        elif code == 10:
            check(detail == 0 and rc == -19 or -4095 <= rc < 0 and detail == rc % (1 << 32),
                  'ICC path errno')
        elif code == 11:
            check(detail != 4, 'ICC path length')
        elif code == 13:
            check(detail >> 16 < 4 and 0 < (detail & 65535) < 128, 'ICC request flags')
        elif code == 17:
            check(detail == 1, 'BCM pending detail')
        elif code == 18:
            check(detail in (0, 1), 'BCM unknown index')
        elif code == 19:
            check(detail & ~0x10fff == 0 and (detail & 0xfff) != (0x455 if detail >> 16 else 0x444),
                  'BCM protected scalar snapshot')
    return dict(usb_reason=USB_REASONS[code], usb_first_lock=USB_REASONS[first],
                usb_attempts=attempts, usb_detail=detail)


def stage2_diagnostics(values, *, handoff=False, reset_config=False, disabled_ucrdy=False, stale_ack=False):
    """Decode observed short-circuit predicates, never infer unobserved reads."""
    rc, stage, version = values[:3]
    site, word = values[21:]
    check(0 <= site < 1 << 16 and 0 <= word < 1 << (32 if stale_ack else 28), 'stage-two report word range')
    observed, failed, hcs = word & 0x7ff, (word >> 11) & 0x7ff, (word >> 22) & 0x3f
    check(not (observed & (observed + 1)) and not (failed & ~observed) and
          not (failed & (failed - 1)), 'stage-two short-circuit history')
    hazard = hcs & (0x31 if disabled_ucrdy else 0x39)
    check(not hcs & ~0x39 and bool(hazard) == bool(failed & 2) and
          (not hcs or observed & 2), 'stage-two HCS sample and predicate bits')
    failure = None
    if not site:
        check(not failed and (stage < 2 and observed == 0 or stage > 2 and observed == 0x7ff),
              'stage-two missing or unexpected evidence')
    else:
        component, operation = site >> 8, site & 255
        allowed = {1:{1,2,3,4}, 2:{5}, 3:{1,6,7}, 4:{1,6,7},
                   5:{8,9,10,11,12,13,14,15,20}, 6:{8,9,10,11,12,13,14,15,20},
                   7:{8,9,10,11,12,13,14,15,20}, 8:{8,9,10,13,14,16,17,18,19,20}}
        if handoff:
            allowed[1] |= {21,22,23,24,25}
        if stale_ack:
            allowed[1] |= {26,27,28}
        check(component in allowed and operation in allowed[component], 'stage-two failure site')
        check(stage == 2 and -4095 <= rc < 0 and not any(values[3:11]),
              'stage-two failure before later hardware')
        fixed_errno = {1:110, 2:19, 3:19, 4:16, 5:16, 7:34, 9:110,
                       11:110, 13:110, 15:34, 17:110, 19:34,
                       21:16, 22:110, 23:16, 24:110, 25:5, 26:110, 27:16, 28:5}
        check(operation not in fixed_errno or rc == -fixed_errno[operation], 'stage-two branch errno')
        if component == 1 and operation <= 3:
            check(observed == failed == 0, 'stage-two early HCI evidence')
            check(version == 0 if operation < 3 else version >> 28 != 4, 'stage-two HCI version')
        elif component == 1 and operation >= 26:
            check(observed == 0x7ff and failed == 0 and version >> 28 == 4,
                  'initial acknowledgement needs all eleven guards')
        elif component == 1 and operation >= 21:
            check(observed == failed == hcs == 0 and version >> 28 == 4,
                  'handoff failure must precede post-state predicates')
        elif component == 1:
            check(0 < observed <= 0x1ff and failed == (observed ^ (observed >> 1)),
                  'stage-two first HCI rejection')
        elif component == 2:
            check(observed in (0x3ff, 0x7ff) and failed == (observed ^ (observed >> 1)),
                  'stage-two first reset rejection')
        else:
            check(observed == 0x7ff and failed == 0, 'stage-two completed guards')
        if component != 1 or operation == 4:
            check(version >> 28 == 4, 'stage-two admitted HCI version')
        failure = dict(component=STAGE2_COMPONENTS[component], operation=STAGE2_OPERATIONS[operation])
    return dict(stage2_site=site, stage2_failure=failure, stage2_observed=observed, stage2_failed=failed,
                stage2_hcs_masked=hcs if observed & 2 else None,
                stage2_conditions={name:('UNOBSERVED' if not observed & (1 << i) else
                                        'FAIL' if failed & (1 << i) else 'PASS')
                                   for i, name in enumerate(RESET_CONFIG_CHECKS if reset_config else STAGE2_CHECKS)})


def hci_snapshot(values):
    """Raw captures never upgrade the separate short-circuit predicate proof."""
    captured, *samples = values[23:]
    check(len(samples) == 6 and 0 <= captured < 64 and not (captured & (captured + 1)) and
          all(0 <= x < 1 << 32 for x in samples), 'HCI snapshot shape')
    observed, failed = values[22] & 0x7ff, (values[22] >> 11) & 0x7ff
    check(bool(captured) == bool(observed & 1) and
          bool(samples[0]) == bool(failed & 1), 'HCI snapshot original predicate')
    check(all(value == 0 for i, value in enumerate(samples) if not captured & (1 << i)),
          'HCI uncaptured value')
    if captured > 1:
        check(samples[0] in (1, 2, 3) and values[:2] == [-16, 2] and
              values[21] & 0xffff == 0x104 and observed == failed == 1,
              'HCI additional read outside refusal scope')
    hw_read = values[1] >= 2 and (values[21] & 0xffff) not in (0x101, 0x102)
    return dict(hci_snapshot_captured=captured, hci_hw_version=values[2] if hw_read else None,
                hci_snapshot={name:(samples[i] if captured & (1 << i) else None)
                              for i, name in enumerate(HCI_SAMPLES)})


def hce_handoff(values, *, reset_config=False, stale_ack=False):
    """Versioned stop history; V8 permits UCRDY in disabled-state checks."""
    word, pre_hce, pre_hcs, pre_is, last_hce, index, raw = values[23:30]
    check(0 <= word < 1 << 32, 'handoff metadata range')
    flags, polls, elapsed = word & 8191, (word >> 13) & 127, word >> 20
    check(0 <= flags <= 8191 and not flags & (flags + 1) and
          all(0 <= n < 1 << 32 for n in values[24:38]) and index <= 11,
          'handoff report shape or read prefix')
    check(bool(polls) == bool(flags & 1024) and (flags & 512 or elapsed == 0) and
          (not flags & 4096 or elapsed < 1000), 'handoff poll/time history')
    site = values[21] & 0xffff
    observed, failed = values[22] & 0x7ff, (values[22] >> 11) & 0x7ff
    check((flags & 1 or pre_hce == 0) and (flags & 2 or pre_hcs == 0) and
          (flags & 32 or pre_is == 0) and (flags & 256 or last_hce == 0) and
          (index or raw == 0), 'handoff uncaptured values')
    check(flags <= 1 or pre_hce == 1, 'handoff expanded a cold or unknown HCE')
    check(bool(flags & 2048) == bool(flags & 1024 and last_hce == 0),
          'handoff zero/readback history')
    check(not flags & 512 or flags & 1024 or last_hce == 1,
          'handoff issued without final enabled sample')
    post = flags == 8191 or flags == 1 and pre_hce == 0
    check(bool(observed) == post and not failed & 1,
          'post-state predicates lack cold entry or timely stop')
    # A completed pre-read only permits progression if its admission passed.
    if flags >= 3 and site != 0x115:
        check(pre_hcs & 8 and not pre_hcs & 0x30, 'handoff HCS admission')
    if flags >= 63 and site != 0x115:
        check(pre_is in (0, 0x400), 'handoff interrupt admission')
    phase = None
    if site == 0x115:
        admission = {
            1:(1, pre_hce not in (0,1), pre_hce),
            3:(2, not pre_hcs & 8 or bool(pre_hcs & 0x30), pre_hcs),
            7:(3, raw != 0, raw), 15:(4, raw != 0, raw),
            31:(7, raw != 0, raw),
            63:(8, pre_is not in (0,0x400), pre_is),
            127:(10, raw != RESET_CTL_EXPECTED if reset_config else not raw & (1 << 31), raw),
            255:(11, not raw & 1, raw),
        }
        check(flags in admission, 'handoff admission failure prefix')
        expected, rejected, sample = admission[flags]
        check(index == expected and rejected and raw == sample, 'handoff admission refusal')
        if flags > 3:
            check(pre_hcs & 8 and not pre_hcs & 0x30, 'handoff prior HCS admission')
        if flags > 63:
            check(pre_is in (0,0x400), 'handoff prior interrupt admission')
        status, phase = 'REFUSED', 'PRE_ADMISSION'
    elif site == 0x116:
        check(flags <= 511 and (not flags or pre_hce == 1) and index == raw == 0 and
              (flags < 511 or last_hce == 1), 'handoff pre-write deadline')
        status = 'PRE_WRITE_DEADLINE'
    elif site == 0x117:
        check(flags == 511 and last_hce != 1 and index == 1 and raw == last_hce,
              'handoff final enabled-state drift')
        status, phase = 'ENTRY_DRIFT', 'PRE_WRITE'
    elif site == 0x118:
        check(flags in (1023,2047,4095) and index == raw == 0,
              'handoff timeout after one issued stop')
        status = 'STOP_TIMEOUT'
    elif site == 0x119:
        check(flags == 2047 and last_hce not in (0,1) and index == 1 and raw == last_hce,
              'handoff unexpected poll state')
        status, phase = 'STOP_UNEXPECTED_STATE', 'POLL'
    elif stale_ack and site in (0x11a,0x11b,0x11c):
        check(flags == 8191, 'initial acknowledgement lacks completed stop')
        status, phase = 'STOP_COMPLETE', 'INITIAL_ACK'
    elif post:
        status = 'STOP_COMPLETE' if flags == 8191 else 'COLD_ENTRY'
        if failed:
            check(index == failed.bit_length() and site in (0x104,0x205),
                  'handoff post-state refusal index')
            if index == 2:
                check(raw & 0x39 == (values[22] >> 22) & 0x3f, 'handoff post-state HCS value')
            elif index == 10:
                check(raw != RESET_CTL_EXPECTED if reset_config else not raw & (1 << 31),
                      'handoff post-state reset configuration or legacy direction')
            elif index == 11:
                check(not raw & 1, 'handoff post-state high pin')
            else:
                check(raw != 0, 'handoff post-state nonzero predicate')
            phase = 'POST_CHECKS'
        else:
            check(index == raw == 0, 'handoff unexpected post-state refusal')
    else:
        check(flags == 0 and not any(values[24:]) and
              (values[1] < 2 or site in (0x101,0x102,0x103)),
              'handoff missing transition history')
        status = 'NOT_REACHED'
    return dict(hce_handoff=dict(status=status, flags=flags,
        poll_reads=polls, poll_reads_saturated=polls == 127,
        elapsed_us=elapsed if flags & 512 else None, elapsed_us_saturated=elapsed == 4095,
        pre_hce=pre_hce if flags & 1 else None, pre_hcs=pre_hcs if flags & 2 else None,
        pre_is=pre_is if flags & 32 else None, last_hce=last_hce if flags & 256 else None,
        stop_issued=bool(flags & 512), stop_readback_observed=bool(flags & 1024),
        stop_zero_observed=bool(flags & 2048), stop_completed_in_time=bool(flags & 4096),
        refusal_phase=phase, refusal_condition=(RESET_CONFIG_CHECKS if reset_config else STAGE2_CHECKS)[index-1] if index else None,
        refusal_raw=raw if index else None))


def initial_ack(values):
    """V9 initial UCCS history, separate from the completed HCE stop.

    Neither a committed store nor a zero readback proves event origin or
    write efficacy. A late zero is retained, but never permits progression.
    """
    flags = values[22] >> 28
    observed, failed = values[22] & 0x7ff, (values[22] >> 11) & 0x7ff
    site, stage, rc = values[21] & 0xffff, values[1], values[0]
    index, raw = values[28:30]
    ack_sites = (0x11a,0x11b,0x11c)
    check(flags in (0,1,3,7,15), 'initial acknowledgement prefix')
    if flags:
        check(values[23] & 8191 == 8191 and values[26] == 0x400 and
              observed >= 0xff and not failed & 0xff,
              'initial acknowledgement lacks timely stop and exact completion admission')
    if site in ack_sites:
        check(stage == 2 and observed == 0x7ff and failed == 0,
              'initial acknowledgement failure before all guards')
        if site == 0x11a:
            check(rc == -110 and (
                flags in (1,3) and index == raw == 0 or
                flags == 7 and index == 8 and raw != 0 or
                flags == 15 and index == 8 and raw == 0),
                'initial acknowledgement deadline prefix/readback')
            status = 'DEADLINE'
        elif site == 0x11b:
            check(rc == -16 and flags == 1 and (
                index == 1 and raw != 0 or index == 8 and raw != 0x400),
                'initial acknowledgement final-state drift')
            status = 'DRIFT'
        else:
            check(rc == -5 and flags == 7 and index == 8 and raw != 0,
                  'initial acknowledgement nonzero readback')
            status = 'NONZERO_READBACK'
    elif flags == 1:
        check(stage == 2 and rc == -16 and (
            site == 0x104 and observed == 0x1ff and failed == 0x100 or
            site == 0x205 and observed in (0x3ff,0x7ff) and
            failed == (observed ^ (observed >> 1))),
            'pending completion only precedes AHIT or pin refusal')
        status = 'PENDING_GUARD_REFUSAL'
    elif flags == 15:
        check(observed == 0x7ff and failed == 0 and
              (stage > 2 and site == 0 or stage == 2 and site >> 8 in range(3,9)),
              'completed acknowledgement cannot precede an old guard failure')
        status = 'ZERO_OBSERVED_IN_TIME'
    else:
        check(flags == 0, 'incomplete acknowledgement outside its refusal')
        status = 'NOT_REQUESTED'
    return dict(initial_uccs_ack=dict(flags=flags, status=status,
        pending_admitted=bool(flags & 1), write_committed=bool(flags & 2),
        readback_observed=bool(flags & 4), zero_observed=bool(flags & 8),
        completed_in_time=status == 'ZERO_OBSERVED_IN_TIME',
        refusal_condition=STAGE2_CHECKS[index-1] if site in ack_sites and index else None,
        refusal_raw=raw if site in ack_sites and index else None,
        readback_raw=raw if site in ack_sites and flags & 4 else 0 if flags == 15 else None))


def cfg1_diagnostics(values, *, report_version):
    """V10 asserts bit 0; V11 requires only its ordered write and budget."""
    ordered_selection = report_version >= ORDERED_SELECTION
    outcome, before, after = values[30:33]
    check(outcome in (0, 1, 2, 3) and 0 <= before < 2**32 and 0 <= after < 2**32,
          'CFG1 diagnostic range')
    rc, stage, _, pcs, local, issued = values[:6]
    hce = values[10]
    if outcome == 0:
        check(before == after == hce == local == issued == 0 and rc < 0,
              'unreached CFG1 has reached state')
        # V13 selects inside stage four; stages five and six follow a selection.
        check(report_version < UPSTREAM_LINK or stage <= 4, 'stage six without CFG1 selection')
    elif report_version >= UPSTREAM_LINK:
        # V13 selects at the end of stage four, before lane clocks (stage five)
        # and the stage-six HCE/UIC path.
        check(stage in (4, 5, 6) and pcs == 1 and hce in (0, 1) and
              values[21] == report_modes.tag(report_version) and
              values[22] & 0x3fffff == 0x7ff and values[27:30] == [0, 0, 0],
              'CFG1 reached before its prerequisites')
        if outcome == 2:
            check(stage == 4 and rc == -5 and hce == local == issued == 0 and
                  not any(values[6:10]), 'CFG1 failed-branch contradiction')
        else:
            check(stage in (5, 6) and bool(after & 1) == (outcome == 3),
                  'CFG1 continuing branch contradicts sample')
            if not hce:
                check(stage == 6 or rc < 0, 'stage five ended without an error')
                check(-4095 <= rc < 0 and local == issued == 0 and not any(values[6:10]),
                      'CFG1 passed but impossible pre-HCE result')
            else:
                check(stage == 6, 'HCE started outside stage six')
                if not local:
                    check(issued == 0 and not any(values[6:10]) and rc in (-110, -16),
                          'CFG1 passed but impossible pre-command result')
    else:
        check(stage == 6 and pcs == values[10] == 1 and
              values[21] == report_modes.tag(report_version) and
              values[22] & 0x3fffff == 0x7ff and values[27:30] == [0, 0, 0],
              'CFG1 reached before its prerequisites')
        if outcome == 2 or outcome == 1 and not ordered_selection:
            check(rc == -5 and local == issued == 0 and not any(values[6:10]) and
                  (ordered_selection or bool(after & 1) == (outcome == 2)), 'CFG1 failed-branch contradiction')
        else:
            check(bool(after & 1) == (outcome == 3), 'CFG1 continuing branch contradicts sample')
            if not local:
                check(issued == 0 and not any(values[6:10]) and rc in (-110, -16),
                      'CFG1 passed but impossible pre-command result')
    names = ('UNREACHED', 'BIT_CLEAR_BUDGET_PASS', 'BUDGET_EXPIRED', 'BIT_SET_BUDGET_PASS') if ordered_selection else (
             'UNREACHED', 'READBACK_BIT_CLEAR', 'BUDGET_EXPIRED', 'CHECK_PASSED')
    evaluated = outcome != 0 if ordered_selection else outcome in (2, 3)
    return dict(cfg1=dict(outcome=names[outcome],
        pre=before if outcome else None, post=after if outcome else None,
        budget_evaluated=evaluated,
        budget_expired=(outcome == 2) if evaluated else None))


STORAGE_TEST_LBA = 62305152
STORAGE_GPT_WORD = 0xa0de4421          # first word of the pinned live-GPT SHA-256
STORAGE_ZERO_DIGEST = [int.from_bytes(hashlib.sha256(bytes(4096)).digest()[i:i + 4], 'big')
                       for i in range(0, 32, 4)]
STORAGE_LAST_LBA = 62305279
STORAGE_STEPS = ('NONE', 'ADMIT', 'LIST', 'NOP', 'INIT_SET', 'INIT_POLL', 'TUR', 'CAPACITY',
                 'GPT', 'BLOCK', 'DONE')
STORAGE_FLAGS = ('LIST', 'NOP', 'INIT_SET', 'INIT_CLEAR', 'UNIT_ATTENTION', 'TUR', 'CAPACITY',
                 'GPT_READ', 'GPT_MATCH', 'RANGE', 'BLOCK_READ', 'BLOCK_ZERO', 'UNCERTAIN',
                 'SENSE_UNPARSED', 'TUR_REPEAT', 'TARGET_FAILURE')
STORAGE_DONE = (1 << 13) - 1 & ~(1 << 4 | 1 << 11 | 1 << 12)   # every step flag


def result_size(report_version=1):
    """The sealed module result record for one report version's envelope."""
    return HEADER.size + 12 + report_modes.ENVELOPE.get(report_version, 256) + 32


def storage_read(values, link_completed, header=False, target_failure=False):
    """V14: the fixed read-only storage stage, run only after a completed link.

    V15 (header=True) adds the last response's header bytes 8-11 and two flags:
    SENSE_UNPARSED (a CHECK CONDITION with a nonzero Total EHS Length, sense not
    located) and TUR_REPEAT (the one TEST UNIT READY repeat was attempted).
    V16 (target_failure=True, implies header) accepts response Target Failure
    (0x01) only with CHECK CONDITION and flags it TARGET_FAILURE."""
    header = header or target_failure
    rc, step, flags, polls, sense, status, capacity, gpt = values[38:46]
    digest = values[46:54]
    end = 55 if header else 54
    rsp_header = values[54] if header else 0
    check(-4095 <= rc <= 0 and 0 <= step < len(STORAGE_STEPS) and 0 <= flags < 1 << (16 if target_failure else 15 if header else 13) and
          all(0 <= v < 2**32 for v in (polls, sense, status, capacity, gpt, rsp_header, *digest)),
          'storage field range')
    if not link_completed:
        check(not any(values[38:end]), 'storage stage without a completed link')
        return dict(storage=None)
    check(step >= 1 and (rc == 0) == (step == 10), 'storage step and rc disagree')
    # Flags each step sets on success; UNIT_ATTENTION (TUR) and BLOCK_ZERO (BLOCK) are optional.
    required = {2: 1 << 0, 3: 1 << 1, 4: 1 << 2, 5: 1 << 3, 6: 1 << 5, 7: 1 << 6,
                8: 1 << 7 | 1 << 8 | 1 << 9, 9: 1 << 10}
    # Flags a step can leave on failure; RANGE and BLOCK_READ advance the step.
    optional = {6: 1 << 4 | (1 << 13 | 1 << 14 if header else 0) | (1 << 15 if target_failure else 0),
                8: 1 << 7 | 1 << 8, 10: 1 << 11}
    done = sum(bits for k, bits in required.items() if k < step)
    allowed = done | sum(bits for k, bits in optional.items() if k <= step) | (1 << 12)
    check(flags & done == done and not flags & ~allowed, 'storage flags and step disagree')
    check(not flags & 1 << 12 or rc == -110, 'uncertain slot without a timeout')
    check(not flags & (1 << 8 | 1 << 9) or flags & 1 << 7, 'GPT result without a GPT read')
    check(not flags & 1 << 9 or flags & 1 << 8, 'GPT range without a matching table')
    check(not flags & 1 << 8 or gpt == STORAGE_GPT_WORD, 'GPT match with another table digest')
    check(not flags & 1 << 10 or bool(flags & 1 << 11) == (digest == STORAGE_ZERO_DIGEST),
          'zero flag and block digest disagree')
    # An uncertain slot is the current step's unfinished command: none of its flags.
    check(not flags & 1 << 12 or not flags & ~(done | 1 << 4 | 1 << 12 | 1 << 13 | 1 << 14 | 1 << 15),
          'uncertain slot with the current step completed')
    check(not flags & 1 << 12 or 3 <= step <= 9, 'uncertain slot without a command step')
    # Each field exists only once its producing step ran (the producer's order).
    check((capacity == STORAGE_LAST_LBA) if step > 7 else (capacity == 0 if step < 7 else True),
          'capacity outside its step')
    check(not flags & 1 << 6 or capacity == STORAGE_LAST_LBA, 'capacity flag with another capacity')
    check(step >= 5 or polls == 0, 'device-init polls before the poll step')
    check(step != 5 or not flags & 1 << 12 or polls >= 1, 'uncertain poll without a poll')
    check(step >= 6 or sense == 0, 'sense before TEST UNIT READY')
    check(bool(flags & 1 << 7) or gpt == 0, 'GPT word without a GPT read')
    check(not flags & 1 << 8 or step > 8 or rc == -6, 'matching GPT stopped without a range refusal')
    good = 0x21 << 24
    # A completed command's result fields exist only with its GOOD response.
    check(step != 8 or not flags & 1 << 7 or (rc == -6 and status == good),
          'GPT read evidence without a GOOD read')
    check(step != 7 or capacity == 0 or (rc == -34 and status == good),
          'capacity value without a GOOD capacity read')
    # sense is the latest CHECK CONDITION; a later failing command may overwrite the
    # initial UNIT ATTENTION, so the key is fixed only when every later command succeeded.
    check(step != 10 or bool(sense) == bool(flags & 1 << 4), 'completed stage sense without a unit attention')
    # sense is written only by a CHECK CONDITION: the UNIT ATTENTION, or the stop (-EAGAIN).
    check(not sense or flags & 1 << 4 or rc == -11, 'sense without a CHECK CONDITION')
    check(not flags & 1 << 4 or rc == -11 or sense >> 16 & 15 == 6,
          'unit attention sense replaced without a CHECK CONDITION')
    check(step != 10 or not flags & 1 << 4 or sense >> 16 & 15 == 6, 'unit attention with another sense key')
    # The block digest exists only after its successful read, which ends the stage.
    check(not flags & (1 << 10 | 1 << 11) or step == 10, 'block evidence before the stage ended')
    check(not flags & 1 << 3 or polls >= 1, 'device init cleared without a poll')
    check(not flags & 1 << 11 or flags & 1 << 10, 'zero block without a read')
    if header:
        UA, UNPARSED, REPEAT = 1 << 4, 1 << 13, 1 << 14
        ehs = rsp_header >> 24
        # The header word is written with the status by every completed exchange, from NOP OUT on.
        check(step >= 3 or rsp_header == 0, 'response header before the first command')
        # The repeat follows the first TUR's UNIT ATTENTION (UA set) or its unparsed
        # CHECK CONDITION (UA clear); a first unparsed TUR always takes the repeat.
        check(not flags & UA or flags & REPEAT, 'unit attention without the repeat')
        first_unparsed = bool(flags & REPEAT) and not flags & UA
        check(step != 6 or not flags & UNPARSED or flags & REPEAT, 'unparsed TUR without the repeat')
        # Any other unparsed CHECK CONDITION ended the stage.
        check(not flags & UNPARSED or first_unparsed or rc == -11, 'unparsed sense without its stop')
        check(not first_unparsed or flags & UNPARSED, 'repeat without its CHECK CONDITION')
        # (status, header word) is the sample of the last exchange that completed: ring()
        # records both before any check, and records nothing when it refuses to ring
        # (busy, late) or the slot times out.
        segment = rsp_header & 0xffff
        check(sense < 1 << 20, 'sense wider than its packed key, ASC and ASCQ')
        ocs, response, scsi, upiu = status & 255, status >> 8 & 255, status >> 16 & 255, status >> 24
        # V16: a CHECK CONDITION's sample may carry response Target Failure, which sets
        # the sticky flag; the flag needs a CHECK CONDITION (the first TUR's or the stop).
        TF = 1 << 15
        # V16: the module was compiled with the live table's digest, and range_ok() holds
        # for that exact table, so a GPT match always continues past the range check.
        check(not target_failure or not flags & 1 << 8 or flags & 1 << 9, 'pinned GPT match without its range')
        checks = (0x21020000, 0x21020100) if target_failure else (0x21020000,)
        check(not flags & TF or flags & UA or first_unparsed or rc == -11,
              'target failure without a CHECK CONDITION')
        if step < 3:
            check(status == 0 and rsp_header == 0, 'response sample before the first command')
        elif rc == -11:
            # A stop is a CHECK CONDITION of a SCSI step: RESPONSE, status 2, response 0, OCS 0.
            check(step in (6, 7, 8, 9), 'CHECK CONDITION stop outside a SCSI step')
            check(status in checks, 'CHECK CONDITION stop with another status')
            check(status != 0x21020100 or flags & TF, 'target failure stop without its flag')
            if target_failure and step == 6 and not flags & REPEAT:   # the only CHECK CONDITION
                check(bool(flags & TF) == (status == 0x21020100), 'target failure flag disagrees with the stop')
            if ehs:   # unparsed: no byte past the header was read
                check(flags & UNPARSED and sense == 0, 'unparsed stop with a parsed sense')
            else:     # parsed: nonzero sense needs the length field and an 8-byte record
                check(not flags & UNPARSED or first_unparsed, 'unparsed flag with a parsed stop')
                check(not sense or segment >= 10, 'parsed sense without its data segment')
                # A parsed first-TUR UNIT ATTENTION always takes the repeat.
                check(step != 6 or flags & REPEAT or sense >> 16 != 6, 'unit attention stop without the repeat')
        elif rc in (-16, -110):
            # Refused, late or uncertain: the sample is the previous completed exchange.
            if step == 3:
                check(status == 0 and rsp_header == 0, 'response sample before NOP OUT completed')
            elif step == 4:
                check(status & 0xff00ffff == 0x20000000, 'sample is not the NOP IN')
            elif step == 5 or (step == 6 and not flags & REPEAT):
                check(status & 0xff00ffff == 0x36000000, 'sample is not the query response')
            elif step == 6:
                # The repeat's sample is the first TUR's CHECK CONDITION and its reason.
                check(status in checks, 'repeat sample is not the first CHECK CONDITION')
                check(status != 0x21020100 or flags & TF, 'target failure repeat without its flag')
                if target_failure:   # the sample is the only CHECK CONDITION so far
                    check(bool(flags & TF) == (status == 0x21020100), 'target failure flag disagrees with the repeat sample')
                check(bool(ehs) == first_unparsed, 'repeat sample disagrees with its reason')
                check(not flags & UA or segment >= 10, 'parsed unit attention without its data segment')
            else:
                check(status == 0x21000000, 'sample is not the previous GOOD response')
        elif rc == -71:
            # A completed reply with a wrong type or response (OCS 0).
            expected = {3: 0x20, 4: 0x36, 5: 0x36}.get(step, 0x21)
            # V16 admits response 1 with CHECK CONDITION on a SCSI reply.
            tolerated = target_failure and step >= 6 and response == 1 and scsi == 2
            check(ocs == 0 and (step in (4, 5) or upiu != expected or (response and not tolerated)),
                  'protocol refusal of a well-formed reply')
        elif rc == -5 and step >= 3:
            check(ocs or (step >= 6 and scsi not in (0, 2) and (not target_failure or response == 0)),
                  'transfer error without its status')
        elif rc == -61:
            check(status == 0x21000000, 'residual refusal without a GOOD response')
    if rc == 0:
        # The last command is the block READ: OCS 0, response 0, GOOD, RESPONSE UPIU.
        check(flags & STORAGE_DONE == STORAGE_DONE and capacity == STORAGE_LAST_LBA and
              not flags & 1 << 12 and status == 0x21 << 24 and any(digest),
              'completed storage stage is incomplete')
    if not flags & 1 << 10:
        check(not any(digest), 'block digest without a read')
    block = b''.join(v.to_bytes(4, 'big') for v in digest) if flags & 1 << 10 else None
    return dict(storage=dict(
        rc=rc, step=STORAGE_STEPS[step], completed=rc == 0,
        flags=[name for i, name in enumerate(STORAGE_FLAGS) if flags >> i & 1],
        init_polls=polls, sense=dict(key=sense >> 16 & 15, asc=sense >> 8 & 255, ascq=sense & 255),
        last_status=dict(ocs=status & 255, response=status >> 8 & 255, scsi=status >> 16 & 255,
                         upiu=status >> 24),
        capacity_last_lba_low=capacity, gpt_digest_word=gpt,
        gpt_match=bool(flags & 1 << 8), range_ok=bool(flags & 1 << 9),
        test_lba=STORAGE_TEST_LBA, block_sha256=block.hex() if block else None,
        block_zero=bool(flags & 1 << 11),
        **(dict(response_header=dict(raw=rsp_header, ehs_length=rsp_header >> 24,
                                     device_information=rsp_header >> 16 & 255,
                                     data_segment_length=rsp_header & 0xffff)) if header else {})))


def upstream_link(values):
    """V13: OR of all link-poll IS samples and the one-pass UEC prefix."""
    seen, mask, pa, dl, ntd = values[33:38]
    check(0 <= seen < 2**32 and mask in (0, 1, 3, 7, 15, 31) and
          all(0 <= word < 2**32 for word in (pa, dl)) and 0 <= ntd and not ntd & ~0x70707ff,
          'upstream link field range')
    layers = {}
    for i, ((name, code_mask), word) in enumerate(zip(UEC_RAW, (pa, dl))):
        if mask >> i & 1:
            layers[name] = dict(raw=word, error=bool(word >> 31), code=word & code_mask,
                                reserved_set=bool(word & 0x7fffffff & ~code_mask))
        else:
            check(not word, 'unread UEC word is nonzero')
    for i, (name, shift, code_mask, error_bit, reserved_bit) in enumerate(UEC_PACKED, 2):
        part = (ntd >> shift & code_mask, ntd >> error_bit & 1, ntd >> reserved_bit & 1)
        if mask >> i & 1:
            layers[name] = dict(raw=None, error=bool(part[1]), code=part[0],
                                reserved_set=bool(part[2]))
        else:
            check(not any(part), 'unread UEC word is nonzero')
    if not values[5]:
        check(not seen and not mask, 'link observation before issue')
        return dict(link_poll=None)
    check(not mask or seen & 4, 'UEC read without UIC_ERROR')
    irq = values[7]
    check(irq & ~seen == 0, 'terminal sample outside the observed union')
    # A bit outside UCCS/ULSS/UIC_ERROR ends the poll on that very sample.
    check(seen & ~0x504 == irq & ~0x504, 'refused bits outside the terminal sample')
    pa = layers.get('PA')
    return dict(link_poll=dict(seen=seen, uic_error_seen=bool(seen & 4), uec_read_mask=mask,
        uec=layers, pa_line_reset=bool(pa and pa['error'] and pa['code'] & 0x10)))


def link_irq_diagnostics(values, *, report_version=LINK_IRQ):
    """Interpret terminal link samples saved by the V12/V13 producer."""
    rc, stage, version, pcs, local, issued, before, irq, code, after, hce = values[:11]
    tolerated = 0x504 if report_version >= UPSTREAM_LINK else 0x500
    if not issued:
        check(not any((before, irq, code, after)), 'link words before issue')
        return dict(link_irq=None)

    check(stage == 6 and version >> 28 == 4 and pcs == hce == 1 and local == 6 and
          values[30] in (1, 3) and (before & 0x39) == 8, 'issued link prerequisites')
    unexpected = irq & ~tolerated
    if unexpected:
        check(rc == -5 and code == after == 0, 'unexpected link IRQ refusal')
        return dict(link_irq=dict(branch='UNEXPECTED_STATUS', raw=irq, unexpected_bits=unexpected))
    if not irq:
        check(rc == -110 and code == after == 0, 'link poll without terminal sample')
        if report_version >= UPSTREAM_LINK:
            check(not values[33] & ~0x104, 'link poll timeout after completion or refused bits')
        return dict(link_irq=None)

    check(irq & 0x400 and irq & ~tolerated == 0 and code <= 0xff, 'link completion sample')
    failed = bool(code or after & 0x30 or not after & 1)
    # A successful command can still be followed by a module-level failure.
    if failed:
        check(rc == -5, 'link completion result')
    return dict(link_irq=dict(branch='COMPLETION', raw=irq, unexpected_bits=0))


def result(raw, verified_witness, key, identity, *, report_version=1):
    check(report_version in REPORT_FIELDS, 'unselected module report schema')
    check(len(raw) == result_size(report_version) and len(verified_witness) == HEADER.size+32,
          "incomplete module result")
    check(verified_witness[:40] == b"G030WIT1" + identity and
          hmac.compare_digest(verified_witness[-32:],tag(key,identity,17,verified_witness[:-32])),
          "unverified result witness")
    check(hmac.compare_digest(raw[-32:], tag(key,identity,20,raw[:-32])) and
          raw[:HEADER.size] == b"G030RES1" + verified_witness[8:HEADER.size], "module result binding")
    load, read, size = struct.unpack_from("<III",raw,HEADER.size)
    payload = raw[HEADER.size+12:-32]
    check(size <= len(payload) and not any(payload[size:]) and not (load and (read or size)),
          "module result length")
    if load or read:
        return recovery_result(dict(status="NO_PROOF",load_errno=load,read_errno=read,
                                    report_bytes=size,normal_return=False), raw, report_version)
    numbers = payload[:size]
    fields = REPORT_FIELDS[report_version]
    pattern = rb"(?:0|-?[1-9][0-9]*)(?: (?:0|-?[1-9][0-9]*)){" + str(fields-1).encode() + rb"}\n"
    check(re.fullmatch(pattern, numbers),
          "invalid module status line")
    values = list(map(int, numbers.split()))
    rc,stage,version,pcs,local,issued,before,irq,code,after,hce,count,claimed,triggered,acked,reclaimed,error,usb,release = values[:19]
    check(-(1<<31)<=rc<=0 and -(1<<31)<=error<=0 and all(0<=v<2**32 for v in
          (stage,version,pcs,local,issued,before,irq,code,after,hce,count,claimed,triggered,acked,reclaimed,usb,release))
          and count<=32 and stage<=6 and local<=6 and all(v in (0,1) for v in (pcs,issued,hce,usb,release)),
          "module status range")
    mask = (1<<count)-1
    check(claimed & ~mask == 0 and triggered & ~claimed == 0 and acked & ~triggered == 0 and
          reclaimed & ~claimed == 0 and not (triggered & reclaimed), "impossible slot history")
    facts = dict(operation_errno=-rc,stage=stage,records=count,claimed=claimed,triggered=triggered,
                 acknowledged=acked,reclaimed=reclaimed,usb_covered=bool(usb),usb_released=bool(release),
                 local_commands=local,link_issued=bool(issued),status="NO_PROOF",normal_return=False)
    if report_version >= 2:
        facts.update(usb_diagnostics(values[:21]))
    pre_effect = False
    if report_version >= 3:
        diagnostic = values[:23]
        if report_version >= 4:
            check(0 <= values[21] < 1 << 32 and
                  values[21] & ~0x1ffff == report_modes.tag(report_version),
                  'pre-effect report version tag')
            pre_effect = bool(values[21] & 0x10000)
            diagnostic[21] &= 0xffff
            if pre_effect:
                check(-4095 <= rc < 0 and not any(values[1:19]) and diagnostic[21] == values[22] == 0
                      and 2 < (values[19] & 255) <= 20, 'pre-effect terminal evidence')
        facts.update(stage2_diagnostics(diagnostic, handoff=report_version >= HANDOFF,
                     reset_config=report_version >= RESET_CONFIG,
                     disabled_ucrdy=report_version >= DISABLED_UCRDY,
                     stale_ack=report_version >= STALE_ACK))
        if report_version == 5:
            facts.update(hci_snapshot(values))
        elif report_version >= HANDOFF:
            facts.update(hce_handoff(values, reset_config=report_version >= RESET_CONFIG,
                                     stale_ack=report_version >= STALE_ACK))
        if report_version >= STALE_ACK:
            facts.update(initial_ack(values))
        if report_version >= CFG1:
            facts.update(cfg1_diagnostics(values, report_version=report_version))
        if report_version >= LINK_IRQ:
            facts.update(link_irq_diagnostics(values, report_version=report_version))
        if report_version >= UPSTREAM_LINK:
            facts.update(upstream_link(values))
    storage = report_version >= STORAGE_READ
    if storage:
        facts.update(storage_read(values, link_completed=rc == 0 and not pre_effect,
                                  header=report_version >= STORAGE_HEADER,
                                  target_failure=report_version >= STORAGE_RESPONSE))
    if pre_effect:
        return recovery_result(dict(facts, normal_return=True, return_reason='PRE_EFFECT_REJECTION',
                    control_nonce=hashlib.sha256(raw).digest()), raw, report_version)
    if rc:
        return recovery_result(facts, raw, report_version)
    check(stage == 6 and version>>28 == 4 and pcs == hce == issued == usb == release == 1 and
          local == 6 and (before & 0x39) == 8 and (after & 0x31) == 1 and
          irq & 0x400 and irq & ~(0x504 if report_version >= UPSTREAM_LINK else 0x500) == 0 and
          code == error == reclaimed == 0 and count>0 and
          claimed == triggered == acked == mask, "incomplete successful link or power settlement")
    return recovery_result(dict(facts,status="UFS_LINK_COMPLETED",normal_return=True,
                control_nonce=hashlib.sha256(raw).digest()), raw, report_version)
