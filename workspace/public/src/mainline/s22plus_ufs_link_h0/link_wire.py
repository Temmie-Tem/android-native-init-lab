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


def result(raw, verified_witness, key, identity):
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
    check(re.fullmatch(rb"(?:0|-?[1-9][0-9]*)(?: (?:0|-?[1-9][0-9]*)){18}\n", numbers),
          "invalid module status line")
    rc,stage,version,pcs,local,issued,before,irq,code,after,hce,count,claimed,triggered,acked,reclaimed,error,usb,release = map(int,numbers.split())
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
    if rc:
        return facts
    check(stage == 6 and version>>28 == 4 and pcs == hce == issued == usb == release == 1 and
          local == 6 and (before & 0x39) == 8 and (after & 0x31) == 1 and
          irq in (0x400,0x500) and code == error == reclaimed == 0 and count>0 and
          claimed == triggered == acked == mask, "incomplete successful link or power settlement")
    return dict(facts,status="UFS_LINK_COMPLETED",normal_return=True,
                control_nonce=hashlib.sha256(raw).digest())
