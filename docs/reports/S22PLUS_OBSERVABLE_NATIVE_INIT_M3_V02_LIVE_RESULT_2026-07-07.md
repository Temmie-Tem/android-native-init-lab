# S22+ Observable Native-Init M3 v0.2 Live Result - 2026-07-07

## Scope

Executed the guarded attended M3 v0.2 boot-only live gate once, then rolled back
to the pinned Magisk boot-only AP. No recovery, vbmeta, vendor_boot, userdata,
EFS, modem, keymaster, RPMB, or non-boot partition was flashed.

## Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py \
  --live \
  --ack S22PLUS-M3-OBSERVABLE-LIVE-GATE
```

Private run directory:

```text
workspace/private/runs/s22plus_m3_observable_live_gate_20260706T182057Z/
```

## Candidate And Rollback Identities

Candidate:

```text
AP.tar.md5 SHA256=4a07a5b24101db6e74e102498c557d457c751e13d932f9f5604125629f06ce3b
boot.img SHA256=aa66602e49045de5666b390ef7b434e07cd234d59a4503f9bac021d11383f6d0
tar members=['boot.img.lz4']
```

Rollback:

```text
Magisk boot-only AP.tar.md5 SHA256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
tar members=['boot.img.lz4']
```

## Timeline

```text
18:20:57Z  rooted Android preflight passed
18:21:08Z  candidate download-mode target appeared
18:21:10Z  M3 v0.2 candidate Odin flash completed, rc=0
18:21:10Z  candidate observation began
18:21:43Z  Odin download-mode target reappeared during candidate observation
18:23:00Z  rollback download target accepted
18:23:02Z  Magisk boot-only rollback Odin flash completed, rc=0
18:23:34Z  rooted Android rollback verification passed
```

## Candidate Observation

Safety outcome:

```text
candidate_odin_rc=0
magisk_rollback_odin_rc=0
post_rollback_android_ok=1
```

Native-init observability outcome:

```text
ADB during candidate: absent
new host network/NCM links: none
Odin during candidate: absent until candidate_017, then present through the end
pstore files after rollback: []
S22_NATIVE_INIT_OBSERVABLE_M3 in pstore: no
host dmesg tail capture: no useful bytes
```

The target returned to download/Odin visibility roughly 33 seconds after the
candidate observation window began. That is much earlier than the M3 v0.2
programmed `download` reboot after about 90 seconds, so this run must not be
counted as the intended software-download reboot proof.

## Post-Rollback Health

Current Android health after rollback:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
boot_completed=1
verifiedbootstate=orange
boot_recovery=0
Magisk root=uid 0
Odin devices after rollback: none
bootreason=reboot,download
pstore after rollback: empty
```

## Interpretation

This is a recovery-success / native-observation-fail run.

The boot-only flash and rollback path worked exactly as intended, and the device
returned to the rooted Android measurement baseline. However, there is no
authoritative evidence that M3 reached the early `S22_NATIVE_INIT_OBSERVABLE_M3`
marker path:

- no ADB or NCM appeared;
- no new host network interface appeared;
- no pstore/pmsg marker survived;
- download mode returned too early to be the programmed M3 90-second reboot.

The strongest current interpretation is an early boot/download fallback before
observable native init. This could be an initramfs/direct-PID1 execution issue,
an early kernel/userspace panic before `write_markers()`, or a Samsung boot
policy/watchdog path. This run does not yet distinguish those possibilities.

## Next Boundary

Do not immediately flash another S22+ native-init candidate. Per the stop-on-fail
discipline, the next unit should be host-only postmortem/design:

- compare the direct-PID1 boot packaging against the stock/Magisk boot path;
- move any future proof marker earlier than current filesystem setup where
  possible;
- design a smaller marker-only M3.1 candidate only after the postmortem narrows
  why the device re-entered download mode before marker evidence.
