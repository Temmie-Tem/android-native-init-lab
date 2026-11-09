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
USB_REASONS = ('OK', 'USB_HELD', 'RUN_STATE', 'USB_NODE', 'USB_DEVICE', 'USB_LOCK',
               'USB_DRIVER', 'USB_DATA', 'USB_PM', 'ICC_NODE', 'ICC_PATH', 'ICC_LENGTH',
               'ICC_LOCK', 'ICC_REQUEST', 'BCM_GLOBAL_LOCK', 'BCM_VOTER', 'BCM_LOCK',
               'BCM_PENDING', 'BCM_UNKNOWN', 'BCM_VALUES', 'COVER_CEILING')
USB_LOCKS = {5, 12, 14, 16}


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


def result(raw, verified_witness, key, identity, *, report_version=1):
    check(report_version in (1, 2), 'unselected module report schema')
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
        return dict(status="NO_PROOF",load_errno=load,read_errno=read,report_bytes=size,normal_return=False)
    numbers = payload[:size]
    fields = 19 if report_version == 1 else 21
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
    if report_version == 2:
        facts.update(usb_diagnostics(values))
    if rc:
        return facts
    check(stage == 6 and version>>28 == 4 and pcs == hce == issued == usb == release == 1 and
          local == 6 and (before & 0x39) == 8 and (after & 0x31) == 1 and
          irq in (0x400,0x500) and code == error == reclaimed == 0 and count>0 and
          claimed == triggered == acked == mask, "incomplete successful link or power settlement")
    return dict(facts,status="UFS_LINK_COMPLETED",normal_return=True,
                control_nonce=hashlib.sha256(raw).digest())
