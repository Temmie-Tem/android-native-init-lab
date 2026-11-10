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


def recovery_result(facts, raw, report_version):
    if report_version not in (6, 7, 8):
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
                     'HANDOFF_DEADLINE', 'HANDOFF_DRIFT', 'HANDOFF_TIMEOUT', 'HANDOFF_STATE')
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


def frame(magic, kind, key, identity, first, second, boot, t0, t1):
    check(len(first) == len(second) == 32 and len(boot) == 16 and first != second and
          any(first) and any(second) and any(boot), "late identity fields")
    check(0 < t0 < 120000 and (t1 == 0 or t0 + GAP_MS <= t1 < END_MS), "late uptime fields")
    body = HEADER.pack(magic, identity, first, second, boot, t0, t1)
    return body + tag(key,identity,kind,body)


def witness(raw, key, identity, first, second, boot, t0):
    check(len(raw) == HEADER.size+32, "incomplete late witness")
    t1 = HEADER.unpack_from(raw)[-1]
    check(t1 > 0 and hmac.compare_digest(raw,frame(b"G030WIT1",17,key,identity,first,second,boot,t0,t1)),
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


def stage2_diagnostics(values, *, handoff=False, reset_config=False, disabled_ucrdy=False):
    """Decode observed short-circuit predicates, never infer unobserved reads."""
    rc, stage, version = values[:3]
    site, word = values[21:]
    check(0 <= site < 1 << 16 and 0 <= word < 1 << 28, 'stage-two report word range')
    observed, failed, hcs = word & 0x7ff, (word >> 11) & 0x7ff, word >> 22
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
        check(component in allowed and operation in allowed[component], 'stage-two failure site')
        check(stage == 2 and -4095 <= rc < 0 and not any(values[3:11]),
              'stage-two failure before later hardware')
        fixed_errno = {1:110, 2:19, 3:19, 4:16, 5:16, 7:34, 9:110,
                       11:110, 13:110, 15:34, 17:110, 19:34,
                       21:16, 22:110, 23:16, 24:110, 25:5}
        check(operation not in fixed_errno or rc == -fixed_errno[operation], 'stage-two branch errno')
        if component == 1 and operation <= 3:
            check(observed == failed == 0, 'stage-two early HCI evidence')
            check(version == 0 if operation < 3 else version >> 28 != 4, 'stage-two HCI version')
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


def hce_handoff(values, *, reset_config=False):
    """Versioned stop history; V8 permits UCRDY in disabled-state checks."""
    word, pre_hce, pre_hcs, pre_is, last_hce, index, raw = values[23:]
    check(0 <= word < 1 << 32, 'handoff metadata range')
    flags, polls, elapsed = word & 8191, (word >> 13) & 127, word >> 20
    check(0 <= flags <= 8191 and not flags & (flags + 1) and
          all(0 <= n < 1 << 32 for n in values[24:]) and index <= 11,
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
    elif post:
        status = 'STOP_COMPLETE' if flags == 8191 else 'COLD_ENTRY'
        if failed:
            check(index == failed.bit_length() and site in (0x104,0x205),
                  'handoff post-state refusal index')
            if index == 2:
                check(raw & 0x39 == values[22] >> 22, 'handoff post-state HCS value')
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


def result(raw, verified_witness, key, identity, *, report_version=1):
    check(report_version in (1, 2, 3, 4, 5, 6, 7, 8), 'unselected module report schema')
    check(len(raw) == RESULT_SIZE and len(verified_witness) == HEADER.size+32, "incomplete module result")
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
    fields = {1:19, 2:21, 3:23, 4:23, 5:30, 6:30, 7:30, 8:30}[report_version]
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
                  values[21] & ~0x1ffff == {4:0x40000000, 5:0x50000000, 6:0x60000000, 7:0x70000000, 8:0x80000000}[report_version],
                  'pre-effect report version tag')
            pre_effect = bool(values[21] & 0x10000)
            diagnostic[21] &= 0xffff
            if pre_effect:
                check(-4095 <= rc < 0 and not any(values[1:19]) and diagnostic[21] == values[22] == 0
                      and 2 < (values[19] & 255) <= 20, 'pre-effect terminal evidence')
        facts.update(stage2_diagnostics(diagnostic, handoff=report_version in (6, 7, 8), reset_config=report_version in (7, 8), disabled_ucrdy=report_version == 8))
        if report_version == 5:
            facts.update(hci_snapshot(values))
        elif report_version in (6, 7, 8):
            facts.update(hce_handoff(values, reset_config=report_version in (7, 8)))
    if pre_effect:
        return recovery_result(dict(facts, normal_return=True, return_reason='PRE_EFFECT_REJECTION',
                    control_nonce=hashlib.sha256(raw).digest()), raw, report_version)
    if rc:
        return recovery_result(facts, raw, report_version)
    check(stage == 6 and version>>28 == 4 and pcs == hce == issued == usb == release == 1 and
          local == 6 and (before & 0x39) == 8 and (after & 0x31) == 1 and
          irq in (0x400,0x500) and code == error == reclaimed == 0 and count>0 and
          claimed == triggered == acked == mask, "incomplete successful link or power settlement")
    return recovery_result(dict(facts,status="UFS_LINK_COMPLETED",normal_return=True,
                control_nonce=hashlib.sha256(raw).digest()), raw, report_version)
