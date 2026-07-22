# S22+ FYG8 P2.39 connected D0 prepared pass

Date: 2026-07-23 KST
Tier: D1 normal reboot followed by D0 connected read-only
Status: `PASS_P239_E1B_CONNECTED_D0_PREPARED`
F1 authority: inactive pending one fresh exact approval

## Result

The operator clarified that all preparation before the F1 candidate transfer
was approved. One exact D1 `adb reboot` rotated the historical P2.37 E1A record
out of the retained baseline. Android returned boot-complete with the boot
animation stopped.

A fresh P2.39 manifest and fresh run directory then passed the reusable Device
Action Process v2 connected D0 adapter. The adapter produced one private
prepared binding for the exact E1B candidate, exact Magisk rollback, current
execution closure, target evidence, and clean observation baseline.

No candidate or rollback AP was transferred. Odin was not invoked. D0 requested
no reboot or Download transition and performed no device or partition write.

## D1 Boundary

Before the reboot, a second bounded D0 read confirmed that the retained
baseline still contained one valid P2.37 E1A terminal-success record. The D1
action then:

1. required exactly one connected FYG8 S22+ target;
2. issued `adb reboot` exactly once;
3. observed disconnect and reconnect; and
4. waited for Android boot completion and stopped boot animation.

The first post-reboot read contained no E1 long or UNSAT family and no integrity
issue. The stopped manifest and run directory from the historical-baseline
attempt remain private and were not reused.

## Connected D0 Evidence

The fresh D0 result passed:

- exact target and FYG8 identity;
- Android boot completion and stopped boot animation;
- root verification and the expected unlocked verified-boot state;
- exact current boot and supporting-partition identities;
- absence of an Odin endpoint in Android state;
- exact regular-file candidate and rollback AP identities;
- one allowed AP member, `boot.img.lz4`;
- clean `/proc/last_kmsg` read to EOF with zero E1 family records; and
- current runner, adapter, evidence decoder, and execution-closure binding.

The D0 result is `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Its private
prepared binding preauthorizes only the mandatory exact rollback after an
approved candidate attempt. It cannot authorize F1 by itself.

## Live-Ready Gate

P2.39 is now ready for one exact F1 approval bound to the private prepared
result. Execution must use the reusable live adapter with that exact manifest
and run directory. The approval authorizes one boot-only E1B candidate attempt
and its mandatory Magisk rollback; it does not authorize any other partition,
artifact, target, or retry.

Until that exact approval is supplied, the device remains on healthy Android
and no live candidate action is authorized.

E1B live module insertion and terminal stage `0x3f` remain unproved. Platform
bind, watchdog registration, UDC, ACM bytes, NCM, shell, and Debian remain
separate later rungs.
